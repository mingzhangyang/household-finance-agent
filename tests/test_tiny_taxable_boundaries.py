"""PR #12 numerical edges, using fictional input and the actual output verifier.

No production accounts or remote actions. These tests must run against the
reviewed PR head with the local patch applied.
"""
import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'tests'))
from audit_plan import evaluate, trace
from test_taxable_account import LEGACY, WITH, with_distributions
from test_verifier_independence import household
from verify_outputs import VerifyFailure, verify, verify_trace


def first_row(result):
    return result['deterministic_annual_ledger']['rows'][0]


class TinyTaxableBoundaryRegressions(unittest.TestCase):
    def test_sub_nanodollar_sale_funds_steep_loss_tax(self):
        # Before the fix, the 1e-8 draw cutoff makes this tax response
        # discontinuous and the safeguarded bisection raises ModelError.
        plan = with_distributions(household(birth=1966, brokerage=10., basis=1e9,
                                            living=28580.01))
        plan['members'][0].update(annual_pension_2026_real=30000., pension_start_age=60)
        result = evaluate(plan)
        row = first_row(result)
        record = row['taxable_accounts']['brokerage']
        # Pension - spending = $1,419.99. Without a sale, tax = $1,420.
        # In the 12% bracket the recognized loss is (1e8-1) times the sale.
        expected_sale = .01 / (1 + .12 * (1e8 - 1))
        self.assertGreater(record['sale_proceeds'], 0.)
        self.assertLess(record['sale_proceeds'], 1e-8)
        self.assertAlmostEqual(record['sale_proceeds'], expected_sale, delta=5e-11)
        self.assertAlmostEqual(record['basis_sold'], expected_sale * 1e8, delta=.005)
        self.assertEqual(row['extra_draws']['brokerage'], 0.)  # presentation rounded
        self.assertGreater(row['account_flows']['brokerage']['optional_draw'], 0.)  # exact journal
        self.assertEqual((row['tax_due_total'], row['unpaid_tax'], row['unmet_spending']),
                         (1419.99, 0., 0.))
        self.assertTrue(verify(result, plan, ROOT / 'scripts')['passed'])
        self.assertTrue(verify(result)['passed'])
        self.assertTrue(verify_trace(trace(plan, 0), plan, result)['passed'])

    def test_raw_subcent_sale_is_not_allowed_to_disappear_from_record(self):
        plan = with_distributions(household(birth=1966, brokerage=10., basis=1e9,
                                            living=28580.01))
        plan['members'][0].update(annual_pension_2026_real=30000., pension_start_age=60)
        forged = copy.deepcopy(evaluate(plan))
        record = first_row(forged)['taxable_accounts']['brokerage']
        self.assertGreater(record['sale_proceeds'], 0.)
        record['sale_proceeds'] = 0.
        with self.assertRaisesRegex(VerifyFailure, 'sale proceeds are the draw'):
            verify(forged)

    def test_normal_funded_sale_remains_valid(self):
        plan = with_distributions(household(birth=1966, cash=10000., brokerage=20000.,
                                            basis=12000., living=14000.))
        result = evaluate(plan)
        row = first_row(result)
        self.assertAlmostEqual(row['taxable_accounts']['brokerage']['sale_proceeds'], 4000., delta=.001)
        self.assertTrue(verify(result)['passed'])
        self.assertTrue(verify(result, plan, ROOT / 'scripts')['passed'])

    def small_plan(self, treatment=WITH, living=.006):
        plan = household(birth=1966, brokerage=.01, basis=.02, living=living)
        return with_distributions(plan) if treatment == WITH else plan

    def test_no_funding_gap_means_no_taxable_sale(self):
        # Replacing the threshold must not create sales when obligations are funded.
        plan = with_distributions(household(birth=1966, cash=1000., brokerage=1.,
                                            basis=2., living=1000.))
        result = evaluate(plan)
        row = first_row(result)
        self.assertEqual(row['taxable_accounts']['brokerage']['sale_proceeds'], 0.)
        self.assertEqual(row['taxable_basis_end']['brokerage'], 2.)
        self.assertTrue(verify(result, plan)['passed'])

    def test_rounded_zero_balance_is_not_full_liquidation(self):
        # The first review's older full-liquidation inference rejects this
        # valid 0.006 sale / 0.004 remainder even though its balance rounds 0.00.
        for treatment in (WITH, LEGACY):
            with self.subTest(treatment=treatment):
                plan = self.small_plan(treatment)
                result = evaluate(plan)
                row = first_row(result)
                record = row['taxable_accounts']['brokerage']
                self.assertAlmostEqual(record['sale_proceeds'], .006, delta=1e-12)
                self.assertAlmostEqual(record['basis_sold'], .012, delta=1e-12)
                self.assertEqual(row['closing_accounts']['brokerage'], 0.)
                self.assertEqual(row['taxable_basis_end']['brokerage'], .01)
                self.assertTrue(verify(result)['passed'])
                self.assertTrue(verify(result, plan, ROOT / 'scripts')['passed'])
                self.assertTrue(verify_trace(trace(plan, 0), plan, result)['passed'])

    def test_full_liquidation_still_uses_all_basis(self):
        for treatment in (WITH, LEGACY):
            with self.subTest(treatment=treatment):
                plan = self.small_plan(treatment, living=.01)
                result = evaluate(plan)
                row = first_row(result)
                record = row['taxable_accounts']['brokerage']
                self.assertAlmostEqual(record['sale_proceeds'], .01, delta=1e-12)
                self.assertAlmostEqual(record['basis_sold'], .02, delta=1e-12)
                self.assertEqual(row['taxable_basis_end']['brokerage'], 0.)
                self.assertTrue(verify(result, plan)['passed'])
                self.assertTrue(verify(result)['passed'])

    def test_output_only_still_rejects_unproportional_sale(self):
        plan = self.small_plan()
        result = evaluate(plan)
        forged = copy.deepcopy(result)
        row = first_row(forged)
        row['taxable_accounts']['brokerage']['basis_sold'] = .002
        row['taxable_accounts']['brokerage']['sale_gain_or_loss'] = .004
        with self.assertRaises(VerifyFailure):
            verify(forged)

    def test_output_only_still_rejects_basis_creation(self):
        result = evaluate(self.small_plan())
        forged = copy.deepcopy(result)
        first_row(forged)['taxable_basis_end']['brokerage'] = .04
        with self.assertRaisesRegex(VerifyFailure, 'basis increased on a sale'):
            verify(forged)

    def test_raw_sale_record_must_match_raw_account_journal(self):
        result = evaluate(self.small_plan())
        forged = copy.deepcopy(result)
        first_row(forged)['taxable_accounts']['brokerage']['sale_proceeds'] += .004
        with self.assertRaisesRegex(VerifyFailure, 'sale proceeds are the draw'):
            verify(forged)

    def test_plan_backed_rejects_false_remaining_basis_after_full_sale(self):
        # Output-only cannot distinguish exactly zero from <half a cent;
        # the plan/return and unrounded sale record provide independent evidence.
        plan = self.small_plan(living=.01)
        forged = copy.deepcopy(evaluate(plan))
        first_row(forged)['taxable_basis_end']['brokerage'] = .01
        with self.assertRaisesRegex(VerifyFailure, 'unrounded taxable basis'):
            verify(forged, plan)


if __name__ == '__main__':
    unittest.main()
