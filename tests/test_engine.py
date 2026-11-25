import unittest

from congress_backtest.engine import backtest, prepare_signals
from congress_backtest.data import parse_text

CALENDAR = ['2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05', '2024-01-08']


def prices(values=None):
    values = values or [10, 10, 20, 20, 20]
    return {'SPY': {d: {'open': 10, 'close': 10} for d in CALENDAR},
            'ABC': {d: {'open': v, 'close': v} for d, v in zip(CALENDAR, values)},
            'XYZ': {d: {'open': 10, 'close': 10} for d in CALENDAR}}


def row(action='buy', filing='2024-01-02', trade='2024-01-01', ticker='ABC', partial=False, name='A', id='1'):
    return {'id': id, 'politician': name, 'ticker': ticker, 'action': action,
            'trade_date': trade, 'filing_date': filing, 'excluded_reason': None,
            'partial': partial, 'source_url': 'https://example.test/filing'}


def run(rows, p=None, **kwargs):
    options = dict(initial=100, buy_fraction=1, cap_fraction=1, cost_bps=0)
    options.update(kwargs)
    return backtest(rows, p or prices(), ['A'], CALENDAR[0], CALENDAR[-1], **options)


class EngineTests(unittest.TestCase):
    def test_only_trade_after_filing_and_skip_weekend(self):
        s, _ = prepare_signals([row(filing='2024-01-05')], CALENDAR, ['A'], CALENDAR[0], CALENDAR[-1])
        self.assertEqual(list(s), ['2024-01-08'])
        result = run([row()])
        self.assertEqual(result['ledger'][0]['date'], '2024-01-03')
        self.assertAlmostEqual(result['return_pct'], 100)

    def test_partial_sale_cash_and_profit_reconcile(self):
        result = run([row(), row('sell', '2024-01-03', '2024-01-03', partial=True, id='2')])
        self.assertAlmostEqual(result['realized_profit'], 50)
        self.assertAlmostEqual(result['unrealized_profit'], 50)
        self.assertAlmostEqual(result['ending_value'], 200)
        self.assertAlmostEqual(result['curve'][-1]['cash'], 100)

    def test_costs_on_both_sides(self):
        result = run([row(), row('sell', '2024-01-03', '2024-01-03', id='2')], prices([10]*5), cost_bps=100)
        expected = 100 / 1.01 * .99
        self.assertAlmostEqual(result['ending_value'], expected)
        self.assertAlmostEqual(result['costs'], 100-expected)
        self.assertEqual(result['positions'], [])

    def test_cash_prorated_no_alphabetical_preference(self):
        result = run([row(), row(ticker='XYZ', id='2')])
        self.assertEqual([t['value'] for t in result['ledger']], [50, 50])
        self.assertAlmostEqual(result['ending_value'], 150)

    def test_latest_sale_in_same_filing_prevents_stale_buy(self):
        result = run([row(filing='2024-01-04'), row('sell', '2024-01-04', '2024-01-03', id='2')])
        self.assertEqual(result['buy_count'], 0)
        self.assertEqual(result['sell_count'], 0)

    def test_duplicate_same_day_signal_not_bought_twice(self):
        result = run([row(), row(id='2')], buy_fraction=.1)
        self.assertEqual(result['buy_count'], 1)
        self.assertEqual(result['ledger'][0]['value'], 10)

    def test_conflicting_same_date_direction_is_flagged(self):
        result = run([row(), row('sell', id='2')])
        self.assertEqual(result['buy_count'], 0)
        self.assertTrue(any(a['reason']=='ambiguous_same_day_buy_and_sell' for a in result['audit']))

    def test_missing_held_price_fails_instead_of_erasing_loss(self):
        p = prices()
        del p['ABC']['2024-01-04']
        with self.assertRaisesRegex(ValueError, 'Missing held-position'):
            run([row()], p)

    def test_missing_entry_and_out_of_window_signals_are_audited(self):
        result = run([row(ticker='MISSING'), row(filing='2024-01-08', id='2')])
        self.assertEqual(result['return_pct'], 0)
        self.assertEqual({a['reason'] for a in result['audit']}, {'missing_execution_price', 'execution_after_end'})

    def test_separate_sleeves_do_not_sell_each_others_positions(self):
        result = backtest([row(), row('sell', '2024-01-03', '2024-01-03', name='B', id='2')],
                          prices(), ['A', 'B'], CALENDAR[0], CALENDAR[-1], initial=100,
                          buy_fraction=1, cap_fraction=1, cost_bps=0)
        self.assertEqual(result['sell_count'], 0)
        self.assertEqual(result['ending_value'], 150)

    def test_repeated_buys_obey_cost_basis_cap(self):
        result = run([row(), row(filing='2024-01-03', id='2')], buy_fraction=.1, cap_fraction=.15)
        self.assertAlmostEqual(sum(t['value'] for t in result['ledger']), 15)

    def test_twenty_seven_days_is_explicit_counterfactual(self):
        r = row(filing='2024-01-08', trade='2023-12-06')
        actual, _ = prepare_signals([r], CALENDAR, ['A'], CALENDAR[0], CALENDAR[-1])
        counterfactual, _ = prepare_signals([r], CALENDAR, ['A'], CALENDAR[0], CALENDAR[-1], mode='lag27')
        self.assertEqual(dict(actual), {})
        self.assertEqual(list(counterfactual), ['2024-01-03'])


class ParserTests(unittest.TestCase):
    def test_wrapped_asset_and_partial_sale(self):
        text = 'Company name S (partial) 01/02/2024 01/03/2024 $1,001 -\n Common Stock (ABC) [ST] $15,000\n Fʋʎʋʐʉ Sʖʃʖʗʕ: New\n'
        filing = {'id': '1', 'politician': 'A', 'filing_date': '2024-01-04', 'url': 'source'}
        rows, errors = parse_text(text, filing)
        self.assertFalse(errors)
        self.assertEqual(rows[0]['ticker'], 'ABC')
        self.assertTrue(rows[0]['partial'])
        self.assertEqual(rows[0]['trade_date'], '2024-01-02')

    def test_amendments_and_options_are_not_stock_signals(self):
        filing = {'id': '1', 'politician': 'A', 'filing_date': '2024-01-04', 'url': 'source'}
        for code, status, reason in [('OP', 'New', 'not_common_stock'), ('ST', 'Amended', 'amendment_requires_review')]:
            rows, _ = parse_text(f'Company (ABC) [{code}] P 01/02/2024 01/03/2024 $1,001 - $15,000\nFʋʎʋʐʉ Sʖʃʖʗʕ: {status}', filing)
            self.assertEqual(rows[0]['excluded_reason'], reason)

    def test_scanned_or_unknown_layout_is_an_error(self):
        _, errors = parse_text('', {'id': '1'})
        self.assertEqual(errors[0]['reason'], 'no_machine_readable_rows')


if __name__ == '__main__':
    unittest.main()
