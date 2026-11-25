"""Browser smoke checks against the two local Wrangler processes (requires Playwright)."""
from pathlib import Path
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
    page.set_default_timeout(15000)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    assert page.goto('http://127.0.0.1:8787/capitol-lens/').status == 401
    assert page.request.get('http://127.0.0.1:8787/capitol-lens/data/dataset.json').status == 401
    page.goto('http://127.0.0.1:8790/login')
    page.get_by_role('heading', name='See the trades. Find the connections.').wait_for()
    output = Path(__file__).resolve().parents[1] / 'web/test-output'
    output.mkdir(exist_ok=True)
    page.screenshot(path=str(output / 'desktop-light.png'), full_page=True)
    page.get_by_role('button', name='Explain Public disclosure', exact=True).first.hover()
    assert page.get_by_role('tooltip').is_visible()
    page.keyboard.press('Escape')
    page.get_by_role('button', name='Switch to dark mode').click()
    page.screenshot(path=str(output / 'desktop-dark.png'), full_page=True)
    page.get_by_role('button', name='Word help', exact=True).click()
    page.get_by_role('textbox', name='Search dictionary').fill('return')
    page.get_by_role('dialog').get_by_role('button', name='Explain Return', exact=True).hover()
    assert page.get_by_role('tooltip').is_visible()
    page.get_by_role('button', name='Close word help').click()
    page.get_by_role('button', name='Stock story', exact=True).click()
    page.get_by_role('button', name='Get latest quote', exact=True).click()
    page.get_by_text('The latest-price provider has not been configured.', exact=False).wait_for()
    page.get_by_role('button', name='What if', exact=True).click()
    page.get_by_role('button', name='Run this what-if', exact=True).click()
    page.get_by_text('+9.59%', exact=True).wait_for()
    page.screenshot(path=str(output / 'what-if.png'), full_page=True)
    page.get_by_role('combobox', name='Purchase rule').select_option('0.02-initial')
    page.get_by_text('Settings changed. Run again to update these results.').wait_for()
    page.get_by_role('button', name='Run this what-if', exact=True).click()
    page.get_by_text('+8.37%', exact=True).wait_for()
    page.set_viewport_size({'width': 390, 'height': 844})
    page.get_by_role('button', name='Explore trades', exact=True).click()
    page.screenshot(path=str(output / 'mobile.png'), full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Horizontal page overflow'
    assert not errors, errors
    print('Browser checks passed: auth, themes, tooltips, dictionary, stock, what-if, mobile.')
    browser.close()
