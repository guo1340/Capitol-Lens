Implement the Capitol Lens login gateway in the guopq-admin project.

Goal: add a sidebar entry named “Capitol Lens” linking to https://www.guopq.com/capitol-lens/. Preserve the existing main website and admin login behavior. Only the verified account guo1340@vt.edu may access Capitol Lens.

The Capitol Lens Worker already expects this integration:

1. GET https://api.guopq.com/api/auth/capitol-lens/start?returnTo=<encoded URL>
   Validate returnTo with a URL parser: HTTPS, exact host www.guopq.com, no credentials, and pathname exactly /capitol-lens or beginning /capitol-lens/. Reject other destinations. Default to https://www.guopq.com/capitol-lens/.
   If the existing admin session is valid and the verified email is authorized, issue the separate access cookie below and redirect to returnTo. Otherwise send the user to the existing admin login, securely retaining the validated destination through the authentication flow (including OAuth state if applicable). After successful login, revisit this gateway so that its Set-Cookie is issued by api.guopq.com. Never redirect an unauthorized account into the project; display access denied.

2. Dedicated cookie: capitol_session, Secure; HttpOnly; SameSite=Lax; Domain=guopq.com; Path=/capitol-lens.
   Use a short-lived, cryptographically authenticated or opaque server-stored session, specifically scoped/audienced to Capitol Lens and bound to the existing admin session. Do NOT copy the admin_token into this cookie or change admin_token's existing host-only scope. Verify expiration, signature, audience and active parent session on every validation. Revoke this access with admin logout/session revocation. Because this cookie spans sibling subdomains, never authorize other admin capabilities with it. Reject ambiguous duplicate session cookies. Never put access tokens in URLs or browser storage.

3. GET /api/auth/capitol-lens/me on the ADMIN service binding.
   The Capitol Lens Worker forwards ONLY Cookie: capitol_session=<value> to this endpoint through the existing ADMIN -> guopq-admin service binding. Read that cookie explicitly even though its browser path is /capitol-lens (the service call forwards it manually). Validate the dedicated session and parent session and enforce guo1340@vt.edu server-side.
   Return 200 JSON {"success":true,"data":{"email":"guo1340@vt.edu"}} only for authorized access; 401 for missing/invalid/expired session; 403 for disallowed account. Use Cache-Control: private, no-store. Do not trust supplied email headers or unsigned claims.

4. Keep /api/auth/me and the host-only admin_token working as before. Capitol Lens calls its own backend at https://api.guopq.com/capitol-lens/api/* with credentials:include; the browser sends the original admin cookie there. Its frontend page/assets at www are independently protected by the dedicated cookie and your validation endpoint.

5. Add tests for valid login and deep-link return (/capitol-lens/manual), no session, wrong email, expired/tampered/wrong-audience cookie, parent logout/revocation, duplicate cookies and malicious returnTo values (other hosts, //evil, userinfo, /capitol-lens-evil). Preserve existing auth tests. Confirm sidebar entry, logged-in gateway shortcut and full logged-out login-return flow.

Deploy the admin changes and tell me when the gateway endpoints are ready. Capitol Lens changes are already pushed but deliberately deny frontend access until this integration is deployed. The main website must remain unchanged.
