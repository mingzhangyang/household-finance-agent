"""Sourced fixed answers plus independently solved Decimal funding equations."""
import json
import sys
import unittest
from decimal import Decimal as D
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from audit_plan import run_path
from tax2026 import progressive_tax, taxable_social_security

CASES = json.loads((ROOT/'tests/golden/reference-cases.json').read_text())


def projection_plan(case):
    p = json.loads((ROOT/'examples/audited-household-2026.json').read_text())
    p.update(name=case['id'], end_year=2026+case['years'], events=[],
             living_expenses_annual_real=case['spending'], terminal_target_2026_real=0)
    p['members'] = [dict(id='adult', birth_year=case['birth_year'], retirement_age=40,
        annual_wages_2026=0, wage_growth=0, ss_claim_age=67,
        ss_annual_2026_real_at_chosen_claim_age=0, ss_estimate_basis='2026_real_at_selected_claim_age')]
    p['tax_policy'].update(filing_status='single', future_bracket_inflation=0)
    p['accounts'] = [dict(id='cash', kind='cash', balance=case['cash']),
        dict(id='taxable', kind='taxable', balance=case['taxable'], basis=case['basis'],
             gain_treatment='long_term_proportional_no_loss_offset'),
        dict(id='ira', kind='traditional_ira', balance=case['ira'], owner='adult',
             fully_pretax_confirmed=True, rmd_table='uniform'),
        dict(id='roth', kind='roth_ira', balance=0, owner='adult', qualified_distributions_confirmed=True)]
    p['withdrawal_order'] = ['cash', 'taxable', 'ira', 'roth']
    p['roth_conversions'] = ([{'year':2027, 'from':'ira', 'to':'roth',
                              'amount_nominal':case['conversion']}] if case['conversion'] else [])
    p['assumptions'] = {k:0 for k in p['assumptions']}
    p['assumptions'].update(trials=2, seed=42)
    p['input_provenance'] = {'mode':'fictional_demo', 'register':[]}
    return p


class GoldenReferences(unittest.TestCase):
    def test_sourced_component_cases(self):
        for case in CASES['component_cases']:
            with self.subTest(case=case['id']):
                self.assertIn(case['source'], CASES['sources'])
                fn = progressive_tax if case['kind']=='progressive' else taxable_social_security
                self.assertAlmostEqual(fn(**case['inputs']), case['expected'], delta=case['tolerance'])

    def test_integrated_fixed_answers(self):
        for case in CASES['projection_cases']:
            with self.subTest(case=case['id']):
                result = run_path(projection_plan(case), [0]*case['years'])
                self.assertEqual(result['first_failure_year'], case['first_failure_year'])
                self.assertEqual(len(result['rows']), len(case['expected_rows']))
                for row, expected in zip(result['rows'], case['expected_rows']):
                    for field, value in expected.items():
                        self.assertAlmostEqual(row[field], value, delta=.01, msg=f'{case["id"]}.{row["year"]}.{field}')

    def test_independent_closed_form_multiyear_cash_and_accounts(self):
        # Closed-form equations, Decimal arithmetic; no production tax/funding
        # function or constants reused to obtain the reference answers.
        case = next(c for c in CASES['projection_cases'] if c['id']=='conversion-ira-tax-gross-up')
        rows = run_path(projection_plan(case), [0,0])['rows']
        draws = [D('20220')/D('.88'), D('18390')/D('.90')]
        ira = D('80000')
        for row, draw in zip(rows, draws):
            ira -= draw
            expected = {'cash':D(0), 'taxable':D(0), 'ira':ira, 'roth':D(20000)}
            for account, balance in expected.items():
                self.assertAlmostEqual(row['closing_accounts'][account], float(balance), delta=.01)
            self.assertAlmostEqual(row['tax']['ordinary_taxable'], float(draw-D(16100)+(D(20000) if row['year']==2027 else 0)), delta=.01)
            self.assertAlmostEqual(row['tax_paid'], float(draw-D(20000)), delta=.01)
            self.assertEqual(row['living_expenses_paid'], 20000)
            self.assertEqual(row['unpaid_tax'], 0)
            self.assertEqual(row['unmet_spending'], 0)


if __name__ == '__main__':
    unittest.main()
