import { it, expect, vi, afterEach } from 'vitest';
import { glossary } from '../src/glossary';
import { translate } from '../src/translations';
import { chat } from '../worker/chat';
import worker from '../worker/index';
import { readFileSync } from 'node:fs';
import { gunzipSync } from 'node:zlib';

afterEach(() => vi.unstubAllGlobals());
it('translates every dictionary title and explanation', () => {
  for (const entry of Object.values(glossary)) {
    expect(translate(entry.title, 'zh-CN')).not.toBe(entry.title);
    expect(translate(entry.text, 'zh-CN')).not.toBe(entry.text);
    expect(translate(entry.text, 'en')).toBe(entry.text);
  }
});
it('preserves stock identifiers and translates dynamic labels', () => {
  expect(translate('NVDA', 'zh-CN')).toBe('NVDA');
  expect(translate('27 days', 'zh-CN')).toBe('27 天');
  expect(translate('Pelosi · NVDA · filed 2025-01-21', 'zh-CN')).toBe('Pelosi · NVDA · 披露于 2025-01-21');
});
it('provides a language switch on the protected login page', async () => {
  const response = await worker.fetch(new Request('https://www.guopq.com/capitol-lens/?lang=zh-CN', { headers: { Accept: 'text/html' } }), {} as Env, {} as ExecutionContext);
  expect(response.status).toBe(401);
  expect(await response.text()).toContain('打开 guopq 管理后台');
  expect(response.headers.get('Set-Cookie')).toContain('capitol-language=zh-CN');
});
it('sends the selected Chinese language to OpenAI without altering evidence', async () => {
  const data = JSON.parse(gunzipSync(readFileSync(new URL('./historical-fixture.json.gz', import.meta.url))).toString());
  const provider = vi.fn(async () => Response.json({ status: 'completed', output: [{ type: 'message', content: [{ type: 'output_text', text: '历史数据截至 2025 年底。[D1]' }] }] }));
  vi.stubGlobal('fetch', provider);
  const env = { OPENAI_API_KEY: 'test-only', ASSETS: { fetch: async () => Response.json(data) } } as unknown as Env;
  const response = await chat(new Request('https://example.test', { method: 'POST', body: JSON.stringify({ language: 'zh-CN', messages: [{ role: 'user', content: '请总结数据' }] }) }), env);
  expect(response.status).toBe(200);
  const options = (provider.mock.calls[0] as unknown as [string, RequestInit])[1];
  const payload = JSON.parse(options.body as string);
  expect(payload.instructions).toContain('Respond in Simplified Chinese');
  expect(payload.input[0].content).toContain('2025-12-31');
});
