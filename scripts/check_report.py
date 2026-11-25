"""Optional local browser QA; requires playwright and an installed Chrome."""
from pathlib import Path
import sys
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parents[1]
report = root / (sys.argv[1] if len(sys.argv)>1 else 'output/report.html')
with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 1100}, device_scale_factor=1)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(report.as_uri())
    page.screenshot(path=str(report.parent / 'report-desktop.png'))
    assert page.locator('details').count() > 0
    page.locator('summary').first.click()
    assert page.locator('details').first.get_attribute('open') is not None
    page.set_viewport_size({'width': 390, 'height': 844})
    page.evaluate('scrollTo(0, 0)')
    page.screenshot(path=str(report.parent / 'report-mobile.png'))
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    assert not errors, errors
    browser.close()
print('Report renders at desktop/mobile widths; expandable ledgers work; no page errors.')
