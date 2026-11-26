import json
from pathlib import Path
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]
with sync_playwright() as p:
 b=p.chromium.launch(channel='chrome',headless=True);page=b.new_page();calls=[]; state={'version':1,'denied':False}
 def api(route):
  path=route.request.url.split('/api/')[-1];calls.append(path)
  if state['denied']:route.fulfill(status=401,json={'error':'unauthorized'});return
  if path in ('dataset','dataset-version','recommendations'):body=json.loads((root/f'web/public/data/{path}.json').read_text(encoding='utf-8'))
  elif path=='status':body={'environment':'local','chatConfigured':False}
  else:body={'email':'guo1340@vt.edu'}
  if path=='dataset-version':body['version']+=str(state['version'])
  route.fulfill(json=body)
 page.route('**/capitol-lens/api/**',api)
 page.goto('http://127.0.0.1:5173/capitol-lens/recommendations');page.get_by_role('heading',name='Long-term research, fewer decisions').wait_for();assert 'dataset' not in calls,calls
 page.get_by_role('button',name='Explore trades',exact=True).click();page.get_by_role('heading',name='See the trades. Find the connections.').wait_for();assert calls.count('dataset')==1,calls
 page.reload();page.get_by_role('heading',name='See the trades. Find the connections.').wait_for();assert calls.count('dataset')==1,calls;assert calls.count('dataset-version')==2,calls
 state['version']=2;page.reload();page.get_by_role('heading',name='See the trades. Find the connections.').wait_for();assert calls.count('dataset')==2,calls
 state['denied']=True;page.reload();page.get_by_role('button',name='Try again').wait_for();assert not page.get_by_role('heading',name='See the trades. Find the connections.').count();assert calls.count('dataset')==2
 print('PASS: recommendation loads no politician dataset; first Explore loads once; refresh validates manifest and reuses IndexedDB.');b.close()
