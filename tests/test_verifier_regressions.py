"""Independent-verifier regressions for the second PR #2 review."""
import copy
import math
import unittest

from test_niit_integration import fixture
import audit_plan
from verify_outputs import verify,VerifyFailure


class MonteCarloPlanContract(unittest.TestCase):
    def test_truncated_manifest_with_recomputed_summaries_is_rejected(self):
        plan=fixture()
        plan['assumptions']['trials']=300
        result=audit_plan.evaluate(plan)
        path=result['simulated_path_manifest'][0]
        result['simulated_path_manifest']=[path]
        result['trials']=1
        result['mc_sampling_wilson95']=([.2065,1.] if path['funded'] else [0.,.7935])
        result['success_paths']=int(path['funded'])
        result['modeled_all_obligations_funded_fraction']=int(path['funded'])
        result['terminal_real_p10_p50_p90']=[path['terminal_real']]*3
        result['funded_and_target_fraction']=int(
            path['funded'] and path['terminal_real']>=plan['terminal_target_2026_real'])
        # Without a plan the verifier cannot know how many paths were requested.
        self.assertTrue(verify(result)['passed'])
        with self.assertRaisesRegex(VerifyFailure,'trial count mismatched to plan'):
            verify(result,plan)

    def test_invalid_trial_counts_fail_cleanly(self):
        result=audit_plan.evaluate(fixture())
        for count in (0,-1,True,3.0):
            with self.subTest(count=count):
                altered=copy.deepcopy(result)
                altered['trials']=count
                with self.assertRaisesRegex(VerifyFailure,'positive integer'):
                    verify(altered)

    def test_valid_one_trial_plan(self):
        plan=fixture()
        plan['assumptions']['trials']=1
        self.assertTrue(verify(audit_plan.evaluate(plan),plan)['passed'])


class DeterministicFailureContract(unittest.TestCase):
    def skipped_conversion(self):
        plan=fixture()
        plan['end_year']=2028
        plan['roth_conversions']=[{'year':2028,'from':'ira','to':'roth',
                                  'amount_nominal':.001}]
        return plan,audit_plan.evaluate(plan)

    def test_skipped_conversion_summary_cannot_hide_failure(self):
        plan,result=self.skipped_conversion()
        summary=result['deterministic_annual_ledger']
        self.assertTrue(summary['failed'])
        self.assertEqual(summary['first_failure_year'],2028)
        self.assertTrue(verify(result,plan)['passed'])
        summary.update(failed=False,first_failure_year=None)
        with self.assertRaisesRegex(VerifyFailure,'failed summary'):
            verify(result,plan)

    def test_first_failure_year_must_be_earliest_recorded_failure(self):
        plan,result=self.skipped_conversion()
        for year in (None,2027,2029):
            with self.subTest(year=year):
                result['deterministic_annual_ledger']['first_failure_year']=year
                with self.assertRaisesRegex(VerifyFailure,'first failure year'):
                    verify(result,plan)

    def test_funded_rows_cannot_report_failure_or_nonboolean_status(self):
        plan=fixture()
        for status,year in ((True,2027),(False,2027),(0,None)):
            with self.subTest(status=status,year=year):
                result=audit_plan.evaluate(plan)
                result['deterministic_annual_ledger'].update(failed=status,first_failure_year=year)
                with self.assertRaises(VerifyFailure): verify(result,plan)

    def test_every_annual_shortfall_contributes_to_failure_summary(self):
        for field in ('unmet_spending','unpaid_tax','unmet_rmd'):
            with self.subTest(field=field):
                plan=fixture()
                result=audit_plan.evaluate(plan)
                # A one-cent mutation remains within journal rounding tolerance,
                # but must still invalidate a summary claiming no failed years.
                result['deterministic_annual_ledger']['rows'][0][field]=.01
                with self.assertRaisesRegex(VerifyFailure,'RMD unmet aggregate' if field=='unmet_rmd' else 'failed summary'):
                    verify(result,plan)

    def test_cent_rounding_policy_agrees_across_engine_manifest_and_verifier(self):
        for spending,failed in ((0,False),(.004,False),(.006,True),(.01,True)):
            with self.subTest(spending=spending):
                plan=fixture()
                plan['members'][0].update(annual_wages_2026=0,annual_pretax_401k_2026_real=0)
                for account in plan['accounts']: account['balance']=0
                plan['living_expenses_annual_real']=spending
                result=audit_plan.evaluate(plan)
                summary=result['deterministic_annual_ledger']
                self.assertEqual(summary['rows'][0]['unmet_spending'],round(spending,2))
                self.assertEqual(summary['failed'],failed)
                self.assertEqual(summary['first_failure_year'],2027 if failed else None)
                self.assertTrue(all(path['funded']==(not failed)
                                    for path in result['simulated_path_manifest']))
                self.assertTrue(verify(result,plan)['passed'])

    def test_invalid_or_unrounded_shortfalls_rejected(self):
        for amount in (-.01,.004,math.nan,math.inf,True):
            with self.subTest(amount=amount):
                result=audit_plan.evaluate(fixture())
                result['deterministic_annual_ledger']['rows'][0]['unmet_spending']=amount
                with self.assertRaisesRegex(VerifyFailure,'whole-cent amounts'): verify(result)


class IncomeReconstruction(unittest.TestCase):
    def test_consistently_lowered_agi_niit_and_cash_entries_rejected(self):
        plan=fixture()
        result=audit_plan.evaluate(plan)
        row=result['deterministic_annual_ledger']['rows'][0]
        tax=row['tax']
        saved_tax=tax['niit_due']
        self.assertEqual(saved_tax,380)
        tax.update(adjusted_gross_income=190000,niit_magi_assumed_equal_agi=190000,
                   niit_tax_base=0,niit_due=0)
        tax['total_federal_income_and_niit']-=saved_tax
        row['tax_due_total']-=saved_tax
        row['tax_paid']-=saved_tax
        row['account_flows']['cash']['cash_tax_and_spending_outflow']-=saved_tax
        row['closing_accounts']['cash']+=saved_tax
        row['closing_total']+=saved_tax
        row['closing_total_real']+=saved_tax
        with self.assertRaisesRegex(VerifyFailure,'AGI income components'):
            verify(result,plan)

    def test_niit_magi_checked_against_income_components(self):
        plan=fixture()
        result=audit_plan.evaluate(plan)
        result['deterministic_annual_ledger']['rows'][0]['tax']['niit_magi_assumed_equal_agi']-=100
        with self.assertRaisesRegex(VerifyFailure,'NIIT MAGI income components'):
            verify(result,plan)

    def test_all_supported_taxable_income_components(self):
        plan=fixture()
        plan['members'][0].update(birth_year=1951,retirement_age=90,
            annual_pension_2026_real=20000,ss_annual_2026_real_at_chosen_claim_age=30000)
        plan['accounts'][1].update(balance=500000,basis=200000)
        plan['accounts'][2]['balance']=300000
        plan['accounts'][3]['balance']=500000
        plan['accounts'][4]['balance']=100000
        plan['living_expenses_annual_real']=1200000
        plan['roth_conversions']=[{'year':2027,'from':'ira','to':'roth','amount_nominal':10000}]
        plan['events']=[{'year':2027,'kind':'income','amount':10000,
                         'dollars':'year_nominal','tax_status':'net_after_all_taxes'}]
        result=audit_plan.evaluate(plan)
        row=result['deterministic_annual_ledger']['rows'][0]
        components=[row['wages_taxable'],row['pension_gross'],row['rmd_total'],
                    row['ira_extra_taxable'],row['roth_converted'],
                    row['growth_by_account']['cash'],row['tax']['taxable_social_security'],
                    row['realized_ltcg']]
        self.assertTrue(all(value>0 for value in components),components)
        self.assertAlmostEqual(sum(components),row['tax']['adjusted_gross_income'],delta=.05)
        self.assertNotEqual(row['tax']['taxable_social_security'],row['social_security_gross'])
        self.assertTrue(verify(result,plan)['passed'])


if __name__=='__main__': unittest.main()
