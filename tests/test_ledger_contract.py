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

    def test_omitted_401k_contributions_equal_explicit_zero(self):
        p=short()
        for member in p['members']:
            member.pop('annual_pretax_401k_2026_real')
            member.pop('pretax_401k_target')
        explicit=copy.deepcopy(p)
        for member in explicit['members']:
            member['annual_pretax_401k_2026_real']=0
        result=audit_plan.evaluate(p)
        self.assertEqual(result['deterministic_annual_ledger'],
                         audit_plan.evaluate(explicit)['deterministic_annual_ledger'])
        self.assertTrue(verify(result,p)['passed'])
        for row in result['deterministic_annual_ledger']['rows']:
            self.assertGreater(row['wages_gross'],0)
            self.assertEqual(row['pretax_contributions'],0)


class OutputContinuity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan=short()
        cls.result=audit_plan.evaluate(cls.plan)

    def test_reordered_duplicate_and_gapped_years_rejected(self):
        for change in ('reorder','duplicate','gap','shift'):
            for supplied_plan in (self.plan,None):
                with self.subTest(change=change,with_plan=supplied_plan is not None):
                    result=copy.deepcopy(self.result)
                    rows=result['deterministic_annual_ledger']['rows']
                    if change=='reorder': rows.reverse()
                    elif change=='duplicate': rows[1]['year']=rows[0]['year']
                    elif change=='gap': rows[1]['year']+=1
                    else:
                        for row in rows: row['year']+=1
                    with self.assertRaises(VerifyFailure): verify(result,supplied_plan)

    def test_fabricated_balance_between_years_rejected(self):
        result=copy.deepcopy(self.result)
        # Keep every year's journal and conservation equation balanced while
        # introducing $1,000 between the first and second year's ledgers.
        for row in result['deterministic_annual_ledger']['rows'][1:]:
            for phase in ('opening','closing'):
                row[phase+'_accounts']['cash']+=1000
                row[phase+'_total']+=1000
        for supplied_plan in (self.plan,None):
            with self.assertRaisesRegex(VerifyFailure,'continuity'):
                verify(result,supplied_plan)

    def test_first_year_anchored_to_plan(self):
        result=copy.deepcopy(self.result)
        for row in result['deterministic_annual_ledger']['rows']:
            for phase in ('opening','closing'):
                row[phase+'_accounts']['cash']+=1000
                row[phase+'_total']+=1000
            row['closing_total_real']+=1000/row['inflation_factor']
        # An output-only verifier cannot know the true initial balances.
        self.assertTrue(verify(result)['passed'])
        with self.assertRaisesRegex(VerifyFailure,'continuity'): verify(result,self.plan)

    def test_totals_must_equal_accounts(self):
        result=copy.deepcopy(self.result)
        for row in result['deterministic_annual_ledger']['rows']:
            row['opening_total']+=1000
            row['closing_total']+=1000
        with self.assertRaisesRegex(VerifyFailure,'account sum'): verify(result)

    def test_missing_account_journal_rejected(self):
        result=copy.deepcopy(self.result)
        result['deterministic_annual_ledger']['rows'][0]['account_flows'].pop('cash')
        with self.assertRaisesRegex(VerifyFailure,'account IDs'): verify(result,self.plan)

    def test_plan_year_range_anchor(self):
        result=copy.deepcopy(self.result)
        result['year_range']=[2028,2031]
        for row in result['deterministic_annual_ledger']['rows']: row['year']+=1
        with self.assertRaisesRegex(VerifyFailure,'year range'): verify(result,self.plan)

    def test_tax_bracket_multiplication(self):
        p=short()
        p['living_expenses_annual_real']=500000
        p['accounts'][0]['balance']=0
        p['accounts'][1].update(balance=1000000,basis=0)
        result=audit_plan.evaluate(p)
        self.assertTrue(verify(result,p)['passed'])
        for field in ('ordinary_bracket_lines','capital_gain_rate_lines'):
            for key in ('rate','taxable'):
                with self.subTest(field=field,key=key):
                    altered=copy.deepcopy(result)
                    lines=altered['deterministic_annual_ledger']['rows'][0]['tax'][field]
                    line=next(line for line in lines if line['tax']>0)
                    line[key]+=.01 if key=='rate' else 100
                    with self.assertRaisesRegex(VerifyFailure,'multiplication'): verify(altered,p)

if __name__=='__main__':unittest.main()
