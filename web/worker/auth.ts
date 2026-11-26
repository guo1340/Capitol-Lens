import { boundedJson } from './http';
export const ALLOWED_EMAIL = 'guo1340@vt.edu';
export type Authorization = { status: 'allowed'; email: string } | { status: 'unauthorized' | 'forbidden' | 'unavailable' };
/** The existing admin Worker verifies the HttpOnly admin_token JWT itself. */
export async function authorize(request: Request, admin: Fetcher): Promise<Authorization> {
  const cookie = request.headers.get('Cookie') ?? '';
  const gateway = new URL(request.url).hostname === 'www.guopq.com';
  const cookieName = gateway ? 'capitol_session=' : 'admin_token=';
  const token = cookie.split(';').map(s => s.trim()).find(s => s.startsWith(cookieName));
  if (!token || token === cookieName || token.length > 8192) return { status: 'unauthorized' };
  try {
    const response = await admin.fetch(new Request(gateway ? 'https://api.guopq.com/api/auth/capitol-lens/me' : 'https://api.guopq.com/api/auth/me', {
      headers: { Cookie: token, Accept: 'application/json' }, redirect: 'manual', signal: AbortSignal.timeout(8000),
    }));
    if (response.status === 403) return { status: 'forbidden' };
    if (response.status === 401) return { status: 'unauthorized' };
    if (!response.ok) return { status: 'unavailable' };
    const body = await boundedJson<{ success?: boolean; data?: { email?: unknown } }>(response, 16_000);
    if (!body.success || typeof body.data?.email !== 'string') return { status: 'unauthorized' };
    return body.data.email.trim().toLowerCase() === ALLOWED_EMAIL
      ? { status: 'allowed', email: ALLOWED_EMAIL } : { status: 'forbidden' };
  } catch { return { status: 'unavailable' }; }
}
