"""Manual deep-link/navigation checks; no provider requests or API spending."""
from pathlib import Path
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto('http://127.0.0.1:5173/capitol-lens/manual')
    page.get_by_role('heading', name='How to use Capitol Lens.').wait_for()
    assert page.locator('.manual-section').count() == 8
    page.get_by_role('navigation', name='Manual contents').get_by_role('link', name='4. What if:', exact=False).click()
    page.get_by_role('button', name='Explain Historical what-if test', exact=True).first.hover()
    assert page.get_by_role('tooltip').is_visible()
    page.keyboard.press('Escape')
    page.get_by_role('button', name='Open What if', exact=True).click()
    page.get_by_role('heading', name='What would your money have done?').wait_for()
    assert page.url == 'http://127.0.0.1:5173/capitol-lens/'
    page.go_back()
    page.get_by_role('heading', name='How to use Capitol Lens.').wait_for()
    page.get_by_role('button', name='切换到中文').click()
    page.get_by_role('heading', name='如何使用 Capitol Lens。').wait_for()
    page.reload()
    page.get_by_role('heading', name='如何使用 Capitol Lens。').wait_for()
    assert page.locator('.manual-section').count() == 8
    output = Path(__file__).resolve().parents[1] / 'web/test-output'
    output.mkdir(exist_ok=True)
    page.evaluate('scrollTo(0,0)')
    page.screenshot(path=str(output/'manual-desktop.png'))
    page.set_viewport_size({'width': 390, 'height': 844})
    page.get_by_role('button', name='切换到深色模式').click()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    assert page.get_by_role('button', name='使用手册', exact=True).is_visible()
    page.screenshot(path=str(output/'manual-mobile.png'))
    # Protected production-style routing serves index for the manual after login.
    assert page.request.get('http://127.0.0.1:8787/capitol-lens/manual').status == 401
    page.goto('http://127.0.0.1:8790/login')
    page.goto('http://127.0.0.1:8787/capitol-lens/manual')
    page.get_by_role('heading', name='如何使用 Capitol Lens。').wait_for()
    assert not errors, errors
    print('Manual passed: direct URL, 8 sections, contents links, tooltips, navigation/back/reload, Chinese, mobile dark mode, protected Worker route.')
    browser.close()
