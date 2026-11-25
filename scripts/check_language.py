"""Exercise both site languages. AI and quote replies are mocked; no API spending."""
from pathlib import Path
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True)
    page = browser.new_page(viewport={'width': 1440, 'height': 1000})
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.route('**/api/status', lambda route: route.fulfill(json={'chatConfigured': True, 'environment': 'local'}))
    page.route('**/api/quote?*', lambda route: route.fulfill(status=503, json={'message': 'The latest-price provider has not been configured. Historical prices remain available.'}))
    page.goto('http://127.0.0.1:5173/capitol-lens/')
    page.get_by_role('button', name='切换到中文', exact=True).click()
    page.get_by_role('heading', name='看懂交易，发现关联。').wait_for()
    assert page.locator('html').get_attribute('lang') == 'zh-CN'
    page.get_by_role('button', name='解释：公开披露').first.hover()
    assert '向公众报告' in page.get_by_role('tooltip').inner_text()
    page.keyboard.press('Escape')
    page.get_by_role('button', name='打开术语词典').click()
    page.get_by_role('textbox', name='搜索术语词典').fill('收益')
    page.get_by_role('dialog').get_by_text('收益率', exact=True).wait_for()
    page.get_by_role('button', name='关闭术语词典').click()
    page.get_by_role('button', name='个股分析', exact=True).click()
    page.get_by_role('button', name='获取最新报价', exact=True).click()
    page.get_by_text('最新报价服务尚未配置，历史价格仍可查看。', exact=True).wait_for()
    page.get_by_role('button', name='模拟投资', exact=True).click()
    page.get_by_role('button', name='运行模拟', exact=True).click()
    page.get_by_text('+9.59%', exact=True).wait_for()
    page.get_by_role('button', name='与 AI 对话', exact=True).click()
    seen = []
    def answer(route):
        seen.append(route.request.post_data_json)
        route.fulfill(json={'answer': '测试回答：收益率不代表未来表现。数据截至 2025 年底。[D1]', 'model': 'mock-ui-test', 'sources': [{'id': 'D1', 'label': 'Dataset · 2024-01-01 to 2025-12-31'}]})
    page.route('**/api/chat', answer)
    page.get_by_role('button', name='请用简单的话解释我的模拟投资结果。', exact=True).click()
    page.get_by_role('button', name='发送问题', exact=True).click()
    page.get_by_text('测试回答：', exact=False).wait_for()
    assert seen[0]['language'] == 'zh-CN'
    assert seen[0]['scenario']['initial'] == 10000
    page.get_by_role('button', name='解释：收益率', exact=True).hover()
    assert '百分比变化' in page.get_by_role('tooltip').inner_text()
    page.keyboard.press('Escape')
    page.reload()
    page.get_by_role('heading', name='看懂交易，发现关联。').wait_for()
    output = Path(__file__).resolve().parents[1] / 'web/test-output'
    output.mkdir(exist_ok=True)
    page.screenshot(path=str(output/'chinese-desktop.png'), full_page=True)
    page.set_viewport_size({'width': 390, 'height': 844})
    page.get_by_role('button', name='切换到深色模式').click()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.screenshot(path=str(output/'chinese-mobile.png'))
    page.get_by_role('button', name='Switch to English').click()
    page.get_by_role('heading', name='See the trades. Find the connections.').wait_for()
    assert page.locator('html').get_attribute('lang') == 'en'
    assert not errors, errors
    print('Language checks passed: all tabs, glossary, dates, errors, AI language, unchanged simulation, persistence, mobile, English switch-back.')
    browser.close()
