"""Independent known-answer tests from the cited SSA and IRS formulas."""
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from ssa_benefits import (pia_from_aime,retirement_claim_factor,full_retirement_age_months,
    retirement_worker_estimate,aime_from_indexed_earnings,SSAUnsupported)
from market_history import load_history,metrics,historical_windows,paired_block_bootstrap,MarketDataError
from lifecycle_rules import lifecycle_year,LifecycleUnsupported
from tax_extensions import niit_core

class SSATests(unittest.TestCase):
    def test_official_2026_case_a(self):self.assertEqual(pia_from_aime(5825,2026),2609.8)
    def test_official_2026_maximum_earning_aime(self):self.assertEqual(pia_from_aime(14358,2026),4216.9)
    def test_2027_formula(self):self.assertEqual(pia_from_aime(1340,2027),1206.)
    def test_fra(self):
        self.assertEqual(full_retirement_age_months(1954),792)
        self.assertEqual(full_retirement_age_months(1959),802)
        self.assertEqual(full_retirement_age_months(1960),804)
    def test_age_62_and_70(self):
        self.assertAlmostEqual(retirement_claim_factor(1964,744),.7)
        self.assertAlmostEqual(retirement_claim_factor(1964,840),1.24)
    def test_aime_top_35(self):self.assertEqual(aime_from_indexed_earnings([42000.]*35+[1.]),3500)
    def test_claim_reference_year_must_match_eligibility(self):
        with self.assertRaises(SSAUnsupported):
            retirement_worker_estimate(birth_year=1964,claim_age_months=804,pia=3000,pia_reference_year=2027)

class LifeTests(unittest.TestCase):
    def test_death_year_convention(self):
        m=[{'id':'A','birth_year':1964,'death_year':2040},{'id':'B','birth_year':1965}]
        self.assertEqual(lifecycle_year(m,2040)['filing_status'],'mfj')
        with self.assertRaises(LifecycleUnsupported):lifecycle_year(m,2041)
        self.assertEqual(lifecycle_year(m,2041,verified_survivor_annual=14000)['filing_status'],'single')
    def test_no_invented_spouse_benefit(self):
        with self.assertRaises(LifecycleUnsupported):
            lifecycle_year([{'id':'A','birth_year':1970,'death_year':2030},{'id':'B','birth_year':1972}],2032)

class MarketTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.csv=Path(self.temp.name)/'market.csv'
        self.csv.write_text('year,equity_total_return,bond_total_return\n'+''.join(
            f'{2000+i},{v},{.01*i}\n' for i,v in enumerate([.1,-.25,.2,.05,-.12,.13])))
        self.series=load_history(self.csv,source_url='https://example.org/fictional',verified_by_user=False)
    def test_metrics(self):self.assertEqual(metrics(self.series)['observations'],6)
    def test_historical_window_no_wrap(self):
        windows=historical_windows(self.series,3,.6)
        self.assertEqual(len(windows),4)
        self.assertEqual(windows[0]['start_year'],2000)
    def test_reproducible_bootstrap(self):
        a=paired_block_bootstrap(self.series,horizon=20,draws=3,block_years=3,equity_weight=.6,seed=41)
        b=paired_block_bootstrap(self.series,horizon=20,draws=3,block_years=3,equity_weight=.6,seed=41)
        self.assertEqual(a,b)
        self.assertFalse(a['calibrated_future_probability'])
    def test_out_of_order_rejected(self):
        self.csv.write_text('year,equity_total_return,bond_total_return\n2001,0.2,0.01\n2000,-0.3,0.02\n2002,0.1,0.01\n2003,0.1,0.01\n2004,0.1,0.01\n')
        with self.assertRaises(MarketDataError):
            load_history(self.csv,source_url='https://example.org')

class TaxTests(unittest.TestCase):
    def test_irs_niit_base(self):
        self.assertAlmostEqual(niit_core(modified_agi=300000,net_investment_income=50000,filing_status='mfj')['niit'],1900)
        self.assertAlmostEqual(niit_core(modified_agi=260000,net_investment_income=50000,filing_status='mfj')['niit'],380)
        self.assertEqual(niit_core(modified_agi=180000,net_investment_income=70000,filing_status='single')['niit'],0)

if __name__=='__main__':unittest.main()
