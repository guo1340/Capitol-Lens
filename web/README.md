# Capitol Lens — web application

A private research workspace for six politicians, historical stock prices and
interactive what-if scenarios. The first snapshot covers 2024–2025 and contains
820 disclosure rows (681 eligible stock transactions), with 119 price histories
including SPY. Unpriced symbols remain visible. The UI offers relationship tables,
stock charts, source links, four allocation rules, delay/cost controls, browser-saved
settings, a central question-mark glossary, and light/dark themes.

## Deploy from GitHub to Cloudflare

Use **Workers**, with static assets, in the same Cloudflare account as the existing
`guopq-admin` Worker. No database or separate frontend deployment is required.

1. In Cloudflare Workers & Pages, create a Worker connected to
   `guo1340/Capitol-Lens`, production branch `main`.
2. Set the root directory to `web`, build command to `npm ci && npm run build`,
   and deploy command to `npx wrangler deploy`.
3. Keep the checked-in route `api.guopq.com/capitol-lens*` and service binding
   `ADMIN = guopq-admin`. Confirm `guopq.com` is in this account and the existing
   API hostname is configured. The intended address is
   <https://api.guopq.com/capitol-lens/>.
4. Add the following **Worker secrets**, never frontend variables or Git files:

   | Secret | Purpose |
   | --- | --- |
   | `FINNHUB_API_KEY` | Latest quotes; obtain your own free key at <https://finnhub.io/dashboard>. |
   | `GITHUB_TOKEN` | Manual refresh; a fine-grained token scoped only to this repository with Actions read/write permission. |

   The repository and branch variables are already set in `wrangler.jsonc`.
   API responses never return secrets. Without keys, historical exploration and
   simulations work; the affected buttons display a configuration message.
5. Enable GitHub Actions. `refresh-data.yml` runs daily at 03:23 UTC and supports
   **Run workflow**. The workflow's built-in GitHub token has contents-write
   permission solely to commit the regenerated snapshot. The Worker secret above
   is a separate token used to dispatch that workflow.
6. After the first deployment, sign in at <https://admin.guopq.com/login> with
   `guo1340@vt.edu`, return to Capitol Lens, and reload. Test both an authenticated
   page and an incognito request to `/capitol-lens/api/dataset` (must return 401).
   Check a latest quote and its timestamp, then request a refresh and inspect its
   GitHub Actions run and the subsequent Cloudflare build.

Cloudflare's Git integration must watch data-only commits under `web/public/data`.
If a workflow-generated commit does not start a build in your account, redeploy the
latest commit in Cloudflare; the app keeps displaying the previous snapshot until
that build succeeds. Check account usage limits for builds and Actions.

## Existing-login integration

Every page, JS/CSS asset and dataset passes through the Worker before static asset
delivery (`run_worker_first: true`). It forwards only the `admin_token` cookie to
the existing admin Worker's `/api/auth/me`, then requires its verified email to
match `guo1340@vt.edu`. Missing, invalid, different-account or unavailable
verification fails closed. Responses are private/no-store. POST refresh requests
must have a same-origin Origin header. No admin application files or JWT secrets
need changing. `workers.dev` and public preview URLs are disabled.

The service binding and real existing session have to be verified after deployment;
local tests use a deliberately separate fixture, not a production login bypass.
Repository contents follow GitHub repository visibility; the app's login does not
make a public repository private.

## Local development

Requires Node 24 and npm. From the repository root:

```powershell
cd web
npm ci
npm run dev
```

Wait for the ready message, then open
<http://127.0.0.1:5173/capitol-lens/>. This **single command** builds the local
assets and starts all three required services: Vite on 5173, the real application
Worker on 8787, and a local test identity service on 8790. You do not need to
start the backend separately or sign in to production for local development.
The local Vite proxy supplies only the fixture identity. The UI labels this
session as a local preview; production always checks the real admin session.
Press Ctrl+C once to shut down the stack. Frontend edits update automatically.

For a production-build preview with explicit local login, use two terminals
instead of `npm run dev`:

```powershell
# Terminal 1, in web
npm run build
npm run preview:auth
# Terminal 2, in web
npm run preview
```

Open <http://127.0.0.1:8787/capitol-lens/> and follow the local login link.
Do not run this preview and `npm run dev` simultaneously: both use 8787/8790.

### Troubleshooting local startup

- **Port already in use:** stop the prior dev/preview terminals with Ctrl+C,
  then rerun. The launcher fails clearly instead of choosing a different port.
- **Old page keeps flashing/reloading:** close that tab, run the updated command,
  and open the exact 5173 URL above. The former authentication reload loop has
  been removed; failures now show a stable, readable message.
- **Missing package/module:** run `npm ci` inside `web`, then `npm run dev`.
- **Missing latest quotes:** set `FINNHUB_API_KEY` as described below and restart.
  No key is needed to explore the bundled historical snapshot or run simulations.
- **Refresh not configured locally:** this is expected until a repository token
  and repository variable are configured. Use GitHub's Run workflow to refresh
  data directly; production setup is described above.
- **Changed a backend secret/config:** stop and restart the stack.

Optional local provider secrets go in `web/.dev.vars`, copied from
`.dev.vars.example`; these are ignored by Git. Never deploy `wrangler.local.jsonc`
or `tests/auth-fixture.jsonc`.

## Validation

```powershell
# In web
npm test
npm run build
# From repository root
python -m unittest discover -s tests -v
# With both previews running and Playwright + Chrome installed
python scripts/check_web.py
```

The web suite compares all 112 scenarios with independent Python research results
and tests authorization, asset protection, refresh origin checks and provider
configuration errors. The compressed historical test fixture stays frozen even
when the app dataset refreshes. Browser checks cover local login, dictionary
hover, themes, missing-key messaging, simulations and mobile overflow.

## Data and calculations

- Disclosures come directly from official House Clerk yearly indexes and PDFs.
  The filing date is a proxy for public availability, not a verified historical
  publication timestamp. Simulated orders execute at the next available market
  open strictly after filing plus the selected extra calendar delay.
- Latest quotes use Finnhub's supported API, fetched server-side on demand with
  five-minute caching and an explicit provider timestamp. Provider plan limits
  and delays apply. Historical values are never relabeled as live quotes.
- Historical daily prices currently use the existing unofficial Yahoo research
  source. Finnhub's free quote key does not replace this historical dataset.
  Adjusted history approximates total returns for simulations; raw historical
  OHLC is used in stock exploration. Historical adjustments can be revised.
- Each selected politician receives an equal starting-cash portion; cash cannot
  move between politicians. Purchases are proportional when cash is constrained.
  Caps use remaining purchase cost. Partial sales, execution costs and empty
  starting positions are explicit assumptions. SPY uses the same start and cost.
- PDF extraction problems or missing held-position valuations stop publication
  of a new snapshot. Missing entry prices are reported as skipped orders. The
  old dataset remains available with its original coverage dates if refresh fails.
- This is exploratory retrospective research. Selection effects, source changes,
  taxes, liquidity and actual execution can materially change real-world results.
  Stage 1 has no Webull connection and cannot submit brokerage orders.

Architecture references: [static asset routing](https://developers.cloudflare.com/workers/static-assets/routing/worker-script/),
[service bindings](https://developers.cloudflare.com/workers/runtime-apis/bindings/service-bindings/),
[Git builds](https://developers.cloudflare.com/workers/ci-cd/builds/),
[Finnhub API](https://finnhub.io/docs/api).
