/** Local preview only. Never deploy this test identity provider. */
export default {
  fetch(request: Request): Response {
    const url = new URL(request.url);
    if (url.pathname === '/login' && ['127.0.0.1','localhost'].includes(url.hostname)) return new Response(null, { status: 302, headers: { Location: 'http://127.0.0.1:8787/capitol-lens/', 'Set-Cookie': 'admin_token=local-preview-only; HttpOnly; SameSite=Lax; Path=/' } });
    const valid = request.headers.get('Cookie') === 'admin_token=local-preview-only';
    return Response.json(valid ? { success: true, data: { email: 'guo1340@vt.edu' } } : { success: false }, { status: valid ? 200 : 401 });
  },
};
