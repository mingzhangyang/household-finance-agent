"""2026 enhanced senior deduction: source-anchored joint-filer phaseout.

IRS Internal Revenue Manual 3.11.6 and 26 USC 151:
https://www.irs.gov/irm/part3/irm_03-011-006r
https://uscode.house.gov/us/usc/119-120/t26/s151/
The full maximum for two seniors is $12,000, reduced by 6% of joint MAGI
above $150,000 (not twice the 6% household phaseout).
"""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from tax2026 import federal_tax

def tax(magi, ages):
    return federal_tax(wages_taxable=magi,pension=0,ira_distributions=0,
        roth_conversions=0,cash_interest=0,ltcg=0,ss_benefits=0,
        status='mfj',ages=ages,year=2026)['enhanced_senior_deduction']

class SeniorDeductionRules(unittest.TestCase):
    def test_two_seniors_below_threshold(self):
        self.assertEqual(tax(150000,[70,68]),12000)
    def test_joint_phaseout_applied_once(self):
        self.assertEqual(tax(160000,[70,68]),11400)
    def test_joint_zero_at_350k(self):
        self.assertEqual(tax(350000,[70,68]),0)
    def test_one_senior(self):
        self.assertEqual(tax(160000,[70,64]),5400)
        self.assertEqual(tax(250000,[70,64]),0)
    def test_no_eligible_spouse(self):
        self.assertEqual(tax(145000,[62,64]),0)

if __name__=='__main__':unittest.main()
