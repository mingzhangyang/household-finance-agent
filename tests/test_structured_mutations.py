"""Missing/type/reorder/consistent corruption, with honest verifier boundaries."""
import copy
import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from audit_plan import evaluate
from verify_outputs import verify, VerifyFailure
from verify_replay import verify_replay


class StructuredMutations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan=json.loads((ROOT/'examples/audited-household-2026.json').read_text())
        cls.plan.update(end_year=2028,events=[])
        cls.plan['assumptions']['trials']=3
        cls.result=evaluate(cls.plan)

    def check_rejected(self, mutate):
        result=copy.deepcopy(self.result)
        mutate(result)
        with self.assertRaises(VerifyFailure):
            verify(result,self.plan,ROOT/'scripts')

    def test_missing_arrays_wrong_types_and_order(self):
        mutations=[
            lambda r:r.pop('deterministic_annual_ledger'),
            lambda r:r['deterministic_annual_ledger']['rows'].reverse(),
            lambda r:r['deterministic_annual_ledger']['rows'].pop(),
            lambda r:r['simulated_path_manifest'].reverse(),
            lambda r:r['annual_real_percentiles'].pop(),
            lambda r:r.update(success_paths=True),
            lambda r:r['tax_policy'].update(filing_status='single'),
            lambda r:r['deterministic_annual_ledger']['rows'][0].update(wages_gross='1'),
            lambda r:r['deterministic_annual_ledger']['rows'][0].update(skipped_conversions={}),
            lambda r:r['deterministic_annual_ledger']['rows'][0]['tax'].update(federal_income_tax='1'),
            lambda r:r['evidence_status'].update(professional_review='passed'),
            lambda r:r['input_provenance'].update(mode='documented_verified'),
        ]
        for i,mutation in enumerate(mutations):
            with self.subTest(case=i):
                self.check_rejected(mutation)

    def test_legacy_metadata_absent_with_matching_plan(self):
        result=copy.deepcopy(self.result)
        del result['evidence_status']
        del result['input_provenance']
        self.assertTrue(verify(result,self.plan)['passed'])

    def test_provenance_remains_checked_without_evidence_status(self):
        result=copy.deepcopy(self.result)
        del result['evidence_status']
        self.assertTrue(verify(result,self.plan)['passed'])
        result['input_provenance']['mode']='not_provided'
        with self.assertRaisesRegex(VerifyFailure,'input_provenance mismatched'):
            verify(result,self.plan)

    def test_evidence_status_requires_provenance(self):
        result=copy.deepcopy(self.result)
        del result['input_provenance']
        with self.assertRaises(VerifyFailure):
            verify(result,self.plan)

    def test_malformed_root_raises_public_failure(self):
        for result in (None, [], {}, {'engine_version':'2.2-auditable-restricted'}):
            with self.subTest(result=result), self.assertRaises(VerifyFailure):
                verify(result)

    def test_nonfinite_account_flow_is_not_a_pass(self):
        self.check_rejected(lambda r:r['deterministic_annual_ledger']['rows'][0]['account_flows']['cash'].update(contribution=float('nan')))

    def test_consistent_annual_percentile_forgery_requires_replay(self):
        result=copy.deepcopy(self.result)
        # All three intermediate bands move together; ordering/endpoints remain
        # valid. The arithmetic-only verifier explicitly cannot prove these.
        for key in ('p10','p50','p90'):
            result['annual_real_percentiles'][0][key]+=1000
        self.assertTrue(verify(result,self.plan)['passed'])
        with self.assertRaisesRegex(VerifyFailure,'annual_real_percentiles'):
            verify_replay(result,self.plan)

    def test_consistent_income_relabeling_requires_replay(self):
        result=copy.deepcopy(self.result)
        row=result['deterministic_annual_ledger']['rows'][0]
        row['wages_gross']-=100
        row['wages_taxable']-=100
        row['pension_gross']+=100
        # Conservation/AGI still agree. Payroll-source and input timing truth
        # are outside the output-only identities, exposed by whole-result replay.
        self.assertTrue(verify(result,self.plan)['passed'])
        with self.assertRaisesRegex(VerifyFailure,'wages_gross'):
            verify_replay(result,self.plan)

    def test_clean_replay_is_not_labeled_independent(self):
        status=verify_replay(self.result,self.plan)
        self.assertTrue(status['passed'])
        self.assertFalse(status['independent_model_validation'])


if __name__=='__main__':
    unittest.main()
