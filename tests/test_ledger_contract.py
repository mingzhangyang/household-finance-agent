"""Small independent regression gates for main annual cash and tax engine.

The complete legacy v2.1 development test suite is not yet stored in Git;
this file gives the GitHub PR an executable annual-accounting baseline.
"""
import copy,hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import audit_plan
from verify_outputs import verify,VerifyFailure
P=json.loads((ROOT/'examples/audited-household-2026.json').read_text())

def short():
    p=copy.deepcopy(P)
    p['end_year']=2030
    p['events']=[]
    p['assumptions']['trials']=12
    return p

class AnnualLedgerContract(unittest.TestCase):
    def test_fiction_only_schema(self):
        self.assertTrue(audit_plan.validate(P))
    def test_each_year_conserves_total_and_each_account(self):
        p=short()
        result=audit_plan.run_path(p,[.05]*4)
        for row in result['rows']:
            self.assertLess(abs(row['reconciliation_residual']),.01)
            for v in row['account_reconciliation_residuals'].values():
                self.assertLess(abs(v),.01)
    def test_income_and_deduction_reconcile(self):
        row=audit_plan.run_path(short(),[0]*4)['rows'][0]
        self.assertAlmostEqual(row['wages_gross']-row['pretax_contributions'],
            row['wages_taxable'],delta=.03)
        self.assertAlmostEqual(row['tax']['ordinary_tax'],
            sum(b['tax'] for b in row['tax']['ordinary_bracket_lines']),delta=.03)
        self.assertAlmostEqual(row['tax']['capital_gains_tax'],
            sum(b['tax'] for b in row['tax']['capital_gain_rate_lines']),delta=.03)
        self.assertAlmostEqual(row['tax_due_total'],row['tax']['federal_income_tax']+
            row['tax']['niit_due']+row['payroll_tax']['total'],delta=.03)
    def test_cash_account_in_ledger(self):
        result=audit_plan.run_path(short(),[0]*4)
        for row in result['rows']:
            self.assertEqual(row['cash_account_id'],'cash')
            self.assertIn('cash',row['account_flows'])
    def test_input_sha_and_engine_source_hash(self):
        p=short();result=audit_plan.evaluate(p)
        self.assertTrue(verify(result,p,ROOT/'scripts')['passed'])
        expected=hashlib.sha256((ROOT/'scripts/audit_plan.py').read_bytes()+
              (ROOT/'scripts/tax2026.py').read_bytes()+
              (ROOT/'scripts/tax_extensions.py').read_bytes()).hexdigest()
        self.assertEqual(result['engine_source_sha256'],expected)
    def test_tampered_ledger_rejected(self):
        p=short();result=audit_plan.evaluate(p)
        result['deterministic_annual_ledger']['rows'][0]['tax_due_total']+=100
        with self.assertRaises(VerifyFailure):
            verify(result,p)
    def test_missing_taxable_cost_basis_rejected(self):
        p=short();p['accounts'][1].pop('basis')
        with self.assertRaises(audit_plan.ModelError):audit_plan.validate(p)
    def test_missing_401k_owner_rejected(self):
        p=short();p['accounts'][2].pop('owner')
        with self.assertRaises(audit_plan.ModelError):audit_plan.validate(p)
    def test_state_tax_claim_rejected(self):
        p=short();p['tax_policy']['state_income_tax']='Virginia'
        with self.assertRaises(audit_plan.ModelError):audit_plan.validate(p)
    def test_unsupported_ss_claim_benefit_reuse_rejected(self):
        p=short();p['members'][0]['ss_estimate_basis']='age_67_regardless_of_claim'
        with self.assertRaises(audit_plan.ModelError):audit_plan.validate(p)
    def test_1959_1960_rmd_reference_age(self):
        self.assertEqual(audit_plan.rmd_age(1959),73)
        self.assertEqual(audit_plan.rmd_age(1960),75)
    def test_seeded_scenario_reproduces_exact_summaries(self):
        p=short()
        a=audit_plan.evaluate(p);b=audit_plan.evaluate(p)
        self.assertEqual(a['simulated_path_manifest'],b['simulated_path_manifest'])
        self.assertEqual(a['success_paths'],b['success_paths'])

if __name__=='__main__':unittest.main()
