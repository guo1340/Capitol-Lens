"""Mocked browser checks. No credentials, brokerage orders or paid AI calls."""
import json
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright
root = Path(__file__).resolve().parents[1]
rec = json.loads((root/'web/public/data/recommendations.json').read_text(encoding='utf-8'))
row = next(r for r in rec['rows'] if r.get('price'))
card = dict(ticker=row['ticker'], company=row['company'], action='watch', origin='rules', research=row, politicians=[])
with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True)
    page = browser.new_page(viewport={'width':1440,'height':1000})
    calls = []
    account = dict(status='connected',environment='production',asOf=datetime.now(timezone.utc).isoformat(),cash=1000,holdings=[dict(ticker=row['ticker'],quantity=2,price=row['price'],value=2*row['price'])],unsupported=0)
    def api(route):
        path=route.request.url.split('/api/')[-1];calls.append(path)
        if path=='status': body={'environment':'local','chatConfigured':True}
        elif path=='daily': body=dict(asOf=rec['asOf'],builtAt=rec['builtAt'],strategyVersion=rec['strategyVersion'],cards=[card],periods=[])
        elif path=='webull/portfolio': body=account
        elif path=='chat': body=dict(answer='Mock assessment',plan=dict(summary='Mock assessment',cards=[dict(ticker=row['ticker'],action='watch',reason='Mock evidence; uncertain future.')]),cards=[card],account=account)
        else: body={'email':'guo1340@vt.edu'}
        route.fulfill(json=body)
    page.route('**/capitol-lens/api/**',api)
    page.goto('http://127.0.0.1:5173/capitol-lens/')
    page.get_by_role('heading',name='Your long-term decision desk').wait_for()
    assert 'dataset' not in calls and 'chat' not in calls
    page.locator('.decision-card').click()
    assert page.get_by_role('button',name='Save draft — no order').is_disabled()
    page.keyboard.press('Escape');assert not page.locator('dialog.decision-dialog').is_visible()
    page.get_by_role('button',name='Connect / refresh Webull').click()
    page.get_by_text('Conservative cash estimate;',exact=False).wait_for()
    page.locator('.decision-card').click()
    dialog=page.locator('dialog.decision-dialog')
    dialog.get_by_role('combobox').nth(1).select_option('usd')
    dialog.get_by_role('spinbutton').fill('1001')
    assert dialog.get_by_role('button',name='Save draft — no order').is_disabled()
    dialog.get_by_role('spinbutton').fill('100')
    dialog.get_by_role('button',name='Save draft — no order').click()
    page.locator('.decision-card').click()
    dialog.get_by_role('combobox').nth(0).select_option('sell')
    dialog.get_by_role('combobox').nth(1).select_option('shares')
    dialog.get_by_role('spinbutton').fill('3')
    assert dialog.get_by_role('button',name='Save draft — no order').is_disabled()
    dialog.get_by_role('spinbutton').fill('1')
    dialog.get_by_role('button',name='Save draft — no order').click()
    page.get_by_role('button',name='Generate AI recommendations').click()
    page.get_by_text('AI assessment',exact=True).wait_for()
    assert not any('order' in call for call in calls)
    page.screenshot(path=str(root/'output/daily-desktop.png'),full_page=True)
    page.locator('.language-button').click()
    page.get_by_role('heading',name='你的长期决策工作台').wait_for()
    page.set_viewport_size({'width':390,'height':844})
    page.evaluate("document.documentElement.dataset.theme='dark'")
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), 'Mobile overflow'
    page.screenshot(path=str(root/'output/daily-mobile.png'),full_page=True)
    print('PASS: lazy homepage, dialog/Escape, unverified draft block, cash/share limits, AI merge, Chinese mobile/dark, no order calls')
    browser.close()

