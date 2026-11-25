import argparse
import json
from pathlib import Path

from .data import collect_house, load_prices, save_json
from .engine import backtest
from .report import write_report


def main():
    parser = argparse.ArgumentParser(description='Historical disclosure-following backtest. Never places real orders.')
    parser.add_argument('--names', nargs='+', default=['Pelosi', 'Greene'])
    parser.add_argument('--start', default='2024-01-01')
    parser.add_argument('--end', default='2025-12-31')
    parser.add_argument('--initial', type=float, default=10000)
    parser.add_argument('--buy-fraction', type=float, default=.05)
    parser.add_argument('--cap-fraction', type=float, default=.20)
    parser.add_argument('--cost-bps', type=float, default=10)
    parser.add_argument('--partial-fraction', type=float, default=.5)
    parser.add_argument('--offline', action='store_true', help='Use cached normalized inputs only; no network')
    parser.add_argument('--data', default='data')
    parser.add_argument('--output', default='output')
    args = parser.parse_args()
    config = vars(args).copy()
    root = Path(args.data)
    if args.start > args.end:
        parser.error('start must precede end')
    if args.offline:
        disclosures = json.loads((root / 'disclosures.json').read_text(encoding='utf-8'))
        cached = json.loads((root / 'normalized_prices.json').read_text(encoding='utf-8'))
        if cached['start'] > args.start or cached['end'] < args.end:
            parser.error('cached prices do not cover this date range')
        prices, price_errors = cached['prices'], cached['errors']
    else:
        disclosures = collect_house(root, range(int(args.start[:4]), int(args.end[:4])+1), args.names)
        eligible = [r for r in disclosures['transactions'] if not r['excluded_reason']]
        prices, price_errors = load_prices(root, {r['ticker'] for r in eligible}, args.start, args.end)
    available_names = {f['politician'] for f in disclosures['filings']}
    if set(args.names) - available_names:
        parser.error(f'No cached/downloaded filings for {set(args.names)-available_names}')
    if disclosures['issues']:
        raise RuntimeError('Unresolved filing extraction issues: inspect data/disclosures.json before running returns')
    common = dict(initial=args.initial, buy_fraction=args.buy_fraction, cap_fraction=args.cap_fraction,
                  cost_bps=args.cost_bps, partial_fraction=args.partial_fraction)
    groups = [[name] for name in args.names]
    if len(args.names) > 1:
        groups.append(args.names)
    results = []
    scenarios = [('Filing date', {}), ('Filing +3 calendar days', {'extra_days': 3}),
                 ('Full exit on partial sale', {'partial_fraction': 1}), ('27-day counterfactual', {'mode': 'lag27'})]
    if args.start < f'{args.end[:4]}-01-01':
        scenarios.append((f'{args.end[:4]} only / filing date', {'start': f'{args.end[:4]}-01-01'}))
    for label, overrides in scenarios:
        for names in groups:
            settings = dict(common, start=args.start, end=args.end)
            settings.update(overrides)
            result = backtest(disclosures['transactions'], prices, names, **settings)
            result['scenario'] = label
            results.append(result)
            print(f"{'+'.join(names):20} {label:30} {result['return_pct']:+.2f}% vs SPY {result['benchmark_pct']:+.2f}%", flush=True)
    save_json(Path(args.output) / 'results.json', {'config': config, 'results': results})
    write_report(args.output, results, disclosures, price_errors, config)
    print(f'Report: {Path(args.output).resolve() / "report.html"}')


if __name__ == '__main__':
    main()
