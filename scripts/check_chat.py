"""Chat UI checks with explicitly mocked AI responses; never spends API credits."""
from pathlib import Path
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    status = {'chatConfigured': False, 'quoteConfigured': False, 'refreshConfigured': False, 'repository': None, 'environment': 'local'}
    page.route('**/api/status', lambda route: route.fulfill(json=status))
    page.goto('http://127.0.0.1:5173/capitol-lens/')
    page.get_by_role('button', name='Chat with AI', exact=True).click()
    page.get_by_text('Chat is not connected yet.', exact=False).wait_for()
    assert page.get_by_role('button', name='Send question').is_disabled()
    status['chatConfigured'] = True
    page.reload()
    page.get_by_role('button', name='Chat with AI', exact=True).click()
    seen = []
    def answer(route):
        seen.append(route.request.post_data_json)
        route.fulfill(json={'answer': 'Test response: historical data ends in 2025. Return [D1]. Review NVDA [S1].', 'model': 'mock-ui-test', 'sources': [{'id': 'D1', 'label': 'Dataset 2024–2025'}, {'id': 'S1', 'label': 'NVDA history', 'ticker': 'NVDA'}]})
    page.route('**/api/chat', answer)
    page.get_by_role('button', name='Explain my what-if result in everyday language.', exact=True).click()
    page.get_by_role('button', name='Send question', exact=True).click()
    page.get_by_text('Test response:', exact=False).wait_for()
    assert seen[0]['scenario']['initial'] == 10000
    assert seen[0]['messages'][-1]['role'] == 'user'
    page.get_by_role('button', name='Explain Return', exact=True).hover()
    assert page.get_by_role('tooltip').is_visible()
    page.keyboard.press('Escape')
    output = Path(__file__).resolve().parents[1] / 'web/test-output'
    output.mkdir(exist_ok=True)
    page.screenshot(path=str(output / 'chat-desktop.png'))
    page.get_by_role('button', name='[S1] NVDA history', exact=True).click()
    page.get_by_role('heading', name='Every stock has a story.').wait_for()
    page.get_by_role('button', name='Chat with AI', exact=True).click()
    page.get_by_text('Test response:', exact=False).wait_for()
    page.unroute('**/api/chat')
    page.route('**/api/chat', lambda route: route.fulfill(status=502, json={'message': 'Test: API credits exhausted.'}))
    page.get_by_label('Your question', exact=True).fill('Another question')
    page.get_by_role('button', name='Send question', exact=True).click()
    page.get_by_role('alert').wait_for()
    assert page.get_by_label('Your question', exact=True).input_value() == 'Another question'
    page.get_by_role('button', name='New chat', exact=True).click()
    assert page.get_by_text('Test response:', exact=False).count() == 0
    page.get_by_role('button', name='Switch to dark mode').click()
    page.set_viewport_size({'width': 390, 'height': 844})
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.screenshot(path=str(output / 'chat-mobile.png'))
    assert not errors, errors
    print('Chat UI passed: missing key, mocked reply, scenario sharing, sources, help, persistence, errors, clear, mobile dark mode.')
    browser.close()
