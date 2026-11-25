"""Daily/manual refresh. Fresh source downloads; preserve last good asset on failure."""
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from congress_backtest.data import collect_house, load_prices
from export_web_data import export_data, NAMES


def main():
    end = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
    with tempfile.TemporaryDirectory(prefix='capitol-lens-refresh-') as temporary:
        disclosures = collect_house(temporary, range(2024,int(end[:4])+1), list(NAMES))
        if disclosures['issues']:
            raise RuntimeError(f"{len(disclosures['issues'])} source extraction issues; keeping the existing published snapshot")
        for name in NAMES:
            if not any(row['politician'] == name for row in disclosures['transactions']):
                raise RuntimeError(f'No transactions found for {name}; keeping the existing published snapshot')
        tickers = {r['ticker'] for r in disclosures['transactions'] if not r['excluded_reason']}
        prices, errors = load_prices(temporary, tickers, '2024-01-01', end)
        if 'SPY' not in prices or len(prices) < len(tickers)*.8:
            raise RuntimeError('Insufficient price coverage; keeping the existing published snapshot')
        # Unknown securities remain explicitly flagged. Never patch guessed prices.
        staged = Path(temporary)/'dataset.json'
        payload = export_data(temporary, 'disclosures.json', 'normalized_prices.json', staged)
        # Use a full-period smoke simulation to reject broken held-price coverage.
        from congress_backtest.engine import backtest
        for name in NAMES:
            backtest(disclosures['transactions'], prices, [name], '2024-01-01', end)
        target = ROOT/'web/public/data/dataset.json'
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(staged.read_bytes())
        print(f"Updated through {payload['coverageEnd']}; {len(errors)} unpriced symbols explicitly reported.")


if __name__ == '__main__':
    main()
