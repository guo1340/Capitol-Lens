from pathlib import Path
import json
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]
with sync_playwright() as p:
 b=p.chromium.launch(channel='chrome',headless=True);page=b.new_page(viewport={'width':1440,'height':1000});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 def api(route):
  path=route.request.url.split('/api/')[-1]
  if path=='dataset':body=json.loads((root/'web/public/data/dataset.json').read_text(encoding='utf-8'))
  elif path=='recommendations':
   source=root/'web/public/data/recommendations.json'
   body=json.loads(source.read_text()) if source.exists() else {'builtAt':'2026-01-01','asOf':'2026-01-01','quarter':'2026-Q1','basketDate':'2026-01-01','nextReview':'2026-04-01','strategyVersion':'test-unavailable','universe':[],'rows':[],'gaps':[],'basket':[],'cashWeight':100,'status':'unavailable'}
  elif path=='session':body={'email':'guo1340@vt.edu','local':True}
  else:body={'environment':'local','chatConfigured':False}
  route.fulfill(json=body)
 page.route('**/capitol-lens/api/**',api)
 page.goto('http://127.0.0.1:5173/capitol-lens/recommendations')
 page.get_by_role('heading',name='Long-term research, fewer decisions').wait_for()
 page.get_by_role('button',name='Explain Quality research score').first.hover();assert page.get_by_role('tooltip').is_visible();page.keyboard.press('Escape')
 page.get_by_role('button',name='切换到中文').click();page.get_by_role('heading',name='长期研究，减少日常决策').wait_for()
 out=root/'web/test-output';out.mkdir(exist_ok=True);page.screenshot(path=str(out/'recommendations-desktop.png'))
 page.set_viewport_size({'width':390,'height':844});page.get_by_role('button',name='切换到深色模式').click();assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
 page.screenshot(path=str(out/'recommendations-mobile.png'));page.reload();page.get_by_role('heading',name='长期研究，减少日常决策').wait_for()
 assert not errors,errors
 b.close();print('Recommendations: deep link, reload, bilingual, tooltip, mobile dark layout passed; API mocked, no trades or paid requests.')
