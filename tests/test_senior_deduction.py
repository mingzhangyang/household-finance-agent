"""2026 enhanced senior deduction: source-anchored joint-filer phaseout.

IRS Schedule 1-A Part V, lines 31–37:
https://www.irs.gov/pub/irs-pdf/f1040s1a.pdf
Reduce each eligible person’s $6,000 by 6% of joint MAGI above $150,000,
then sum the amounts for both eligible spouses.
"""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from tax2026 import federal_tax

def tax(magi, ages, year=2026, status='mfj'):
    return federal_tax(wages_taxable=magi,pension=0,ira_distributions=0,
        roth_conversions=0,cash_interest=0,ltcg=0,ss_benefits=0,
        status=status,ages=ages,year=year)['enhanced_senior_deduction']

class SeniorDeductionRules(unittest.TestCase):
    def test_two_seniors_below_threshold(self):
        self.assertEqual(tax(150000,[70,68]),12000)
    def test_joint_phaseout_applied_per_person(self):
        self.assertEqual(tax(160000,[70,68]),10800)
    def test_joint_zero_at_250k(self):
        self.assertEqual(tax(250000,[70,68]),0)
    def test_one_senior(self):
        self.assertEqual(tax(160000,[70,64]),5400)
        self.assertEqual(tax(250000,[70,64]),0)
    def test_no_eligible_spouse(self):
        self.assertEqual(tax(145000,[62,64]),0)
    def test_phaseout_boundary_and_expiration(self):
        for year in (2026,2027,2028):
            self.assertAlmostEqual(tax(249999,[70,68],year),.12)
            self.assertEqual(tax(250001,[70,68],year),0)
            self.assertEqual(tax(160000,[70,68],year),10800)
        self.assertEqual(tax(150000,[70,68],2029),0)
    def test_single_senior_phaseout(self):
        for magi,expected in ((75000,6000),(85000,5400),(175000,0)):
            self.assertEqual(tax(magi,[70],status='single'),expected)

if __name__=='__main__':unittest.main()
