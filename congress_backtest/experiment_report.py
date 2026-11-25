from __future__ import annotations

import base64
import html
import io
from collections import Counter
from datetime import date
from pathlib import Path


def plot_matrix(config, results):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import StrMethodFormatter
    fig, axes = plt.subplots(2, 2, figsize=(13, 8), layout='constrained')
    names_list = [[n] for n in config['names']] + [config['names']]
    colors = ['#3568c0', '#c86b32', '#138378', '#9159ac', '#ac435e', '#637c25', '#172238']
    for ax, rule in zip(axes.flat, config['rules']):
        selected = [r for r in results if r['scenario_id']=='main' and r['rule_id']==rule['id']]
        for names, color in zip(names_list, colors):
            r = next((r for r in selected if set(r['names'])==set(names)), None)
            if not r:
                continue
            ax.plot([date.fromisoformat(p['date']) for p in r['curve']], [p['equity'] for p in r['curve']],
                    label=names[0] if len(names)==1 else 'All six', color=color, linewidth=1.4 if len(names)==1 else 2.5)
        if selected:
            r = selected[0]
            ax.plot([date.fromisoformat(p['date']) for p in r['curve']], [p['benchmark'] for p in r['curve']],
                    label='SPY', color='#666666', linestyle='--')
        ax.set_title(rule['label'], loc='left', fontsize=11, fontweight='bold')
        ax.yaxis.set_major_formatter(StrMethodFormatter('${x:,.0f}'))
        ax.grid(alpha=.15)
        ax.spines[['top','right']].set_visible(False)
        ax.tick_params(axis='x', labelsize=8)
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='outside lower center', ncols=8, frameon=False)
    stream = io.BytesIO()
    fig.savefig(stream, format='png', dpi=150)
    plt.close(fig)
    return stream.getvalue()


def write_report(output, config, disclosures, payload):
    output = Path(output)
    e = html.escape
    results, failed = payload['results'], payload['failed']
    chart = plot_matrix(config, results)
    (output / 'comparison.png').write_bytes(chart)
    table_sections = ''
    groups = [[n] for n in config['names']] + [config['names']]
    for scenario in config['scenarios']:
        rows = ''
        for names in groups:
            label = names[0] if len(names)==1 else 'All six / equal sleeves'
            cells = ''
            for rule in config['rules']:
                r = next((r for r in results if r['scenario_id']==scenario['id'] and r['rule_id']==rule['id'] and set(r['names'])==set(names)), None)
                if r:
                    flag = ' *' if r['missing_entry_count'] else ''
                    cells += f"<td><strong>{r['return_pct']:+.2f}%{flag}</strong><small>DD {r['max_drawdown_pct']:.1f}% · cash {r['average_cash_pct']:.0f}%</small></td>"
                else:
                    cells += '<td>Blocked — see audit</td>'
            rows += f'<tr><th>{e(label)}</th>{cells}</tr>'
        benchmark = next((r['benchmark_pct'] for r in results if r['scenario_id']==scenario['id']), None)
        benchmark_label = f'{benchmark:+.2f}%' if benchmark is not None else 'unavailable'
        table_sections += f"<section><h2>{e(scenario['label'])}</h2><p>SPY buy and hold: <strong>{benchmark_label}</strong>. Each portfolio begins with $10,000; standalone years restart in cash. DD = worst peak-to-trough decline; cash = average uninvested share.</p><div class='scroll'><table><thead><tr><th>Portfolio</th>{''.join('<th>'+e(r['label'])+'</th>' for r in config['rules'])}</tr></thead><tbody>{rows}</tbody></table></div></section>"
    coverage = ''
    for name in config['names']:
        fs = [f for f in disclosures['filings'] if f['politician']==name]
        rs = [r for r in disclosures['transactions'] if r['politician']==name]
        included = [r for r in rs if not r['excluded_reason']]
        full_names = ', '.join(sorted({f['full_name'] for f in fs}))
        counts = Counter(r['excluded_reason'] for r in rs if r['excluded_reason'])
        coverage += f"<tr><th>{e(name)}</th><td>{e(full_names)}</td><td>{len(fs)}</td><td>{len(included)} / {len(rs)}</td><td>{e(str(dict(counts)))}</td></tr>"
    main = [r for r in results if r['scenario_id']=='main']
    beat_count = sum(r['return_pct'] > r['benchmark_pct'] for r in main)
    flagged = sum(bool(r['missing_entry_count']) for r in results)
    config_file = config['id'] + '.json'
    prior_note = ''
    if config.get('coverage_exclusions'):
        prior_note = '<p>Coverage-only exclusions from the initial expansion: ' + e(str(config['coverage_exclusions'])) + ". <a href='../expanded/report.html'>Inspect the retained first expansion</a>.</p>"
    detail_rows = ''
    for r in results:
        name = r['names'][0] if len(r['names'])==1 else 'All six'
        detail_rows += f"<tr><td>{e(name)}</td><td>{e(r['rule_id'])}</td><td>{e(r['scenario_label'])}</td><td>${r['ending_value']:,.2f}</td><td>{r['excess_percentage_points']:+.2f} pp</td><td>{r['buy_count']} / {r['sell_count']}</td><td>{r['missing_entry_count']}</td><td>{r['audit_counts'].get('no_cash_or_position_cap',0)}</td></tr>"
    failed_html = ''.join(f"<li>{e('+'.join(f['names']))} / {e(f['rule_id'])} / {e(f['scenario_label'])}: {e(f['reason'])}</li>" for f in failed) or '<li>None.</li>'
    trades = ''
    for r in main:
        name = r['names'][0] if len(r['names'])==1 else 'All six'
        orders = ''.join(f"<tr><td>{t['date']}</td><td>{e(t['politician'])}</td><td>{e(t['ticker'])}</td><td>{t['action']}</td><td>${t['value']:,.2f}</td><td><a href='{e(t['source_url'], quote=True)}' target='_blank' rel='noopener'>{e(t['source_id'])}</a></td></tr>" for t in r['ledger'])
        trades += f"<details><summary>{e(name)} · {e(r['rule_label'])}</summary><div class='scroll'><table><thead><tr><th>Date</th><th>Politician</th><th>Ticker</th><th>Action</th><th>Cash amount</th><th>Official source</th></tr></thead><tbody>{orders}</tbody></table></div></details>"
    document = f"""<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Expanded disclosure backtest</title><style>
    *{{box-sizing:border-box}}body{{margin:0;background:#f4f6fa;color:#18283c;font:16px/1.6 system-ui,sans-serif}}main{{max-width:1300px;margin:44px auto;padding:0 24px}}h1{{font-size:38px;line-height:1.2;margin:12px 0}}h2{{font-size:23px}}.eyebrow{{color:#3568c0;font-size:12px;letter-spacing:2px;font-weight:700}}section{{background:white;border:1px solid #dce3ed;border-radius:12px;margin:22px 0;padding:26px}}.note{{background:#fff3dc;border-left:4px solid #c88d27;padding:14px 20px}}.scroll{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;font-size:14px}}th,td{{padding:13px;text-align:left;border-bottom:1px solid #e2e8f0;vertical-align:top}}thead{{background:#eff3f9}}small{{display:block;white-space:nowrap;color:#58677a;font-size:12px;margin-top:4px}}img{{width:100%;height:auto}}li{{margin:8px 0}}details{{padding:14px 0;border-top:1px solid #dce3ed}}summary{{cursor:pointer;font-weight:600}}a{{color:#285dbb}}code{{overflow-wrap:anywhere}}footer{{font-size:13px;color:#58677a;margin:30px 0}}@media(max-width:700px){{main{{margin-top:24px;padding:0 14px}}h1{{font-size:29px}}section{{padding:16px}}th,td{{min-width:125px}}}}@media print{{details{{display:none}}section{{break-inside:avoid}}}}
    </style></head><body><main><header><div class='eyebrow'>RESEARCH / {e(config['id'].upper())}</div><h1>Six politicians. Four allocation rules.</h1><p>January 2024–December 2025 · $10,000 per portfolio · Official House filings · Research only</p></header>
    <section><h2>Comparison, not a winning-strategy search</h2><p>{len(results)} simulations completed; {len(failed)} blocked. In the two-year main comparison, <strong>{beat_count} of {len(main)}</strong> completed portfolio/rule combinations beat SPY. These combinations overlap and are not independent observations.</p><p class='note'>The rules and added names were fixed before computing this expanded run, but this is still retrospective exploration. A best historical result is not a recommendation. {flagged} runs have missing-entry-price flags (*); do not treat them as complete-data estimates.</p><img alt='Equity curves for six politicians, the combined portfolio and SPY under four allocation rules' src='data:image/png;base64,{base64.b64encode(chart).decode()}'></section>
    {table_sections}
    <section><h2>Rules fixed for this experiment</h2><p>{e(config['selection_rule'])}</p>{prior_note}<ul>
    <li>The first three rules spend 2%, 5%, or 10% of initial capital per eligible buy, with remaining-cost-basis caps of 10%, 20%, and 30%. They do not force investments when there are no new signals.</li>
    <li>The fourth rule spends 10% of the politician sleeve's <strong>previous session closing equity</strong>, with a 30% remaining-cost-basis cap measured against that same equity. Today's closing price never determines today's opening order. It does not automatically rebalance or sell down an appreciated position.</li>
    <li>The combined portfolio divides starting cash equally among all six and applies each rule within each sleeve. No cross-sleeve funding, borrowing, deposits or short sales. Simultaneous buys share limited cash pro rata.</li>
    <li>Trade at the next market open strictly after the filing date; the delay scenario adds three calendar days. Filing dates are availability proxies, not verified historical posting timestamps.</li>
    <li>Full sales exit the strategy position; partial sales exit an assumed 50%. Household transactions in each member's filings are included. Latest transaction per ticker/politician/execution day wins; same-date conflicting directions are skipped.</li>
    <li>Adjusted prices approximate splits and reinvested dividends. Costs are 0.1% per execution. Cash earns zero; taxes, settlement constraints and final liquidation costs are excluded. Open holdings contribute unrealized P/L.</li>
    <li>SPY is fully invested from the first session. Cash exposure differs substantially; excess return is not risk-adjusted alpha. Separate-year comparisons start fresh and are not untouched holdout tests.</li>
    <li>Options, bonds, unreviewed amended rows and unidentified stocks are excluded. Current archives and ticker histories may incorporate later corrections. Prices are from an unofficial Yahoo research feed.</li>
    </ul><p>Frozen configuration: <a href='../../experiments/{e(config_file)}'>{e(config_file)}</a>. Exact config/input hashes: <a href='run-manifest.json'>run manifest</a>. Full data: <a href='results.json'>results JSON</a>.</p></section>
    <section><h2>Coverage and exclusions</h2><div class='scroll'><table><thead><tr><th>Label</th><th>Filer names in index</th><th>Reports</th><th>Eligible / parsed rows</th><th>Exclusions</th></tr></thead><tbody>{coverage}</tbody></table></div><p>Parsing issues: {len(disclosures['issues'])}. Price-download failures: {e(str(payload['price_errors']))}.</p><p>Missing entry prices are recorded and skipped. Missing held-position valuations block the affected run, rather than discarding or zero-valuing the holding. Report counts can include filings with no eligible stock trades.</p><h3>Blocked runs</h3><ul>{failed_html}</ul></section>
    <section><h2>All run diagnostics</h2><p>The last column counts signals skipped because available cash or the position cap prevented a buy.</p><div class='scroll'><table><thead><tr><th>Portfolio</th><th>Rule</th><th>Scenario</th><th>Ending value</th><th>vs SPY</th><th>Buys / sells</th><th>Unpriced entries</th><th>Cash / cap skips</th></tr></thead><tbody>{detail_rows}</tbody></table></div></section>
    <section><h2>Main-run trade ledgers</h2>{trades}</section><footer>No brokerage connection or real orders. All completed runs reconcile realized and unrealized P/L with the account's total profit. Results are conditional on the stated assumptions and coverage.</footer></main></body></html>"""
    (output / 'report.html').write_text(document, encoding='utf-8')
