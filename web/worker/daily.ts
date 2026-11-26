import type { Dataset } from '../src/types';
import { boundedJson } from './http';
import { portfolio } from './webull';
export async function dailyEvidence(env:Env,includeHoldings=false){
 const [r,d]=await Promise.all([env.ASSETS.fetch(new Request('https://internal/data/recommendations.json')),env.ASSETS.fetch(new Request('https://internal/data/dataset.json'))]);
 if(!r.ok||!d.ok)throw Error('Research snapshot unavailable');
 const snapshot=await boundedJson<any>(r,8_000_000);const dataset=await boundedJson<Dataset>(d,24_000_000);
 const account=includeHoldings?await portfolio(env):{status:'not_requested' as const,message:'Holdings not requested'};
 const rows=snapshot.rows as any[];const tickers=new Set<string>(snapshot.basket.map((b:any)=>b.ticker));
 if(account.status==='connected')for(const h of account.holdings)tickers.add(h.ticker);
 const cards=[...tickers].map(ticker=>{const row=rows.find(r=>r.ticker===ticker);const holding=account.status==='connected'?account.holdings.find(h=>h.ticker===ticker):null;
  return {ticker,company:row?.company??dataset.companies[ticker]??ticker,action:holding?'hold':'watch',holding:holding??null,research:row??null,politicians:dataset.trades.filter(t=>!t.excludedReason&&t.ticker===ticker).sort((a,b)=>b.filingDate.localeCompare(a.filingDate)).slice(0,3).map(t=>({...t,politician:dataset.politicians.find(p=>p.id===t.politician)?.name??t.politician})),origin:'rules'};});
 const periods=snapshot.backtest?.periods?.map((p:any)=>({label:p.label,start:p.qualityOnly.start,end:p.qualityOnly.end,qualityReturn:p.qualityOnly.returnPercent,valueReturn:p.qualityValue.returnPercent,spyReturn:p.qualityOnly.spyPercent}));
 return {stale:Date.now()-Date.parse(snapshot.builtAt)>4*86400000,asOf:snapshot.asOf,builtAt:snapshot.builtAt,strategyVersion:snapshot.strategyVersion,defaultRule:'quality_only',valuationUse:'context_only',periods,account,cards,limitations:['Retrospective split, not untouched validation','Today-selected surviving companies','Historical prices, not executable quotes','No taxes or personal loss tolerance assessed']};
}
