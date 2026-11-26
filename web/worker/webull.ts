import { boundedJson } from './http';
export interface Holding { ticker:string; quantity:number; price:number; value:number }
export type Portfolio = { status:'connected'; asOf:string; environment:'production'|'sandbox'; cash:number; holdings:Holding[]; unsupported:number } | {status:'not_configured'|'unavailable'; message:string};
export async function signRead(path:string, query:Record<string,string>, key:string, secret:string,host:string,timestamp:string,nonce:string){
 const signed:Record<string,string>={'x-app-key':key,'x-timestamp':timestamp,'x-signature-algorithm':'HMAC-SHA1','x-signature-version':'1.0','x-signature-nonce':nonce,host};
 const all={...query,...signed};const message=path+'&'+Object.keys(all).sort().map(k=>`${k}=${all[k]}`).join('&');
 const encoded=encodeURIComponent(message).replace(/[!'()*]/g,c=>'%'+c.charCodeAt(0).toString(16).toUpperCase());
 const signingKey=await crypto.subtle.importKey('raw',new TextEncoder().encode(secret+'&'),{name:'HMAC',hash:'SHA-1'},false,['sign']);
 const signature=await crypto.subtle.sign('HMAC',signingKey,new TextEncoder().encode(encoded));
 const {host:_,...headers}=signed;return {...headers,'x-version':'v3','x-signature':btoa(String.fromCharCode(...new Uint8Array(signature)))};
}
const paths=new Set(['/trading/accounts/list','/trading/assets/balances/get','/trading/assets/positions/list']);
async function read(env:Env,path:string,query:Record<string,string>={}){
 if(!paths.has(path))throw Error('Read-only endpoint rejected');
 const host=env.WEBULL_ENVIRONMENT==='production'?'api.webull.com':'api.sandbox.webull.com';
 const headers=await signRead(path,query,env.WEBULL_APP_KEY!,env.WEBULL_APP_SECRET!,host,new Date().toISOString().replace(/\.\d{3}Z$/,'Z'),crypto.randomUUID().replaceAll('-',''));
 const response=await fetch(`https://${host}${path}?${new URLSearchParams(query)}`,{method:'GET',headers:{...headers,...(env.WEBULL_ACCESS_TOKEN?{'x-access-token':env.WEBULL_ACCESS_TOKEN}:{})},signal:AbortSignal.timeout(12000),redirect:'error'});
 if(!response.ok){await response.body?.cancel();throw Error(`Webull read rejected (${response.status}). Check approval, token, and permissions.`);}
 return boundedJson<unknown>(response,1_000_000);
}
const number=(v:unknown)=>{if((typeof v!=='number'&&typeof v!=='string')||v==='')throw Error('Incomplete Webull account data');const n=Number(v);if(!Number.isFinite(n))throw Error('Invalid Webull account data');return n;};
export function normalizePortfolio(balance:any,positions:any,environment:'production'|'sandbox'):Portfolio {
 if(!Array.isArray(positions)||balance?.total_asset_currency!=='USD'||!Array.isArray(balance.account_currency_assets))throw Error('Unsupported Webull response');
 const usd=balance.account_currency_assets.find((r:any)=>r.currency==='USD');if(!usd)throw Error('Missing USD cash');
 const cash=Math.max(0,Math.min(number(usd.cash_balance),number(usd.settled_cash))-Math.max(0,number(usd.frozen_amount))-Math.max(0,number(usd.held_amount)));
 let unsupported=0;const holdings:Holding[]=[];
 for(const r of positions){if(r.instrument_type!=='EQUITY'||r.currency!=='USD'){unsupported++;continue;}const quantity=number(r.quantity),price=number(r.last_price);if(quantity<0||price<=0||typeof r.symbol!=='string'||!/^[A-Z][A-Z0-9.-]{0,9}$/.test(r.symbol)){unsupported++;continue;}holdings.push({ticker:r.symbol,quantity,price,value:quantity*price});}
 return {status:'connected',asOf:new Date().toISOString(),environment,cash,holdings,unsupported};
}
export async function portfolio(env:Env):Promise<Portfolio>{
 if(!env.WEBULL_APP_KEY||!env.WEBULL_APP_SECRET)return {status:'not_configured',message:'Apply for official Webull OpenAPI access, then configure server secrets. No account is connected.'};
 try{const accounts=await read(env,'/trading/accounts/list') as {account_id:string}[];if(!Array.isArray(accounts))throw Error('Unexpected account list');
 const id=env.WEBULL_ACCOUNT_ID||(accounts.length===1?accounts[0].account_id:undefined);if(!id||!accounts.some(a=>a.account_id===id))throw Error('Set WEBULL_ACCOUNT_ID to an authorized stock account.');
 const [balance,positions]=await Promise.all([read(env,'/trading/assets/balances/get',{account_id:id}),read(env,'/trading/assets/positions/list',{account_id:id})]);return normalizePortfolio(balance,positions,env.WEBULL_ENVIRONMENT==='production'?'production':'sandbox');
 }catch(e){return {status:'unavailable',message:e instanceof Error&&e.message.startsWith('Webull read rejected')?e.message:'Webull account could not be verified. Check credentials, account selection, response format and 2FA token.'};}
}
