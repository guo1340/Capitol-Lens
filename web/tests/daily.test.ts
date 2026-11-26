import {it,expect,vi,afterEach} from 'vitest';
import {readFileSync} from 'node:fs';
import {chat} from '../worker/chat';
const data=JSON.parse(readFileSync(new URL('../public/data/dataset.json',import.meta.url),'utf8'));
const rec=JSON.parse(readFileSync(new URL('../public/data/recommendations.json',import.meta.url),'utf8'));
const env={OPENAI_API_KEY:'fake',ASSETS:{fetch:async(r:Request)=>Response.json(r.url.endsWith('recommendations.json')?rec:data)}} as unknown as Env;
afterEach(()=>vi.unstubAllGlobals());
it('rejects AI sell recommendations without verified holdings',async()=>{
 vi.stubGlobal('fetch',vi.fn(async()=>Response.json({status:'completed',output:[{type:'message',content:[{type:'output_text',text:JSON.stringify({summary:'test',cards:[{ticker:rec.basket[0].ticker,action:'review_sell',reason:'test'}]})}]}]})));
 const r=await chat(new Request('https://test/chat',{method:'POST',body:JSON.stringify({daily:true,plan:true,messages:[{role:'user',content:'Plan'}]})}),env);expect(r.status).toBe(502);
});
it('returns a labelled structured plan for verified research symbols only',async()=>{
 vi.stubGlobal('fetch',vi.fn(async()=>Response.json({status:'completed',output:[{type:'message',content:[{type:'output_text',text:JSON.stringify({summary:'test',cards:[{ticker:rec.basket[0].ticker,action:'watch',reason:'test'}]})}]}]})));
 const r=await chat(new Request('https://test/chat',{method:'POST',body:JSON.stringify({daily:true,plan:true,messages:[{role:'user',content:'Plan'}]})}),env);expect(r.status).toBe(200);const b=await r.json() as any;expect(b.plan.cards[0].action).toBe('watch');expect(b.account.status).toBe('not_requested');
});
