"""Regression checks for npm run dev; requires Playwright and Chrome."""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto('http://127.0.0.1:5173/capitol-lens/')
    page.get_by_role('heading', name='See the trades. Find the connections.').wait_for()
    assert 'Local preview' in page.locator('.local-banner').inner_text()
    page.get_by_role('button', name='What if', exact=True).click()
    page.get_by_role('button', name='Run this what-if', exact=True).click()
    page.get_by_text('+9.59%', exact=True).wait_for()
    page.get_by_role('button', name='Refresh data', exact=True).click()
    page.get_by_text('Connect the repository refresh workflow', exact=False).wait_for()
    assert not errors, errors
    # Authorization failure must display a stable error, not reload forever.
    page.route('**/capitol-lens/api/**', lambda route: route.fulfill(status=401, json={'error': 'unauthorized'}))
    navigations = []
    page.on('framenavigated', lambda frame: navigations.append(frame.url))
    page.reload()
    page.get_by_text('Access could not be verified.', exact=False).wait_for()
    page.wait_for_timeout(1000)
    assert len(navigations) == 1, navigations
    print('Dev checks passed: fresh session, data, simulation, refresh, no auth reload loop.')
    browser.close()
