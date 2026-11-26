"""Free, long-horizon research snapshot. No brokerage calls or orders."""
import json, math, time, urllib.request, urllib.error, argparse
from pathlib import Path
from datetime import datetime, timezone, date
ROOT=Path(__file__).resolve().parents[1]
# Explicit diversified research universe, not an index or all US listings.
GROUPS={'Technology':'AAPL MSFT ORCL CSCO IBM ADBE CRM INTC AMD NVDA', 'Healthcare':'JNJ MRK ABBV AMGN GILD BMY MDT ABT', 'Consumer':'PG KO PEP CL KMB COST WMT TGT HD LOW', 'Industrials':'CAT DE HON UPS UNP CSX WM EMR', 'Energy':'XOM CVX COP EOG SLB', 'Utilities':'NEE DUK SO AEP', 'Materials':'LIN APD SHW NUE', 'Communications':'GOOGL META VZ T', 'Consumer discretionary':'MCD SBUX NKE BKNG'}
UNIVERSE=[{'ticker':t,'sector':s} for s,ts in GROUPS.items() for t in ts.split()]
TARGET=ROOT/'web/public/data/recommendations.json'
CACHE=ROOT/'.research-cache'

def get(url,key,ttl=86400):
    CACHE.mkdir(exist_ok=True); p=CACHE/(key+'.json')
    if p.exists() and time.time()-p.stat().st_mtime<ttl:return json.loads(p.read_text())
    time.sleep(.15)
    req=urllib.request.Request(url,headers={'User-Agent':'CapitolLens research guo1340@vt.edu','Accept':'application/json'})
    with urllib.request.urlopen(req,timeout=20) as r: data=json.load(r)
    p.write_text(json.dumps(data));return data

def fact(facts,tags,cutoff,annual=False):
    rows=[]
    for tag in tags:
        for row in facts.get(tag,{}).get('units',{}).get('USD',[]):
            if row.get('form') not in ('10-K','10-Q') or row.get('filed','9999')>=cutoff:continue
            if not isinstance(row.get('val'),(int,float)) or not math.isfinite(row['val']):continue
            if annual:
                if not row.get('start'):continue
                days=(date.fromisoformat(row['end'])-date.fromisoformat(row['start'])).days
                if not 330<=days<=380:continue
            rows.append({**row,'tag':tag})
    return max(rows,key=lambda r:(r['end'],r['filed']),default=None)

def financials(raw,cutoff):
    f=raw.get('facts',{}).get('us-gaap',{})
    profit=fact(f,['OperatingIncomeLoss'],cutoff,True)
    cash=fact(f,['NetCashProvidedByUsedInOperatingActivities'],cutoff,True)
    assets=fact(f,['Assets'],cutoff)
    liabilities=fact(f,['Liabilities'],cutoff)
    if not all([profit,cash,assets,liabilities]):raise ValueError('missing_comparable_financials')
    if assets['val']<=0:raise ValueError('invalid_assets')
    if profit['end']!=cash['end'] or assets['end']!=liabilities['end']:raise ValueError('mismatched_statement_periods')
    # Use matching year-end assets, not a more recent denominator.
    af={tag:{'units':{'USD':[r for r in f.get(tag,{}).get('units',{}).get('USD',[]) if r.get('end')==profit['end']]}} for tag in ['Assets','Liabilities']}
    assets=fact(af,['Assets'],cutoff);liabilities=fact(af,['Liabilities'],cutoff)
    if not assets or not liabilities or assets['val']<=0:raise ValueError('missing_year_end_balance_sheet')
    if (date.fromisoformat(cutoff)-date.fromisoformat(profit['end'])).days>550:raise ValueError('old_financial_statements')
    if profit['val']<=0 or cash['val']<=0:raise ValueError('nonpositive_profit_or_cashflow')
    return {'profitability':profit['val']/assets['val'],'cashGeneration':cash['val']/assets['val'],'liabilitiesRatio':liabilities['val']/assets['val'], 'periodEnd':profit['end'],'filingDate':max(r['filed'] for r in [profit,cash,assets,liabilities]),'facts':[{'tag':r['tag'],'value':r['val'],'filed':r['filed'],'periodEnd':r['end'],'accession':r.get('accn')} for r in [profit,cash,assets,liabilities]]}

def rank(rows):
    for row in rows:
        scores=[]
        for key,sign in [('profitability',1),('cashGeneration',1),('liabilitiesRatio',-1)]:
            v=row[key]*sign; vals=[r[key]*sign for r in rows]
            scores.append(100*(sum(x<v for x in vals)+.5*sum(x==v for x in vals))/len(vals))
        row['score']=round(sum(scores)/3,1)
    return sorted(rows,key=lambda r:(-r['score'],r['ticker']))

def main():
    now=datetime.now(timezone.utc);cutoff=now.date().isoformat();quarter=f'{now.year}-Q{(now.month-1)//3+1}'
    rows=[];gaps=[]
    try: mapping=get('https://www.sec.gov/files/company_tickers.json','tickers',604800);mapping={r['ticker']:r for r in mapping.values()}
    except Exception as e: mapping={};gaps.append({'ticker':'ALL','reason':'issuer_directory_unavailable','detail':type(e).__name__})
    # At most three downloads at a time, below SEC fair-access limits.
    from concurrent.futures import ThreadPoolExecutor
    def prefetch(item):
        try:
            cik=str(mapping[item['ticker']]['cik_str']).zfill(10)
            get(f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json',cik)
        except Exception: pass
    with ThreadPoolExecutor(max_workers=3) as pool: list(pool.map(prefetch,UNIVERSE))
    for item in UNIVERSE:
        t=item['ticker']
        try:
            issuer=mapping[t];cik=str(issuer['cik_str']).zfill(10)
            url=f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json'
            raw=get(url,cik);row={**item,'company':raw.get('entityName',issuer['title']),'sourceUrl':url,**financials(raw,cutoff)}
            rows.append(row)
        except Exception as e:gaps.append({'ticker':t,'reason':str(e) if isinstance(e,ValueError) else 'source_unavailable','detail':type(e).__name__})
        print(t, 'eligible' if rows and rows[-1]['ticker']==t else 'unavailable',flush=True)
    rows=rank(rows)
    old=json.loads(TARGET.read_text()) if TARGET.exists() else {}
    basket=[];counts={}
    if old.get('strategyVersion')=='quality-operating-v1' and old.get('quarter')==quarter and len(old.get('basket',[]))==20:
        # Freeze constituents within quarter, never silently substitute a new stock.
        basket=old['basket'];basketDate=old['basketDate']
    else:
        for row in rows:
            if counts.get(row['sector'],0)>=5:continue
            basket.append({'ticker':row['ticker'],'weight':5});counts[row['sector']]=counts.get(row['sector'],0)+1
            if len(basket)==20:break
        basketDate=cutoff
    payload={'schemaVersion':1,'strategyVersion':'quality-operating-v1','builtAt':now.isoformat(),'asOf':cutoff,'quarter':quarter,'basketDate':basketDate,'nextReview':f'{now.year+1}-01-01' if now.month>=10 else f'{now.year}-{((now.month-1)//3+1)*3+1:02d}-01','universe':UNIVERSE,'rows':rows,'gaps':gaps,'basket':basket,'cashWeight':100-sum(r['weight'] for r in basket),'status':'research_only' if rows else 'unavailable','previousSuccessfulAsOf':old.get('asOf') if old.get('rows') else old.get('previousSuccessfulAsOf')}
    from long_term_value import augment
    payload=augment(payload,mapping)
    if old.get('strategyVersion')==payload['strategyVersion'] and old.get('quarter')==quarter and len(old.get('basket',[]))==20:
        payload['basket']=old['basket'];payload['basketDate']=old['basketDate'];payload['cashWeight']=old['cashWeight']
    TARGET.parent.mkdir(parents=True,exist_ok=True)
    temp=TARGET.with_suffix('.tmp');temp.write_text(json.dumps(payload,ensure_ascii=False,indent=2));temp.replace(TARGET)
    # Immutable daily evidence for prospective review; failed attempts are explicit.
    archive=ROOT/'research_snapshots'/f"{cutoff}-{payload['strategyVersion']}.json";archive.parent.mkdir(exist_ok=True)
    if not archive.exists():archive.write_text(json.dumps(payload,ensure_ascii=False,indent=2))
    print(f"{len(payload['rows'])}/{len(UNIVERSE)} eligible; {len(payload['gaps'])} gaps; backtest {payload['backtest']['status']}")
if __name__=='__main__':main()
