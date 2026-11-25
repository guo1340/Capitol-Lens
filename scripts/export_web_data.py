"""Export the existing audited snapshot into a deployment-ready private asset."""
from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from congress_backtest.data import save_json

NAMES = {'Pelosi':'Nancy Pelosi', 'Greene':'Marjorie Taylor Greene', 'Allen':'Rick Allen',
         'Doggett':'Lloyd Doggett', 'Foxx':'Virginia Foxx', 'Franklin':'Scott Franklin'}


def export_data(root, disclosure_name, price_name, output):
    root, output = Path(root), Path(output)
    disclosures = json.loads((root / disclosure_name).read_text(encoding='utf-8'))
    normalized = json.loads((root / price_name).read_text(encoding='utf-8'))
    districts = {}
    for archive in sorted((root / 'raw').glob('*FD.zip')):
        with zipfile.ZipFile(archive) as z:
            xml = next(n for n in z.namelist() if n.endswith('.xml'))
            for row in ET.fromstring(z.read(xml)):
                d = {node.tag: node.text or '' for node in row}
                if d['Last'] in NAMES:
                    districts[d['Last']] = d.get('StateDst','')
    prices, companies = {}, {}
    for ticker, history in normalized['prices'].items():
        raw_file = root / 'prices' / f"{ticker.replace('.', '-')}_{normalized['start']}_{normalized['end']}.json"
        raw = json.loads(raw_file.read_text())['chart']['result'][0]
        companies[ticker] = raw['meta'].get('longName', raw['meta'].get('shortName', ticker))
        quotes = raw['indicators']['quote'][0]
        by_date = {datetime.fromtimestamp(ts, timezone.utc).date().isoformat(): (quotes['open'][i], quotes['close'][i]) for i, ts in enumerate(raw['timestamp'])}
        prices[ticker] = [{'date': day, 'open': by_date[day][0], 'close': by_date[day][1],
                          'adjustedOpen': p['open'], 'adjustedClose': p['close']} for day, p in sorted(history.items())]
    trades = []
    for row in disclosures['transactions']:
        if row['politician'] not in NAMES:
            continue
        amount = re.search(r'\$[\d,]+\s*-\s*\$[\d,]+', row['raw_text'])
        trades.append({'id':row['id'], 'politician':row['politician'], 'ticker':row['ticker'],
                       'action':row['action'], 'partial':row['partial'], 'tradeDate':row['trade_date'],
                       'filingDate':row['filing_date'], 'amount':re.sub(r'\s+',' ',amount.group()) if amount else 'Not parsed',
                       'assetType':row['asset_type'], 'excludedReason':row['excluded_reason'], 'sourceUrl':row['source_url']})
    payload = {'schemaVersion':1, 'builtAt':datetime.now(timezone.utc).isoformat(),
               'coverageStart':normalized['start'], 'coverageEnd':normalized['end'],
               'politicians':[{'id':n,'name':name,'district':districts.get(n,''),
                               'filingCount':sum(f['politician']==n for f in disclosures['filings'])} for n,name in NAMES.items()],
               'trades':trades,'prices':prices,'priceErrors':normalized['errors'], 'companies':companies,
               'source':'US House Clerk disclosures; Yahoo historical research prices',
               'sourceIssues':len(disclosures['issues'])}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, separators=(',',':'), ensure_ascii=False, allow_nan=False), encoding='utf-8')
    print(f'Exported {len(trades)} transactions and {len(prices)} price histories to {output} ({output.stat().st_size:,} bytes).')
    return payload


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', default=str(ROOT/'data'))
    parser.add_argument('--disclosures', default='disclosures-expanded-v2.json')
    parser.add_argument('--prices', default='prices-expanded-v2.json')
    parser.add_argument('--output', default=str(ROOT/'web/public/data/dataset.json'))
    args = parser.parse_args()
    export_data(args.data, args.disclosures, args.prices, args.output)
