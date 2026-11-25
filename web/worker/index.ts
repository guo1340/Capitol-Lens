import { translate, type Language } from '../src/translations';
import { authorize } from './auth';
import { boundedJson, json } from './http';
import { chat } from './chat';

const BASE = '/capitol-lens';
const securityHeaders = {
  'Cache-Control': 'private, no-store', 'X-Content-Type-Options': 'nosniff',
  'Referrer-Policy': 'same-origin', 'X-Frame-Options': 'DENY',
  'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; worker-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
};
function secured(response: Response): Response {
  const headers = new Headers(response.headers);
  for (const [key, value] of Object.entries(securityHeaders)) headers.set(key, value);
  return new Response(response.body, { status: response.status, headers });
}
async function asset(env: Env, path: string): Promise<Response> {
  return env.ASSETS.fetch(new Request(`https://capitol-lens.internal${path}`));
}
export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);
    if (url.pathname !== BASE && !url.pathname.startsWith(`${BASE}/`)) return json({ error: 'Not found' }, 404);
    const path = url.pathname.slice(BASE.length) || '/';
    const auth = await authorize(request, env.ADMIN);
    if (auth.status !== 'allowed') {
      const status = auth.status === 'forbidden' ? 403 : auth.status === 'unavailable' ? 503 : 401;
      if (path.startsWith('/api/') || !request.headers.get('Accept')?.includes('text/html')) return json({ error: auth.status }, status);
      const local = String(env.ENVIRONMENT) === 'local';
      const language: Language = (url.searchParams.get('lang') ?? request.headers.get('Cookie')?.match(/(?:^|;\s*)capitol-language=([^;]+)/)?.[1]) === 'zh-CN' ? 'zh-CN' : 'en';
      const l = (text: string) => translate(text, language);
      const login = local ? 'http://127.0.0.1:8790/login' : 'https://admin.guopq.com/login';
      return secured(new Response(`<!doctype html><html lang="${language}"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Capitol Lens · ${language === 'zh-CN' ? '私人访问' : 'Private access'}</title><style>body{font:18px/1.7 system-ui;background:#101822;color:#edf4fa;max-width:580px;margin:15vh auto;padding:24px}a{color:#89d8ca}h1{font-size:38px}</style><h1>Capitol Lens</h1><p>${l(status === 503 ? 'Your admin session could not be checked. Please retry shortly.' : status === 403 ? 'This account does not have access to Capitol Lens.' : 'Use your existing guopq admin session to open your research workspace.')}</p><p><a href="${login}">${l('Open guopq admin')}</a></p><p>${l('After signing in, return here and reload.')}</p><a href="?lang=${language === 'en' ? 'zh-CN' : 'en'}">${language === 'en' ? '中文' : 'English'}</a>${local ? '<p>' + l('Local development preview: uses a test identity, not your production session.') + '</p>' : ''}</html>`, { status, headers: { 'Content-Type': 'text/html; charset=utf-8', 'Set-Cookie': `capitol-language=${language}; Path=/capitol-lens; SameSite=Lax${url.protocol === 'https:' ? '; Secure' : ''}` } }));
    }
    if (request.method === 'POST' && request.headers.get('Origin') !== url.origin) return json({ error: 'Cross-origin action rejected' }, 403);
    try {
      if (path === '/api/chat' && request.method === 'POST') return await chat(request, env);
      if (path === '/api/session') return json({ email: auth.email, local: String(env.ENVIRONMENT) === 'local' });
      if (path === '/api/status') return json({ chatConfigured: Boolean(env.OPENAI_API_KEY), quoteConfigured: Boolean(env.FINNHUB_API_KEY), refreshConfigured: Boolean(env.GITHUB_TOKEN && env.GITHUB_REPOSITORY), repository: env.GITHUB_REPOSITORY || null, environment: env.ENVIRONMENT });
      if (path === '/api/dataset' && request.method === 'GET') return secured(await asset(env, '/data/dataset.json'));
      if (path === '/api/quote' && request.method === 'GET') {
        const symbol = (url.searchParams.get('symbol') ?? '').toUpperCase();
        if (!/^[A-Z][A-Z0-9.\-]{0,9}$/.test(symbol)) return json({ error: 'Invalid stock symbol' }, 400);
        if (!env.FINNHUB_API_KEY) return json({ error: 'provider_not_configured', message: 'The latest-price provider has not been configured. Historical prices remain available.' }, 503);
        const cacheKey = new Request(`https://capitol-lens.internal/quotes/${symbol}`);
        const cache = await caches.open('capitol-lens-quotes');
        const cached = await cache.match(cacheKey);
        if (cached) return secured(cached);
        const response = await fetch(`https://finnhub.io/api/v1/quote?symbol=${encodeURIComponent(symbol)}`, { headers: { 'X-Finnhub-Token': env.FINNHUB_API_KEY }, signal: AbortSignal.timeout(10_000) });
        if (!response.ok) return json({ error: 'provider_unavailable', message: response.status === 429 ? 'The price provider’s request limit was reached. Try again later.' : 'The price provider could not return this stock.' }, 502);
        const quote = await boundedJson<{ c?: number; t?: number; dp?: number; pc?: number }>(response);
        if (!quote.c || !quote.t || !Number.isFinite(quote.c) || quote.c <= 0 || !Number.isFinite(quote.t)) return json({ error: 'quote_unavailable', message: 'No valid latest quote was returned for this stock.' }, 502);
        const body = { symbol, price: quote.c, asOf: new Date(quote.t * 1000).toISOString(), fetchedAt: new Date().toISOString(), changePercent: quote.dp ?? null, provider: 'Finnhub', currency: 'USD' };
        const cachedResponse = Response.json(body, { headers: { 'Cache-Control': 'public, max-age=300' } });
        ctx.waitUntil(cache.put(cacheKey, cachedResponse.clone()));
        return secured(cachedResponse);
      }
      if (path === '/api/refresh' && request.method === 'POST') {
        if (!env.GITHUB_TOKEN || !/^[\w.-]+\/[\w.-]+$/.test(env.GITHUB_REPOSITORY)) return json({ error: 'refresh_not_configured', message: 'Connect the repository refresh workflow before requesting an update.' }, 503);
        const response = await fetch(`https://api.github.com/repos/${env.GITHUB_REPOSITORY}/actions/workflows/refresh-data.yml/dispatches`, {
          method: 'POST', headers: { Authorization: `Bearer ${env.GITHUB_TOKEN}`, Accept: 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'Capitol-Lens', 'Content-Type': 'application/json' },
          body: JSON.stringify({ ref: env.GITHUB_REF }), signal: AbortSignal.timeout(10_000),
        });
        if (response.status !== 204) { await response.body?.cancel(); return json({ error: 'refresh_failed', message: 'GitHub did not accept the refresh. Check workflow permissions and configuration.' }, 502); }
        return json({ accepted: true, message: 'Refresh requested. The snapshot changes only after the workflow and Cloudflare build succeed.', runsUrl: `https://github.com/${env.GITHUB_REPOSITORY}/actions/workflows/refresh-data.yml` }, 202);
      }
      if (path.startsWith('/api/')) return json({ error: 'Not found' }, 404);
      if (!['GET', 'HEAD'].includes(request.method)) return json({ error: 'Method not allowed' }, 405);
      if (url.pathname === BASE) return Response.redirect(`${url.origin}${BASE}/`, 302);
      return secured(await asset(env, path === '/' ? '/index.html' : path));
    } catch {
      console.error(JSON.stringify({ event: 'request_failed', path }));
      return json({ error: 'request_failed', message: 'This request could not be completed. Please retry.' }, 502);
    }
  },
} satisfies ExportedHandler<Env>;
