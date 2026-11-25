import { boundedJson } from './http';
export const ALLOWED_EMAIL = 'guo1340@vt.edu';
export type Authorization = { status: 'allowed'; email: string } | { status: 'unauthorized' | 'forbidden' | 'unavailable' };
/** The existing admin Worker verifies the HttpOnly admin_token JWT itself. */
export async function authorize(request: Request, admin: Fetcher): Promise<Authorization> {
  const cookie = request.headers.get('Cookie') ?? '';
  const token = cookie.split(';').map(s => s.trim()).find(s => s.startsWith('admin_token='));
  if (!token || token === 'admin_token=' || token.length > 8192) return { status: 'unauthorized' };
  try {
    const response = await admin.fetch(new Request('https://api.guopq.com/api/auth/me', {
      headers: { Cookie: token, Accept: 'application/json' }, redirect: 'manual', signal: AbortSignal.timeout(8000),
    }));
    if (response.status === 401) return { status: 'unauthorized' };
    if (!response.ok) return { status: 'unavailable' };
    const body = await boundedJson<{ success?: boolean; data?: { email?: unknown } }>(response, 16_000);
    if (!body.success || typeof body.data?.email !== 'string') return { status: 'unauthorized' };
    return body.data.email.trim().toLowerCase() === ALLOWED_EMAIL
      ? { status: 'allowed', email: ALLOWED_EMAIL } : { status: 'forbidden' };
  } catch { return { status: 'unavailable' }; }
}
