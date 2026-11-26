"""Free research prices and point-in-time annual-fundamental comparison, not trading."""
import json, math, subprocess
from datetime import date,datetime,timezone
from concurrent.futures import ThreadPoolExecutor
from refresh_recommendations import CACHE, UNIVERSE, financials, rank

def prices(ticker,cutoff):
 p=CACHE/f'price-{ticker}-{cutoff}.json'
 if p.exists():return json.loads(p.read_text())
 end=int(datetime.fromisoformat(cutoff).replace(tzinfo=timezone.utc).timestamp())
 url=f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?period1=1420070400&period2={end}&interval=1d&events=div%2Csplits'
 r=subprocess.run(['curl','-fsS','-A','Mozilla/5.0','--max-time','25',url],capture_output=True,text=True)
 if r.returncode:raise ValueError('price_source_unavailable')
 raw=json.loads(r.stdout)['chart']['result'][0]
 if raw['meta'].get('currency')!='USD':raise ValueError('non_USD_price')
 q=raw['indicators']['quote'][0];adj=raw['indicators']['adjclose'][0]['adjclose'];splits=raw.get('events',{}).get('splits',{})
 splitRows=[{'date':datetime.fromtimestamp(v['date'],timezone.utc).date().isoformat(),'ratio':v['numerator']/v['denominator']} for v in splits.values()]
 result=[]
 for i,ts in enumerate(raw['timestamp']):
  day=datetime.fromtimestamp(ts,timezone.utc).date().isoformat()
  if day>=cutoff:continue
  vals=[q['open'][i],q['close'][i],adj[i]]
  if not all(isinstance(v,(int,float)) and math.isfinite(v) and v>0 for v in vals):continue
  op,cl,ac=vals
  splitFactor=math.prod(x['ratio'] for x in splitRows if x['date']>day)
  result.append({'date':day,'open':op*ac/cl,'close':ac,'rawClose':cl*splitFactor})
 if not result:raise ValueError('missing_prices')
 value={'rows':result,'splits':splitRows,'sourceUrl':url};p.write_text(json.dumps(value));return value

def valuation(raw,history,cutoff,row):
 candidates=[p for p in history['rows'] if p['date']<cutoff]
 if not candidates:raise ValueError('missing_price_before_signal')
 price=candidates[-1]
 if (date.fromisoformat(cutoff)-date.fromisoformat(price['date'])).days>7:raise ValueError('stale_price')
 facts=raw.get('facts',{});shares=[]
 for ns,tag in [('dei','EntityCommonStockSharesOutstanding'),('us-gaap','CommonStockSharesOutstanding')]:
  shares.extend(r for r in facts.get(ns,{}).get(tag,{}).get('units',{}).get('shares',[]) if r.get('filed','9999')<cutoff and r.get('end','9999')<=price['date'] and r.get('val',0)>0)
 if not shares:raise ValueError('missing_published_share_count')
 sh=max(shares,key=lambda r:(r['end'],r['filed']))
 if (date.fromisoformat(price['date'])-date.fromisoformat(sh['end'])).days>200:raise ValueError('old_share_count')
 splitFactor=math.prod(x['ratio'] for x in history['splits'] if sh['end']<x['date']<=price['date'])
 cap=price['rawClose']*sh['val']*splitFactor
 cash=next(f['value'] for f in row['facts'] if f['tag']=='NetCashProvidedByUsedInOperatingActivities')
 if not math.isfinite(cap) or cap<=0:raise ValueError('invalid_market_cap')
 return {'cashYield':cash/cap,'priceDate':price['date'],'price':price['rawClose'],'sharesDate':sh['end'],'sharesFiled':sh['filed'],'marketCapEstimate':cap,'priceSource':history['sourceUrl']}

def selection(raws,histories,cutoff,with_value=True):
 rows=[];gaps=[]
 for item in UNIVERSE:
  t=item['ticker']
  try:
   raw=raws[t];h=histories[t]
   row={**item,'company':raw.get('entityName',t),'sourceUrl':f'https://data.sec.gov/api/xbrl/companyfacts/CIK{int(raw["cik"]):010d}.json',**financials(raw,cutoff)}
   if with_value:row.update(valuation(raw,h,cutoff,row))
   rows.append(row)
  except (KeyError,ValueError,TypeError,StopIteration) as e:gaps.append({'ticker':t,'reason':str(e)})
 rows=rank(rows)
 if with_value:
  for row in rows:
   v=row['cashYield'];vals=[r['cashYield'] for r in rows];valueRank=100*(sum(x<v for x in vals)+.5*sum(x==v for x in vals))/len(vals)
   row['qualityScore']=row['score'];row['score']=round((row['score']+valueRank)/2,1)
  rows.sort(key=lambda r:(-r['score'],r['ticker']))
 basket=[];sectors={}
 for row in rows:
  if sectors.get(row['sector'],0)>=5:continue
  basket.append({'ticker':row['ticker'],'weight':5});sectors[row['sector']]=sectors.get(row['sector'],0)+1
  if len(basket)==20:break
 return rows,basket,gaps

def simulate(raws,histories,start,end,with_value=True,cost=.001):
 spy=histories['SPY']['rows'];days=[r['date'] for r in spy if start<=r['date']<end];lookup={t:{r['date']:r for r in h['rows']} for t,h in histories.items()}
 if not days:raise ValueError('no_benchmark_history')
 cash=10000.;holdings={};curve=[];audit=[];orders=[];lastQuarter=None;peak=10000.;dd=0.;spyPeak=10000.;spyDrawdown=0.;spyUnits=10000/(1+cost)/lookup['SPY'][days[0]]['open'];fees=0.
 for day in days:
  quarter=(day[:4],(int(day[5:7])-1)//3)
  # Signal is computed using only filings and closes strictly before execution day.
  rebalance=quarter!=lastQuarter
  for t in holdings:
   if day not in lookup[t]:raise ValueError(f'missing_held_price:{t}:{day}')
  if rebalance:
   equity=cash+sum(q*lookup[t][day]['open'] for t,q in holdings.items())
   _,basket,gaps=selection(raws,histories,day,with_value);audit.append({'date':day,'eligible':len(UNIVERSE)-len(gaps),'selected':[r['ticker'] for r in basket],'excluded':gaps})
   targets={r['ticker']:equity*.05/lookup[r['ticker']][day]['open'] for r in basket if day in lookup.get(r['ticker'],{})}
   # Sell first then proportionally scale purchases to available cash including costs.
   for t,q in list(holdings.items()):
    sell=max(0,q-targets.get(t,0));amount=sell*lookup[t][day]['open'];cash+=amount*(1-cost);fees+=amount*cost;holdings[t]-=sell
    if sell:orders.append({'date':day,'ticker':t,'side':'sell','amount':amount})
   buys={t:max(0,q-holdings.get(t,0))*lookup[t][day]['open'] for t,q in targets.items()};needed=sum(buys.values())*(1+cost);scale=min(1,cash/needed) if needed else 0
   for t,amount in buys.items():
    amount*=scale;cash-=amount*(1+cost);fees+=amount*cost;holdings[t]=holdings.get(t,0)+amount/lookup[t][day]['open']
    if amount:orders.append({'date':day,'ticker':t,'side':'buy','amount':amount})
   holdings={t:q for t,q in holdings.items() if q>1e-10};lastQuarter=quarter
  value=cash+sum(q*lookup[t][day]['close'] for t,q in holdings.items());peak=max(peak,value);dd=max(dd,(peak-value)/peak)
  spyValue=spyUnits*lookup['SPY'][day]['close'];spyPeak=max(spyPeak,spyValue);spyDrawdown=max(spyDrawdown,(spyPeak-spyValue)/spyPeak)
  curve.append({'date':day,'value':round(value,2),'spy':round(spyUnits*lookup['SPY'][day]['close'],2)})
 years=(date.fromisoformat(days[-1])-date.fromisoformat(days[0])).days/365.25
 final=curve[-1];return {'start':days[0],'end':days[-1],'returnPercent':(final['value']/10000-1)*100,'spyPercent':(final['spy']/10000-1)*100,'annualizedPercent':((final['value']/10000)**(1/years)-1)*100 if years else None,'spyDrawdownPercent':spyDrawdown*100,'drawdownPercent':dd*100,'costs':fees,'orderCount':len(orders),'curve':curve[::21]+[curve[-1]],'audit':audit}

def augment(payload,mapping):
 cutoff=payload['asOf'];raws={};histories={};errors={}
 for item in UNIVERSE:
  try:raws[item['ticker']]=json.loads((CACHE/(str(mapping[item['ticker']]['cik_str']).zfill(10)+'.json')).read_text())
  except Exception:pass
 def download(t):
  try:return t,prices(t,cutoff),None
  except Exception as e:return t,None,type(e).__name__+':'+str(e)
 with ThreadPoolExecutor(max_workers=3) as pool:
  for t,h,e in pool.map(download,[r['ticker'] for r in UNIVERSE]+['SPY']):
   if h:histories[t]=h
   else:errors[t]=e
 rows,basket,gaps=selection(raws,histories,cutoff,False)
 for row in rows:
  try:row.update(valuation(raws[row['ticker']],histories[row['ticker']],cutoff,row))
  except (ValueError,KeyError,StopIteration):row['valuationUnavailable']=True
 payload.update({'strategyVersion':'quality-baseline-v3','rows':rows,'basket':basket,'basketDate':cutoff,'cashWeight':100-sum(r['weight'] for r in basket),'gaps':gaps,'priceErrors':errors,'backtest':{'status':'unavailable'}})
 try:
  payload['backtest']={'status':'available','qualityValue':simulate(raws,histories,'2018-01-01',cutoff),'qualityOnly':simulate(raws,histories,'2018-01-01',cutoff,False),'higherCosts':simulate(raws,histories,'2018-01-01',cutoff,True,.0025),'costPercent':.1,'universeBias':'Today-selected survivors; not historical market membership. Exploratory, not out-of-sample validation.'}
  payload['backtest']['periods']=[{'label':label,'qualityOnly':simulate(raws,histories,start,end,False),'qualityValue':simulate(raws,histories,start,end,True)} for label,start,end in [('development','2018-01-01','2022-01-01'),('retrospective_test','2022-01-01',cutoff)]]
  payload['backtest']['testCaveat']='Retrospective split after inspecting full-period results. Not an untouched holdout; no parameters were tuned to this split.'
 except Exception as e:payload['backtest']={'status':'unavailable','reason':str(e)}
 return payload
