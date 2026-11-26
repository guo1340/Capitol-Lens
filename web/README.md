# Capitol Lens — web application

A private research workspace for six politicians, historical stock prices and
interactive what-if scenarios. The first snapshot covers 2024–2025 and contains
820 disclosure rows (681 eligible stock transactions), with 119 price histories
including SPY. Unpriced symbols remain visible. The UI offers relationship tables,
stock charts, source links, four allocation rules, delay/cost controls, browser-saved
settings, a central question-mark glossary, and light/dark themes.

## Deployment architecture

Frontend and backend run as independent processes locally. The checked-in
production configuration currently serves the assets and API through one Worker;
it is not yet a pair of independently deployed services. Separate production
hosting is the intended next architecture change. It must preserve the existing
API-domain session and protect the dataset, with an explicit API origin/routing
and authentication arrangement. Do not publish `public/data` directly as an
unprotected static site. The following deployment steps describe the current
combined configuration, not the future split hosting setup.

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

### In-app user manual / 使用手册

Open **User manual / 使用手册** in the navigation, or go directly to
`/capitol-lens/manual` on the app's host. The manual has English and Simplified
Chinese instructions for every tab, a linked contents list, question-mark word
help, troubleshooting and buttons to try each feature. It requires the same login
as the rest of the app. The manual displays the currently loaded coverage dates;
its examples do not imply that the historical snapshot is up to date.

### English / 简体中文

Use the **中文 / English** button in the top bar to switch languages instantly.
The choice is saved in this browser. Navigation, controls, dates, chart labels,
errors and the central question-mark dictionary are translated. The sign-in gate
also offers a language link. New AI answers follow the selected language; existing
messages remain as originally written. Stock symbols, USD values, original company and politician
names and linked government documents are preserved.

Translations live in `src/zh-CN.json`, with shared lookup logic in
`src/translations.ts` and browser preference handling in `src/i18n.ts`.
Run `python scripts/check_language.py` with the frontend and backend running to
check all tabs and the language preference. Its AI/quote replies are mocked, so
the test does not spend API credits.

### Connect Chat with AI

ChatGPT Pro and the API have separate billing, but eligible Pro subscriptions can
claim API credits. Check **ChatGPT → Settings → Billing → API credits benefit**,
link the intended API organization, and confirm the grant in that organization's
API billing page. Eligibility and activation are account-specific; having Pro
alone does not confirm that credits have been issued.
See [OpenAI's credit-benefit instructions](https://help.openai.com/en/articles/20001626-api-credits-benefit-for-eligible-chatgpt-subscriptions)
and [billing separation](https://help.openai.com/en/articles/9039756-managing-billing-for-chatgpt-and-the-api-platform).

1. Create an API key in your intended project at
   <https://platform.openai.com/api-keys>. Ensure that project has access to the
   selected model and usable API credits/billing.
2. Locally, copy `.dev.vars.example` to **`web/.dev.vars`** if the latter does not
   already exist. If it exists, append the OpenAI settings without overwriting
   your existing provider keys:

   ```dotenv
   OPENAI_API_KEY=your-api-key-here
   OPENAI_MODEL=gpt-5-mini
   ```

3. Restart only the backend (`npm run dev:backend`), then reload the frontend.
   Open **Chat with AI**, select a starter question or type your own, and Send.
4. For Cloudflare, add `OPENAI_API_KEY` as a **secret** on the application Worker.
   Optionally add `OPENAI_MODEL` as a backend variable. The default is
   `gpt-5-mini`; overrides must support the Responses API request parameters used
   by `worker/chat.ts`. Redeploy/reload as needed after configuration changes.
   Never use a `VITE_` variable for the key, paste it into chat, or commit it.

The chat can summarize the research, compare historical stock trends, suggest a
shortlist to investigate, and discuss tradeoffs. Checking **Include my current
what-if settings** sends the selected scenario to the backend, which recalculates
it from its own dataset. It does not trust a return supplied by the browser.
Stock price changes and disclosure-following returns are explicitly different.
Source chips open the original House filings or the app's stock view.

The current chat uses the stored historical dataset only: no live quotes, news,
web browsing or brokerage tools are enabled. Its visible coverage end date is
authoritative; rebuilding the app does not make its market evidence current.
Historical shortlists are not verified current purchase recommendations. Model
answers can still be wrong; inspect their supporting records.

Questions, the last nine conversation messages, summarized public research data,
and optionally scenario settings are sent to OpenAI. The API key and admin cookie
are not included in that content. Chat history lives in page memory, survives tab
switches, and is cleared by New chat or page reload. Requests set `store: false`;
this is not a promise of zero provider retention. Each request may spend API
credits. Requests are bounded to 2,000-character questions, a limited history and
4,000 output tokens (including reasoning), with a 55-second upstream timeout.
Stopping the UI request may not cancel provider processing/billing. There is no
app-level monthly spend cap; monitor your OpenAI organization usage and limits.

The endpoint uses the existing admin authorization and same-origin POST checks.
Missing keys, rejected credentials, rate/credit limits and incomplete responses
produce visible errors, not fabricated answers. Tests use mocked provider replies;
a successful paid API request must be verified after you supply your key.

References: [Responses API](https://developers.openai.com/api/reference/resources/responses/methods/create),
[GPT-5 mini](https://developers.openai.com/api/docs/models/gpt-5-mini).

### Start the frontend and backend separately

Requires Node 24 and npm. Install and prepare the assets once:

```powershell
cd web
npm ci
npm run build
```

**Terminal 1 — backend**, from `web`:

```powershell
npm run dev:backend
```

This starts the API Worker on 8787 and its separate local authentication fixture
on 8790. It does not start or build the frontend. Wait for “Backend ready”. The
current Worker reads its bundled dataset from `dist`, so run `npm run build`
again after updating `public/data/dataset.json`.

**Terminal 2 — frontend**, also from `web`:

```powershell
npm run dev
```

Open <http://127.0.0.1:5173/capitol-lens/>. Frontend edits update automatically.
Vite proxies API requests to the separately running backend. The local proxy
supplies a test identity; the UI labels this session as a local preview.
Production always verifies the real admin session. Stop each terminal separately
with Ctrl+C. Stopping the frontend does not stop the backend, or vice versa.

For a built-asset preview, keep the backend running and open
<http://127.0.0.1:8787/capitol-lens/>. Follow the local login link. Alternatively,
start the two backend services manually in separate terminals with
`npm run preview:auth` and `npm run preview`; do not run those alongside
`npm run dev:backend`, because they use the same ports.

### Troubleshooting local startup

- **API errors or loading failure:** ensure `npm run dev:backend` is running in
  another terminal, then reload the frontend. Starting only Vite does not start
  the API. No automatic reload loop is used.
- **Missing dist/assets:** run `npm run build` once before starting the backend.
- **Port already in use:** stop the earlier process on 5173 (frontend), 8787
  (API), or 8790 (local authentication). Each command owns only its own services.
- **Missing package/module:** run `npm ci` inside `web`.
- **Missing latest quotes:** set `FINNHUB_API_KEY` and restart the backend.
  No key is needed for the historical snapshot or simulations.
- **Refresh not configured locally:** configure the repository variable and token,
  or use GitHub's Run workflow. Production setup is described above.
- **Changed a backend secret/config:** restart `npm run dev:backend`.

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
# With dev:backend running and Playwright + Chrome installed
python scripts/check_web.py
# With dev:backend AND dev running
python scripts/check_dev.py
# Chat UI with mocked replies; no API charges
python scripts/check_chat.py
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
  The optional Webull connector reads holdings only and cannot submit brokerage orders.

Architecture references: [static asset routing](https://developers.cloudflare.com/workers/static-assets/routing/worker-script/),
[service bindings](https://developers.cloudflare.com/workers/runtime-apis/bindings/service-bindings/),
[Git builds](https://developers.cloudflare.com/workers/ci-cd/builds/),
[Finnhub API](https://finnhub.io/docs/api).


## Frontend on www, API on api (migration)

The frontend now uses https://www.guopq.com/capitol-lens/ and the API remains
https://api.guopq.com/capitol-lens/api/. Only the /capitol-lens path on www is
routed to this Worker; the existing homepage is untouched. Keep the ADMIN service
binding. Remove obsolete custom domains and old broad routes from this Worker's
Cloudflare dashboard if they remain after deployment. Do not assign www as a
custom domain to this Worker: use the path routes in wrangler.jsonc.

Deploy the admin integration described in ADMIN_AGENT_PROMPT.md first. The page
requires a dedicated capitol_session cookie verified by the ADMIN service; until
that integration exists it intentionally denies access. API calls still use the
existing host-only admin_token with credentials included. No API secrets belong
in frontend build variables. Credentialed CORS allows only https://www.guopq.com.
The manual URL is now https://www.guopq.com/capitol-lens/manual.

## Long-term research page

Open `/capitol-lens/recommendations` (same authorized login). Daily SEC financial data feeds a hand-selected, published multi-sector US universe wider than the politician dataset. Run `python scripts/refresh_recommendations.py` from the repository root to refresh it. No API key or paid service is needed; a documented identifying SEC User-Agent is used. The ignored `.research-cache/` retains downloaded SEC JSON for 24 hours (issuer directory 7 days), limiting repeat downloads. At most 3 downloads run concurrently.

The daily/manual GitHub workflow refreshes both datasets. A politician-source failure does not prevent the independent company research refresh. Inspect workflow logs as well as the coverage panel. `research_snapshots/YYYY-MM-DD-quality-operating-v1.json` preserves the first daily assessment for prospective evaluation. This is not an immutable intraday audit or a historical backtest. Daily failures are published as gaps rather than successful invented data; the prior daily archive remains available.

Strategy `quality-operating-v1` ranks eligible positive-operating-profit/positive-operating-cash-flow companies using equal-weight percentile ranks for operating profit/assets, operating cash flow/assets and lower liabilities/assets. Ratios use matched annual period ends and only filings before the UTC assessment date. Restated data may be used in today's assessment; it must not be reused to reconstruct earlier decisions. Missing or mismatched fields exclude a company. Annual statements older than 550 days are excluded. No industry normalization, valuation, trend or dividend forecast is implemented; this is explicitly shown on the page.

The hypothetical basket has up to 20 names at 5% each and at most 5 names per listed industry group. A complete basket is frozen until the next calendar quarter. An incomplete basket can fill as data arrives and is not shown as a usable amount preview. Missing selected-stock data, fewer than 20 eligible names, a snapshot older than 4 calendar days, or an overdue quarter block the amount preview. Four calendar days is an operational freshness rule, not a US trading calendar calculation; statements retain their own older period/filing dates. No prices or tradable share quantities are fabricated. The optional read-only account connector is separate from this research preview; orders are not implemented.

The amount preview is hypothetical, does not incorporate existing holdings/tax/risk preferences, and is not an income forecast. Research claims require future independent validation. A long horizon still entails losses and dividend reductions. Review quarterly rather than interpreting daily refreshed ranks as buy/sell instructions.

Tests: `python -m unittest discover -s tests -p test_recommendations.py`, `npm --prefix web test`, `npm --prefix web run build`.

## Valuation and historical comparison (v2 experiment, superseded by v3 default)

`quality-value-v2` weights the financial-strength percentile rank and operating-cash-flow/estimated-market-cap percentile rank 50/50. Market capitalization is estimated from a completed daily closing price and the most recent share count published before the signal date. Share counts can lag issuance/buybacks and are rejected when older than 200 days. Reported splits adjust share counts between their effective date and price date. Yahoo split-adjusted historical closes are converted back to contemporaneous price units for valuation, while adjusted open/close units are used for total-return approximations in the portfolio test. Cash flow is annual, not forecast; this is not free-cash-flow yield or dividend yield, and a higher rank is not a fair-value price target.

The free Yahoo chart endpoint is an unofficial research source with no reliability or completeness guarantee. Responses are cached by ticker and cutoff date under `.research-cache/`. Download failures and price gaps remain explicit. No paid key is used. SEC fact records remain constrained by their filing dates; later restatements cannot enter an earlier signal. Availability is conservatively delayed until the day after the filing date; exact intraday publication timestamps are not modeled.

`python scripts/refresh_recommendations.py` now also runs `scripts/long_term_value.py`. The historical comparison starts January 2018 and ends at the last available SPY session before the UTC cutoff. It recomputes quarterly selections using only prior filings/prices, trades at quarter-start adjusted opens, sizes at 5% per selected company with 25% industry-group cap, sells before buying, and scales buys to available cash including costs. Unfilled allocations stay as zero-interest cash. SPY buys at the same initial open and includes its initial transaction cost. Terminal holdings are marked at close without hypothetical liquidation costs. Portfolio costs are 0.1% per traded dollar; sensitivity uses 0.25%. Taxes and precise execution spreads are not modeled separately. Missing held-company prices stop the comparison. Monthly sampled chart points are for display; drawdowns are calculated daily. Constituent/exclusion audits for every quarterly decision are in the JSON report.

These are exploratory results on today's manually selected surviving companies; historical membership/delisted-stock coverage is unavailable. The strategy has no held-out validation, and repeated rule changes can overfit the sample. Compare quality-only as well as SPY: a valuation filter can hurt returns. Do not interpret published backtest returns as predictions. Original politician research and its frozen reproducible outputs remain untouched.

### Lazy loading and private browser cache

The long-term page does not request the politician dataset. Other tabs fetch it only on demand. A SHA-256 manifest (`/api/dataset-version`) is generated by `prebuild`/`predev`; every dataset load first authenticates against this small endpoint. IndexedDB retains the matching dataset across refreshes. A new hash replaces the cached snapshot; blocked storage falls back to network. No cached data is read on an authorization error. Raw snapshot endpoints keep private/no-store response headers; shared/public caches are not used. Chat, manual and recommendations use React lazy/Suspense. Browser verification: `python scripts/check_lazy_data.py` with Vite running.

## Daily recommendations (v3)

The home page is now Daily Recommendations: evidence and stock cards on the left, AI chat on the right. Generate an assessment explicitly; loading the page does not call OpenAI. Cards distinguish rule-based candidates from AI assessments. Click a card for dated company evidence, related politician filings, and a local buy/sell draft. A candidate without covered politician activity comes from company research, not a politician signal. AI requests use the existing server-side OpenAI key and incur API usage.

`quality-baseline-v3` restores financial strength alone as the default ranking. Valuation remains visible as context and as an experimental comparator. Reproduction: `python scripts/refresh_recommendations.py`. Original snapshots and Python research results are preserved.

| Independently restarted period | Financial strength | Strength + valuation | SPY |
|---|---:|---:|---:|
| 2018–2021 | 147.53% | 141.55% | 89.87% |
| 2022–2026-11-25 | 67.76% | 59.88% | 60.16% |

These cumulative returns use $10,000 per period and 0.1% transaction costs. The full period had already been inspected before splitting it, so this is **retrospective**, not an untouched holdout. No parameters were tuned to this split. Valuation did not add benefit in either segment. Today's surviving-company universe remains biased; this does not establish future outperformance. The JSON includes each rule's drawdowns, costs, quarterly selection audits and separate curves. Daily refreshes are evidence updates, not daily trading instructions.

## Webull read-only setup

US accounts require approved [official Webull OpenAPI access](https://developer.webull.com/apis/docs/getting-started/). A normal brokerage login is not sufficient. Until approval and credentials are configured, the app correctly shows **not connected**. This integration has mocked protocol tests but cannot be verified against your account before approval.

1. Apply through Webull's official developer portal and obtain the App Key and App Secret. Follow its account authorization/2FA process if an access token is required. Never paste credentials into chat or frontend settings.
2. In the **backend Worker's** Cloudflare settings, create encrypted secrets named `WEBULL_APP_KEY` and `WEBULL_APP_SECRET`. Optionally add `WEBULL_ACCESS_TOKEN` if your authorization requires it. Add `WEBULL_ACCOUNT_ID` when multiple accounts are returned; otherwise the only authorized account is selected. For local development put these in ignored `web/.dev.vars` and restart the backend.
3. The connector defaults to the Webull sandbox. Once approved for production, set `WEBULL_ENVIRONMENT` to `production` in the backend runtime settings (or as an encrypted secret so Wrangler preserves it). Sandbox data is labelled and cannot enable drafts. Use credentials appropriate to that environment.
4. Sign in to Capitol Lens with the authorized admin login. Click **Connect / refresh Webull**. The backend signs GET requests for account list, balances and positions only; keys and account IDs are never returned to the browser. Errors keep the account unverified.
5. Check holdings, cash and retrieval time. Cash is conservatively capped by settled cash and reduced by held/frozen amounts; margin buying power is never used. Unsupported currencies, options and short positions are excluded and counted. Price retrieval time is not an exchange quote timestamp.
6. To incorporate your portfolio into an AI assessment, explicitly check **Include verified holdings and cash in OpenAI requests**, then generate it again. This shares symbols, quantities, reported prices and cash with OpenAI, not account IDs or credentials. Without this choice the AI does not receive your portfolio.

Drafts require production holdings refreshed within five minutes. Purchases reserve existing cash, never planned sale proceeds; sales cannot exceed reported holdings after other sale drafts. Amounts use dated prices and are estimates, not executable quotes. Drafts exist only in browser memory and disappear on reload. There are **no brokerage order endpoints**. Official approval and successful account verification remain necessary before claiming an actual connection.

中文简要：先申请 Webull 美国官方 OpenAPI；审批通过后，仅在后端配置上述密钥。首页点击“连接 / 刷新 Webull”，核对持仓与现金；只有勾选分享选项后，AI 才会收到持仓信息。买卖操作仅保存临时草稿，不会下单。默认财务实力筛选，估值只作参考。
