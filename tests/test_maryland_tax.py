"""Maryland state and local income tax (ROADMAP M2 group 2). Fictional data only.

Printed Comptroller answers anchor both the engine and the verifier's retyped
copy; integration cases check validation, the ledger, the funding threshold
and coherent forgeries. Rules: references/rules-provenance.md (Maryland).
"""
import copy
import json
import sys
import unittest
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import audit_plan
import maryland_tax
import state_tax
import verify_outputs
from verify_outputs import verify,verify_trace,VerifyFailure
from test_verifier_independence import household,first_row

CASES=json.loads((ROOT/'tests/golden/maryland-printed-cases.json').read_text())
EXAMPLE=json.loads((ROOT/'examples/audited-household-2026.json').read_text())
LAW=maryland_tax.PUBLISHED_LOCAL_RATES[2026]['rates']


def md(local='montgomery_county',pensions=None):
    return dict(jurisdiction='US-MD',residency='full_year_resident',local_jurisdiction=local,
                pension_plan_types=pensions or {})


def whole_dollars(value):
    return float(Decimal(str(value)).quantize(Decimal('1'),ROUND_HALF_UP))


def engine_case(case):
    i=case['inputs']
    kind=case['kind']
    if kind=='state_rate':
        return sum(line['tax'] for line in maryland_tax.bracket_lines(i['income'],maryland_tax.STATE_BRACKETS[i['status']]))
    if kind=='state_table':
        # Below $100,000 both schedules agree; the table taxes each row's midpoint.
        middle=(i['at_least']+i['less_than'])/2
        return whole_dollars(sum(line['tax'] for line in maryland_tax.bracket_lines(middle,maryland_tax.STATE_BRACKETS['single'])))
    if kind in ('anne_arundel_table','anne_arundel_rate','frederick'):
        county='frederick_county' if kind=='frederick' else 'anne_arundel_county'
        income=(i['at_least']+i['less_than'])/2 if kind=='anne_arundel_table' else i['income']
        tax=sum(line['tax'] for line in maryland_tax.local_tax(income,county,i.get('status','single'),LAW)[1])
        return whole_dollars(tax) if kind=='anne_arundel_table' else tax
    if kind=='exemption':
        return maryland_tax.exemption_each(i['fagi'],i['status'])
    if kind=='senior_credit':
        return maryland_tax.senior_credit(i['fagi'],i['status'],i['older'])
    return maryland_tax.pension_exclusion(i['qualifying'],i['social_security'],i['limit'],i['age'])


def verifier_case(case):
    i=case['inputs']
    kind=case['kind']
    if kind=='state_rate':
        return sum(r*a for _,_,r,a in verify_outputs.md_portions(i['income'],verify_outputs.MD_BRACKETS[i['status']]))
    if kind=='state_table':
        middle=(i['at_least']+i['less_than'])/2
        return whole_dollars(sum(r*a for _,_,r,a in verify_outputs.md_portions(middle,verify_outputs.MD_BRACKETS['single'])))
    if kind in ('anne_arundel_table','anne_arundel_rate','frederick'):
        county='frederick_county' if kind=='frederick' else 'anne_arundel_county'
        income=(i['at_least']+i['less_than'])/2 if kind=='anne_arundel_table' else i['income']
        tax=sum(r*a for _,_,r,a in verify_outputs.md_local_lines(income,county,i.get('status','single'),verify_outputs.MD_LOCAL[2026])[1])
        return whole_dollars(tax) if kind=='anne_arundel_table' else tax
    if kind=='exemption':
        return verify_outputs.md_exemption(i['fagi'],i['status'])
    if kind=='senior_credit':
        return verify_outputs.md_credit(i['fagi'],i['status'],i['older'])
    return verify_outputs.md_pension_exclusion(i['qualifying'],i['social_security'],i['limit'],i['age'])


class PrintedComptrollerAnswers(unittest.TestCase):
    def test_engine_reproduces_printed_cases(self):
        for case in CASES['cases']:
            with self.subTest(case=case['id']):
                self.assertIn(case['source'],CASES['sources'])
                self.assertAlmostEqual(engine_case(case),case['expected'],delta=1e-6)

    def test_verifier_copy_reproduces_printed_cases(self):
        # The verifier's retyped schedules answer to the same printed values.
        for case in CASES['cases']:
            with self.subTest(case=case['id']):
                self.assertAlmostEqual(verifier_case(case),case['expected'],delta=1e-6)

    def test_retyped_copies_agree_with_the_engine_registry(self):
        to_none=lambda rows:tuple((None if top==float('inf') else top,rate) for top,rate in rows)
        self.assertEqual({k:to_none(v) for k,v in maryland_tax.STATE_BRACKETS.items()},verify_outputs.MD_BRACKETS)
        self.assertEqual(maryland_tax.EXEMPTION_LIMITS,verify_outputs.MD_EXEMPTION_LIMITS)
        self.assertEqual(maryland_tax.SENIOR_CREDIT,verify_outputs.MD_SENIOR_CREDIT)
        self.assertEqual({y:e['amounts'] for y,e in maryland_tax.PUBLISHED_STANDARD_DEDUCTION.items()},verify_outputs.MD_STANDARD)
        self.assertEqual({y:e['amount'] for y,e in maryland_tax.PUBLISHED_PENSION_EXCLUSION.items()},verify_outputs.MD_PENSION_LIMIT)
        kinds={'flat':'flat','brackets':'graduated_brackets','income_band':'income_band_rate'}
        for county,(kind,schedule) in LAW.items():
            with self.subTest(county=county):
                structure,copy_schedule=verify_outputs.MD_LOCAL[2026][county]
                self.assertEqual(structure,kinds[kind])
                self.assertEqual(schedule if kind=='flat' else {k:to_none(v) for k,v in schedule.items()},copy_schedule)
        self.assertEqual(set(LAW),set(verify_outputs.MD_LOCAL[2026]))
        self.assertEqual(len(LAW),24)  # 23 counties and Baltimore City


class SpecValidation(unittest.TestCase):
    def plan(self,spec):
        p=copy.deepcopy(EXAMPLE)
        p['tax_policy']['state_income_tax']=spec
        return p

    def test_unsupported_specs_fail_closed(self):
        pension=copy.deepcopy(EXAMPLE['members'][0])
        cases=[(md()|{'jurisdiction':'US-VA'},'not registered'),('NY','registered jurisdiction object'),
               (md()|{'residency':'part_year_resident'},'full_year_resident'),
               ({k:v for k,v in md().items() if k!='local_jurisdiction'},'local_jurisdiction'),
               (md('montgomery'),'local_jurisdiction'),
               ({k:v for k,v in md().items() if k!='pension_plan_types'},'pension_plan_types'),
               (md(pensions={'person_a':'employee_retirement_system'}),'exactly the members'),
               (md()|{'county_code':16},'unsupported fields'),(None,'registered jurisdiction object')]
        for spec,message in cases:
            with self.subTest(spec=spec):
                with self.assertRaisesRegex(audit_plan.ModelError,message):
                    audit_plan.validate(self.plan(spec))
        missing=copy.deepcopy(EXAMPLE);del missing['tax_policy']['state_income_tax']
        with self.assertRaisesRegex(audit_plan.ModelError,'state_income_tax required'):
            audit_plan.validate(missing)
        with_pension=self.plan(md(pensions={'person_a':'teacher_plan'}))
        with_pension['members'][0].update(annual_pension_2026_real=10000,pension_start_age=65)
        with self.assertRaisesRegex(audit_plan.ModelError,'pension plan type'):
            audit_plan.validate(with_pension)
        self.assertEqual(pension,EXAMPLE['members'][0])

    def test_registry_and_federal_only_scope(self):
        self.assertEqual(set(state_tax.REGISTRY),{'US-MD'})
        self.assertIsNone(state_tax.module(state_tax.EXCLUDED))
        self.assertEqual(state_tax.rule_basis(state_tax.EXCLUDED,2030,.02),{})
        self.assertIsNone(state_tax.compute(state_tax.EXCLUDED))


def retiree(*,pension=0,kind='employee_retirement_system',ira=0,k401=0,living=0,local='howard_county',birth=1960,cash=100000):
    """Single filer, zero returns and rates frozen (rate 0), Maryland."""
    p=household(birth=birth,cash=cash,ira=ira,living=living)
    p['accounts'].append(dict(id='k401',kind='traditional_401k',owner='a',balance=k401,
                              still_working_exception=False,fully_pretax_confirmed=True))
    p['withdrawal_order'].append('k401')
    if pension:
        p['members'][0].update(annual_pension_2026_real=pension,pension_start_age=60)
    p['tax_policy']['state_income_tax']=md(local,{'a':kind} if pension else {})
    return p


class EngineIntegration(unittest.TestCase):
    def test_hand_computed_pensioner(self):
        # 66 in 2027; ERS pension 50,000, no Social Security, cash pays spending.
        # FAGI 50,000; exclusion min(50,000, 40,600); MD AGI 9,400; standard
        # 3,350; exemptions 3,200 + 1,000; taxable 1,850; state 20 + 850 x 3% =
        # 45.50, fully offset by the 1,000 senior credit; Howard 3.2% = 59.20.
        p=retiree(pension=50000)
        result=audit_plan.evaluate(p)
        s=first_row(result)['state_tax']
        expected=dict(federal_adjusted_gross_income=50000,pension_exclusion=40600,maryland_adjusted_gross_income=9400,
                      standard_deduction=3350,exemptions=4200,taxable_net_income=1850,state_tax_before_credits=45.5,
                      senior_tax_credit=45.5,state_tax_after_credits=0,local_tax=59.2,total_state_and_local_tax=59.2)
        for key,value in expected.items():
            self.assertAlmostEqual(s[key],value,delta=.005,msg=key)
        self.assertEqual(s['members']['a']['modified_maryland_agi'],None)
        self.assertTrue(verify(result,p,ROOT/'scripts')['passed'])

    def test_ira_distributions_never_qualify(self):
        # 75 in 2035... use 73 (RMD) for a 1954 birth in 2027: IRA RMD only, then 401(k) RMD only.
        ira=audit_plan.evaluate(retiree(birth=1954,ira=265000))
        k401=audit_plan.evaluate(retiree(birth=1954,k401=265000))
        other=audit_plan.evaluate(retiree(pension=30000,kind='not_employee_retirement_system'))
        self.assertEqual(first_row(ira)['state_tax']['members']['a']['qualifying_pension_income'],0)
        self.assertAlmostEqual(first_row(k401)['state_tax']['members']['a']['qualifying_pension_income'],10000,delta=.005)
        self.assertAlmostEqual(first_row(k401)['state_tax']['pension_exclusion'],10000,delta=.005)
        self.assertEqual(first_row(other)['state_tax']['pension_exclusion'],0)
        for result,plan in ((ira,retiree(birth=1954,ira=265000)),(k401,retiree(birth=1954,k401=265000))):
            self.assertTrue(verify(result,plan)['passed'])

    def test_example_total_due_includes_maryland(self):
        p=copy.deepcopy(EXAMPLE);p.update(end_year=2030,events=[]);p['assumptions']['trials']=4
        result=audit_plan.evaluate(p)
        for row in result['deterministic_annual_ledger']['rows']:
            s=row['state_tax']
            self.assertAlmostEqual(row['tax_due_total'],row['tax']['total_federal_income_and_niit']+row['payroll_tax']['total']
                                   +s['total_state_and_local_tax'],delta=.0151)
            # Both spouses work: the two-income subtraction reaches its $1,200 limit.
            self.assertEqual(s['two_income_subtraction'],1200)
            self.assertEqual(set(row['rule_basis']),{'income_tax_tables','oasdi_wage_base','elective_deferral_limit',
                             'md_standard_deduction','md_pension_exclusion_limit','md_local_income_tax_rates'})
            self.assertEqual(row['rule_basis']['md_local_income_tax_rates']['multiplier'],1)
            self.assertIn('md_income_tax_rates',row['source_ids'])
        self.assertIn('md_local_rates_2026',result['rules_sources'])
        self.assertTrue(verify(result,p,ROOT/'scripts')['passed'])
        for index in range(4):
            self.assertTrue(verify_trace(audit_plan.trace(p,index),p,result)['passed'])
        federal=copy.deepcopy(p);federal['tax_policy']['state_income_tax']='excluded_with_disclosure'
        rows=audit_plan.evaluate(federal)['deterministic_annual_ledger']['rows']
        self.assertTrue(all(row['state_tax'] is None and 'md_standard_deduction' not in row['rule_basis'] for row in rows))

    def test_surtax_needs_fagi_above_350000_and_positive_line_7a(self):
        def plan(ira_draw_cash):
            p=retiree(birth=1950+10,cash=0,living=0,local='frederick_county')
            p['members'][0].update(annual_wages_2026=ira_draw_cash,retirement_age=90)
            p['accounts'][1].update(balance=200000,basis=0,gain_treatment='long_term_proportional_with_distributions',
                annual_distributions=dict(qualified_dividend_yield=0,nonqualified_dividend_yield=0,taxable_interest_yield=0,
                                          capital_gain_distribution_yield=.1,handling='reinvested'))
            p['capital_loss_carryover_into_2027']=0
            return p
        low,high=audit_plan.evaluate(plan(300000)),audit_plan.evaluate(plan(400000))
        self.assertEqual(first_row(low)['state_tax']['capital_gain_surtax'],0)
        s=first_row(high)['state_tax']
        self.assertEqual(s['capital_gain_surtax_base'],20000)
        self.assertAlmostEqual(s['capital_gain_surtax'],400,delta=.005)
        # Frederick: one rate on all taxable net income above $150,000 (single).
        self.assertEqual(s['local_rate_structure'],'income_band_rate')
        self.assertEqual([line['rate'] for line in s['local_tax_lines']],[.032])
        self.assertTrue(verify(high,plan(400000))['passed'])

    def test_two_income_subtraction_needs_income_for_both_spouses(self):
        p=copy.deepcopy(EXAMPLE);p.update(end_year=2027,events=[]);p['assumptions']['trials']=1
        p['members'][1].update(annual_wages_2026=0,annual_pretax_401k_2026_real=0)
        p['members'][1].pop('pretax_401k_target')
        for account in p['accounts']:
            if account['kind'] in ('cash','taxable'):
                account['balance']=0;account.pop('basis',None) if account['kind']=='cash' else account.update(basis=0)
        result=audit_plan.evaluate(p)
        s=first_row(result)['state_tax']
        self.assertEqual(s['members']['person_b']['modified_maryland_agi'],0)
        self.assertEqual(s['two_income_subtraction'],0)
        self.assertTrue(verify(result,p)['passed'])


def threshold_plan(living=83000):
    """A loss sale lowers FAGI to $100,000: the single filer's exemption and
    senior credit return, so the Maryland tax falls by more than the sale."""
    p=household(birth=1957,cash=0,brokerage=100000,basis=200000,living=living)
    p['accounts'][1].update(gain_treatment='long_term_proportional_with_distributions',annual_distributions=dict(
        qualified_dividend_yield=0,nonqualified_dividend_yield=0,taxable_interest_yield=0,
        capital_gain_distribution_yield=0,handling='reinvested'))
    p['capital_loss_carryover_into_2027']=0
    p['members'][0].update(annual_pension_2026_real=101000,pension_start_age=60)
    p['tax_policy']['state_income_tax']=md('howard_county',{'a':'not_employee_retirement_system'})
    return p


class FundingThreshold(unittest.TestCase):
    def setUp(self):
        self.plan=threshold_plan()
        self.result=audit_plan.evaluate(self.plan)
        self.row=first_row(self.result)

    def test_least_funding_crosses_the_threshold_and_keeps_the_excess(self):
        s=self.row['state_tax']
        self.assertEqual(self.row['extra_draws'],{'brokerage':1000.0})
        self.assertEqual(s['federal_adjusted_gross_income'],100000)
        self.assertEqual((s['exemption_per_person'],s['senior_tax_credit']),(3200,1000))
        self.assertGreater(s['funding_cliff_excess_cash'],0)
        self.assertEqual(self.row['closing_accounts']['cash'],s['funding_cliff_excess_cash'])
        self.assertEqual(self.row['unpaid_tax'],0)
        self.assertTrue(verify(self.result,self.plan,ROOT/'scripts')['passed'])
        self.assertTrue(verify(self.result)['passed'])
        self.assertTrue(verify_trace(audit_plan.trace(self.plan,0),self.plan,self.result)['passed'])
        # One cent less of sale keeps FAGI above $100,000 and leaves tax unpaid.
        raised=verify_outputs.md_liability('single','howard_county',verify_outputs.MD_LOCAL[2026],100000.01,
            s['maryland_adjusted_gross_income']+.01,s['standard_deduction'],[70],s['capital_gain_in_maryland_agi']+.01)
        self.assertGreater(raised-s['total_state_and_local_tax'],s['funding_cliff_excess_cash'])

    def test_excess_must_be_the_remaining_cash(self):
        for value in (0,self.row['state_tax']['funding_cliff_excess_cash']+1):
            with self.subTest(value=value):
                forged=copy.deepcopy(self.result)
                first_row(forged)['state_tax']['funding_cliff_excess_cash']=value
                with self.assertRaisesRegex(VerifyFailure,'cash remained|funding threshold excess'):
                    verify(forged,self.plan)

    def test_excess_needs_a_threshold_a_loss_sale_crosses(self):
        row=copy.deepcopy(self.row)
        expect=lambda actual,expected,desc,tol:verify_outputs.close(actual,expected,desc,tol)
        inv=verify_outputs._investment_view(row,True)
        policy=self.plan['tax_policy']
        self.assertGreater(verify_outputs._state_checks(row,policy,expect,True,inv)['excess'],0)
        inv['records']={'brokerage':dict(inv['records']['brokerage'],sale_gain_or_loss=0.)}
        with self.assertRaisesRegex(VerifyFailure,'without a Maryland threshold'):
            verify_outputs._state_checks(row,policy,expect,True,inv)

    def test_federal_scope_has_no_state_threshold(self):
        # Without Maryland tax the pension covers spending and federal tax: no sale.
        federal=copy.deepcopy(self.plan);federal['tax_policy']['state_income_tax']='excluded_with_disclosure'
        result=audit_plan.evaluate(federal)
        row=first_row(result)
        self.assertIsNone(row['state_tax'])
        self.assertEqual(row['extra_draws'],{})
        self.assertTrue(verify(result,federal)['passed'])


class VerifierForgeries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan=copy.deepcopy(EXAMPLE);cls.plan.update(end_year=2028,events=[]);cls.plan['assumptions']['trials']=2
        cls.result=audit_plan.evaluate(cls.plan)

    def forged(self,change):
        result=copy.deepcopy(self.result)
        change(first_row(result))
        return result

    def test_record_presence_must_follow_the_policy(self):
        with self.assertRaisesRegex(VerifyFailure,'Maryland state tax record fields changed'):
            verify(self.forged(lambda row:row.update(state_tax=None)),self.plan)
        federal=copy.deepcopy(self.result);federal['tax_policy']['state_income_tax']='excluded_with_disclosure'
        with self.assertRaisesRegex(VerifyFailure,'state tax reported although the plan excludes'):
            verify(federal)
        with self.assertRaisesRegex(VerifyFailure,'output tax policy mismatched to plan'):
            verify(federal,self.plan)

    def test_county_and_rate_structure_must_match_the_plan(self):
        for change in (lambda row:row['state_tax'].update(local_jurisdiction='howard_county'),
                       lambda row:row['state_tax'].update(local_rate_structure='graduated_brackets'),
                       lambda row:row['state_tax'].update(residency='part_year_resident')):
            with self.assertRaisesRegex(VerifyFailure,'jurisdiction, residency, county or local rate structure'):
                verify(self.forged(change))

    def test_coherently_lowered_local_tax_is_rejected(self):
        def lower(row):
            s=row['state_tax']
            cut=round(s['local_tax']*.1,2)
            s['local_tax']=round(s['local_tax']-cut,2);s['local_tax_lines'][0]['tax']=s['local_tax']
            s['total_state_and_local_tax']=round(s['total_state_and_local_tax']-cut,2)
            row['tax_due_total']=round(row['tax_due_total']-cut,2)
        with self.assertRaisesRegex(VerifyFailure,'Maryland local line 0 multiplication'):
            verify(self.forged(lower))

    def test_exemption_and_credit_follow_reported_fagi(self):
        with self.assertRaisesRegex(VerifyFailure,'Maryland exemption by FAGI'):
            verify(self.forged(lambda row:row['state_tax'].update(exemption_per_person=3200.)))
        with self.assertRaisesRegex(VerifyFailure,'Maryland senior tax credit'):
            verify(self.forged(lambda row:row['state_tax'].update(senior_tax_credit=1750.)))

    def test_member_shares_need_the_plan(self):
        def shift(row):
            members=row['state_tax']['members']
            members['person_a']['modified_maryland_agi']+=500
            members['person_b']['modified_maryland_agi']-=500
        # Output-only, the shares still total FAGI less subtractions.
        self.assertTrue(verify(self.forged(shift))['passed'])
        with self.assertRaisesRegex(VerifyFailure,'two-income share of person_a'):
            verify(self.forged(shift),self.plan)
        with self.assertRaisesRegex(VerifyFailure,'Maryland age of person_a'):
            verify(self.forged(lambda row:row['state_tax']['members']['person_a'].update(age=50)),self.plan)


if __name__=='__main__':
    unittest.main()
