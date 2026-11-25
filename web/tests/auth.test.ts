import { it, expect, vi, afterEach } from 'vitest';
import { authorize } from '../worker/auth';
import worker from '../worker/index';

const request = (path = '/', init: RequestInit = {}) => new Request(`https://api.guopq.com/capitol-lens${path}`, init);
const service = (body: unknown, status = 200) => ({ fetch: vi.fn(async () => Response.json(body, { status })) }) as unknown as Fetcher;
const allowed = () => service({ success: true, data: { email: 'guo1340@vt.edu' } });
const ctx = { waitUntil: vi.fn() } as unknown as ExecutionContext;
const env = (admin = allowed()) => ({ ADMIN: admin, ASSETS: service({ secret: 'protected dataset' }), ENVIRONMENT: 'production', GITHUB_REPOSITORY: 'guo1340/Capitol-Lens', GITHUB_REF: 'main' }) as Env;
const cookie = { Cookie: 'admin_token=test' };
afterEach(() => vi.unstubAllGlobals());

it('does not call admin without a session cookie', async () => {
  const admin = allowed(); expect((await authorize(request(), admin)).status).toBe('unauthorized');
  expect(admin.fetch).not.toHaveBeenCalled();
});
it('forwards only the session cookie and relies on the admin verified email', async () => {
  const admin = allowed();
  expect((await authorize(request('/', { headers: { Cookie: 'other=private; admin_token=test', 'X-Email': 'forged@example.com' } }), admin)).status).toBe('allowed');
  const forwarded = vi.mocked(admin.fetch).mock.calls[0][0] as Request;
  expect(forwarded.headers.get('Cookie')).toBe('admin_token=test');
  expect(forwarded.headers.get('X-Email')).toBeNull();
});
it.each([
  [service({}, 401), 'unauthorized'],
  [service({ success: true, data: { email: 'someone@example.com' } }), 'forbidden'],
  [service({ success: false }), 'unauthorized'],
  [service({}, 500), 'unavailable'],
])('fails closed on rejected or unavailable verification', async (admin, status) => {
  expect((await authorize(request('/', { headers: cookie }), admin as Fetcher)).status).toBe(status);
});
it.each(['/', '/assets/app.js', '/data/dataset.json', '/api/dataset', '/api/status', '/api/quote?symbol=AAPL'])('protects %s before serving content', async path => {
  const bindings = env(); const response = await worker.fetch(request(path), bindings, ctx);
  expect(response.status).toBe(401); expect(bindings.ASSETS.fetch).not.toHaveBeenCalled();
  expect(response.headers.get('Cache-Control')).toBe('private, no-store');
});
it('serves assets only after authorization with private caching', async () => {
  const response = await worker.fetch(request('/api/dataset', { headers: cookie }), env(), ctx);
  expect(response.status).toBe(200); expect(response.headers.get('Cache-Control')).toBe('private, no-store');
});
it('rejects cross-origin refresh before dispatch', async () => {
  const fetchMock = vi.fn(); vi.stubGlobal('fetch', fetchMock);
  const response = await worker.fetch(request('/api/refresh', { method: 'POST', headers: { ...cookie, Origin: 'https://evil.example' } }), env(), ctx);
  expect(response.status).toBe(403); expect(fetchMock).not.toHaveBeenCalled();
});
it('reports missing quote configuration instead of fabricating prices', async () => {
  const response = await worker.fetch(request('/api/quote?symbol=AAPL', { headers: cookie }), env(), ctx);
  expect(response.status).toBe(503);
});
it('validates symbols and queues an authorized refresh', async () => {
  expect((await worker.fetch(request('/api/quote?symbol=../bad', { headers: cookie }), env(), ctx)).status).toBe(400);
  const fetchMock = vi.fn(async () => new Response(null, { status: 204 })); vi.stubGlobal('fetch', fetchMock);
  const bindings = { ...env(), GITHUB_TOKEN: 'test-token' };
  const response = await worker.fetch(request('/api/refresh', { method: 'POST', headers: { ...cookie, Origin: 'https://api.guopq.com' } }), bindings, ctx);
  expect(response.status).toBe(202); expect(fetchMock).toHaveBeenCalledOnce();
});
