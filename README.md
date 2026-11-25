# Capitol Lens

Private politician-trade explorer and historical what-if web application, with
the original Python research engine preserved below. See **[web deployment and
development instructions](web/README.md)** for Cloudflare, existing admin-login
integration, API keys, daily refreshes and browser testing.

The web application is in `web/`. Its initial snapshot covers 2024–2025;
latest quotes require your Finnhub key. Stage 1 cannot place real orders.

## Start the web app locally

Install Node.js 24. One-time setup from the repository root:

```powershell
cd web
npm ci
npm run build
```

Then use **two separate terminals**, both in `web`:

```powershell
# Terminal 1 — backend API and local authentication fixture
npm run dev:backend
```

```powershell
# Terminal 2 — frontend only
npm run dev
```

Open **http://127.0.0.1:5173/capitol-lens/**. The frontend command does not start,
build or stop the backend. Stop each terminal separately with Ctrl+C. No API keys
or production login are required for historical exploration in local development.

## Publish on Cloudflare

### Chat with AI

The separate **Chat with AI** tab summarizes the stored data, discusses historical
stock ideas and can explain your what-if settings. Add `OPENAI_API_KEY` to
`web/.dev.vars`, restart the backend, and reload the frontend. For deployment,
add the key as a Worker secret. `OPENAI_MODEL` is optional (default `gpt-5-mini`).
Never put this key in frontend code or Git.

Eligible ChatGPT Pro subscriptions may provide API credits after activation;
check ChatGPT Settings → Billing and your linked API organization. ChatGPT and
API billing remain separate. See [the complete AI setup and usage notes](web/README.md#connect-chat-with-ai).
Chat uses the displayed historical coverage, not live market/news information.

### Current deployment configuration

The current production configuration packages frontend assets and the API in one
Worker. Separately hosted frontend/backend deployments are a future requirement;
the instructions below describe the current combined deployment only.

Connect this repository to **Cloudflare Workers**, use root directory `web`,
build command `npm ci && npm run build`, and deploy command `npx wrangler deploy`.
The configuration targets `https://api.guopq.com/capitol-lens/` and binds your
existing `guopq-admin` Worker to verify access for `guo1340@vt.edu`.

Add Worker secrets `FINNHUB_API_KEY` (latest quotes) and `GITHUB_TOKEN` (manual
refresh, fine-grained Actions permission for this repository). Enable GitHub
Actions for the daily 03:23 UTC refresh. The initial snapshot is 2024–2025;
new data appears only after a successful refresh and deployment.

See **[the complete setup guide](web/README.md)** for authentication, token scopes,
local troubleshooting, deployment checks, data limitations and test commands.
Cloudflare deployment and live secrets still need to be configured in your account.

## Original research workflow

First milestone: measure historical results before considering broker integration.
This project has no Webull connection and cannot place orders.

## Run on Windows

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m congress_backtest
Start-Process output\report.html
```

The initial configuration uses official House filings for Pelosi and Greene in
2024–2025, $10,000 starting cash, 5% of initial sleeve cash per buy signal, a 20%
remaining-cost-basis cap per stock, 10 basis points per execution, and a 50% exit
on a disclosed partial sale. These are research assumptions, not recommendations.
The combined portfolio gives each politician half the starting capital.

```powershell
# Repeat the exact cached run without network access
.\.venv\Scripts\python -m congress_backtest --offline
# Change allocation assumptions; keep separate output for comparison
.\.venv\Scripts\python -m congress_backtest --offline --buy-fraction 0.1 --cap-fraction 0.3 --output output\larger-buys
# Run unit tests
.\.venv\Scripts\python -m unittest discover -s tests -v
```

Open `output/report.html` for the chart, results, assumptions and expandable
trade ledgers with links to original filings. The report is a standalone file,
not a hosted site. `output/results.json` contains daily equity, positions,
order ledgers and skipped-signal reasons. `output/equity.png` is the chart.

## Data provenance

- House official yearly indexes: `https://disclosures-clerk.house.gov/public_disc/financial-pdfs/{year}FD.zip`.
- Original PTR documents: `https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/{year}/{document_id}.pdf`.
- Daily adjusted OHLC: Yahoo Finance chart endpoint. This is an unofficial,
  unguaranteed research feed. Cache raw responses and audit before relying on it.
- Raw inputs are under `data/raw` and `data/prices`. Download sidecars retain
  URL, retrieval time and SHA-256. Normalized disclosures include original text
  and filing URLs. Existing cached files are reused rather than overwritten.

The official filing date is **not a verified historical publication timestamp**.
The main test assumes availability that day and executes at the following market
session's open. A +3-calendar-day sensitivity test helps expose dependence on this
assumption but does not prove availability. Current historical archives and price
adjustments can incorporate subsequent corrections.

## Simulation rules and limitations

- Begin each run in cash, with no positions or disclosures carried in from before
  its starting date. The 2025-only comparison also starts from cash.
- Use only explicit `[ST]` rows and printed tickers; do not guess unknown names.
  IBIT is explicitly excluded: some reports label this Bitcoin ETF `[ST]`.
  Options, bonds, fund classifications and unreviewed amended rows are excluded.
- Spouse and dependent trades in a member's filings are included. Holdings are
  tracked per politician, not by each household account.
- Scanned PDFs or unrecognized digital layouts stop the pipeline for review.
  Khanna and McCaul were considered but not included in this initial run because
  sample reports are scans. There is no claim of whole-Congress coverage.
- One signal per ticker/politician/execution day. If a filing reports an earlier
  purchase and a later sale, use the later action. Identical/latest-date repeated
  rows collapse into one fixed-dollar signal. Same-date conflicting directions
  are flagged and skipped; rows are not assumed to reveal intraday ordering.
- Full sales close the strategy's position; partial sales sell an assumed 50%.
  Test the alternative of treating partial sales as complete exits as well.
- Same-session buys share available cash proportionally; no borrowing, shorting,
  deposits, or transfers between politician sleeves. Settled-cash timing is not
  modeled. Once cash is exhausted, future buys are skipped until sales free cash.
- Adjusted open is raw open × adjusted close / raw close. Holding fractional
  adjusted units approximates split-adjusted, dividend-reinvested returns.
  This is not a literal historical-share or tax-lot ledger.
- Cash earns zero. Taxes and final liquidation fees are excluded. Remaining
  holdings contribute unrealized gains/losses at the final adjusted close.
- SPY begins fully invested at the first session's adjusted open with identical
  entry costs. Different cash exposure means excess return is not risk-adjusted
  alpha; a cash-heavy strategy can trail even with profitable individual trades.
- Missing entry prices are visible in the audit; missing valuations for held
  stocks abort the run. Delisted securities and symbol changes require careful
  further validation. Never silently value an unpriced holding at zero or drop it.
- The trade-date-plus-27-days scenario is a **counterfactual**: it may trade before
  actual disclosure. Never treat its performance as executable historical evidence.
- Names and rules were chosen retrospectively. Two years are useful exploration,
  not a genuinely unseen test or proof of future profitability.

## Next milestones

1. Validate additional politicians, scanned filings, amendments, publication
   timing, security identities, and a second historical price source.
2. Compare a small predeclared set of allocation rules and market-exposure-matched
   benchmarks; avoid optimizing many rules on the same two-year sample.
3. Freeze a strategy and paper-trade future disclosures before evaluating live
   Webull integration.

Government-source access and use restrictions must be evaluated for any future
automated trading or redistribution product; this first milestone is local
historical research.

## Expanded allocation experiment

The expanded experiment freezes four rules in `experiments/expanded-v2.json`:

| Rule | Buy amount | Remaining-cost-basis cap |
|---|---|---|
| Small | 2% of initial sleeve cash | 10% of initial sleeve cash |
| Original baseline | 5% of initial sleeve cash | 20% of initial sleeve cash |
| Larger | 10% of initial sleeve cash | 30% of initial sleeve cash |
| Portfolio-value sizing | 10% of previous session closing sleeve equity | 30% of that equity |

Previous-close sizing avoids using the same day's closing price to place an
opening order. Caps govern additional purchases; they do not trigger rebalancing
or force sales when market value rises or the sizing base falls.

The active comparison includes Pelosi, Greene, Rick Allen, Lloyd Doggett,
Virginia Foxx, and Scott Franklin. Each is tested independently, plus an equal
initial-capital portfolio of all six. Four scenarios give 112 combinations:
2024–2025, 2024–2025 with three extra calendar days of delay, 2024 alone, and
2025 alone. Standalone years restart in cash; they are not unseen holdout data.

```powershell
# Fetch/cache official inputs and run the full matrix
.\.venv\Scripts\python -m congress_backtest.experiment
# Reproduce the expanded run entirely offline
.\.venv\Scripts\python -m congress_backtest.experiment --offline
Start-Process output\expanded-v2\report.html
# Retained original expansion (includes members without eligible stock buys)
.\.venv\Scripts\python -m congress_backtest.experiment --offline --config experiments\expanded-v1.json --output output\expanded
```

The initial expansion picked additional members alphabetically by electronic
filing availability. Beyer and Collins had no eligible common-stock transactions;
DelBene had only eligible stock sales. Their zero-activity runs remain in
`output/expanded`, with the original configuration retained. The next three
alphabetical candidates were selected for the active comparison based on stock
purchase coverage, before calculating their returns. This refinement is explicit
in the v2 configuration; it is not a preregistered experiment.

Each report includes return/drawdown/cash comparisons, coverage, failures, and
source-linked trade ledgers. `results.json` retains complete daily curves and
audit records; `run-manifest.json` records the configuration and normalized-input
SHA-256 hashes. Source/price snapshots for the expanded experiments are separate
from the original baseline. Unpriced entry signals are flagged rather than hidden;
missing held-position prices block a run. An unheld sale does not require a quote.
SCHX (ETF) and VIASP (preferred stock) are explicitly excluded despite `[ST]`
labels in their filings. No live trading functionality has been added.
