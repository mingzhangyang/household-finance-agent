"""Executable M0 boundaries and evidence-status separation."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from audit_plan import ModelError, evaluate, run_path, validate


def plan():
    p = json.loads((ROOT / 'examples/audited-household-2026.json').read_text())
    p.update(end_year=2028, events=[])
    p['assumptions']['trials'] = 2
    return p


class ScopeContract(unittest.TestCase):
    def test_supported_research_does_not_assert_verification(self):
        p = plan()
        for mode in ('fictional_demo', 'unverified_user_data', None):
            if mode is None:
                p.pop('input_provenance')
            else:
                p['input_provenance']['mode'] = mode
            status = evaluate(p)['evidence_status']
            self.assertEqual(status['model'], 'restricted_research')
            self.assertEqual(status['input'], mode or 'not_provided')
            self.assertFalse(status['input_independently_verified'])
            self.assertFalse(status['full_household_conclusion'])
            self.assertEqual(status['professional_review'], 'not_recorded')

    def test_unsupported_dimensions_fail_closed(self):
        mutations = [
            lambda p: p.update(as_of_year=2027),
            lambda p: p['tax_policy'].update(reference_year=2027),
            lambda p: p['tax_policy'].update(filing_status='mfs'),
            lambda p: p['tax_policy'].update(state_income_tax='NY'),
            lambda p: p['members'][0].update(birth_year=1950),
            lambda p: p['members'][0].update(death_year=2028),
            lambda p: p['members'][0].update(dividends=1),
            lambda p: p['accounts'][2].update(fully_pretax_confirmed=False),
            lambda p: p['accounts'][5].update(qualified_distributions_confirmed=False),
            lambda p: p.update(liabilities={'mortgage': 1}),
            lambda p: p.update(events=[{'year': 2027, 'amount': 1, 'kind': 'income', 'dollars': 'year_nominal'}]),
        ]
        for i, mutate in enumerate(mutations):
            with self.subTest(case=i):
                p = plan(); mutate(p)
                with self.assertRaises(ModelError):
                    evaluate(p)

    def test_malformed_nested_values_use_public_error(self):
        for key, value in [('tax_policy', None), ('members', [None]), ('accounts', [None]),
                           ('input_provenance', {'mode': 'documented_verified', 'register': [None]})]:
            with self.subTest(key=key):
                p = plan(); p[key] = value
                with self.assertRaises(ModelError) as caught:
                    validate(p)
                self.assertEqual(caught.exception.code, 'INVALID_OR_UNSUPPORTED_PLAN')

    def test_status_cannot_be_supplied_as_an_approval(self):
        p = plan(); p['evidence_status'] = {'professional_review': 'passed'}
        with self.assertRaises(ModelError):
            validate(p)

    def test_explicit_null_provenance_rejected(self):
        p = plan(); p['input_provenance'] = None
        for operation in (validate, evaluate):
            with self.subTest(operation=operation.__name__), self.assertRaises(ModelError):
                operation(p)

    def test_oversized_json_integer_rejected(self):
        p = plan(); p['accounts'][0]['balance'] = 10**400
        for operation in (validate, evaluate):
            with self.subTest(operation=operation.__name__), self.assertRaises(ModelError):
                operation(p)

    def test_oversized_path_return_rejected(self):
        with self.assertRaises(ModelError):
            run_path(plan(), [10**400, 0])

    def test_cli_rejections_have_exit_two_without_traceback_or_output(self):
        for case in ('null_provenance', 'oversized_integer'):
            p = plan()
            if case == 'null_provenance':
                p['input_provenance'] = None
            else:
                p['accounts'][0]['balance'] = 10**400
            with tempfile.TemporaryDirectory() as tmp:
                source = Path(tmp)/'invalid.json'
                source.write_text(json.dumps(p))
                commands = [[str(ROOT/'scripts/audit_plan.py'), command, str(source)]
                            for command in ('validate', 'run', 'trace')]
                commands.append([str(ROOT/'scripts/render_audit.py'), str(source)])
                for index, command in enumerate(commands):
                    with self.subTest(case=case, command=command[0:2]):
                        output = Path(tmp)/f'output-{index}'
                        check = subprocess.run([sys.executable, *command, '--output', str(output)],
                                               capture_output=True, text=True)
                        self.assertEqual(check.returncode, 2, check.stdout+check.stderr)
                        self.assertIn('ERROR:', check.stderr)
                        self.assertNotIn('Traceback', check.stderr)
                        self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
