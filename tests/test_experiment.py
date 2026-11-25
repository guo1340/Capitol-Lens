import copy
import unittest

from congress_backtest.engine import backtest
from congress_backtest.data import parse_text
from congress_backtest.experiment import run_matrix
from test_engine import CALENDAR, prices, row, run


class AllocationTests(unittest.TestCase):
    def test_equity_rule_uses_previous_close_not_execution_close(self):
        rows = [row(), row(filing='2024-01-04', trade='2024-01-04', ticker='XYZ', id='2')]
        p = prices()
        # Initial $100, first buy $10 -> prior close $90 cash + $20 stock.
        result = run(rows, p, buy_fraction=.1, allocation_basis='previous_close_equity')
        self.assertAlmostEqual(result['ledger'][1]['value'], 11)
        p['ABC']['2024-01-05']['close'] = 9999
        changed = run(rows, p, buy_fraction=.1, allocation_basis='previous_close_equity')
        self.assertAlmostEqual(changed['ledger'][1]['value'], 11)

    def test_equity_rule_cap_uses_same_previous_close_equity(self):
        result = run([row(), row(filing='2024-01-04', trade='2024-01-04', id='2')],
                     buy_fraction=.1, cap_fraction=.15, allocation_basis='previous_close_equity')
        self.assertAlmostEqual(result['ledger'][1]['value'], 6.5)

    def test_initial_rule_does_not_grow_with_market_value(self):
        result = run([row(), row(filing='2024-01-04', trade='2024-01-04', ticker='XYZ', id='2')], buy_fraction=.1)
        self.assertEqual(result['ledger'][1]['value'], 10)

    def test_equity_rule_has_independent_sleeves(self):
        result = backtest([row(), row(name='B', ticker='XYZ', filing='2024-01-04', trade='2024-01-04', id='2')],
                          prices(), ['A','B'], CALENDAR[0], CALENDAR[-1], initial=200,
                          buy_fraction=.1, cap_fraction=.3, cost_bps=0,
                          allocation_basis='previous_close_equity')
        self.assertEqual(result['ledger'][1]['value'], 10)

    def test_invalid_allocation_basis_rejected(self):
        with self.assertRaises(ValueError):
            run([row()], allocation_basis='future_equity')

    def test_unheld_sale_needs_no_price_and_is_not_short_sold(self):
        result = run([row(action='sell', ticker='DELISTED')])
        self.assertEqual(result['return_pct'], 0)
        self.assertEqual([a['reason'] for a in result['audit']], ['sell_without_strategy_position'])

    def test_known_etf_and_preferred_misclassifications_are_excluded(self):
        filing = {'id':'1','politician':'A','filing_date':'2024-01-04','url':'source'}
        for ticker in ('SCHX','VIASP'):
            parsed, errors = parse_text(f'Asset ({ticker}) [ST] P 01/02/2024 01/03/2024 $1,001 - $15,000\nFʋʎʋʐʉ Sʖʃʖʗʕ: New', filing)
            self.assertFalse(errors)
            self.assertIsNotNone(parsed[0]['excluded_reason'])


class MatrixTests(unittest.TestCase):
    def config(self):
        return {'names':['A','B'], 'initial':100, 'cost_bps':10, 'partial_fraction':.5,
                'rules':[{'id':'small','label':'Small','buy_fraction':.02,'cap_fraction':.1,'allocation_basis':'initial'},
                         {'id':'equity','label':'Equity','buy_fraction':.1,'cap_fraction':.3,'allocation_basis':'previous_close_equity'}],
                'scenarios':[{'id':'main','label':'Main','start':CALENDAR[0],'end':CALENDAR[-1],'extra_days':0}]}

    def disclosures(self):
        return {'filings':[{'id':'a','politician':'A'}, {'id':'b','politician':'B'}],
                'transactions':[row(), row(name='B', ticker='XYZ', id='2')], 'issues':[]}

    def test_every_rule_portfolio_combination_preserved(self):
        result, failed = run_matrix(self.config(), self.disclosures(), prices())
        self.assertEqual(len(result), 6)
        self.assertEqual(failed, [])
        for r in result:
            self.assertAlmostEqual(r['profit'], r['realized_profit']+r['unrealized_profit'])
            self.assertTrue(all(p['cash'] >= -1e-8 for p in r['curve']))

    def test_parse_error_blocks_member_and_combination_not_other_member(self):
        d = self.disclosures()
        d['issues'] = [{'filing_id':'a','reason':'unparsed'}]
        result, failed = run_matrix(self.config(), d, prices())
        self.assertEqual(len(result), 2)
        self.assertEqual(len(failed), 4)
        self.assertTrue(all(r['names']==['B'] for r in result))

    def test_missing_price_flag_remains_visible(self):
        d = self.disclosures()
        d['transactions'][0]['ticker'] = 'UNKNOWN'
        result, _ = run_matrix(self.config(), d, prices())
        flagged = [r for r in result if 'A' in r['names']]
        self.assertTrue(all(r['coverage_status']=='incomplete_entry_prices' for r in flagged))

    def test_combined_equal_sleeves_matches_mean_individual_returns(self):
        result, _ = run_matrix(self.config(), self.disclosures(), prices())
        for rule in ('small','equity'):
            selected = [r for r in result if r['rule_id']==rule]
            singles = [r['return_pct'] for r in selected if len(r['names'])==1]
            combined = next(r for r in selected if len(r['names'])==2)
            self.assertAlmostEqual(combined['return_pct'], sum(singles)/2)


if __name__ == '__main__':
    unittest.main()
