"""Independent published-example and accounting tests for optional professional modules."""
import json
import math
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from social_security import pia_from_aime,claiming_factor,full_retirement_age_months,SSARuleError
from lifecycle import timeline,LifecycleError
from tax_extensions import net_investment_income_tax,TaxExtensionError
from market_history import load_annual_csv,calibrate,rolling_backtest,MarketDataError

class ProfessionalModelTests(unittest.TestCase):
    def test_ssa_pia_official_2026_case_a(self):
        # SSA OACT 2026 Case A: AIME 5825 gives PIA 2609.80 after dime truncation.
        self.assertEqual(pia_from_aime(5825,2026),2609.8)
        self.assertEqual(full_retirement_age_months(1960),804)
    def test_ssa_monthly_early_and_delayed_factors(self):
        self.assertAlmostEqual(claiming_factor(1960,744),.7)
        self.assertAlmostEqual(claiming_factor(1960,804),1.)
        self.assertAlmostEqual(claiming_factor(1960,840),1.24)
    def test_ssa_must_not_guess_future_bendpoints(self):
        with self.assertRaises(SSARuleError):
            pia_from_aime(5000,2028)
    def test_niit_lesser_of_two_and_threshold(self):
        a=net_investment_income_tax(modified_agi=210000,net_investment_income=30000,filing_status="single")
        self.assertAlmostEqual(a["niit_tax_base"],10000)
        self.assertAlmostEqual(a["niit_due"],380)
        self.assertEqual(net_investment_income_tax(modified_agi=240000,net_investment_income=9000,filing_status="mfj")["niit_due"],0)
        self.assertAlmostEqual(net_investment_income_tax(modified_agi=280000,net_investment_income=10000,filing_status="mfj")["niit_due"],380)
    def test_niit_fail_closed_other_year(self):
        with self.assertRaises(TaxExtensionError):
            net_investment_income_tax(modified_agi=250000,net_investment_income=10000,filing_status="single",tax_year=2025)
    def test_lifecycle_must_supply_survivor_values(self):
        people=[{"id":"a","birth_year":1960,"retirement_age":65,"claim_age":67,"death_year":2030,
                "annual_wages":0,"annual_pension":0,"annual_social_security":30000},
                {"id":"b","birth_year":1962,"retirement_age":65,"claim_age":67,"death_year":2039,
                "annual_wages":0,"annual_pension":0,"annual_social_security":20000}]
        with self.assertRaises(LifecycleError):
            timeline(people,2029,2032,annual_spending=100000)
        r=timeline(people,2029,2032,annual_spending=100000,
                   survivor_spending_fraction=.7,survivor_total_ss_annual=32000)
        self.assertEqual(r["rows"][2]["alive"],["b"])
        self.assertEqual(r["rows"][2]["gross_social_security"],32000)
        self.assertEqual(r["rows"][2]["assumed_living_expenses"],70000)
    def test_market_fixture_source_digest_and_windows(self):
        snap=load_annual_csv(ROOT/"examples/nyu_2000_2018_partial.csv")
        self.assertEqual(len(snap["rows"]),19)
        self.assertEqual(snap["rows"][0]["year"],2000)
        self.assertEqual(snap["rows"][-1]["year"],2018)
        self.assertEqual(calibrate(snap)["observations"],19)
        out=rolling_backtest(snap,years=10,initial_balance=1000000,annual_spending=50000)
        self.assertEqual(out["window_count"],10)
        self.assertTrue(all("first_unmet_year" in r for r in out["windows"]))
        # Independent single-year weighted 60/40 arithmetic: -9.03%,+16.66%.
        one=rolling_backtest(snap,years=1,initial_balance=100,annual_spending=0,
                             equity_weight=.6,annual_fee=0,spending_inflation=0)
        self.assertAlmostEqual(one["windows"][0]["terminal_balance"],101.25,places=2)
    def test_market_rejects_overlong_window(self):
        s=load_annual_csv(ROOT/"examples/nyu_2000_2018_partial.csv")
        with self.assertRaises(MarketDataError):
            rolling_backtest(s,years=30,initial_balance=100,annual_spending=1)

    def test_lifecycle_survivor_interval_boundaries(self):
        for deaths,start,end,requires in (
                ((2030,2030),2029,2032,False), # simultaneous deaths
                ((2028,2029),2030,2032,False), # both already dead
                ((2030,2040),2029,2030,False), # first death at interval end
                ((2040,2050),2029,2032,False), # both beyond horizon
                ((2028,2030),2030,2032,True),  # survivor alive at start
                ((2030,2040),2031,2032,True),  # survivor throughout
                ((2030,2040),2029,2031,True)):# survivor only in final year
            people=[dict(id=str(i),birth_year=1960+i,retirement_age=65,
                         claim_age=67,death_year=death,annual_wages=0,
                         annual_pension=0,annual_social_security=20000)
                    for i,death in enumerate(deaths)]
            with self.subTest(deaths=deaths,start=start,end=end):
                if requires:
                    with self.assertRaises(LifecycleError):
                        timeline(people,start,end,annual_spending=100000)
                    rows=timeline(people,start,end,annual_spending=100000,
                        survivor_spending_fraction=.7,survivor_total_ss_annual=32000)['rows']
                    for row in rows:
                        if len(row['alive'])==1:
                            self.assertEqual(row['gross_social_security'],32000)
                            self.assertEqual(row['assumed_living_expenses'],70000)
                else:
                    rows=timeline(people,start,end,annual_spending=100000)['rows']
                    self.assertTrue(all(len(row['alive'])!=1 for row in rows))
                    for row in rows:
                        if not row['alive']:
                            self.assertEqual(row['assumed_living_expenses'],0)
                            self.assertEqual(row['gross_social_security'],0)

if __name__=="__main__":
    unittest.main()
