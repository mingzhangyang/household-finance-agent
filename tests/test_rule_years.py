"""Published tax-year values versus labeled projections (ROADMAP M2, first item).

A year uses its own published values when the register has them; otherwise it
indexes the latest published year at the plan's assumed rate and is labeled
projected. The fictional 2027 table below exists only to exercise the update
path; it is NOT IRS law. Fictional household data only.
"""
import copy
import json
import re
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import audit_plan
import tax2026
import verify_outputs
from verify_outputs import verify,verify_trace,VerifyFailure

EXAMPLE=json.loads((ROOT/'examples/audited-household-2026.json').read_text())


def plan(rate=.02,end_year=2029):
    """Example household over three years; one wage above the OASDI base."""
    p=copy.deepcopy(EXAMPLE)
    p.update(end_year=end_year,events=[])
    p['tax_policy']['future_bracket_inflation']=rate
    p['members'][0]['annual_wages_2026']=260000
    p['assumptions']['trials']=3
    return p


def fictional_2027_income_tax():
    """Test-only table: 2026 values plus round amounts. Not published law."""
    law=tax2026.PUBLISHED_INCOME_TAX[2026]
    return {'source_id':'fictional_2027_test_table',
            'brackets':{status:tuple((top+1000 if top!=float('inf') else top,rate) for top,rate in rows)
                        for status,rows in law['brackets'].items()},
            'standard':{status:amount+500 for status,amount in law['standard'].items()},
            'age_65_addition':{status:amount+50 for status,amount in law['age_65_addition'].items()},
            'ltcg':{status:tuple(top+1000 for top in tops) for status,tops in law['ltcg'].items()}}


def verifier_copy(table):
    return {'ordinary':{status:tuple((None if top==float('inf') else top,rate) for top,rate in rows)
                        for status,rows in table['brackets'].items()},
            'standard':table['standard'],'age_65_addition':table['age_65_addition'],'gain_zones':table['ltcg']}


def rows_of(result):
    return result['deterministic_annual_ledger']['rows']


class RuleYearResolution(unittest.TestCase):
    def test_published_years_use_their_own_values(self):
        self.assertEqual(tax2026.rule_year(tax2026.PUBLISHED_OASDI_WAGE_BASE,2027,.02),(2027,1.,'published'))
        self.assertEqual(tax2026.rule_year(tax2026.PUBLISHED_INCOME_TAX,2026,.02),(2026,1.,'published'))

    def test_later_years_index_the_latest_published_year(self):
        self.assertEqual(tax2026.rule_year(tax2026.PUBLISHED_INCOME_TAX,2028,.02),(2026,1.02**2,'projected'))
        self.assertEqual(tax2026.rule_year(tax2026.PUBLISHED_OASDI_WAGE_BASE,2029,.02),(2027,1.02**2,'projected'))

    def test_earlier_years_and_unsupported_rates_fail(self):
        for published,year,rate in ((tax2026.PUBLISHED_INCOME_TAX,2025,.02),
                                    (tax2026.PUBLISHED_OASDI_WAGE_BASE,2025,0.),
                                    (tax2026.PUBLISHED_INCOME_TAX,2030,.11),
                                    (tax2026.PUBLISHED_INCOME_TAX,2030,-.01)):
            with self.subTest(year=year,rate=rate),self.assertRaises(ValueError):
                tax2026.rule_year(published,year,rate)

    def test_each_row_labels_every_rule_family(self):
        result=audit_plan.evaluate(plan())
        expected={2027:('projected',2026,1.02,'published',2027,1.),
                  2028:('projected',2026,1.0404,'projected',2027,1.02),
                  2029:('projected',2026,1.061208,'projected',2027,1.0404)}
        for row in rows_of(result):
            income_status,income_year,income_index,wage_status,wage_year,wage_index=expected[row['year']]
            basis=row['rule_basis']
            self.assertEqual(basis['income_tax_tables'],{'status':income_status,'base_year':income_year,
                'multiplier':income_index,'source_id':'brackets_standard_senior'})
            self.assertEqual(basis['oasdi_wage_base'],{'status':wage_status,'base_year':wage_year,
                'multiplier':wage_index,'source_id':'payroll_2027'})
            self.assertEqual(basis['elective_deferral_limit'],{'status':income_status,'base_year':2026,
                'multiplier':income_index,'source_id':'401k_elective_limit_2026'})
            self.assertEqual(row['tax']['tax_law_year'],2026)
            self.assertIn(f'NOT published {row["year"]} law',row['tax']['policy'])
        self.assertEqual(result['evidence_status']['tax_rules'],
                         'published_tax_year_rules_with_labeled_hypothetical_projection')
        self.assertIn('labeled projected in rule_basis',result['rule_scope'][0])


class ReportRegisterCopy(unittest.TestCase):
    def test_report_template_lists_the_engine_published_years(self):
        # The report retypes published years and source IDs to refuse overstated labels.
        template=(ROOT/'assets/audit-template.html').read_text()
        listed=json.loads(re.search(r'function publishedRuleYears\(\)\{return (\{.*?\});\}',template).group(1))
        engine={family:{str(year):entry['source_id'] for year,entry in published.items()}
                for family,published in tax2026.RULE_FAMILIES.items()}
        self.assertEqual(listed,engine)


class PublishingANewYear(unittest.TestCase):
    """The update path: a newly published year replaces its projection and
    rebases later years; engine and verifier copies must change together."""

    def engine_with_2027(self):
        return mock.patch.dict(tax2026.PUBLISHED_INCOME_TAX,{2027:fictional_2027_income_tax()})

    def verifier_with_2027(self):
        return (mock.patch.dict(verify_outputs.PUBLISHED_INCOME_TAX,{2027:verifier_copy(fictional_2027_income_tax())}),
                mock.patch.dict(verify_outputs.RULE_SOURCES['income_tax_tables'],{2027:'fictional_2027_test_table'}))

    def test_published_year_replaces_projection_and_rebases_later_years(self):
        p=plan()
        before=rows_of(audit_plan.evaluate(p))
        with self.engine_with_2027():
            after=rows_of(audit_plan.evaluate(p))
        self.assertEqual(after[0]['rule_basis']['income_tax_tables'],{'status':'published','base_year':2027,
            'multiplier':1.,'source_id':'fictional_2027_test_table'})
        self.assertEqual(after[0]['tax']['policy'],'2027 published federal tables')
        self.assertEqual(after[1]['rule_basis']['income_tax_tables']['base_year'],2027)
        self.assertEqual(after[1]['tax']['rule_multiplier'],1.02)
        self.assertEqual(after[0]['tax']['standard_plus_age_deduction'],32200+500)
        self.assertNotEqual(after[0]['tax_due_total'],before[0]['tax_due_total'])
        # Families without a new publication keep their own basis.
        self.assertEqual(after[0]['rule_basis']['elective_deferral_limit'],before[0]['rule_basis']['elective_deferral_limit'])

    def test_one_sided_register_change_fails_verification(self):
        p=plan()
        with self.engine_with_2027():
            result=audit_plan.evaluate(p)
        with self.assertRaisesRegex(VerifyFailure,'published law year changed'):
            verify(result,p)
        tables,sources=self.verifier_with_2027()
        with tables,sources:
            self.assertTrue(verify(result,p)['passed'])
            with self.engine_with_2027():
                self.assertTrue(verify_trace(audit_plan.trace(p,1),p,result)['passed'])


class RuleBasisForgeries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan=plan()
        cls.result=audit_plan.evaluate(cls.plan)

    def forged(self,mutate,row=0):
        result=copy.deepcopy(self.result)
        mutate(rows_of(result)[row])
        return result

    def test_valid_result_passes(self):
        self.assertTrue(verify(self.result,self.plan,ROOT/'scripts')['passed'])

    def test_projected_year_cannot_be_labeled_published(self):
        result=self.forged(lambda row:row['rule_basis']['income_tax_tables'].update(status='published',multiplier=1.))
        with self.assertRaisesRegex(VerifyFailure,r'labeled published from 2026 \(brackets_standard_senior\); the register gives projected from 2026 \(brackets_standard_senior\)'):
            verify(result,self.plan)

    def test_published_year_cannot_be_labeled_projected(self):
        result=self.forged(lambda row:row['rule_basis']['oasdi_wage_base'].update(status='projected'))
        with self.assertRaisesRegex(VerifyFailure,'oasdi_wage_base labeled projected'):
            verify(result,self.plan)

    def test_base_year_source_and_index_are_checked(self):
        for family,field,value,message in (
                ('income_tax_tables','base_year',2027,'labeled projected from 2027'),
                ('income_tax_tables','base_year',2026.0,'labeled projected from 2026.0'),
                ('oasdi_wage_base','source_id','payroll',r'oasdi_wage_base labeled published from 2027 \(payroll\); the register gives published from 2027 \(payroll_2027\)'),
                ('elective_deferral_limit','multiplier',1.03,'elective_deferral_limit index from 2026')):
            with self.subTest(family=family,field=field):
                result=self.forged(lambda row:row['rule_basis'][family].update({field:value}))
                with self.assertRaisesRegex(VerifyFailure,message):
                    verify(result,self.plan)

    def test_families_and_fields_are_exact(self):
        for mutate in (lambda row:row['rule_basis'].pop('elective_deferral_limit'),
                       lambda row:row['rule_basis'].update(state_tax_tables={}),
                       lambda row:row['rule_basis']['income_tax_tables'].update(enacted=True),
                       lambda row:row['rule_basis']['income_tax_tables'].pop('source_id')):
            with self.subTest(mutate=mutate),self.assertRaisesRegex(VerifyFailure,'rule_basis'):
                verify(self.forged(mutate),self.plan)

    def test_policy_disclosure_must_match_the_basis(self):
        result=self.forged(lambda row:row['tax'].update(policy='2027 published federal tables'))
        with self.assertRaisesRegex(VerifyFailure,'policy disclosure differs'):
            verify(result,self.plan)

    def test_law_year_must_match_the_register(self):
        for value in (2027,2026.0,True):
            with self.subTest(value=value):
                result=self.forged(lambda row:row['tax'].update(tax_law_year=value),row=1)
                with self.assertRaisesRegex(VerifyFailure,'published law year changed'):
                    verify(result,self.plan)

    def test_contract_results_must_carry_the_basis(self):
        result=self.forged(lambda row:row.pop('rule_basis'),row=2)
        with self.assertRaisesRegex(VerifyFailure,'rule_basis'):
            verify(result,self.plan)

    def test_trace_rows_must_carry_the_basis(self):
        trace=audit_plan.trace(self.plan,0)
        self.assertTrue(verify_trace(trace,self.plan)['passed'])
        rows_of_trace=trace['path_ledger']['rows']
        rows_of_trace[1]['rule_basis']['income_tax_tables']['status']='published'
        with self.assertRaisesRegex(VerifyFailure,'labeled published'):
            verify_trace(trace,self.plan)

    def test_legacy_results_without_metadata_follow_the_same_register(self):
        result=copy.deepcopy(self.result)
        del result['evidence_status'],result['input_provenance']
        for row in rows_of(result):
            del row['rule_basis']
            row['tax']['policy']='2026 rates indexed hypothetically; NOT a future-year statute'
        self.assertTrue(verify(result,self.plan)['passed'])
        rows_of(result)[0]['tax']['rule_multiplier']=1.
        with self.assertRaisesRegex(VerifyFailure,'hypothetical bracket index'):
            verify(result,self.plan)

    def test_evidence_contract_version_is_current(self):
        result=copy.deepcopy(self.result)
        result['evidence_status']['contract_version']='1.0'
        with self.assertRaisesRegex(VerifyFailure,'evidence or professional-approval claim'):
            verify(result,self.plan)


if __name__=='__main__':
    unittest.main()
