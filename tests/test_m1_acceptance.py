"""Independent cross-function references must detect material result changes."""
import copy
import contextlib
import io
import json
import sys
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from verify_m1_cases import compare, verify_cases
import verify_m1_cases


class M1Acceptance(unittest.TestCase):
    def test_missing_compound_fields_write_failure_diagnostics(self):
        evaluate=verify_m1_cases.evaluate
        for missing in ('rows','closing_accounts','tax'):
            with self.subTest(missing=missing), tempfile.TemporaryDirectory() as temp:
                output=Path(temp)/'independent-cases.json'
                def broken_result(plan):
                    result=evaluate(plan)
                    ledger=result['deterministic_annual_ledger']
                    if missing=='rows': del ledger['rows']
                    else: del ledger['rows'][0][missing]
                    return result
                stdout=io.StringIO()
                with patch.object(verify_m1_cases,'evaluate',side_effect=broken_result), \
                     patch.object(sys,'argv',['verify_m1_cases','--output',str(output)]), \
                     contextlib.redirect_stdout(stdout):
                    self.assertEqual(verify_m1_cases.main(),1)
                report=json.loads(output.read_text())
                self.assertFalse(report['passed'])
                for case in report['cases']:
                    failures=[c for c in case['checks'] if not c['passed']]
                    self.assertEqual(len(failures),1)
                    self.assertTrue(failures[0]['field'].endswith('.'+missing))
                    self.assertIsNone(failures[0]['actual'])
                    self.assertIsInstance(failures[0]['expected'],list if missing=='rows' else dict)
                self.assertIn('FAIL',stdout.getvalue())
                first=next(c['expected'] for c in report['cases'][0]['checks'] if not c['passed'])
                if missing=='rows':
                    self.assertEqual(first[0]['year'],2027)
                    self.assertEqual(first[0]['closing_accounts']['ira'],'500000')
                elif missing=='closing_accounts': self.assertEqual(first['ira'],'500000')
                else: self.assertEqual(first['ordinary_tax'],'7004.00')

    def test_three_cross_function_scenarios(self):
        report=verify_cases()
        self.assertEqual(len(report['cases']),3)
        self.assertEqual(sum(c['years'] for c in report['cases']),9)
        for case in report['cases']:
            with self.subTest(case=case['id']):
                self.assertTrue(case['passed'],[c for c in case['checks'] if not c['passed']])

    def test_consistent_balance_and_summary_mutations_are_rejected(self):
        expected={'rows':[{'year':2029,'closing_accounts':{'ira':100,'cash':0},
                          'closing_total':100,'tax_paid':10}],
                  'failed':True,'first_failure_year':2029}
        mutations=[]
        bad=copy.deepcopy(expected)
        bad['rows'][0]['closing_accounts']['ira']+=10
        bad['rows'][0]['closing_total']+=10
        mutations.append(bad)
        for field,value in [('failed',False),('first_failure_year',2030)]:
            bad=copy.deepcopy(expected); bad[field]=value; mutations.append(bad)
        for value in [True,float('nan'),float('inf'),'10']:
            bad=copy.deepcopy(expected); bad['rows'][0]['tax_paid']=value; mutations.append(bad)
        bad=copy.deepcopy(expected); bad['rows']=[]; mutations.append(bad)
        bad=copy.deepcopy(expected); bad['rows'][0]['closing_accounts']['extra']=1; mutations.append(bad)
        for bad in mutations:
            self.assertFalse(all(c['passed'] for c in compare(bad,expected)),bad)
        self.assertTrue(all(c['passed'] for c in compare(expected,expected)))


if __name__=='__main__': unittest.main()
