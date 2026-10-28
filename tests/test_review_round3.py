"""Known-answer and tampering tests for the eight summary-only review findings."""
import copy
import unittest
from pathlib import Path

from test_niit_integration import fixture
import audit_plan
from social_security import (full_retirement_age_months,claiming_factor,
                             benefit_from_pia_at_claim,SSARuleError)
from tax2026 import federal_tax
from verify_outputs import verify,VerifyFailure

SCRIPTS=Path(__file__).resolve().parents[1]/'scripts'


class OutputReviewChecks(unittest.TestCase):
    def test_real_balance_cannot_be_fabricated(self):
        plan=fixture()
        plan['assumptions']['inflation']=.025
        result=audit_plan.evaluate(plan)
        self.assertTrue(verify(result,plan,SCRIPTS)['passed'])
        result['deterministic_annual_ledger']['rows'][0]['closing_total_real']=1e9
        for supplied in (plan,None):
            with self.assertRaisesRegex(VerifyFailure,'real closing balance'):
                verify(result,supplied,SCRIPTS)

    def test_inflation_factor_is_anchored_to_plan_in_every_year(self):
        plan=fixture()
        plan['end_year']=2030
        plan['assumptions']['inflation']=.025
        result=audit_plan.evaluate(plan)
        for index in range(4):
            with self.subTest(index=index):
                altered=copy.deepcopy(result)
                row=altered['deterministic_annual_ledger']['rows'][index]
                row['inflation_factor']=1
                row['closing_total_real']=row['closing_total']
                with self.assertRaisesRegex(VerifyFailure,'inflation factor'):
                    verify(altered,plan,SCRIPTS)

    def test_rounded_inflation_factor_without_plan(self):
        plan=fixture()
        plan['end_year']=2030
        plan['assumptions']['inflation']=.033333333
        plan['accounts'][0]['balance']=1000000000
        result=audit_plan.evaluate(plan)
        self.assertTrue(verify(result,plan)['passed'])
        self.assertTrue(verify(result)['passed'])

    def test_policy_change_cannot_remove_single_filer_niit(self):
        plan=fixture()
        plan['members'][0]['annual_wages_2026']=240000
        result=copy.deepcopy(audit_plan.evaluate(plan))
        row=result['deterministic_annual_ledger']['rows'][0]
        self.assertEqual(row['tax']['adjusted_gross_income'],230000)
        self.assertEqual(row['tax']['niit_due'],380)
        result['tax_policy']['filing_status']='mfj'
        row['tax'].update(niit_threshold=250000,niit_tax_base=0,niit_due=0)
        row['tax']['total_federal_income_and_niit']-=380
        row['tax_due_total']-=380
        row['tax_paid']-=380
        row['account_flows']['cash']['cash_tax_and_spending_outflow']-=380
        row['closing_accounts']['cash']+=380
        row['closing_total']+=380
        row['closing_total_real']+=380
        # The coherent output still needs the supplied plan to expose the lie.
        self.assertTrue(verify(result)['passed'])
        with self.assertRaisesRegex(VerifyFailure,'tax policy mismatched'):
            verify(result,plan,SCRIPTS)

    def test_all_output_policy_fields_are_anchored(self):
        plan=fixture()
        for key,value in (('future_bracket_inflation',.05),('reference_year',2027),
                          ('state_income_tax','included')):
            with self.subTest(key=key):
                result=copy.deepcopy(audit_plan.evaluate(plan))
                result['tax_policy'][key]=value
                with self.assertRaisesRegex(VerifyFailure,'tax policy mismatched'):
                    verify(result,plan)

    def test_hidden_rmd_shortfall_rejected(self):
        plan=fixture()
        plan['members'][0].update(birth_year=1951,annual_wages_2026=0,
                                  annual_pretax_401k_2026_real=0)
        plan['accounts'][0]['balance']=1000000
        plan['accounts'][3]['balance']=1000
        result=audit_plan.evaluate(plan)
        # A valid adverse annual ledger with an RMD exceeding post-loss assets.
        result['deterministic_annual_ledger']=audit_plan.run_path(plan,[-.999])
        summary=result['deterministic_annual_ledger']
        row=summary['rows'][0]
        self.assertGreater(row['unmet_rmd'],0)
        self.assertEqual(row['unmet_spending']+row['unpaid_tax'],0)
        self.assertTrue(verify(result,plan,SCRIPTS)['passed'])
        row['unmet_rmd']=0
        summary.update(failed=False,first_failure_year=None)
        with self.assertRaisesRegex(VerifyFailure,'RMD unmet aggregate'):
            verify(result,plan,SCRIPTS)

    def test_rmd_aggregates_use_rounded_sum_of_unrounded_details(self):
        plan=fixture()
        plan['members'][0].update(birth_year=1951,annual_wages_2026=0,
                                  annual_pretax_401k_2026_real=0)
        plan['accounts'][2]['balance']=1000.123
        plan['accounts'][3]['balance']=2000.456
        result=audit_plan.evaluate(plan)
        row=result['deterministic_annual_ledger']['rows'][0]
        self.assertEqual(row['rmd_total'],round(sum(item['taken'] for item in row['rmd']),2))
        self.assertTrue(verify(result,plan)['passed'])
        # One cent is significant for aggregates, despite journal tolerances.
        row['rmd_total']+=.01
        with self.assertRaisesRegex(VerifyFailure,'RMD taken aggregate'):
            verify(result,plan)

    def test_wilson_published_score_formula_endpoints(self):
        plan=fixture()
        plan['assumptions']['trials']=10
        for successes,interval in ((0,[0,.2775]),(5,[.2366,.7634]),(10,[.7225,1])):
            with self.subTest(successes=successes):
                result=audit_plan.evaluate(plan)
                for i,path in enumerate(result['simulated_path_manifest']):
                    path['funded']=i<successes
                    path['first_failure_year']=None if path['funded'] else 2027
                result['success_paths']=successes
                result['modeled_all_obligations_funded_fraction']=successes/10
                result['funded_and_target_fraction']=successes/10
                result['mc_sampling_wilson95']=interval
                self.assertTrue(verify(result,plan)['passed'])

    def test_invalid_or_fabricated_wilson_intervals(self):
        plan=fixture()
        for interval in ([1,1],[],[.5],[0,.5,1],[.9,.1],[-.1,1],
                         [0,1.1],[0,float('nan')],[0,True],None):
            with self.subTest(interval=interval):
                result=audit_plan.evaluate(plan)
                result['mc_sampling_wilson95']=interval
                with self.assertRaisesRegex(VerifyFailure,'Wilson interval'):
                    verify(result,plan)

    def test_manifest_funded_and_failure_year_consistency(self):
        plan=fixture()
        for funded,year in ((True,2027),(False,None),(False,2026),(False,2028),
                            (False,2027.),(False,True),(1,None),('true',None)):
            with self.subTest(funded=funded,year=year):
                result=audit_plan.evaluate(plan)
                result['simulated_path_manifest'][0].update(funded=funded,first_failure_year=year)
                with self.assertRaisesRegex(VerifyFailure,'MC'):
                    verify(result,plan)

    def test_terminal_percentiles_require_exactly_three_finite_numbers(self):
        plan=fixture()
        result=audit_plan.evaluate(plan)
        good=result['terminal_real_p10_p50_p90']
        for values in ([],good[:1],good[:2],good+[1],None,[1,'2',3],
                       [1,float('inf'),3],[1,True,3]):
            with self.subTest(values=values):
                altered=copy.deepcopy(result)
                altered['terminal_real_p10_p50_p90']=values
                with self.assertRaisesRegex(VerifyFailure,'terminal percentiles'):
                    verify(altered,plan)


class ReferenceRuleCorrections(unittest.TestCase):
    def test_pre_1943_claiming_at_fra_needs_no_delayed_schedule(self):
        for birth in (1937,1940,1942):
            with self.subTest(birth=birth):
                fra=full_retirement_age_months(birth)
                self.assertEqual(claiming_factor(birth,fra),1)
                self.assertEqual(benefit_from_pia_at_claim(2000,birth,fra)['unrounded_monthly_benefit'],2000)
                self.assertLess(claiming_factor(birth,fra-1),1)
                with self.assertRaises(SSARuleError): claiming_factor(birth,fra+1)

    def tax(self,wages,gain,status='mfj'):
        return federal_tax(wages_taxable=wages,pension=0,ira_distributions=0,
            roth_conversions=0,cash_interest=0,ltcg=gain,ss_benefits=0,
            status=status,ages=[50,50] if status=='mfj' else [50],year=2026)

    def test_capital_gain_ordinary_rate_cap_known_answer(self):
        tax=self.tax(132200,800)
        # $100,000 ordinary taxable + $800 LTCG: $2,480 + $76,000*.12.
        self.assertEqual(tax['ordinary_tax'],11504)
        self.assertEqual(tax['capital_gains_tax'],96)
        self.assertEqual(tax['federal_income_tax'],11600)
        self.assertEqual(tax['income_tax_method'],'ordinary_rate_cap')
        self.assertEqual(tax['capital_gain_rate_lines'],[{'rate':.12,'taxable':800.,'tax':96.}])

    def test_capital_gain_cap_handles_multiple_ordinary_brackets(self):
        tax=self.tax(132200,1000)
        # Ordinary taxable $100,000: the next $800 is 12%, then $200 is 22%.
        self.assertEqual(tax['income_tax_method'],'ordinary_rate_cap')
        self.assertAlmostEqual(tax['capital_gains_tax'],140)
        self.assertEqual([line['rate'] for line in tax['capital_gain_rate_lines']],[.12,.22])
        self.assertAlmostEqual(sum(line['taxable'] for line in tax['capital_gain_rate_lines']),1000)

    def test_single_filer_cap_known_answer(self):
        tax=self.tax(66100,400,status='single')
        self.assertEqual(tax['ordinary_tax'],5752)
        self.assertEqual(tax['capital_gains_tax'],48)
        self.assertEqual(tax['federal_income_tax'],5800)
        self.assertEqual(tax['income_tax_method'],'ordinary_rate_cap')

    def test_capital_gain_preferential_method_remains_when_lower(self):
        for wages,gain,expected in ((132200,5000,12254),(32200,10000,0),(132200,0,11504)):
            with self.subTest(wages=wages,gain=gain):
                tax=self.tax(wages,gain)
                self.assertEqual(tax['income_tax_method'],'stacked_capital_gains')
                self.assertAlmostEqual(tax['federal_income_tax'],expected)
                self.assertAlmostEqual(tax['federal_income_tax'],tax['ordinary_tax']+tax['capital_gains_tax'])

    def test_selected_cap_ledger_verifies_and_changes_cash_funding(self):
        plan=fixture()
        plan['members']=[dict(id=name,birth_year=1970,retirement_age=65,
            annual_wages_2026=wages,wage_growth=0,ss_claim_age=67,
            ss_annual_2026_real_at_chosen_claim_age=0,
            ss_estimate_basis='2026_real_at_selected_claim_age')
            for name,wages in (('a',132200),('b',0))]
        plan['tax_policy']['filing_status']='mfj'
        plan['accounts']=[{'id':'cash','kind':'cash','balance':0},
            {'id':'brokerage','kind':'taxable','balance':10000,'basis':0,
             'gain_treatment':'long_term_proportional_no_loss_offset'}]
        plan['withdrawal_order']=['cash','brokerage']
        plan['assumptions'].update(cash_yield=0,equity_mean=0,bond_mean=0,
            equity_volatility=0,bond_volatility=0,annual_investment_fee=0)
        # 2027 brackets fixed at 2026 values; payroll is 132200*7.65%=10113.30.
        plan['living_expenses_annual_real']=111286.70
        result=audit_plan.evaluate(plan)
        row=result['deterministic_annual_ledger']['rows'][0]
        self.assertAlmostEqual(row['realized_ltcg'],800,delta=.01)
        self.assertAlmostEqual(row['tax']['federal_income_tax'],11600,delta=.01)
        self.assertEqual(row['tax']['income_tax_method'],'ordinary_rate_cap')
        self.assertTrue(verify(result,plan,SCRIPTS)['passed'])


if __name__=='__main__': unittest.main()
