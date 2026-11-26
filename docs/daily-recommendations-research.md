# Daily research recommendations: research and implementation specification

Status: research proposal, not a validated strategy or live recommendation engine.
User scope: broader US stocks; intended holding period >= one year; daily assessment; plan Webull integration but do not connect accounts or place orders.

## Evidence reviewed

- Robert Novy-Marx, The Other Side of Value: Good Growth and the Gross Profitability Premium, NBER working paper 15940 (2010; published research followed). https://www.nber.org/papers/w15940 — motivates testing gross profit / assets alongside valuation. Requires financial statements and their public availability timestamps. Does not establish a specific allocation or expected return for our app.
- Asness, Frazzini, Pedersen, Quality Minus Junk (2018 version). https://www.aqr.com/insights/research/working-paper/quality-minus-junk — studies profitable, growing, safer companies and a long-short portfolio across markets. A long-only shortlist is an adaptation, not a replication. Avoid paying any price for quality.
- Daniel and Moskowitz, Momentum Crashes (NBER working paper 20439). https://www.nber.org/system/files/working_papers/w20439/w20439.pdf — reason to test trend signals cautiously; momentum portfolios can experience sharp losses. Do not assume a winner keeps rising or use the paper's long-short results as bundle returns.
- Sullivan, Timmermann, White, Data-Snooping, Technical Trading Rule Performance, and the Bootstrap. https://eprints.lse.ac.uk/119144/1/dp303.pdf — motivates controlling repeated strategy searches and using genuinely unseen evaluation periods. Source discovery is complete; detailed full-text replication review remains required before implementation claims.

This is an initial literature review, not a systematic review or claim that the papers' strategies were reproduced. Do not promote complicated pattern recognition or machine learning before simple baselines survive costs and unseen data.

## Proposed research experiments (predeclare before testing)

Separate quality-only, valuation-only, combined quality/valuation, price-trend-only, politician-only, and combined variants. Use equal-weight baseline ranks before tuning weights. Politician disclosures are an optional comparison/annotation until incremental out-of-sample benefit is demonstrated. Do not add an unexplained politician bonus to a score.

Define a documented broad US common-stock universe, with explicit handling of ETFs, ADRs, financial companies and REITs. Do not describe today's surviving stock list as a historical investable universe. Sector comparisons and accounting comparability are required; missing financial items remain missing rather than zero.

Suggested prototype parameters, not user portfolio advice: evaluate a 20-stock equal-weight long-only basket, max 5% initial allocation per company, max 25% initial sector allocation, quarterly review, daily evidence refresh. Leave unallocated cash when constraints prevent filling the basket; do not force buys. Test 12- and 24-month holding outcomes as well as the ongoing portfolio. Weights/limits require validation and may be changed only with a new strategy version and a fresh holdout.

## Required data and reproducibility

Current app snapshot (checked 2026-11-26): coverage 2024-01-01 through 2026-11-24; 132 price histories; politician-linked universe, no financial statements. This is insufficient for broad-market quality/value selection and robust year-plus evaluation.

Acquire adjusted historical prices with corporate actions, actual/unadjusted quotes for order previews, security identifiers, industry/sector, trading eligibility and financial statements. Record source URL/provider, fetchedAt, priceAsOf, statement period end, filing publication/acceptance time and availability assumptions separately. Retain original filings; do not use later restatements in earlier backtests. Preserve all existing Python research and frozen historical results.

User confirmed strictly free data on 2026-11-26; display all coverage gaps and do not subscribe to paid services. Do not invent API entitlements or pretend free quote access includes bulk historical prices/fundamentals. If historical universe membership/delistings are unavailable, explicitly label survivorship bias and narrow the conclusion.

## Validation gates

- Daily signal uses only data available by its cutoff; execution occurs at a later tradable price, never the signal day's already-known close.
- Chronological training/validation/holdout, with a purge for overlapping forward holding-period labels; no random train/test split.
- Prefer 10+ years including multiple market conditions. If unavailable, report limited evidence rather than optimize 1-2 years.
- Compare SPY buy-and-hold, equal-weight same universe and politician-only under identical dates, capital and cash assumptions.
- Include turnover, fees/spreads/slippage, missing prices, delistings where available, corporate actions, sector concentration, drawdowns and costs sensitivity. Taxes are excluded unless specifically modeled and must be labelled.
- Report all predeclared variants, not only the winner. Distinguish historical tests, paper forward tracking and live results. No probability of profit or expected return without a calibrated validated model.
- Freshness is checked against completed US trading sessions, including holidays; stale/failed feeds block 'today' labels and executable bundle export.

## Daily recommendations page

Bilingual English / Simplified Chinese with original English company/politician names. Central dictionary and question-mark hover/focus/tap/Escape controls; dark/light charts and dialogs.

Display: assessment timestamp, latest completed market session, data completeness, strategy version, research-only status, and why a bundle is unavailable when blocked. Each candidate: company/ticker, selection evidence, weaknesses, source links/timestamps, suggested research weight, and politician activity separately. Score is a relative research ranking, not a probability or return prediction. Explain changes since previous assessment. Keep immutable daily snapshots for forward paper evaluation. Daily refresh does not mean daily buying/selling.

A budget-based bundle preview is illustrative, not personalized until risk tolerance, existing holdings and investment budget are supplied. Show cash remainder and concentration. Historical ranks cannot be labelled today's recommendations. AI may summarize computed evidence, but must not invent scores, replace missing data, or create orders.

## Webull integration plan (no connection or orders in this phase)

Official sources checked 2026-11-26:
https://developer.webull.com/apis/docs/getting-started/
https://developer.webull.com/apis/docs/authentication/IndividualApplicationAPI/
https://developer.webull.com/apis/docs/trade-api/account/
https://developer.webull.com/apis/docs/reference/trading/

Individual OpenAPI access requires an application and approved credentials. Confirm account/region eligibility, data entitlements, supported securities and fractional/notional order capabilities for the exact API/account; do not assume a bundle is an atomic exchange order.

Future sequence: approved official API access -> isolated sandbox -> read-only balances/holdings -> reconcile existing positions with desired weights -> expiring order preview -> explicit user confirmation -> idempotent per-order submission -> reconcile fills/rejections/cancellations. Handle partial bundle failures without blindly resubmitting filled orders. Use unique client order IDs, order-state persistence, cash reservation, market-hours checks, stale-price blocks, kill switch and audit trail. Keep secrets server-side, separate sandbox/live credentials, and do not expose the secret through AI prompts. No trading endpoint is authorized or implemented by this plan.

## Next dependencies

1. Free-provider entitlement, field coverage and reliability verification.
2. Data acquisition and point-in-time storage; test coverage/quality before ranking.
3. Independent research engine and reproducible validation reports.
4. Protected daily page, snapshots, paper bundle tracking, dictionary/manual updates.
5. Webull sandbox integration only in a separately authorized phase.


## Confirmed free-data approach

SEC submissions and companyfacts APIs require no API key and provide public filing histories and extracted financial facts: https://www.sec.gov/search-filings/edgar-application-programming-interfaces . Use documented fair-access identification/rate limits, caching and incremental refresh. Financial facts are not uniform across sectors or filers; SEC availability alone does not guarantee comparable metrics. Cross-check each value with filing dates and units.

Broader coverage must be an explicit published universe and include a coverage funnel (listed -> mapped to issuer -> financials valid -> price coverage valid -> eligible). Do not imply all US stocks are covered. Free price-source coverage/terms are still unverified for this expansion; the existing unofficial Yahoo research source is not a supported-provider guarantee. Until a viable free daily-price pipeline is verified, current actionable recommendations remain unavailable. A stale historical research preview is permissible only with explicit date labels and no current bundle export.

A free-only historical backtest cannot be called survivorship-free without historical membership and delisted securities. Prefer prospective paper tracking when these inputs cannot be obtained.
