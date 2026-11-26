import {expect,it,vi,afterEach} from 'vitest';
import {normalizePortfolio,portfolio,signRead} from '../worker/webull';
import {createHmac} from 'node:crypto';
afterEach(()=>vi.unstubAllGlobals());
it('does not contact Webull without approved configured credentials',async()=>{const fetch=vi.fn();vi.stubGlobal('fetch',fetch);expect((await portfolio({} as Env)).status).toBe('not_configured');expect(fetch).not.toHaveBeenCalled();});
it('signs GET requests per the documented Webull algorithm',async()=>{
 const h=await signRead('/trading/accounts/list',{},'test-key','test-secret','api.sandbox.webull.com','2026-01-01T00:00:00Z','nonce');
 const message='/trading/accounts/list&host=api.sandbox.webull.com&x-app-key=test-key&x-signature-algorithm=HMAC-SHA1&x-signature-nonce=nonce&x-signature-version=1.0&x-timestamp=2026-01-01T00:00:00Z';
 expect(h['x-signature']).toBe(createHmac('sha1','test-secret&').update(encodeURIComponent(message)).digest('base64'));expect(JSON.stringify(h)).not.toContain('test-secret');
});
it('uses conservative settled cash and identifies unsupported instruments',()=>{
 const p=normalizePortfolio({total_asset_currency:'USD',account_currency_assets:[{currency:'USD',cash_balance:'1000',settled_cash:'700',frozen_amount:'100',held_amount:'20'}]},[{instrument_type:'EQUITY',currency:'USD',symbol:'AAPL',quantity:'2',last_price:'100'},{instrument_type:'OPTION'}],'sandbox');
 expect(p.status).toBe('connected');if(p.status==='connected'){expect(p.cash).toBe(580);expect(p.holdings[0].value).toBe(200);expect(p.unsupported).toBe(1);expect(p.environment).toBe('sandbox');}
});
it('fails closed when settled cash is unknown',()=>{expect(()=>normalizePortfolio({total_asset_currency:'USD',account_currency_assets:[{currency:'USD',cash_balance:'1000'}]},[],'production')).toThrow();});
it('only calls the three allowed read endpoints',async()=>{
 const requests:Request[]=[];vi.stubGlobal('fetch',vi.fn(async(url:string,init:RequestInit)=>{requests.push(new Request(url,init));return Response.json(url.includes('accounts/list')?[{account_id:'id'}]:url.includes('balances/get')?{total_asset_currency:'USD',account_currency_assets:[{currency:'USD',cash_balance:'0',settled_cash:'0',held_amount:'0',frozen_amount:'0'}]}:[]);}));
 expect((await portfolio({WEBULL_APP_KEY:'k',WEBULL_APP_SECRET:'s'} as Env)).status).toBe('connected');expect(requests).toHaveLength(3);expect(requests.every(r=>r.method==='GET'&&new URL(r.url).hostname==='api.sandbox.webull.com')).toBe(true);
});
