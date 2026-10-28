"""NIIT cash-flow integration checks using independently computable figures.
These are fictional test households, never personal statements.
"""
import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import audit_plan
from tax_extensions import net_investment_income_tax,TaxExtensionError
from verify_outputs import verify,VerifyFailure
import json
P=json.loads((Path(__file__).resolve().parents[1]/'examples/audited-household-2026.json').read_text())

def fixture():
    p=copy.deepcopy(P)
    p['members']=[{'id':'a','birth_year':1980,'retirement_age':65,
        'annual_wages_2026':300000,'wage_growth':0,
        'ss_claim_age':67,'ss_annual_2026_real_at_chosen_claim_age':0,
        'ss_estimate_basis':'2026_real_at_selected_claim_age',
        'annual_pretax_401k_2026_real':20000,'pretax_401k_target':'retirement'}]
    p['tax_policy']['filing_status']='single'
    p['tax_policy']['future_bracket_inflation']=0
    p['accounts']=[{'id':'cash','kind':'cash','balance':200000},
      {'id':'brokerage','kind':'taxable','balance':0,'basis':0,
       'gain_treatment':'long_term_proportional_no_loss_offset'},
      {'id':'retirement','kind':'traditional_401k','balance':0,'owner':'a',
       'fully_pretax_confirmed':True,'still_working_exception':False},
      {'id':'ira','kind':'traditional_ira','balance':0,'owner':'a',
       'fully_pretax_confirmed':True,'rmd_table':'uniform'},
      {'id':'roth','kind':'roth_ira','balance':0,'owner':'a',
       'qualified_distributions_confirmed':True}]
    p['withdrawal_order']=['cash','brokerage','ira','retirement','roth']
    p['as_of_year']=2026
    p['end_year']=2027
    p['living_expenses_annual_real']=60000
    p['events']=[]
    p['roth_conversions']=[]
    p['assumptions']['inflation']=0
    p['assumptions']['cash_yield']=.05
    p['assumptions']['trials']=3
    return p

class NIITIntegration(unittest.TestCase):
    def test_irs_lesser_of_calculation(self):
        self.assertAlmostEqual(net_investment_income_tax(
            modified_agi=310000,net_investment_income=20000,
            filing_status='mfj')['niit_due'],760)
        self.assertAlmostEqual(net_investment_income_tax(
            modified_agi=210000,net_investment_income=30000,
            filing_status='single')['niit_due'],380)
    def test_one_year_niit_funding_and_3_8pct_precision(self):
        p=fixture()
        r=audit_plan.run_path(p,[0])['rows'][0]
        self.assertAlmostEqual(r['tax']['niit_net_investment_income'],10000)
        self.assertEqual(r['tax']['niit_rate'],.038)
        self.assertAlmostEqual(r['tax']['niit_due'],380)
        self.assertAlmostEqual(r['tax_due_total'],
            r['tax']['federal_income_tax']+r['tax']['niit_due']+
            r['payroll_tax']['total'],delta=.03)
        self.assertEqual(r['unpaid_tax'],0)
    def test_niit_affects_asset_liquidation(self):
        p=fixture();p['members'][0]['annual_wages_2026']=0
        p['members'][0]['annual_pretax_401k_2026_real']=0
        p['accounts'][0]['balance']=0
        p['accounts'][1]['balance']=1000000
        p['accounts'][1]['basis']=400000
        p['living_expenses_annual_real']=400000
        r=audit_plan.run_path(p,[0])['rows'][0]
        self.assertGreater(r['tax']['niit_due'],0)
        self.assertGreater(r['realized_ltcg'],200000)
        self.assertEqual(r['unmet_spending'],0)
        self.assertEqual(r['unpaid_tax'],0)
    def test_output_verifier_catches_niit_tampering(self):
        p=fixture();r=audit_plan.evaluate(p)
        self.assertTrue(verify(r,p,Path(__file__).resolve().parents[1]/'scripts')['passed'])
        x=copy.deepcopy(r)
        x['deterministic_annual_ledger']['rows'][0]['tax']['niit_tax_base']+=100
        with self.assertRaises(VerifyFailure):verify(x,p)
        x=copy.deepcopy(r)
        x['deterministic_annual_ledger']['rows'][0]['tax']['niit_rate']=.04
        with self.assertRaises(VerifyFailure):verify(x,p)
    def test_hypothetical_future_threshold(self):
        r=net_investment_income_tax(modified_agi=260000,net_investment_income=10000,
            filing_status='mfj',tax_year=2046)
        self.assertEqual(r['threshold'],250000)
        self.assertEqual(r['reference_tax_year'],2026)
        self.assertIn('hypothetically',r['policy'])

if __name__=='__main__':
    unittest.main()
