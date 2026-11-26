import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from refresh_recommendations import fact,financials,rank
class ResearchTests(unittest.TestCase):
 def test_no_future_or_same_day_filings(self):
  f={'Assets':{'units':{'USD':[{'val':1,'end':'2025-12-31','filed':'2026-02-01','form':'10-K'},{'val':999,'end':'2025-12-31','filed':'2026-04-01','form':'10-K'}]}}}
  self.assertEqual(fact(f,['Assets'],'2026-04-01')['val'],1)
 def test_missing_not_zero(self):
  with self.assertRaises(ValueError):financials({'facts':{}},'2026-11-26')
 def test_annual_not_quarterly(self):
  f={'GrossProfit':{'units':{'USD':[{'val':9,'start':'2025-10-01','end':'2025-12-31','filed':'2026-02-01','form':'10-K'}]}}}
  self.assertIsNone(fact(f,['GrossProfit'],'2026-11-26',True))
 def test_ranks_reward_lower_liabilities(self):
  a={'ticker':'A','profitability':.2,'cashGeneration':.1,'liabilitiesRatio':.2};b={**a,'ticker':'B','liabilitiesRatio':.8}
  self.assertEqual(rank([b,a])[0]['ticker'],'A')
if __name__=='__main__':unittest.main()
