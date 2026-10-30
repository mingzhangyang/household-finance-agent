"""Taxable brokerage account: distributions, losses and the capital-loss carryover (M2 group 1).

Known answers come from the documents in
references/primary-source-review-2026-10-29-taxable-account.md or are worked by
hand in the comments; none is copied from engine output. Fictional data only.
"""
import copy
import json
import random
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'tests'))
import audit_plan
from audit_plan import ModelError,evaluate,trace,validate
from tax2026 import federal_tax
from test_verifier_independence import household
from verify_outputs import VerifyFailure,verify,verify_trace

WITH='long_term_proportional_with_distributions'
LEGACY='long_term_proportional_no_loss_offset'


def with_distributions(plan,q=0.,nq=0.,interest=0.,cgd=0.,carryover=0.):
    plan['accounts'][1].update(gain_treatment=WITH,annual_distributions=dict(
        qualified_dividend_yield=q,nonqualified_dividend_yield=nq,taxable_interest_yield=interest,
        capital_gain_distribution_yield=cgd,handling='reinvested'))
    plan['capital_loss_carryover_into_2027']=carryover
    return plan


def tax(**kwargs):
    base=dict(wages_taxable=0,pension=0,ira_distributions=0,roth_conversions=0,cash_interest=0,
              ltcg=0,ss_benefits=0,status='single',ages=[50],year=2026)
    base.update(kwargs)
    return federal_tax(**base)


def rows(result):
    return result['deterministic_annual_ledger']['rows']


class FailClosedInputs(unittest.TestCase):
    def plan(self):
        return with_distributions(household(birth=1956,brokerage=100000,basis=80000,living=1000),q=.02)

    def test_supported_plan_validates(self):
        self.assertTrue(validate(self.plan()))

    def test_unstated_or_unsupported_distribution_inputs_are_rejected(self):
        mutations=[
            lambda p:p['accounts'][1].pop('annual_distributions'),
            lambda p:p['accounts'][1]['annual_distributions'].pop('taxable_interest_yield'),
            lambda p:p['accounts'][1]['annual_distributions'].update(handling='paid_to_cash'),
            lambda p:p['accounts'][1]['annual_distributions'].update(qualified_dividend_yield=.21),
            lambda p:p['accounts'][1]['annual_distributions'].update(nonqualified_dividend_yield=-.01),
            lambda p:p['accounts'][1]['annual_distributions'].update(return_of_capital_yield=0),
            lambda p:p.pop('capital_loss_carryover_into_2027'),
            lambda p:p.update(capital_loss_carryover_into_2027=-1),
            lambda p:p['accounts'][1].update(gain_treatment='short_term_lots'),
            # The legacy label models neither distributions nor losses.
            lambda p:p['accounts'][1].update(gain_treatment=LEGACY),
            lambda p:(p['accounts'][1].update(gain_treatment=LEGACY),p['accounts'][1].pop('annual_distributions'),
                      p.update(capital_loss_carryover_into_2027=500)),
        ]
        for index,mutate in enumerate(mutations):
            with self.subTest(case=index):
                plan=self.plan()
                mutate(plan)
                with self.assertRaises(ModelError):
                    validate(plan)

    def test_documented_verified_requires_a_documented_carryover(self):
        plan=self.plan()
        plan['input_provenance']={'mode':'documented_verified','register':[
            {'json_pointer':pointer,'evidence_id':'E'+str(i),'source_type':'statement',
             'as_of_date':'2026-12-31','confidence':'documented'}
            for i,pointer in enumerate(['/living_expenses_annual_real','/accounts/0/balance','/accounts/1/balance',
                '/accounts/1/basis','/accounts/2/balance','/accounts/3/balance','/members/0/annual_wages_2026',
                '/members/0/ss_annual_2026_real_at_chosen_claim_age'])]}
        with self.assertRaisesRegex(ModelError,'capital_loss_carryover_into_2027'):
            validate(plan)
        plan['input_provenance']['register'].append({'json_pointer':'/capital_loss_carryover_into_2027',
            'evidence_id':'SCHEDULE-D-2026','source_type':'tax_form','as_of_date':'2026-12-31','confidence':'documented'})
        self.assertTrue(validate(plan))


class FederalKnownAnswers(unittest.TestCase):
    def test_publication_550_bob_and_shelly(self):
        # Pub 550 (2025) p. 102: $7,000 loss, taxable income $26,000 -> deduct
        # $3,000 and carry $4,000. 2026 MFJ standard deduction is $32,200, so
        # wages of $61,200 give AGI 58,200 and taxable income 26,000.
        r=tax(wages_taxable=61200,ltcg=-7000,status='mfj',ages=[50,50])
        self.assertEqual((r['adjusted_gross_income'],r['ordinary_taxable']),(58200,26000))
        self.assertEqual((r['capital_loss_deduction'],r['capital_loss_used'],r['capital_loss_carryover_out']),(3000,3000,4000))
        self.assertEqual(r['capital_gain_or_loss_in_agi'],-3000)

    def test_loss_smaller_than_limit_with_negative_taxable_income_carries_in_full(self):
        # Worksheet line 1 is taxable income as if it could be negative:
        # 10,000 - 2,000 - 16,100 = -8,100; line 3 = max(0, -8,100 + 2,000) = 0.
        r=tax(wages_taxable=10000,ltcg=-2000)
        self.assertEqual((r['capital_loss_deduction'],r['capital_loss_used'],r['capital_loss_carryover_out']),(2000,0,2000))
        self.assertEqual(r['capital_loss_adjusted_taxable_income'],-6100)

    def test_section_151_senior_deduction_is_added_back(self):
        # IRC 1212(b)(2)(B) adds the section 151 deduction; Pub. L. 119-21 put the
        # $6,000 senior deduction in section 151(d)(5)(C). Single, 66 in 2027,
        # frozen 2026 tables: deductions 16,100 + 2,050 + 6,000 = 24,150.
        # Pension 20,150, loss 5,000: AGI 17,150; taxable income -7,000;
        # adjusted = -7,000 + 3,000 + 6,000 = 2,000 used, 3,000 carried.
        # Without the add-back (the 2025 worksheet text) nothing would be used.
        r=tax(pension=20150,ltcg=-5000,ages=[66],year=2027)
        self.assertEqual(r['enhanced_senior_deduction'],6000)
        self.assertEqual((r['capital_loss_adjusted_taxable_income'],r['capital_loss_used'],r['capital_loss_carryover_out']),(2000,2000,3000))

    def test_qualified_dividends_use_the_capital_gain_worksheet(self):
        # Form 1040 instructions p. 38 with 2026 single values: wages 60,000,
        # qualified dividends 20,000. Line 1 = 63,900; line 5 = 43,900; line 9 =
        # 49,450 - 43,900 = 5,550 at 0%; line 17 = 14,450 at 15% = 2,167.50;
        # line 22 = 1,240 + .12 x 31,500 = 5,020; line 24 = 8,770; line 25 = 7,187.50.
        r=tax(wages_taxable=60000,qualified_dividends=20000)
        self.assertEqual((r['preferential_income'],r['long_term_gain_taxable'],r['ordinary_taxable']),(20000,20000,43900))
        self.assertEqual([round(line['taxable'],2) for line in r['capital_gain_rate_lines']],[5550,14450,0])
        self.assertAlmostEqual(r['federal_income_tax'],7187.5,places=6)

    def test_nonqualified_dividends_and_interest_are_ordinary(self):
        r=tax(wages_taxable=50000,nonqualified_dividends=1000,taxable_interest=2000)
        self.assertEqual((r['gross_ordinary'],r['adjusted_gross_income'],r['preferential_income']),(53000,53000,0))

    def test_netting_with_distributions_and_carryover(self):
        cases=[  # sale, capital gain distributions, carryover in -> net, deduction, line 7a, carryover out
            (-4000,1500,0,-2500,2500,-2500,0),
            (10000,0,7000,3000,0,3000,0),
            (2000,500,9000,-6500,3000,-3000,3500)]
        for sale,cgd,carry,net,deduction,line7,out in cases:
            with self.subTest(sale=sale,cgd=cgd,carry=carry):
                r=tax(wages_taxable=200000,ltcg=sale,capital_gain_distributions=cgd,capital_loss_carryover_in=carry)
                self.assertEqual((r['net_capital_gain_or_loss'],r['capital_loss_deduction'],
                                  r['capital_gain_or_loss_in_agi'],r['capital_loss_carryover_out']),(net,deduction,line7,out))
                self.assertEqual(r['adjusted_gross_income'],200000+line7)

    def test_social_security_provisional_income_includes_dividends_and_line_7a(self):
        # Pub 915 Worksheet 1 line 3: lines 2b, 3b and 7a. Other income 30,000
        # pension + 2,000 interest + 3,000 dividends - 3,000 allowed loss.
        r=tax(pension=30000,taxable_interest=2000,qualified_dividends=1000,nonqualified_dividends=2000,
              ltcg=-9000,ss_benefits=20000,ages=[70],year=2027)
        self.assertEqual(r['ss_provisional_income'],32000+10000)
        # A loss larger than all other income leaves negative other income: no taxable benefits.
        r=tax(ltcg=-9000,ss_benefits=20000,ages=[70],year=2027)
        self.assertEqual((r['ss_provisional_income'],r['taxable_social_security']),(-3000+10000,0))


class CarryoverWorksheetCharacter(unittest.TestCase):
    def test_short_and_long_term_split_never_changes_the_total(self):
        """With no short-term gains in the model, the Capital Loss Carryover
        Worksheet (Schedule D instructions p. 10) gives the same total carryover
        however the loss splits between short- and long-term."""
        def worksheet(taxable_income,short_loss,long_net):
            line7=-short_loss                      # Schedule D line 7: net short-term
            line15=long_net                        # line 15: net long-term
            line16=line7+line15
            if line16>=0:
                return 0.
            line21=-min(3000.,-line16)
            l1=taxable_income; l2=-line21; l3=max(0.,l1+l2); l4=min(l2,l3)
            l5=-line7 if line7<0 else 0.
            l6=max(0.,line15)
            short_carry=max(0.,l5-(l4+l6)) if line7<0 else 0.
            long_carry=0.
            if line15<0:
                l9=-line15; l10=max(0.,line7); l11=max(0.,l4-l5); long_carry=max(0.,l9-(l10+l11))
            return short_carry+long_carry
        rng=random.Random(1212)
        for _ in range(2000):
            total=rng.uniform(-50000,20000)
            short=rng.uniform(0,max(0.,-total)+rng.uniform(0,10000))
            taxable_income=rng.uniform(-40000,60000)
            combined=worksheet(taxable_income,0.,total)
            split=worksheet(taxable_income,short,total+short)
            self.assertAlmostEqual(combined,split,places=6)
            deduction=min(3000.,-total) if total<0 else 0.
            expected=(-total-min(deduction,max(0.,taxable_income+deduction))) if total<0 else 0.
            self.assertAlmostEqual(combined,expected,places=6)


class EngineIntegration(unittest.TestCase):
    def loss_plan(self,**kwargs):
        # Value 100,000 below basis 150,000 plus reinvested distributions; zero returns.
        return with_distributions(household(birth=1956,brokerage=100000,basis=150000,living=20000,years=3),
                                  q=.02,nq=.005,interest=.01,cgd=.01,carryover=1000,**kwargs)

    def test_distributions_raise_basis_and_losses_carry_forward(self):
        plan=self.loss_plan()
        result=evaluate(plan)
        first,second=rows(result)[:2]
        record=first['taxable_accounts']['brokerage']
        # 2% + 0.5% + 1% + 1% of 100,000; zero return keeps the value at 100,000.
        self.assertEqual({k:record[k] for k in ('qualified_dividends','nonqualified_dividends','interest',
                          'capital_gain_distributions','reinvested_distributions')},
                         dict(qualified_dividends=2000,nonqualified_dividends=500,interest=1000,
                              capital_gain_distributions=1000,reinvested_distributions=4500))
        # 20,000 sold at basis ratio 154,500 / 100,000.
        self.assertEqual((record['basis_sold'],record['sale_gain_or_loss'],first['taxable_basis_end']['brokerage']),
                         (30900,-10900,123600))
        t=first['tax']
        self.assertEqual((t['net_capital_gain_or_loss'],t['capital_loss_deduction'],t['adjusted_gross_income']),(-10900,3000,500))
        # Age 71 single: taxable income 500 - 24,150 < 0 even with the add-back, so all 10,900 carries.
        self.assertEqual((t['capital_loss_used'],t['capital_loss_carryover_out']),(0,10900))
        self.assertEqual(second['tax']['capital_loss_carryover_in'],10900)
        # Form 8960: 1,000 interest + 2,500 dividends - 3,000 allowed loss.
        self.assertEqual(t['niit_net_investment_income'],500)
        self.assertTrue(verify(result,plan,ROOT/'scripts')['passed'])
        self.assertTrue(verify(result)['passed'])
        self.assertTrue(verify_trace(trace(plan,0),plan,result)['passed'])

    def test_legacy_label_ignores_the_same_loss(self):
        plan=household(birth=1956,brokerage=100000,basis=150000,living=20000)
        first=rows(evaluate(plan))[0]
        self.assertEqual(first['realized_ltcg'],0)
        self.assertEqual(first['taxable_accounts']['brokerage']['sale_gain_or_loss'],-10000)
        self.assertEqual((first['tax']['capital_loss_deduction'],first['tax']['capital_loss_carryover_out']),(0,0))

    def test_carryover_offsets_later_gains(self):
        plan=with_distributions(household(birth=1956,brokerage=100000,basis=50000,living=20000,years=1),carryover=8000)
        t=rows(evaluate(plan))[0]['tax']
        # Sale gain 10,000 at basis ratio 0.5, less the 8,000 carryover.
        self.assertEqual((t['realized_sale_gain_or_loss'],t['net_capital_gain_or_loss'],t['preferential_income']),(10000,2000,2000))
        self.assertEqual(t['capital_loss_carryover_out'],0)

    def test_senior_add_back_in_the_engine(self):
        plan=with_distributions(household(birth=1961,brokerage=10000,basis=15000,ira=100000,living=29150,years=1),carryover=0)
        plan['members'][0]['annual_pension_2026_real']=0
        result=evaluate(plan)
        t=rows(result)[0]['tax']
        # Born 1961, 66 in 2027: the brokerage sale of 10,000 loses 5,000, then
        # 19,150 comes from the IRA: AGI 19,150 - 3,000 = 16,150, taxable
        # income 16,150 - 24,150 = -8,000, adjusted = -8,000 + 3,000 + 6,000 = 1,000.
        self.assertEqual((t['adjusted_gross_income'],t['enhanced_senior_deduction']),(16150,6000))
        self.assertEqual((t['capital_loss_used'],t['capital_loss_carryover_out']),(1000,4000))
        self.assertTrue(verify(result,plan)['passed'])
        # The literal 2025 worksheet (no add-back) would carry all 5,000.
        forged=copy.deepcopy(result)
        ft=rows(forged)[0]['tax']
        ft.update(capital_loss_adjusted_taxable_income=-5000.,capital_loss_used=0.,capital_loss_carryover_out=5000.)
        with self.assertRaisesRegex(VerifyFailure,'adjusted taxable income for the capital loss carryover'):
            verify(forged,plan)


class FundingWithSteepLosses(unittest.TestCase):
    """PR #12 review: with basis far above value, each sold dollar is a large
    deductible loss, tax falls faster than the sale grows, and fixed-point steps
    alternate. The bracketed fallback must find the unique funding solution."""
    def plan(self,basis):
        plan=with_distributions(household(birth=1966,brokerage=100000,basis=basis,living=29000))
        plan['members'][0].update(annual_pension_2026_real=30000,pension_start_age=60)
        return plan

    def test_reported_case_converges_to_the_hand_solution(self):
        # Single, 61 in 2027, frozen 2026 tables; ratio 12 so a sale S loses 11S.
        # Taxable income 30,000 - 11S - 16,100 stays below 12,400: T = .1(13,900 - 11S)
        # and S = T - 1,000 (pension 30,000 against spending 29,000), so
        # T = 2,490 / 2.1 = 1,185.714..., S = 185.714..., loss 2,042.86 < 3,000.
        plan=self.plan(1200000)
        result=evaluate(plan)
        row=rows(result)[0]
        self.assertAlmostEqual(row['tax_due_total'],2490/2.1,delta=.006)
        self.assertAlmostEqual(row['extra_draws']['brokerage'],2490/2.1-1000,delta=.006)
        self.assertEqual((row['unpaid_tax'],row['unmet_spending'],row['closing_accounts']['cash']),(0,0,0))
        self.assertTrue(verify(result,plan,ROOT/'scripts')['passed'])
        self.assertTrue(verify_trace(trace(plan,0),plan,result)['passed'])

    def test_extreme_basis_ratio_still_funds(self):
        # Ratio 10,000: the loss hits the 3,000 limit within a cent of sale, so tax
        # is 0.1 x (13,900 - 3,000) = 1,090 and the sale 90.
        plan=self.plan(1e9)
        result=evaluate(plan)
        row=rows(result)[0]
        self.assertAlmostEqual(row['tax_due_total'],1090,delta=.006)
        self.assertAlmostEqual(row['extra_draws']['brokerage'],90,delta=.006)
        self.assertTrue(verify(result,plan)['passed'])


class FundingAtFloatResolution(unittest.TestCase):
    def test_root_needed_to_the_last_representable_digit(self):
        # PR #12 review: $10 account with $1 billion basis, pension 30,000, spending
        # 28,600. Tax with no sale is 1,420; a sale S = T - 1,400 loses (1e8 - 1)S,
        # which lowers tax by .12 per dollar of loss, so T = 1,400 + 20 / (1.2e7 - .12 + 1),
        # a sale of about 1.67e-6 and a loss of about 166.67 (below the 3,000 limit).
        plan=with_distributions(household(birth=1966,brokerage=10,basis=1e9,living=28600))
        plan['members'][0].update(annual_pension_2026_real=30000,pension_start_age=60)
        result=evaluate(plan)
        row=rows(result)[0]
        sale=20/(.12*(1e8-1)+1)
        self.assertAlmostEqual(row['tax']['capital_loss_deduction'],round(sale*(1e8-1),2),delta=.011)
        self.assertEqual((row['tax_due_total'],row['unpaid_tax'],row['unmet_spending']),(1400,0,0))
        self.assertTrue(verify(result,plan)['passed'])


class VerifierRejectsForgedInvestmentRecords(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan=with_distributions(household(birth=1956,brokerage=100000,basis=150000,living=20000,years=3),
                                    q=.02,nq=.005,interest=.01,cgd=.01,carryover=1000)
        cls.result=evaluate(cls.plan)

    def forged(self):
        return copy.deepcopy(self.result)

    def assert_rejected(self,result,message,plan=True):
        with self.assertRaisesRegex(VerifyFailure,message):
            verify(result,self.plan if plan else None)

    def test_inflated_carryover_out(self):
        r=self.forged()
        rows(r)[0]['tax']['capital_loss_carryover_out']+=100
        self.assert_rejected(r,'capital loss carried to next year',plan=False)

    def test_carryover_chain_broken(self):
        r=self.forged()
        rows(r)[1]['tax']['capital_loss_carryover_in']+=100
        self.assert_rejected(r,'carryover in from the prior year',plan=False)
        r=self.forged()
        rows(r)[0]['tax']['capital_loss_carryover_in']=0.
        self.assert_rejected(r,'carryover in from the prior year')

    def test_dividends_off_the_plan_yield(self):
        # Reclassify 500 of qualified dividends as non-qualified: AGI is unchanged
        # and taxable income stays below zero, so only the plan yield shows it.
        r=self.forged()
        row=rows(r)[0]
        record=row['taxable_accounts']['brokerage']
        record['qualified_dividends']-=500; record['nonqualified_dividends']+=500
        t=row['tax']
        t['qualified_dividends']-=500; t['nonqualified_dividends']+=500
        t['gross_ordinary']+=500; t['preferential_income']-=500
        self.assertTrue(verify(r)['passed'])
        self.assert_rejected(r,'at the plan yield')

    def test_legacy_records_cannot_carry_distributions(self):
        # 100 of reinvested interest with every total adjusted to match; the
        # standard deduction absorbs it, so only the legacy label is violated.
        plan=household(birth=1956,brokerage=100000,basis=80000,living=1000,years=2)
        r=evaluate(plan)
        row=rows(r)[1]
        row['taxable_accounts']['brokerage'].update(interest=100.,reinvested_distributions=100.)
        row['taxable_basis_end']['brokerage']=round(row['taxable_basis_end']['brokerage']+100,2)
        t=row['tax']
        t['taxable_account_interest']=100.
        for key in ('gross_ordinary','adjusted_gross_income','niit_magi_assumed_equal_agi',
                    'ss_provisional_income','niit_net_investment_income'):
            t[key]=round(t[key]+100,2)
        self.assertEqual(t['ordinary_taxable'],0)
        with self.assertRaisesRegex(VerifyFailure,'legacy no-loss-offset treatment reports distributions'):
            verify(r)

    def test_treatment_relabelled(self):
        r=self.forged()
        for row in rows(r):
            row['taxable_accounts']['brokerage']['gain_treatment']=LEGACY
        with self.assertRaises(VerifyFailure):
            verify(r)
        with self.assertRaises(VerifyFailure):
            verify(r,self.plan)

    def test_legacy_label_cannot_carry_a_loss(self):
        # PR #12 review: zero yields, no sale and a 10,000 opening carryover, then
        # every record relabeled legacy. All amounts stay coherent, so only the
        # legacy rule (inputs forbid this combination) rejects it without the plan.
        plan=with_distributions(household(birth=1956,cash=100000,brokerage=50000,basis=50000,living=1000,years=2),
                                carryover=10000)
        r=evaluate(plan)
        self.assertEqual(rows(r)[0]['tax']['capital_loss_deduction'],3000)
        for row in rows(r):
            row['taxable_accounts']['brokerage']['gain_treatment']=LEGACY
        with self.assertRaisesRegex(VerifyFailure,'legacy no-loss-offset treatment cannot carry a capital loss'):
            verify(r)
        with self.assertRaises(VerifyFailure):
            verify(r,plan)

    def test_records_missing_from_a_current_result(self):
        r=self.forged()
        del rows(r)[0]['taxable_accounts']
        self.assert_rejected(r,'taxable account records must cover',plan=False)

    def test_adjusted_taxable_income_missing_in_a_loss_year(self):
        r=self.forged()
        rows(r)[0]['tax']['capital_loss_adjusted_taxable_income']=None
        self.assert_rejected(r,'net capital loss without adjusted taxable income',plan=False)

    def test_niit_income_without_dividends(self):
        r=self.forged()
        tax_row=rows(r)[0]['tax']
        tax_row['niit_net_investment_income']=0.
        self.assert_rejected(r,'NIIT income',plan=False)

    def test_basis_sold_off_proportion(self):
        r=self.forged()
        row=rows(r)[1]
        record=row['taxable_accounts']['brokerage']
        record['basis_sold']-=100; record['sale_gain_or_loss']+=100
        row['taxable_basis_end']['brokerage']+=100
        self.assert_rejected(r,'proportional basis after sale',plan=False)


if __name__=='__main__':
    unittest.main()
