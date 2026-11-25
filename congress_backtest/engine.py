"""Deterministic, cash-constrained daily event simulator."""
from __future__ import annotations

from bisect import bisect_right
from collections import defaultdict
from datetime import date, timedelta
from statistics import mean


def prepare_signals(rows, calendar, names, start, end, mode='filing', extra_days=0):
    grouped = defaultdict(list)
    audit = []
    for row in rows:
        if row['politician'] not in names or row.get('excluded_reason'):
            continue
        known = (date.fromisoformat(row['trade_date']) + timedelta(days=27)).isoformat() if mode == 'lag27' else row['filing_date']
        # Start each requested period in cash, with no inherited earlier signals.
        if not start <= known <= end:
            continue
        available = (date.fromisoformat(known) + timedelta(days=extra_days)).isoformat()
        index = bisect_right(calendar, available)
        if index >= len(calendar):
            audit.append({'id': row['id'], 'reason': 'execution_after_end'})
            continue
        day = calendar[index]
        grouped[(day, row['politician'], row['ticker'])].append(row)
    scheduled = defaultdict(list)
    for (day, politician, ticker), batch in sorted(grouped.items()):
        # A single filing may reveal both an earlier buy and a later sale.
        # Use the latest dated activity; never blindly replay stale buys first.
        latest = max(r['trade_date'] for r in batch)
        candidates = [r for r in batch if r['trade_date'] == latest]
        if len({r['action'] for r in candidates}) > 1:
            audit.append({'date': day, 'politician': politician, 'ticker': ticker, 'reason': 'ambiguous_same_day_buy_and_sell'})
            continue
        chosen = sorted(candidates, key=lambda r: (r['partial'], r['id']))[0]
        scheduled[day].append(chosen)
        if len(batch) > 1:
            audit.append({'date': day, 'politician': politician, 'ticker': ticker,
                          'reason': 'collapsed_same_session_signals', 'kept': chosen['id'],
                          'source_ids': [r['id'] for r in batch]})
    return scheduled, audit


def backtest(rows, prices, names, start, end, initial=10000.0, buy_fraction=.05,
             cap_fraction=.20, cost_bps=10.0, partial_fraction=.5, mode='filing', extra_days=0,
             allocation_basis='initial'):
    if allocation_basis not in ('initial', 'previous_close_equity'):
        raise ValueError('Unknown allocation basis')
    if initial <= 0 or not 0 < buy_fraction <= cap_fraction <= 1:
        raise ValueError('Positive cash and 0 < buy_fraction <= cap_fraction <= 1 required')
    if not 0 <= cost_bps < 10000 or not 0 < partial_fraction <= 1:
        raise ValueError('Invalid cost or partial-sale fraction')
    names = sorted(set(names))
    if not names:
        raise ValueError('At least one politician required')
    calendar = sorted(day for day in prices['SPY'] if start <= day <= end)
    if not calendar:
        raise ValueError('No benchmark sessions')
    scheduled, audit = prepare_signals(rows, calendar, names, start, end, mode, extra_days)
    sleeve = initial / len(names)
    cash = {name: sleeve for name in names}
    sizing_equity = {name: sleeve for name in names}
    holdings, basis = {}, {}
    ledger, curve = [], []
    costs = 0.0
    realized = []
    cost = cost_bps / 10000
    benchmark_units = initial / (prices['SPY'][calendar[0]]['open'] * (1 + cost))
    peak, max_drawdown = initial, 0.0
    for day in calendar:
        orders = scheduled.get(day, [])
        valid = []
        for row in orders:
            if row['action'] == 'sell' and holdings.get((row['politician'], row['ticker']), 0) <= 1e-12:
                audit.append({'id': row['id'], 'date': day, 'reason': 'sell_without_strategy_position'})
                continue
            if day not in prices.get(row['ticker'], {}):
                audit.append({'id': row['id'], 'ticker': row['ticker'], 'date': day, 'reason': 'missing_execution_price'})
            else:
                valid.append(row)
        for row in [r for r in valid if r['action'] == 'sell']:
            key = (row['politician'], row['ticker'])
            units = holdings.get(key, 0)
            if units <= 1e-12:
                audit.append({'id': row['id'], 'date': day, 'reason': 'sell_without_strategy_position'})
                continue
            fraction = partial_fraction if row['partial'] else 1.0
            quantity = units * fraction
            price = prices[row['ticker']][day]['open']
            gross = quantity * price
            proceeds = gross * (1 - cost)
            sold_basis = basis[key] * fraction
            profit = proceeds - sold_basis
            realized.append(profit)
            cash[key[0]] += proceeds
            holdings[key] -= quantity
            basis[key] -= sold_basis
            costs += gross * cost
            ledger.append({'date': day, 'politician': key[0], 'ticker': key[1], 'action': 'sell',
                           'value': proceeds, 'units': quantity, 'adjusted_price': price,
                           'realized_profit': profit, 'source_id': row['id'], 'source_url': row['source_url']})
        requests = defaultdict(list)
        for row in [r for r in valid if r['action'] == 'buy']:
            key = (row['politician'], row['ticker'])
            capital = sleeve if allocation_basis == 'initial' else sizing_equity[key[0]]
            budget = max(0.0, min(capital * buy_fraction, capital * cap_fraction - basis.get(key, 0)))
            requests[key[0]].append((row, budget))
        for name, batch in requests.items():
            requested = sum(budget for _, budget in batch)
            scale = min(1.0, cash[name] / requested) if requested else 0.0
            for row, budget in batch:
                spend = budget * scale
                if spend <= 1e-8:
                    audit.append({'id': row['id'], 'date': day, 'reason': 'no_cash_or_position_cap'})
                    continue
                key = (name, row['ticker'])
                price = prices[row['ticker']][day]['open']
                quantity = spend / (price * (1 + cost))
                holdings[key] = holdings.get(key, 0) + quantity
                basis[key] = basis.get(key, 0) + spend
                cash[name] -= spend
                costs += spend - quantity * price
                ledger.append({'date': day, 'politician': name, 'ticker': key[1], 'action': 'buy',
                               'value': spend, 'units': quantity, 'adjusted_price': price,
                               'source_id': row['id'], 'source_url': row['source_url']})
        market_value = 0.0
        sleeve_market_values = {name: 0.0 for name in names}
        for (name, ticker), units in holdings.items():
            if units <= 1e-12:
                continue
            if day not in prices.get(ticker, {}):
                raise ValueError(f'Missing held-position valuation: {ticker} {day}; result refused rather than silently dropping a holding')
            market_value += units * prices[ticker][day]['close']
            sleeve_market_values[name] += units * prices[ticker][day]['close']
        sizing_equity = {name: cash[name] + sleeve_market_values[name] for name in names}
        total_cash = sum(cash.values())
        if total_cash < -1e-6 or any(u < -1e-8 for u in holdings.values()):
            raise AssertionError('Negative cash or short position')
        equity = total_cash + market_value
        peak = max(peak, equity)
        max_drawdown = min(max_drawdown, equity / peak - 1)
        curve.append({'date': day, 'equity': equity, 'cash': total_cash,
                      'benchmark': benchmark_units * prices['SPY'][day]['close']})
    final = curve[-1]
    elapsed_years = ((date.fromisoformat(end) - date.fromisoformat(start)).days + 1) / 365.25
    total_return = final['equity'] / initial - 1
    benchmark_return = final['benchmark'] / initial - 1
    positions = [{'politician': name, 'ticker': ticker, 'value': units * prices[ticker][calendar[-1]]['close'],
                  'cost_basis': basis[(name, ticker)], 'adjusted_units': units}
                 for (name, ticker), units in holdings.items() if units > 1e-12]
    annual = []
    previous = initial
    for year in sorted({p['date'][:4] for p in curve}):
        last = [p for p in curve if p['date'].startswith(year)][-1]['equity']
        annual.append({'year': year, 'return_pct': (last / previous - 1) * 100})
        previous = last
    return {'names': names, 'start': start, 'end': end, 'mode': mode, 'extra_days': extra_days,
            'allocation_basis': allocation_basis, 'buy_fraction': buy_fraction, 'cap_fraction': cap_fraction,
            'initial': initial, 'ending_value': final['equity'], 'profit': final['equity'] - initial,
            'return_pct': total_return * 100, 'annualized_pct': ((1 + total_return) ** (1 / elapsed_years) - 1) * 100,
            'benchmark_pct': benchmark_return * 100, 'excess_percentage_points': (total_return - benchmark_return) * 100,
            'max_drawdown_pct': max_drawdown * 100, 'costs': costs,
            'buy_count': sum(r['action'] == 'buy' for r in ledger), 'sell_count': len(realized),
            'winning_exit_pct': 100 * mean(p > 0 for p in realized) if realized else None,
            'average_cash_pct': mean(p['cash'] / p['equity'] for p in curve) * 100,
            'realized_profit': sum(realized), 'unrealized_profit': sum(p['value'] - p['cost_basis'] for p in positions),
            'annual_returns': annual, 'positions': positions, 'ledger': ledger, 'curve': curve, 'audit': audit}
