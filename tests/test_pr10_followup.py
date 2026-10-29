"""PR #10 follow-up: coherent forgeries must fail without rejecting boundary cases."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from test_niit_integration import fixture
from audit_plan import evaluate,run_path
from verify_outputs import verify,VerifyFailure


class FollowupVerifierGates(unittest.TestCase):
    def zero_income_plan(self):
        plan=fixture()
        plan['members'][0].update(annual_wages_2026=0,annual_pretax_401k_2026_real=0)
        for account in plan['accounts']:
            account['balance']=0
        plan['living_expenses_annual_real']=0
        plan['assumptions'].update(inflation=0,cash_yield=0,equity_mean=0,bond_mean=0,
                                   annual_investment_fee=0)
        return plan

    def test_realized_gain_cannot_exceed_tiny_sale_even_with_huge_basis(self):
        plan=self.zero_income_plan()
        plan['accounts'][1].update(balance=.03,basis=1000)
        plan['living_expenses_annual_real']=.02
        result=evaluate(plan)
        self.assertTrue(verify(result,plan)['passed'])  # Small-balance sale is legitimate.
        row=result['deterministic_annual_ledger']['rows'][0]
        self.assertAlmostEqual(row['account_flows']['brokerage']['optional_draw'],.02)
        self.assertEqual(row['realized_ltcg'],0)
        row['realized_ltcg']=100.
        tax=row['tax']
        tax.update(adjusted_gross_income=100.,niit_magi_assumed_equal_agi=100.,
                   niit_net_investment_income=100.,ss_provisional_income=100.)
        # The deduction absorbs the fabricated gain; the ordinary worksheets
        # and account conservation remain consistent, but the sale cap does not.
        for supplied in (None,plan):
            with self.subTest(plan=supplied is not None):
                with self.assertRaisesRegex(VerifyFailure,'realized gains exceed taxable-sale proceeds'):
                    verify(result,supplied)

    def test_coordinated_four_cent_false_tax_shortfall_is_rejected(self):
        plan=self.zero_income_plan()
        plan['accounts'][3]['balance']=100000
        plan['roth_conversions']=[{'year':2027,'from':'ira','to':'roth','amount_nominal':100000}]
        first=run_path(plan,[0.])['rows'][0]
        self.assertGreater(first['tax_due_total'],0)
        plan['accounts'][0]['balance']=first['tax_due_total']
        result=evaluate(plan)
        summary=result['deterministic_annual_ledger']
        row=summary['rows'][0]
        self.assertFalse(summary['failed'])
        self.assertEqual(row['unpaid_tax'],0)
        self.assertEqual(row['closing_accounts']['cash'],0)
        self.assertTrue(verify(result,plan)['passed'])
        row['tax_due_total']=round(row['tax_due_total']+.04,2)
        row['unpaid_tax']=.04
        summary.update(failed=True,first_failure_year=2027)
        summary['notices']=[{'year':2027,'blocks':[
            f"{a['id']}: early distributions before 60 not modeled"
            for a in plan['accounts'] if a['kind'] in
            ('traditional_ira','traditional_401k','roth_ira')]}]
        for supplied in (None,plan):
            with self.subTest(plan=supplied is not None):
                with self.assertRaisesRegex(VerifyFailure,'total due'):
                    verify(result,supplied)

    def conversion_plan(self,balance):
        plan=self.zero_income_plan()
        plan['accounts'][3]['balance']=balance
        plan['roth_conversions']=[{'year':2027,'from':'ira','to':'roth',
                                  'amount_nominal':10000}]
        return plan

    def test_exact_balance_conversion_cannot_be_reclassified_as_skipped(self):
        plan=self.conversion_plan(10000.)
        result=evaluate(plan)
        summary=result['deterministic_annual_ledger']
        row=summary['rows'][0]
        self.assertEqual(row['roth_converted'],10000)
        self.assertTrue(verify(result,plan)['passed'])
        row['conversion_transfers']=[]
        row['skipped_conversions']=[{'year':2027,'from':'ira','amount':10000.,
                                    'reason':'insufficient source balance after RMD'}]
        row['roth_converted']=0.
        row['account_flows']['ira']['roth_conversion_out']=0.
        row['account_flows']['roth']['roth_conversion_in']=0.
        row['closing_accounts']['ira']=10000.
        row['closing_accounts']['roth']=0.
        row['tax'].update(gross_ordinary=0.,adjusted_gross_income=0.,
                          niit_magi_assumed_equal_agi=0.,ss_provisional_income=0.)
        summary.update(failed=True,first_failure_year=2027)
        with self.assertRaisesRegex(VerifyFailure,'conversion skipped although'):
            verify(result,plan)

    def test_subcent_shortfall_may_legitimately_skip_conversion(self):
        # The exported IRA opening rounds to 10,000, but the unrounded balance
        # is 9,999.996. A zero-tolerance check on rounded data would reject it.
        plan=self.conversion_plan(9999.996)
        result=evaluate(plan)
        row=result['deterministic_annual_ledger']['rows'][0]
        self.assertEqual(row['opening_accounts']['ira'],10000.)
        self.assertEqual(row['roth_converted'],0)
        self.assertEqual(len(row['skipped_conversions']),1)
        self.assertTrue(verify(result,plan)['passed'])

    def test_chained_tax_component_tolerances_cannot_forge_failure(self):
        # Unlike the simpler total-due mutation, this coordinated forgery
        # stays within EVERY individual subtotal tolerance in the old verifier.
        plan=self.zero_income_plan()
        plan['accounts'][3]['balance']=100000
        plan['roth_conversions']=[{'year':2027,'from':'ira','to':'roth','amount_nominal':100000}]
        plan['accounts'][0]['balance']=run_path(plan,[0.])['rows'][0]['tax_due_total']
        result=evaluate(plan)
        summary=result['deterministic_annual_ledger']
        row=summary['rows'][0]
        self.assertFalse(summary['failed'])
        self.assertEqual(row['unpaid_tax'],0.)
        self.assertEqual(row['closing_accounts']['cash'],0.)
        self.assertTrue(verify(result,plan)['passed'])
        tax=row['tax']
        self.assertEqual(tax['capital_gain_rate_lines'][0]['rate'],0.)
        tax['capital_gain_rate_lines'][0]['tax']=.01
        tax['capital_gains_tax']=.01
        tax['niit_due']=.01
        tax['federal_income_tax']=round(tax['federal_income_tax']+.02,2)
        tax['total_federal_income_and_niit']=round(tax['total_federal_income_and_niit']+.04,2)
        row['tax_due_total']=round(row['tax_due_total']+.04,2)
        row['unpaid_tax']=.04
        summary.update(failed=True,first_failure_year=2027)
        summary['notices']=[{'year':2027,'blocks':[
            f"{a['id']}: early distributions before 60 not modeled"
            for a in plan['accounts'] if a['kind'] in
            ('traditional_ira','traditional_401k','roth_ira')]}]
        for supplied in (None,plan):
            with self.subTest(plan=supplied is not None):
                with self.assertRaisesRegex(VerifyFailure,
                                            'independently recomputed total federal liability'):
                    verify(result,supplied)

    def test_nonzero_return_exact_balance_conversion_and_ira_continuity(self):
        for conversion_year in (2027,2028):
            with self.subTest(conversion_year=conversion_year):
                plan=self.conversion_plan(20000001.)
                plan['end_year']=conversion_year
                plan['assumptions'].update(equity_weight=1.,equity_mean=-.15,
                    equity_volatility=0.,bond_mean=0.,bond_volatility=0.,
                    annual_investment_fee=0.)
                amount=20000001.
                for year in range(2027,conversion_year+1):
                    amount+=amount*(-.15)
                plan['roth_conversions']=[{'year':conversion_year,
                    'from':'ira','to':'roth','amount_nominal':amount}]
                result=evaluate(plan)
                rows=result['deterministic_annual_ledger']['rows']
                self.assertEqual(rows[-1]['conversion_transfers'][0]['amount'],amount)
                self.assertEqual(rows[-1]['skipped_conversions'],[])
                # The 2028 case independently tests sub-cent carry-forward
                # of the 2027 balance before executing the exact conversion.
                self.assertTrue(verify(result,plan)['passed'])


if __name__=='__main__':
    unittest.main()
