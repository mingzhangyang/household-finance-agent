"""Independent cross-function references must detect material result changes."""
import copy
import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from verify_m1_cases import compare, verify_cases


class M1Acceptance(unittest.TestCase):
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
