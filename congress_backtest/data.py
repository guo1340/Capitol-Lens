"""Download original House filings and cache every input used by a run."""
from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

BASE = 'https://disclosures-clerk.house.gov/public_disc'
STATUS = re.compile(r'Fʋʎʋʐʉ Sʖʃʖʗʕ:\s*([^\n]+)')
TRANSACTION = re.compile(r'\b(P|S(?:\s*\(partial\))?|E)\s+(\d{2}/\d{2}/\d{4})\s+(\d{2}/\d{2}/\d{4})\s+\$')


def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf-8')


def fetch(url, path):
    path = Path(path)
    if path.exists():
        data = path.read_bytes()
        sidecar = path.with_suffix(path.suffix + '.source.json')
        if not sidecar.exists():
            save_json(sidecar, {'url': url, 'retrieved_at': None,
                               'manifest_created_at': datetime.now(timezone.utc).isoformat(),
                               'note': 'Cached during initial exploration; exact retrieval time not recorded.',
                               'sha256': hashlib.sha256(data).hexdigest()})
        return data
    path.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (personal historical research)'})
            with urllib.request.urlopen(request, timeout=45) as response:
                data = response.read()
            path.write_bytes(data)
            save_json(path.with_suffix(path.suffix + '.source.json'), {
                'url': url, 'retrieved_at': datetime.now(timezone.utc).isoformat(),
                'sha256': hashlib.sha256(data).hexdigest(),
            })
            return data
        except Exception:
            if attempt == 2:
                raise
            time.sleep(1 + attempt)


def parse_date(value):
    return datetime.strptime(value, '%m/%d/%Y').date().isoformat()


def parse_text(text, filing):
    """Fail visibly when digital PTR structure changes; never infer missing tickers."""
    rows, issues = [], []
    previous = 0
    for index, status in enumerate(STATUS.finditer(text)):
        chunk = text[previous:status.start()]
        previous = status.end()
        matches = list(TRANSACTION.finditer(chunk))
        if len(matches) != 1:
            issues.append({'filing_id': filing['id'], 'row': index, 'reason': 'unparsed_transaction', 'text': chunk})
            continue
        m = matches[0]
        # Asset codes/tickers can wrap after the dates; previous row descriptions
        # precede the current asset, so use the last explicit asset code and ticker.
        codes = re.findall(r'\[([A-Z]{2})\]', chunk)
        tickers = re.findall(r'\(([A-Z][A-Z0-9.\-]{0,9})\)', chunk)
        code = codes[-1] if codes else None
        ticker = tickers[-1] if tickers else None
        trade_date = parse_date(m.group(2))
        action = 'buy' if m.group(1) == 'P' else 'sell' if m.group(1).startswith('S') else 'exchange'
        row = {
            'id': f"{filing['id']}:{index}", 'filing_id': filing['id'],
            'politician': filing['politician'], 'ticker': ticker, 'asset_type': code,
            'action': action, 'partial': 'partial' in m.group(1),
            'trade_date': trade_date, 'filing_date': filing['filing_date'],
            'date_basis': 'official_filing_date_proxy',
            'status': status.group(1).strip(), 'source_url': filing['url'],
            'raw_text': chunk.strip(),
        }
        reason = None
        if code != 'ST':
            reason = 'not_common_stock'
        elif ticker == 'IBIT':
            # Explicitly named "iShares Bitcoin Trust ETF" in the source even
            # though the filer selected [ST]. Do not treat it as company equity.
            reason = 'bitcoin_etf_mislabeled_as_stock'
        elif ticker == 'SCHX':
            # Explicit ETF name in Foxx filing 20024424 despite the [ST] code.
            reason = 'etf_mislabeled_as_stock'
        elif ticker == 'VIASP':
            # Filing 20026516 explicitly describes perpetual preferred stock.
            reason = 'preferred_stock_outside_common_stock_universe'
        elif not ticker:
            reason = 'missing_ticker'
        elif action == 'exchange':
            reason = 'exchange_not_buy_or_sell'
        elif trade_date > filing['filing_date']:
            reason = 'trade_after_filing'
        elif row['status'].lower() != 'new':
            reason = 'amendment_requires_review'
        row['excluded_reason'] = reason
        rows.append(row)
    expected = len(TRANSACTION.findall(text))
    if expected != len(rows) + len(issues):
        issues.append({'filing_id': filing['id'], 'reason': 'row_count_mismatch', 'expected': expected, 'parsed': len(rows)})
    if not rows and not issues:
        issues.append({'filing_id': filing['id'], 'reason': 'no_machine_readable_rows'})
    return rows, issues


def collect_house(root, years, names, snapshot_name='disclosures.json'):
    import pymupdf
    root = Path(root)
    filings, rows, issues = [], [], []
    for year in years:
        archive = root / 'raw' / f'{year}FD.zip'
        fetch(f'{BASE}/financial-pdfs/{year}FD.zip', archive)
        with zipfile.ZipFile(archive) as z:
            members = ET.fromstring(z.read(f'{year}FD.xml'))
        for member in members:
            item = {node.tag: node.text or '' for node in member}
            if item['Last'] not in names or item['FilingType'] != 'P':
                continue
            filing = {
                'id': item['DocID'], 'politician': item['Last'],
                'full_name': f"{item['First']} {item['Last']}",
                'filing_date': parse_date(item['FilingDate']),
                'url': f"{BASE}/ptr-pdfs/{year}/{item['DocID']}.pdf",
            }
            filings.append(filing)
    for i, filing in enumerate(filings):
        pdf = root / 'raw' / (filing['id'] + '.pdf')
        try:
            fetch(filing['url'], pdf)
            with pymupdf.open(pdf) as document:
                text = '\n'.join(page.get_text(sort=True) for page in document)
            pdf.with_suffix('.txt').write_text(text, encoding='utf-8')
            parsed, errors = parse_text(text, filing)
            rows.extend(parsed)
            issues.extend(errors)
        except Exception as exc:
            issues.append({'filing_id': filing['id'], 'reason': 'download_or_parse_failed', 'error': str(exc)})
        print(f"Filings {i+1}/{len(filings)}: {filing['politician']} {filing['id']}", flush=True)
    result = {'filings': filings, 'transactions': rows, 'issues': issues}
    save_json(root / snapshot_name, result)
    return result


def load_prices(root, tickers, start, end, snapshot_name='normalized_prices.json'):
    """Yahoo daily adjusted OHLC: total-return approximation, not tradable share units.

    Raw JSON retained; adjusted open = raw open * adjusted close / raw close.
    Yahoo is an unofficial research feed; no claim of exchange-grade completeness.
    """
    prices, errors = {}, {}
    start_ts = int(datetime.combine(date.fromisoformat(start), datetime.min.time(), timezone.utc).timestamp())
    end_ts = int(datetime.combine(date.fromisoformat(end) + timedelta(days=1), datetime.min.time(), timezone.utc).timestamp())
    for ticker in sorted(set(tickers) | {'SPY'}):
        symbol = ticker.replace('.', '-')
        url = f'https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}?period1={start_ts}&period2={end_ts}&interval=1d&events=div%2Csplits'
        path = Path(root) / 'prices' / f'{symbol}_{start}_{end}.json'
        try:
            data = json.loads(fetch(url, path))['chart']['result'][0]
            if data['meta'].get('currency') != 'USD':
                raise ValueError('Non-USD security requires FX support')
            quotes = data['indicators']['quote'][0]
            adjusted = data['indicators']['adjclose'][0]['adjclose']
            history = {}
            for i, timestamp in enumerate(data['timestamp']):
                day = datetime.fromtimestamp(timestamp, timezone.utc).date().isoformat()
                close, opening, adj = quotes['close'][i], quotes['open'][i], adjusted[i]
                if close and opening and adj and start <= day <= end:
                    history[day] = {'open': opening * adj / close, 'close': adj}
            if not history:
                raise ValueError('No daily prices in requested window')
            prices[ticker] = history
        except Exception as exc:
            errors[ticker] = str(exc)
        print(f"Prices {ticker}: {len(prices.get(ticker, {}))} sessions", flush=True)
    save_json(Path(root) / snapshot_name, {'prices': prices, 'errors': errors, 'start': start, 'end': end})
    return prices, errors
