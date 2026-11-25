"""Run a frozen comparison matrix and retain failed runs as well as successes."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .data import collect_house, load_prices, save_json
from .engine import backtest


def run_matrix(config, disclosures, prices):
    issue_ids = {issue['filing_id'] for issue in disclosures['issues']}
    blocked_names = {f['politician'] for f in disclosures['filings'] if f['id'] in issue_ids}
    present = {f['politician'] for f in disclosures['filings']}
    groups = [[name] for name in config['names']] + [config['names']]
    results, failed = [], []
    for scenario in config['scenarios']:
        for rule in config['rules']:
            for names in groups:
                identity = {'names': names, 'rule_id': rule['id'], 'rule_label': rule['label'],
                            'scenario_id': scenario['id'], 'scenario_label': scenario['label']}
                try:
                    if set(names) & blocked_names:
                        raise ValueError('Unresolved source parsing issues for ' + ', '.join(sorted(set(names) & blocked_names)))
                    if set(names) - present:
                        raise ValueError('No filings for ' + ', '.join(sorted(set(names)-present)))
                    result = backtest(disclosures['transactions'], prices, names,
                                      start=scenario['start'], end=scenario['end'], extra_days=scenario['extra_days'],
                                      initial=config['initial'], cost_bps=config['cost_bps'],
                                      partial_fraction=config['partial_fraction'],
                                      **{key: rule[key] for key in ('buy_fraction', 'cap_fraction', 'allocation_basis')})
                    # An independent accounting identity across every complete run.
                    if abs(result['profit'] - result['realized_profit'] - result['unrealized_profit']) > 1e-6:
                        raise AssertionError('Realized/unrealized P&L reconciliation failed')
                    if any(point['cash'] < -1e-6 for point in result['curve']):
                        raise AssertionError('Cash constraint violated')
                    result.update(identity)
                    result['audit_counts'] = dict(Counter(item['reason'] for item in result['audit']))
                    result['missing_entry_count'] = result['audit_counts'].get('missing_execution_price', 0)
                    result['coverage_status'] = 'incomplete_entry_prices' if result['missing_entry_count'] else 'priced_signals'
                    results.append(result)
                except ValueError as error:
                    failed.append(dict(identity, reason=str(error)))
    return results, failed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='experiments/expanded-v2.json')
    parser.add_argument('--data', default='data')
    parser.add_argument('--output', default='output/expanded-v2')
    parser.add_argument('--offline', action='store_true')
    args = parser.parse_args()
    config_bytes = Path(args.config).read_bytes()
    config = json.loads(config_bytes)
    output, root = Path(args.output), Path(args.data)
    suffix = config.get('snapshot_suffix', 'expanded')
    disclosure_file, price_file = f'disclosures-{suffix}.json', f'prices-{suffix}.json'
    manifest = {'config': config, 'config_sha256': hashlib.sha256(config_bytes).hexdigest(),
                'run_started_at': datetime.now(timezone.utc).isoformat()}
    # Save the exact rules before acquiring data or computing returns.
    save_json(output / 'run-manifest.json', manifest)
    if args.offline:
        disclosures = json.loads((root / disclosure_file).read_text(encoding='utf-8'))
        cached = json.loads((root / price_file).read_text(encoding='utf-8'))
        if cached['start'] > config['start'] or cached['end'] < config['end']:
            raise ValueError('Cached price dates do not cover experiment')
        prices, errors = cached['prices'], cached['errors']
    else:
        disclosures = collect_house(root, range(int(config['start'][:4]), int(config['end'][:4])+1),
                                    config['names'], disclosure_file)
        tickers = {r['ticker'] for r in disclosures['transactions'] if not r['excluded_reason']}
        prices, errors = load_prices(root, tickers, config['start'], config['end'], price_file)
    results, failed = run_matrix(config, disclosures, prices)
    manifest['input_sha256'] = {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                                for name in (disclosure_file, price_file)}
    manifest['run_finished_at'] = datetime.now(timezone.utc).isoformat()
    save_json(output / 'run-manifest.json', manifest)
    payload = {'manifest': manifest, 'results': results, 'failed': failed, 'price_errors': errors}
    save_json(output / 'results.json', payload)
    from .experiment_report import write_report
    write_report(output, config, disclosures, payload)
    print(f"Completed {len(results)} runs; blocked {len(failed)}. Report: {output.resolve() / 'report.html'}")
    for result in results:
        if result['scenario_id'] == 'main':
            print(f"{'+'.join(result['names']):46} {result['rule_id']:10} {result['return_pct']:+7.2f}%  drawdown {result['max_drawdown_pct']:6.2f}%  cash {result['average_cash_pct']:5.1f}%")
    for failure in failed:
        print('BLOCKED', failure)


if __name__ == '__main__':
    main()
