from __future__ import annotations

import base64
import html
import io
from collections import Counter
from datetime import date
from pathlib import Path
from statistics import mean, median


def chart(results):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10})
    fig, ax = plt.subplots(figsize=(11, 4.8), layout='constrained')
    colors = ['#2767d8', '#b75b2e', '#138276']
    for result, color in zip(results, colors):
        ax.plot([date.fromisoformat(p['date']) for p in result['curve']],
                [p['equity'] for p in result['curve']], label=' + '.join(result['names']), color=color, linewidth=2)
    r = results[0]
    ax.plot([date.fromisoformat(p['date']) for p in r['curve']], [p['benchmark'] for p in r['curve']],
            label='SPY buy & hold', color='#697586', linestyle='--', linewidth=2)
    ax.yaxis.set_major_formatter(mticker.StrMethodFormatter('${x:,.0f}'))
    ax.set_title('Account value, including uninvested cash', loc='left', pad=18, weight='bold')
    ax.grid(axis='y', alpha=.18)
    ax.spines[['top', 'right']].set_visible(False)
    ax.legend(loc='upper left', frameon=False)
    stream = io.BytesIO()
    fig.savefig(stream, format='png', dpi=160)
    plt.close(fig)
    return stream.getvalue()


def write_report(output, results, disclosures, price_errors, config):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    baseline = [r for r in results if r['scenario'] == 'Filing date']
    graph = chart(baseline)
    (output / 'equity.png').write_bytes(graph)
    eligible = [r for r in disclosures['transactions'] if not r['excluded_reason']]
    lags = [(date.fromisoformat(r['filing_date']) - date.fromisoformat(r['trade_date'])).days for r in eligible]
    e = html.escape
    rows = ''
    details = ''
    for index, r in enumerate(results):
        rows += f"""<tr><td>{e(' + '.join(r['names']))}</td><td>{e(r['scenario'])}</td>
        <td>${r['ending_value']:,.2f}</td><td>{r['return_pct']:+.2f}%</td><td>{r['excess_percentage_points']:+.2f} pp</td>
        <td>{r['max_drawdown_pct']:.2f}%</td><td>{r['buy_count']} / {r['sell_count']}</td><td>{r['average_cash_pct']:.1f}%</td></tr>"""
        trades = ''.join(f"<tr><td>{t['date']}</td><td>{e(t['politician'])}</td><td>{e(t['ticker'])}</td><td>{t['action']}</td><td>${t['value']:,.2f}</td><td><a href='{e(t['source_url'], quote=True)}' target='_blank' rel='noopener'>{e(t['source_id'])}</a></td></tr>" for t in r['ledger'])
        positions = ', '.join(f"{p['politician']} {p['ticker']} ${p['value']:,.0f}" for p in sorted(r['positions'], key=lambda p: -p['value'])) or 'None'
        counts = Counter(a['reason'] for a in r['audit'])
        annual = ', '.join(f"{p['year']}: {p['return_pct']:+.2f}%" for p in r['annual_returns'])
        details += f"""<details><summary>{e(' + '.join(r['names']))} · {e(r['scenario'])} — trade ledger and assumptions</summary>
        <p>Window: {r['start']} to {r['end']}. Annualized return: {r['annualized_pct']:+.2f}%. Calendar returns within this run: {annual}.</p>
        <p>Realized P/L: ${r['realized_profit']:,.2f}. Unrealized P/L: ${r['unrealized_profit']:,.2f}. Modeled execution costs: ${r['costs']:,.2f}.</p>
        <p>Audit counts: {e(str(dict(counts)))}.</p><p>Ending holdings: {e(positions)}.</p>
        <div class='scroll'><table><thead><tr><th>Execution</th><th>Politician</th><th>Stock</th><th>Action</th><th>Cash amount</th><th>Official filing</th></tr></thead><tbody>{trades}</tbody></table></div></details>"""
    exclusions = Counter(r['excluded_reason'] for r in disclosures['transactions'] if r['excluded_reason'])
    coverage = ''.join(f"<li>{e(name)}: {sum(f['politician']==name for f in disclosures['filings'])} filings; {sum(r['politician']==name for r in eligible)} eligible stock rows.</li>" for name in config['names'])
    worst = max(r['return_pct'] for r in baseline)
    benchmark = baseline[0]['benchmark_pct']
    conclusion = ('All three baseline portfolios trailed SPY.' if all(r['return_pct'] < benchmark for r in baseline)
                  else 'Some baseline portfolios beat SPY in this sample; this does not establish a repeatable advantage.')
    document = f"""<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
    <title>Congress disclosure backtest · {config['start']} to {config['end']}</title><style>
    :root{{color-scheme:light}}*{{box-sizing:border-box}}body{{margin:0;background:#f4f6f9;color:#172238;font:16px/1.6 system-ui,sans-serif}}
    main{{max-width:1200px;margin:48px auto;padding:0 28px}}header{{border-bottom:1px solid #d7deea;padding-bottom:24px}}h1{{font-size:38px;line-height:1.15;letter-spacing:-1px;margin:10px 0}}h2{{font-size:23px;margin:0 0 16px}}.eyebrow{{font-size:12px;font-weight:700;letter-spacing:2px;color:#2767d8}}.muted{{color:#576579}}section{{background:white;border:1px solid #dfe5ed;border-radius:12px;padding:28px;margin:22px 0}}.cards{{display:grid;grid-template-columns:repeat(3,1fr);gap:18px;margin:22px 0}}.card{{background:#e9effb;padding:20px;border-radius:10px}}.card strong{{display:block;font-size:28px}}img{{display:block;width:100%;height:auto}}.scroll{{overflow-x:auto}}table{{width:100%;border-collapse:collapse;font-size:14px;white-space:nowrap}}th{{text-align:left;background:#f1f4f8;color:#56647a;font-size:12px}}td,th{{padding:12px;border-bottom:1px solid #e7ecf2}}a{{color:#245fca}}li{{margin:8px 0}}details{{margin:16px 0;border-top:1px solid #dde3ec;padding-top:16px}}summary{{cursor:pointer;font-weight:600}}.note{{border-left:4px solid #d69631;padding:12px 18px;background:#fff6e5}}footer{{padding:20px 0 48px;color:#576579;font-size:13px}}@media(max-width:700px){{main{{padding:0 16px;margin-top:24px}}h1{{font-size:30px}}section{{padding:18px}}.cards{{grid-template-columns:1fr}}}}@media print{{body{{background:white}}main{{margin:0;max-width:none}}section{{break-inside:avoid}}details{{display:none}}}}
    </style></head><body><main><header><div class='eyebrow'>RESEARCH / MILESTONE 01</div><h1>What if we followed the disclosures?</h1>
    <p class='muted'>{config['start']}–{config['end']} · Official House filings · ${config['initial']:,.0f} hypothetical starting cash · No live trading</p></header>
    <div class='cards'><div class='card'>Best baseline return<strong>{worst:+.2f}%</strong>under the stated allocation rules</div><div class='card'>SPY buy & hold<strong>{benchmark:+.2f}%</strong>same period and starting balance</div><div class='card'>Sample median filing lag<strong>{median(lags):.0f} days</strong>mean {mean(lags):.1f} days; selected stock rows</div></div>
    <section><h2>What this first test tells us</h2><p>{conclusion}</p><p class='note'>This is an illustrative historical test of two selected filers and one sizing rule. It is not a reproduction of their full portfolios, an independent out-of-sample result, or evidence that future returns will match.</p>
    <img alt='Daily equity curves for each disclosure strategy and SPY benchmark' src='data:image/png;base64,{base64.b64encode(graph).decode()}'></section>
    <section><h2>Results and sensitivity checks</h2><p>Returns include idle cash and ending holdings. “vs SPY” is a difference in percentage points, not risk-adjusted alpha. Each row starts with ${config['initial']:,.0f}. The 2025-only rows restart in cash on January 1, 2025 and use a 2025-only SPY comparison.</p>
    <div class='scroll'><table><thead><tr><th>Portfolio</th><th>Scenario</th><th>Ending value</th><th>Total return</th><th>vs SPY</th><th>Worst drawdown</th><th>Buys / sells</th><th>Avg. cash</th></tr></thead><tbody>{rows}</tbody></table></div></section>
    <section><h2>Exactly what was simulated</h2><ol>
    <li><strong>Timing:</strong> main scenario uses the next SPY market session's opening price strictly after the official filing date. Filing date is a proxy for availability; the archive does not prove an exact historical public-posting timestamp. The +3-day scenario adds three calendar days before choosing the next session.</li>
    <li><strong>Starting cash:</strong> no inherited holdings, borrowing, shorting, or deposits. ${config['initial']*config['buy_fraction']:,.0f} per stock buy signal in a single-politician portfolio, up to {config['cap_fraction']*100:.0f}% of initial sleeve capital in remaining cost basis per stock. Appreciation can exceed that cap. Same-session purchases share limited cash proportionally.</li>
    <li><strong>Combined portfolio:</strong> equal initial cash sleeves for the selected politicians, with the same percentage sizing rules inside each sleeve. Cash is not transferred between sleeves. A sale only affects that politician's sleeve.</li>
    <li><strong>Sales:</strong> sell all strategy-owned units on a full sale, {config['partial_fraction']*100:.0f}% on a partial sale. “Full exit on partial sale” tests 100% instead. Sales of stocks this strategy never bought are ignored.</li>
    <li><strong>Repeated signals:</strong> one action per politician/ticker/execution session, using the latest underlying trade date. Conflicting buy/sell directions on that latest date are flagged and skipped. Earlier purchases already followed by a disclosed sale are not blindly replayed.</li>
    <li><strong>Prices and costs:</strong> Yahoo Finance daily adjusted open/close values, with {config['cost_bps']:g} basis points per buy or sell. Adjusted values approximate splits and reinvested dividends; units are synthetic total-return units, not literal historical shares. Fractional units are allowed. No taxes, cash interest, settlement delays, or final liquidation costs are modeled. Positions still open are valued at the final close.</li>
    <li><strong>Benchmark:</strong> invest all starting cash in SPY at the first session's adjusted open, with the same entry cost; hold to the final adjusted close.</li>
    <li><strong>27-day scenario:</strong> assumes knowledge at trade date +27 calendar days, then trades next session. This can precede the actual filing and is explicitly a non-executable counterfactual, not a valid disclosure strategy.</li>
    </ol></section>
    <section><h2>Data coverage and limits</h2><ul>{coverage}<li>{len(disclosures['transactions'])} parsed rows; {len(eligible)} eligible common-stock rows; excluded categories: {e(str(dict(exclusions)))}.</li>
    <li>Unresolved document/row parsing issues: {len(disclosures['issues'])}. Price-download errors: {e(str(price_errors))}.</li>
    <li>Options, bonds, funds, unknown symbols and unreviewed amended rows are excluded. Spouse/dependent trades appearing in these filings are included. Khanna and McCaul are not in this run because scanned-report extraction needs separate validation.</li>
    <li>Dates and transactions come directly from <a href='https://disclosures-clerk.house.gov/FinancialDisclosure'>the House Clerk</a>, using its 2024 and 2025 filing indexes. The current archives can contain later corrections; no claim is made that today's archive is a perfectly preserved historical snapshot.</li>
    <li>Yahoo is an unofficial research price feed. Missing execution prices are recorded; missing prices for held positions abort the run. Current ticker mappings and corporate actions still need broader validation before drawing investment conclusions.</li>
    <li>A positive return can simply reflect a rising market. Selecting politicians or tuning rules after viewing these results creates selection bias. Reserve genuinely future data for validation.</li></ul></section>
    <section><h2>Inspect every simulated order</h2><p>Cash amounts include modeled costs. Each source link opens the original government filing. Complete inputs, decisions and exclusions are also in the local JSON outputs.</p>{details}</section>
    <footer>Generated locally from cached sources. Research only; no Webull credentials or brokerage connection are used.</footer></main></body></html>"""
    (output / 'report.html').write_text(document, encoding='utf-8')
