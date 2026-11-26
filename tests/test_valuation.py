import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from long_term_value import valuation
class ValuationTests(unittest.TestCase):
 def setUp(self):
  self.raw={'facts':{'dei':{'EntityCommonStockSharesOutstanding':{'units':{'shares':[{'val':10,'end':'2020-01-01','filed':'2020-01-02'}]}}}}}
  self.row={'facts':[{'tag':'NetCashProvidedByUsedInOperatingActivities','value':100}]}
  self.h={'rows':[{'date':'2020-02-01','rawClose':50}],'splits':[],'sourceUrl':'test'}
 def test_uses_prior_price_and_published_shares(self):
  v=valuation(self.raw,self.h,'2020-02-02',self.row);self.assertEqual(v['cashYield'],.2)
 def test_future_filing_not_usable(self):
  self.raw['facts']['dei']['EntityCommonStockSharesOutstanding']['units']['shares'][0]['filed']='2020-02-02'
  with self.assertRaises(ValueError):valuation(self.raw,self.h,'2020-02-02',self.row)
 def test_split_adjusts_share_count(self):
  self.h['splits']=[{'date':'2020-01-15','ratio':2}]
  self.assertEqual(valuation(self.raw,self.h,'2020-02-02',self.row)['cashYield'],.1)
 def test_stale_price_rejected(self):
  with self.assertRaises(ValueError):valuation(self.raw,self.h,'2020-03-01',self.row)
if __name__=='__main__':unittest.main()

class PortfolioTests(unittest.TestCase):
 def test_known_return_and_costs(self):
  from unittest.mock import patch
  from long_term_value import simulate
  h={'rows':[{'date':'2020-01-02','open':100,'close':100},{'date':'2020-01-03','open':200,'close':200}]}
  with patch('long_term_value.selection',return_value=([],[{'ticker':'TEST','weight':5}],[])):
   r=simulate({}, {'SPY':h,'TEST':h},'2020-01-01','2020-01-04')
  self.assertAlmostEqual(r['returnPercent'],4.995)
  self.assertAlmostEqual(r['costs'],.5)
  self.assertEqual(r['orderCount'],1)
 def test_held_price_gap_stops_comparison(self):
  from unittest.mock import patch
  from long_term_value import simulate
  h={'rows':[{'date':'2020-01-02','open':100,'close':100},{'date':'2020-01-03','open':200,'close':200}]}
  with patch('long_term_value.selection',return_value=([],[{'ticker':'TEST','weight':5}],[])):
   with self.assertRaisesRegex(ValueError,'missing_held_price'):simulate({}, {'SPY':h,'TEST':{'rows':h['rows'][:1]}},'2020-01-01','2020-01-04')
