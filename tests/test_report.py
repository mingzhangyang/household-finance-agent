"""Round-trip report inputs and validate generated scenario boundaries."""
import copy
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from audit_plan import evaluate,validate
from render_audit import create_scenarios,render
from verify_outputs import verify


class ReportData(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_data=False
        self.raw=''

    def handle_starttag(self,tag,attrs):
        if tag=='script' and dict(attrs).get('id')=='data': self.in_data=True

    def handle_endtag(self,tag):
        if tag=='script': self.in_data=False

    def handle_data(self,data):
        if self.in_data: self.raw+=data


def fixture():
    plan=json.loads((ROOT/'examples/audited-household-2026.json').read_text())
    plan['end_year']=2028
    plan['events']=[]
    plan['assumptions']['trials']=3
    return plan


class ReportRoundTrip(unittest.TestCase):
    def payload(self,plan):
        with tempfile.TemporaryDirectory() as tmp:
            path=render(plan,Path(tmp)/'report.html')
            parser=ReportData()
            parser.feed(path.read_text())
            return json.loads(parser.raw)

    def test_every_embedded_plan_reproduces_its_result(self):
        plan=fixture()
        # Plan strings must also survive HTML script escaping exactly.
        plan['name']='Fictional </script> <scenario> & comparison'
        original=copy.deepcopy(plan)
        data=self.payload(plan)
        self.assertEqual(plan,original)
        self.assertEqual(data['plans'],create_scenarios(plan))
        self.assertEqual(len(data['plans']),4)
        for embedded,result,status in zip(data['plans'],data['results'],data['verification']):
            self.assertEqual(evaluate(embedded),result)
            self.assertEqual(verify(result,embedded,ROOT/'scripts'),status)

    def test_conservative_means_remain_supported(self):
        for equity,bond in ((-.5,-.5),(-.49,-.495),(.072,.032)):
            with self.subTest(equity=equity,bond=bond):
                plan=fixture()
                plan['assumptions'].update(equity_mean=equity,bond_mean=bond)
                original=copy.deepcopy(plan)
                data=self.payload(plan)
                self.assertEqual(plan,original)
                conservative=data['plans'][-1]
                self.assertTrue(validate(conservative))
                self.assertAlmostEqual(conservative['assumptions']['equity_mean'],max(-.5,equity-.02))
                self.assertAlmostEqual(conservative['assumptions']['bond_mean'],max(-.5,bond-.01))
                self.assertTrue(all(v['passed'] for v in data['verification']))

    def test_report_with_omitted_contributions_and_skipped_conversion(self):
        plan=fixture()
        for member in plan['members']:
            member.pop('annual_pretax_401k_2026_real')
            member.pop('pretax_401k_target')
        plan['roth_conversions']=[dict(year=2027,amount_nominal=1000000,
                                      **{'from':'ira_a','to':'roth_a'})]
        data=self.payload(plan)
        for result in data['results']:
            ledger=result['deterministic_annual_ledger']
            row=ledger['rows'][0]
            self.assertEqual(row['unmet_spending']+row['unpaid_tax']+row['unmet_rmd'],0)
            self.assertTrue(row['skipped_conversions'])
            self.assertEqual(ledger['first_failure_year'],2027)

    @unittest.skipUnless(shutil.which('node'),'Node.js required for report handler regression')
    def test_invalid_report_hides_conclusions_and_exports(self):
        with tempfile.TemporaryDirectory() as tmp:
            report=render(fixture(),Path(tmp)/'report.html')
            for mode in ('empty','invalid-json','failed-verification','second-scenario',
                         'numeric-mutations','tax-method-text'):
                with self.subTest(mode=mode):
                    check=subprocess.run(['node',str(ROOT/'tests/report_ui.cjs'),str(report),mode],
                                         capture_output=True,text=True)
                    self.assertEqual(check.returncode,0,check.stdout+check.stderr)

    @unittest.skipUnless(shutil.which('node'),'Node.js required for report handler regression')
    def test_report_status_and_download_handlers(self):
        plan=fixture()
        plan['roth_conversions']=[dict(year=2027,amount_nominal=1000000,
                                      **{'from':'ira_a','to':'roth_a'})]
        with tempfile.TemporaryDirectory() as tmp:
            report=render(plan,Path(tmp)/'report.html')
            check=subprocess.run(['node',str(ROOT/'tests/report_ui.cjs'),str(report)],
                                 capture_output=True,text=True)
            self.assertEqual(check.returncode,0,check.stdout+check.stderr)


if __name__=='__main__': unittest.main()
