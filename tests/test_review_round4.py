"""Regression and coherent-tampering checks for the fourth Copilot review."""
import copy
import unittest

from test_niit_integration import fixture
import audit_plan
from verify_outputs import verify, VerifyFailure


class AnnualMonteCarloChecks(unittest.TestCase):
    def setUp(self):
        self.plan=fixture()
        self.plan['end_year']=2029
        self.result=audit_plan.evaluate(self.plan)

    def test_missing_duplicate_and_reordered_years(self):
        original=self.result['annual_real_percentiles']
        for bands in ([],original[:-1],[original[0]]*3,list(reversed(original))):
            with self.subTest(bands=bands):
                result=copy.deepcopy(self.result)
                result['annual_real_percentiles']=bands
                with self.assertRaisesRegex(VerifyFailure,'annual MC'):
                    verify(result,self.plan)

    def test_nonfinite_and_unordered_percentiles(self):
        for values in ((float('nan'),1,2),(0,float('inf'),2),(True,1,2),(3,2,1)):
            with self.subTest(values=values):
                result=copy.deepcopy(self.result)
                result['annual_real_percentiles'][0].update(zip(('p10','p50','p90'),values))
                with self.assertRaisesRegex(VerifyFailure,'annual MC'):
                    verify(result,self.plan)

    def test_fabricated_final_percentiles(self):
        self.result['annual_real_percentiles'][-1].update(p10=1,p50=2,p90=3)
        with self.assertRaisesRegex(VerifyFailure,'annual MC terminal'):
            verify(self.result,self.plan)

    def test_every_year_funded_count_checked(self):
        for index in range(3):
            result=copy.deepcopy(self.result)
            result['annual_real_percentiles'][index]['paths_funded_to_date']-=1
            with self.assertRaisesRegex(VerifyFailure,'annual MC funded count'):
                verify(result,self.plan)

    def test_failure_year_is_not_counted_as_funded(self):
        plan=fixture()
        plan['end_year']=2029
        plan['roth_conversions']=[dict(year=2028,**{'from':'ira','to':'roth'},amount_nominal=1)]
        result=audit_plan.evaluate(plan)
        self.assertEqual([r['paths_funded_to_date'] for r in result['annual_real_percentiles']],[3,0,0])
        self.assertTrue(verify(result,plan)['passed'])
        result['annual_real_percentiles'][1]['paths_funded_to_date']=3
        with self.assertRaisesRegex(VerifyFailure,'annual MC funded count'):
            verify(result,plan)


class JournalChecks(unittest.TestCase):
    def test_omitted_tax_bands_with_coherent_tax_and_cash(self):
        plan=fixture()
        result=audit_plan.evaluate(plan)
        row=result['deterministic_annual_ledger']['rows'][0]
        saved=row['tax']['ordinary_tax']
        row['tax']['ordinary_bracket_lines']=[]
        row['tax']['ordinary_tax']=0
        for key in ('federal_income_tax','total_federal_income_and_niit'):
            row['tax'][key]-=saved
        for key in ('tax_due_total','tax_paid'):
            row[key]-=saved
        row['account_flows']['cash']['cash_tax_and_spending_outflow']-=saved
        row['closing_accounts']['cash']+=saved
        row['closing_total']+=saved
        row['closing_total_real']+=saved
        with self.assertRaisesRegex(VerifyFailure,'ordinary taxable coverage'):
            verify(result,plan)

    def test_lowered_rmd_balance_cannot_hide_shortfall(self):
        plan=fixture()
        plan['members'][0].update(birth_year=1951,annual_wages_2026=0,annual_pretax_401k_2026_real=0)
        plan['accounts'][0]['balance']=1000000
        plan['accounts'][3]['balance']=1000
        result=audit_plan.evaluate(plan)
        summary=audit_plan.run_path(plan,[-.999])
        result['deterministic_annual_ledger']=summary
        row=summary['rows'][0]
        self.assertTrue(verify(result,plan)['passed'])
        for item in row['rmd']:
            item['previous_dec31_balance']=item['taken']*item['divisor']
            item['required']=item['taken']
            item['unmet']=0
        row['unmet_rmd']=0
        summary.update(failed=False,first_failure_year=None)
        with self.assertRaisesRegex(VerifyFailure,'RMD opening balance'):
            verify(result,plan)

    def conversion_result(self):
        plan=fixture()
        plan['accounts'][3]['balance']=50000
        plan['roth_conversions']=[dict(year=2027,**{'from':'ira','to':'roth'},amount_nominal=v)
                                  for v in (1000.123,2000.456)]
        return plan,audit_plan.evaluate(plan)

    def test_multiple_unrounded_conversions_pass(self):
        plan,result=self.conversion_result()
        self.assertEqual(result['deterministic_annual_ledger']['rows'][0]['roth_converted'],3000.58)
        self.assertTrue(verify(result,plan)['passed'])

    def test_changed_transfer_total_rejected(self):
        plan,result=self.conversion_result()
        result['deterministic_annual_ledger']['rows'][0]['conversion_transfers'][0]['amount']+=100
        with self.assertRaisesRegex(VerifyFailure,'conversion taxable aggregate'):
            verify(result,plan)

    def test_changed_transfer_source_or_destination_rejected(self):
        for key,account,diagnostic in (('from','retirement','outflow'),('to','cash','inflow')):
            plan,result=self.conversion_result()
            result['deterministic_annual_ledger']['rows'][0]['conversion_transfers'][0][key]=account
            with self.assertRaisesRegex(VerifyFailure,'conversion '+diagnostic):
                verify(result,plan)

    def test_removed_transfers_and_taxable_aggregate_rejected(self):
        plan,result=self.conversion_result()
        row=result['deterministic_annual_ledger']['rows'][0]
        # Recompute all affected income/tax fields using a no-conversion run,
        # while retaining the conversion journal and coherently adjusting cash.
        no_conversion=copy.deepcopy(plan)
        no_conversion['roth_conversions']=[]
        baseline=audit_plan.evaluate(no_conversion)['deterministic_annual_ledger']['rows'][0]
        saved=row['tax_paid']-baseline['tax_paid']
        row['tax']=baseline['tax']
        row['tax_paid']=baseline['tax_paid']
        row['tax_due_total']=baseline['tax_due_total']
        row['roth_converted']=0
        row['conversion_transfers']=[]
        row['account_flows']['cash']['cash_tax_and_spending_outflow']-=saved
        row['closing_accounts']['cash']+=saved
        row['closing_total']+=saved
        row['closing_total_real']+=saved
        with self.assertRaisesRegex(VerifyFailure,'conversion outflow'):
            verify(result,plan)

    def test_invalid_transfer_amounts_and_accounts(self):
        for changes in ({'amount':-1},{'amount':float('nan')},{'amount':True},
                        {'from':'missing'},{'to':'ira'}):
            plan,result=self.conversion_result()
            result['deterministic_annual_ledger']['rows'][0]['conversion_transfers'][0].update(changes)
            with self.assertRaisesRegex(VerifyFailure,'invalid conversion transfer'):
                verify(result,plan)


class SupportedInputChecks(unittest.TestCase):
    def ss_plan(self,birth=1960,end=2027):
        plan=fixture()
        plan['end_year']=end
        plan['members'][0].update(birth_year=birth,retirement_age=70,ss_claim_age=62,
                                 ss_annual_2026_real_at_chosen_claim_age=20000)
        return plan

    def test_early_claimants_already_at_fra_are_accepted(self):
        for birth in (1954,1955,1959,1960):
            with self.subTest(birth=birth):
                plan=self.ss_plan(birth)
                audit_plan.validate(plan)
                self.assertTrue(verify(audit_plan.evaluate(plan),plan)['passed'])

    def test_future_overlap_outside_horizon_is_accepted(self):
        audit_plan.validate(self.ss_plan(1980,2041))
        with self.assertRaisesRegex(audit_plan.ModelError,'earnings-test'):
            audit_plan.validate(self.ss_plan(1980,2042))

    def test_modeled_pre_fra_working_year_is_rejected(self):
        with self.assertRaisesRegex(audit_plan.ModelError,'earnings-test'):
            audit_plan.validate(self.ss_plan(1961))

    def test_retirement_or_claim_at_boundary_has_no_overlap(self):
        for changes in ({'retirement_age':66},{'ss_claim_age':67},
                        {'annual_wages_2026':0},{'ss_annual_2026_real_at_chosen_claim_age':0}):
            plan=self.ss_plan(1961)
            plan['members'][0].update(changes)
            audit_plan.validate(plan)

    def test_401k_uniform_default_and_explicit_table(self):
        plan=fixture()
        audit_plan.validate(plan)
        plan['accounts'][2]['rmd_table']='uniform'
        audit_plan.validate(plan)
        for table in ('joint','single_life','',None,True):
            with self.subTest(table=table):
                plan['accounts'][2]['rmd_table']=table
                with self.assertRaisesRegex(audit_plan.ModelError,'401k only supports uniform'):
                    audit_plan.validate(plan)


if __name__=='__main__':
    unittest.main()
