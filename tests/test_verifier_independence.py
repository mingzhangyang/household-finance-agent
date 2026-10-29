"""Coherent forgeries that keep conservation and AGI identities intact.

Older identity checks run first, so each asserted message names the newer rule,
plan-schedule or funding-order check that rejects the forgery. Plan-only cases
also show that output-only verification still passes. Fictional data only.
"""
import copy
import json
import os
import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import audit_plan
from verify_outputs import plan_sha256,verify,verify_trace,VerifyFailure

EXAMPLE=json.loads((ROOT/'examples/audited-household-2026.json').read_text())


def household(*,birth=1960,wages=0,ss=0,claim=67,cash=0,brokerage=0,basis=None,ira=0,
              roth=0,living=0,conversions=(),years=1,cash_yield=0,order=None):
    """One single filer, frozen 2026 rules, zero portfolio returns unless overridden."""
    p=copy.deepcopy(EXAMPLE)
    p.update(name='Fictional independent-verification case',end_year=2026+years,events=[],
             living_expenses_annual_real=living,terminal_target_2026_real=0)
    p['members']=[dict(id='a',birth_year=birth,retirement_age=90 if wages else 40,
        annual_wages_2026=wages,wage_growth=0,ss_claim_age=claim,
        ss_annual_2026_real_at_chosen_claim_age=ss,ss_estimate_basis='2026_real_at_selected_claim_age')]
    p['tax_policy'].update(filing_status='single',future_bracket_inflation=0)
    p['accounts']=[dict(id='cash',kind='cash',balance=cash),
        dict(id='brokerage',kind='taxable',balance=brokerage,basis=brokerage if basis is None else basis,
             gain_treatment='long_term_proportional_no_loss_offset'),
        dict(id='ira',kind='traditional_ira',balance=ira,owner='a',rmd_table='uniform',fully_pretax_confirmed=True),
        dict(id='roth',kind='roth_ira',balance=roth,owner='a',qualified_distributions_confirmed=True)]
    p['withdrawal_order']=order or ['cash','brokerage','ira','roth']
    p['roth_conversions']=[dict(year=year,amount_nominal=amount,**{'from':'ira','to':'roth'})
                           for year,amount in conversions]
    p['assumptions']={key:0 for key in p['assumptions']}
    p['assumptions'].update(trials=1,seed=42,cash_yield=cash_yield)
    p['input_provenance']={'mode':'fictional_demo','register':[]}
    return p


def first_row(result):
    return result['deterministic_annual_ledger']['rows'][0]


def shift_cash(row,amount):
    """Year-end cash and totals absorb a forged change, preserving conservation."""
    row['closing_accounts']['cash']=round(row['closing_accounts']['cash']+amount,2)
    row['closing_total']=round(row['closing_total']+amount,2)
    row['closing_total_real']=round(row['closing_total']/row['inflation_factor'],2)


def add_untaxed_ordinary(row,amount):
    """Ordinary income fully absorbed by the standard deduction: tax stays zero."""
    tax=row['tax']
    for key in ('gross_ordinary','adjusted_gross_income','niit_magi_assumed_equal_agi','ss_provisional_income'):
        tax[key]=round(tax[key]+amount,2)
    assert tax['ordinary_taxable']==0 and tax['gross_ordinary']<tax['deduction_total']


class OutputOnlyJournalForgeries(unittest.TestCase):
    def test_inflated_cash_receipts_and_payments(self):
        plan=household(cash=50000,living=20000)
        result=audit_plan.evaluate(plan)
        flows=first_row(result)['account_flows']['cash']
        flows['cash_external_inflow']+=1000
        flows['cash_tax_and_spending_outflow']+=1000
        with self.assertRaisesRegex(VerifyFailure,'cash external receipts'):
            verify(result)

    def test_reverse_transfer_disguised_as_negative_draw(self):
        plan=household(birth=1965,cash=50000,ira=10000,living=1000)
        result=audit_plan.evaluate(plan)
        row=first_row(result)
        row['account_flows']['ira']['optional_draw']=-500.
        row['extra_draws']['ira']=-500.
        row['account_flows']['cash']['cash_received_draws']=-500.
        row['closing_accounts']['ira']+=500
        row['closing_accounts']['cash']-=500
        with self.assertRaisesRegex(VerifyFailure,'expected a finite nonnegative amount'):
            verify(result)

    def test_draw_moved_between_account_journals(self):
        plan=household(birth=1956,brokerage=10000,ira=10000,living=12000)
        result=audit_plan.evaluate(plan)
        row=first_row(result)
        flows=row['account_flows']
        self.assertEqual(flows['brokerage']['optional_draw'],10000)
        flows['brokerage']['optional_draw']-=500
        flows['ira']['optional_draw']+=500
        row['closing_accounts']['brokerage']+=500
        row['closing_accounts']['ira']-=500
        with self.assertRaisesRegex(VerifyFailure,'brokerage draw journal'):
            verify(result)

    def test_growth_moved_between_invested_accounts(self):
        plan=household(birth=1956,cash=100000,brokerage=50000,ira=50000,living=1000)
        plan['assumptions'].update(equity_weight=1,equity_mean=.05)
        result=audit_plan.evaluate(plan)
        row=first_row(result)
        row['growth_by_account']['brokerage']+=1000
        row['growth_by_account']['ira']-=1000
        row['closing_accounts']['brokerage']+=1000
        row['closing_accounts']['ira']-=1000
        self.assertEqual(sum(row['growth_by_account'].values()),row['investment_growth_total'])
        with self.assertRaisesRegex(VerifyFailure,'brokerage growth at reported return'):
            verify(result)

    def test_spending_cannot_be_paid_ahead_of_tax(self):
        plan=household(birth=1977,cash=1000,ira=100000,living=60000,conversions=[(2027,50000)])
        result=audit_plan.evaluate(plan)
        row=first_row(result)
        self.assertEqual((row['tax_paid'],row['living_expenses_paid']),(1000,0))
        row['tax_paid']-=500
        row['unpaid_tax']+=500
        row['living_expenses_paid']+=500
        row['unmet_spending']-=500
        self.assertTrue(verify(audit_plan.evaluate(plan),plan)['passed'])
        with self.assertRaisesRegex(VerifyFailure,'spending was paid before taxes'):
            verify(result)

    def rmd_case(self):
        plan=household(birth=1954,cash=50000,ira=26500,living=1000)
        result=audit_plan.evaluate(plan)
        row=first_row(result)
        self.assertEqual((row['rmd'][0]['divisor'],row['rmd'][0]['required']),(26.5,1000))
        return plan,result,row

    def test_fake_partial_rmd_with_remaining_balance(self):
        plan,result,row=self.rmd_case()
        # Report only 600 of the 1,000 RMD as taken, with untaxed income and
        # cash moved coherently, so the unmet 400 looks like a funding failure.
        row['rmd'][0].update(taken=600.,unmet=400.)
        row['rmd_total']=600.
        row['unmet_rmd']=400.
        row['account_flows']['ira']['required_distribution']=600.
        row['account_flows']['cash']['cash_received_rmd']=600.
        row['closing_accounts']['ira']+=400
        row['closing_accounts']['cash']-=400
        add_untaxed_ordinary(row,-400)
        result['deterministic_annual_ledger'].update(failed=True,first_failure_year=2027)
        with self.assertRaisesRegex(VerifyFailure,'ira RMD taken as the lesser of required and the balance before conversions'):
            verify(result)

    def test_fake_cent_rmd_shortfall_beside_a_balance(self):
        # taken+unmet need only match required within five cents; a visible
        # four-cent shortfall would fail the year although the IRA was ample.
        plan,result,row=self.rmd_case()
        row['rmd'][0]['unmet']=.04
        row['unmet_rmd']=.04
        result['deterministic_annual_ledger'].update(failed=True,first_failure_year=2027)
        for supplied in (None,plan):
            with self.subTest(plan=supplied is not None):
                with self.assertRaisesRegex(VerifyFailure,'ira unmet RMD as required less taken'):
                    verify(result,supplied)

    def test_fake_cent_spending_shortfall_when_cash_is_exhausted(self):
        # The draw empties the brokerage exactly, so cash and accessible accounts
        # end at zero; a four-cent unmet amount would fail a funded year.
        plan=household(birth=1956,brokerage=5000,living=5000)
        result=audit_plan.evaluate(plan)
        row=first_row(result)
        self.assertEqual((row['unmet_spending'],row['closing_total']),(0,0))
        row['unmet_spending']=.04
        result['deterministic_annual_ledger'].update(failed=True,first_failure_year=2027)
        for supplied in (None,plan):
            with self.subTest(plan=supplied is not None):
                with self.assertRaisesRegex(VerifyFailure,'unmet living'):
                    verify(result,supplied)

    def test_fake_rmd_requirement_on_an_empty_account(self):
        # The requirement is the prior balance over the divisor: zero here, not 0.04.
        plan=household(birth=1954,cash=50000,ira=0,living=1000)
        result=audit_plan.evaluate(plan)
        row=first_row(result)
        self.assertEqual((row['rmd'][0]['required'],row['rmd'][0]['taken']),(0,0))
        row['rmd'][0].update(required=.04,unmet=.04)
        row['unmet_rmd']=.04
        result['deterministic_annual_ledger'].update(failed=True,first_failure_year=2027)
        for supplied in (None,plan):
            with self.subTest(plan=supplied is not None):
                with self.assertRaisesRegex(VerifyFailure,'ira RMD required as prior balance over divisor'):
                    verify(result,supplied)

    def test_understated_rmd_hidden_by_a_draw_that_empties_the_account(self):
        # The IRA is drawn to zero, so an empty closing balance cannot show
        # whether the RMD was fundable. Move 400 of the RMD into the draw:
        # the same ordinary income and tax, a false RMD shortfall.
        plan=household(birth=1954,ira=26500,living=30000)
        result=audit_plan.evaluate(plan)
        row=first_row(result)
        self.assertEqual((row['rmd'][0]['taken'],row['extra_draws'],row['closing_accounts']['ira']),
                         (1000,{'ira':25500},0))
        self.assertGreater(row['unmet_spending'],0)
        row['rmd'][0].update(taken=600.,unmet=400.)
        row['rmd_total']=600.
        row['unmet_rmd']=400.
        row['extra_draws']['ira']+=400
        row['ira_extra_taxable']+=400
        flows=row['account_flows']
        flows['ira']['required_distribution']=600.
        flows['ira']['optional_draw']+=400
        flows['cash']['cash_received_rmd']=600.
        flows['cash']['cash_received_draws']+=400
        for supplied in (None,plan):
            with self.subTest(plan=supplied is not None):
                with self.assertRaisesRegex(VerifyFailure,'ira RMD taken as the lesser of required and the balance before conversions'):
                    verify(result,supplied)

    def test_rmd_divisor_must_follow_uniform_lifetime_table(self):
        plan,result,row=self.rmd_case()
        # Age 73 with the age-72 divisor 27.4: a smaller RMD, coherent journals.
        required=26500/27.4
        less=1000-required
        row['rmd'][0].update(divisor=27.4,required=required,taken=required)
        row['rmd_total']=round(required,2)
        row['account_flows']['ira']['required_distribution']=required
        row['account_flows']['cash']['cash_received_rmd']=required
        row['closing_accounts']['ira']=round(row['closing_accounts']['ira']+less,2)
        row['closing_accounts']['cash']=round(row['closing_accounts']['cash']-less,2)
        add_untaxed_ordinary(row,-less)
        with self.assertRaisesRegex(VerifyFailure,'RMD divisor for age 73 differs from the Uniform Lifetime Table'):
            verify(result)

    def test_raised_basis_after_sale(self):
        plan=household(birth=1956,brokerage=100000,basis=50000,living=20000)
        result=audit_plan.evaluate(plan)
        row=first_row(result)
        self.assertEqual(row['taxable_basis_end']['brokerage'],40000)
        row['taxable_basis_end']['brokerage']+=1000
        for supplied in (None,plan):
            with self.subTest(plan=supplied is not None):
                if supplied is None:
                    self.assertTrue(verify(result)['passed'])  # first-year basis needs the plan
                else:
                    with self.assertRaisesRegex(VerifyFailure,'proportional basis after sale'):
                        verify(result,supplied)

    def test_small_balance_sales_near_the_rounding_cutoff(self):
        # 0.0250001 growing 20% is reported as 0.03 + 0.01 = 0.04 against a true
        # 0.0300001, so the basis ratio needs the whole cent-rounding interval.
        for living,sale,basis_end in ((.015,'partial',.5),(1,'full',0)):
            plan=household(birth=1956,brokerage=.0250001,basis=1,living=living)
            plan['assumptions'].update(equity_weight=1,equity_mean=.2)
            result=audit_plan.evaluate(plan)
            row=first_row(result)
            self.assertEqual(row['opening_accounts']['brokerage']+row['growth_by_account']['brokerage'],.04)
            self.assertEqual(row['taxable_basis_end']['brokerage'],basis_end)
            with self.subTest(sale=sale):
                self.assertTrue(verify(result,plan)['passed'])

    def test_understated_gain_with_untaxed_consequences(self):
        plan=household(birth=1956,brokerage=100000,basis=50000,living=20000,years=2)
        result=audit_plan.evaluate(plan)
        row=result['deterministic_annual_ledger']['rows'][1]
        self.assertEqual(row['realized_ltcg'],10000)
        self.assertEqual(row['tax']['long_term_gain_taxable'],0)
        row['realized_ltcg']-=1000
        for key in ('adjusted_gross_income','niit_magi_assumed_equal_agi','niit_net_investment_income','ss_provisional_income'):
            row['tax'][key]-=1000
        row['tax']['capital_gain_rate_lines'][0]['taxable']=0.
        with self.assertRaisesRegex(VerifyFailure,'realized long-term gain from proportional basis'):
            verify(result)


class PlanScheduleForgeries(unittest.TestCase):
    def test_social_security_started_early(self):
        plan=household(birth=1961,claim=67,cash=50000,ss=12000,living=20000)
        result=audit_plan.evaluate(plan)
        row=first_row(result)
        self.assertEqual(row['social_security_gross'],0)
        row['social_security_gross']=12000.
        row['tax']['ss_provisional_income']+=6000
        row['account_flows']['cash']['cash_external_inflow']+=12000
        shift_cash(row,12000)
        self.assertTrue(verify(result)['passed'])
        with self.assertRaisesRegex(VerifyFailure,'Social Security scheduled by plan'):
            verify(result,plan)

    def test_omitted_rmd(self):
        plan=household(birth=1954,cash=50000,ira=26500,living=1000)
        result=audit_plan.evaluate(plan)
        row=first_row(result)
        self.assertEqual(row['rmd_total'],1000)
        row['rmd']=[]
        row['rmd_total']=0.
        row['account_flows']['ira']['required_distribution']=0.
        row['account_flows']['cash']['cash_received_rmd']=0.
        row['closing_accounts']['ira']+=1000
        row['closing_accounts']['cash']-=1000
        add_untaxed_ordinary(row,-1000)
        self.assertTrue(verify(result)['passed'])
        with self.assertRaisesRegex(VerifyFailure,'RMD accounts'):
            verify(result,plan)

    def deferral_plan(self,amount):
        plan=household(birth=1970,wages=30000,cash=50000,living=20000)
        plan['members'][0].update(annual_pretax_401k_2026_real=amount,pretax_401k_target='k_a')
        plan['accounts'].append(dict(id='k_a',kind='traditional_401k',owner='a',balance=0,
                                     still_working_exception=False,fully_pretax_confirmed=True))
        plan['withdrawal_order'].append('k_a')
        return plan

    def test_unused_deferral_target_of_a_non_contributing_spouse(self):
        # Valid input: the engine checks a target only for a member who contributes.
        plan=self.deferral_plan(10000)
        plan['members'].append(dict(plan['members'][0],id='b',annual_wages_2026=0,retirement_age=40,
                                    annual_pretax_401k_2026_real=0))
        plan['tax_policy']['filing_status']='mfj'
        result=audit_plan.evaluate(plan)
        self.assertEqual(first_row(result)['pretax_contribution_by_account'],{'k_a':10000})
        self.assertTrue(verify(result,plan)['passed'])

    def test_deferral_above_the_base_elective_limit(self):
        # Income tax stays zero with a 20,000 or 25,000 deferral from 30,000 wages.
        plan=self.deferral_plan(20000)
        result=audit_plan.evaluate(plan)
        self.assertTrue(verify(result,plan)['passed'])
        plan=self.deferral_plan(25000)
        with self.assertRaisesRegex(audit_plan.ModelError,'exceeds modeled wage/2026-base limit'):
            audit_plan.evaluate(plan)
        result['input_sha256']=plan_sha256(plan)
        row=first_row(result)
        row['pretax_contributions']=25000.
        row['pretax_contribution_by_account']={'k_a':25000.}
        row['wages_taxable']-=5000
        row['account_flows']['k_a']['contribution']=25000.
        row['account_flows']['cash']['cash_external_inflow']-=5000
        row['closing_accounts']['k_a']+=5000
        row['closing_accounts']['cash']-=5000
        add_untaxed_ordinary(row,-5000)
        self.assertTrue(verify(result)['passed'])
        with self.assertRaisesRegex(VerifyFailure,'a deferral exceeds wages or the indexed base elective limit'):
            verify(result,plan)

    def test_withdrawal_order_swapped(self):
        plan=household(birth=1956,brokerage=10000,ira=100000,living=5000)
        result=audit_plan.evaluate(plan)
        row=first_row(result)
        self.assertEqual(row['extra_draws'],{'brokerage':5000})
        row['extra_draws']={'ira':5000.}
        row['account_flows']['brokerage']['optional_draw']=0.
        row['account_flows']['ira']['optional_draw']=5000.
        row['ira_extra_taxable']=5000.
        row['closing_accounts']['brokerage']+=5000
        row['closing_accounts']['ira']-=5000
        row['taxable_basis_end']['brokerage']=10000.
        add_untaxed_ordinary(row,5000)
        self.assertTrue(verify(result)['passed'])
        with self.assertRaisesRegex(VerifyFailure,'brokerage kept a balance although the withdrawal order'):
            verify(result,plan)

    def blocked_shortfall(self):
        plan=household(birth=1977,ira=100000,living=5000)
        result=audit_plan.evaluate(plan)
        summary=result['deterministic_annual_ledger']
        self.assertEqual(summary['rows'][0]['unmet_spending'],5000)
        self.assertEqual([n['year'] for n in summary['notices']],[2027])
        self.assertTrue(verify(result,plan)['passed'])
        return plan,result

    def test_blocked_account_drawn_without_penalty_model(self):
        plan,result=self.blocked_shortfall()
        summary=result['deterministic_annual_ledger']
        row=summary['rows'][0]
        row['extra_draws']={'ira':5000.}
        row['account_flows']['ira']['optional_draw']=5000.
        row['account_flows']['cash']['cash_received_draws']=5000.
        row['account_flows']['cash']['cash_tax_and_spending_outflow']=5000.
        row['ira_extra_taxable']=5000.
        row['living_expenses_paid']=5000.
        row['unmet_spending']=0.
        row['closing_accounts']['ira']-=5000
        row['closing_total']-=5000
        row['closing_total_real']-=5000
        add_untaxed_ordinary(row,5000)
        summary.update(failed=False,first_failure_year=None,notices=[])
        self.assertTrue(verify(result)['passed'])
        with self.assertRaisesRegex(VerifyFailure,'ira drawn before its owner reached age 60'):
            verify(result,plan)

    def test_blocked_accounts_must_be_disclosed(self):
        plan,result=self.blocked_shortfall()
        result['deterministic_annual_ledger']['notices']=[]
        self.assertTrue(verify(result)['passed'])
        with self.assertRaisesRegex(VerifyFailure,'blocked account ira missing from funding notices'):
            verify(result,plan)
        for text in ('brokerage: early distributions before 60 not modeled','ira: available'):
            with self.subTest(notice=text):
                plan,result=self.blocked_shortfall()
                result['deterministic_annual_ledger']['notices'][0]['blocks'].append(text)
                with self.assertRaisesRegex(VerifyFailure,'is not the message for a blocked account'):
                    verify(result,plan)

    def test_each_notice_names_exactly_one_account(self):
        # Account IDs may contain ':', so 'ira:spouse: ...' starts with 'ira:'.
        plan=household(birth=1977,ira=100000,living=5000)
        plan['accounts'].append(dict(id='ira:spouse',kind='traditional_ira',balance=1000,owner='a',
                                     rmd_table='uniform',fully_pretax_confirmed=True))
        plan['withdrawal_order'].append('ira:spouse')
        result=audit_plan.evaluate(plan)
        self.assertTrue(verify(result,plan)['passed'])
        notice=result['deterministic_annual_ledger']['notices'][0]
        notice['blocks']=[block for block in notice['blocks'] if not block.startswith('ira: ')]
        self.assertEqual(len(notice['blocks']),2)
        with self.assertRaisesRegex(VerifyFailure,'blocked account ira missing from funding notices'):
            verify(result,plan)

    def conversion_case(self):
        plan=household(birth=1961,cash=50000,ira=20000,living=1000,conversions=[(2027,5000)])
        result=audit_plan.evaluate(plan)
        row=first_row(result)
        self.assertEqual(row['roth_converted'],5000)
        self.assertEqual(row['tax']['ordinary_taxable'],0)
        return plan,result,row

    def remove_conversion(self,row):
        row['conversion_transfers']=[]
        row['roth_converted']=0.
        row['account_flows']['ira']['roth_conversion_out']=0.
        row['account_flows']['roth']['roth_conversion_in']=0.
        row['closing_accounts']['ira']+=5000
        row['closing_accounts']['roth']-=5000
        add_untaxed_ordinary(row,-5000)

    def test_scheduled_conversion_removed(self):
        plan,result,row=self.conversion_case()
        self.remove_conversion(row)
        self.assertTrue(verify(result)['passed'])
        with self.assertRaisesRegex(VerifyFailure,'conversions differ from the plan schedule'):
            verify(result,plan)

    def test_executable_conversion_reported_as_skipped(self):
        plan,result,row=self.conversion_case()
        self.remove_conversion(row)
        row['skipped_conversions']=[dict(year=2027,amount=5000,reason='insufficient source balance after RMD',**{'from':'ira'})]
        result['deterministic_annual_ledger'].update(failed=True,first_failure_year=2027)
        self.assertTrue(verify(result)['passed'])
        with self.assertRaisesRegex(VerifyFailure,'skipped although ira had the balance'):
            verify(result,plan)

    def test_cash_interest_above_plan_yield(self):
        plan=household(birth=1961,cash=50000,living=1000,cash_yield=.01)
        result=audit_plan.evaluate(plan)
        row=first_row(result)
        self.assertEqual(row['growth_by_account']['cash'],500)
        row['growth_by_account']['cash']+=100
        row['investment_growth_total']+=100
        row['tax']['niit_net_investment_income']+=100
        add_untaxed_ordinary(row,100)
        shift_cash(row,100)
        self.assertTrue(verify(result)['passed'])
        with self.assertRaisesRegex(VerifyFailure,'cash interest at plan yield'):
            verify(result,plan)

    def test_inflated_standard_deduction_needs_plan(self):
        plan=household(birth=1961,wages=100000,cash=10000,living=60000)
        result=audit_plan.evaluate(plan)
        row=first_row(result)
        tax=row['tax']
        top=tax['ordinary_bracket_lines'][-1]
        saved=1000*top['rate']
        for key in ('standard_plus_age_deduction','deduction_total'):
            tax[key]+=1000
        tax['ordinary_taxable']-=1000
        top['taxable']-=1000
        top['tax']=round(top['tax']-saved,2)
        for key in ('ordinary_tax','federal_income_tax','total_federal_income_and_niit'):
            tax[key]=round(tax[key]-saved,2)
        for key in ('tax_due_total','tax_paid'):
            row[key]=round(row[key]-saved,2)
        row['account_flows']['cash']['cash_tax_and_spending_outflow']-=saved
        shift_cash(row,saved)
        self.assertTrue(verify(result)['passed'])
        with self.assertRaisesRegex(VerifyFailure,'indexed standard and age-65 deduction'):
            verify(result,plan)


class RetypedRuleForgeries(unittest.TestCase):
    def wage_result(self,wages=100000):
        plan=household(birth=1961,wages=wages,cash=10000,living=60000)
        return plan,audit_plan.evaluate(plan)

    def test_bracket_boundary_moved_with_coherent_tax(self):
        plan,result=self.wage_result()
        row=first_row(result)
        tax=row['tax']
        low,high=tax['ordinary_bracket_lines'][:2]
        self.assertEqual((low['rate'],high['rate']),(.1,.12))
        low.update(to=low['to']+1000,taxable=low['taxable']+1000,tax=low['tax']+100)
        high.update(taxable=high['taxable']-1000,tax=round(high['tax']-120,2),**{'from':high['from']+1000})
        for key in ('ordinary_tax','federal_income_tax','total_federal_income_and_niit'):
            tax[key]=round(tax[key]-20,2)
        for key in ('tax_due_total','tax_paid'):
            row[key]=round(row[key]-20,2)
        row['account_flows']['cash']['cash_tax_and_spending_outflow']-=20
        shift_cash(row,20)
        with self.assertRaisesRegex(VerifyFailure,'ordinary bracket 0 top'):
            verify(result)

    def test_understated_taxable_social_security(self):
        # Cash-funded, so lower tax cannot be confused with an oversized draw.
        plan=household(birth=1956,ss=30000,claim=67,cash=200000,living=60000)
        plan['members'][0].update(annual_pension_2026_real=40000,pension_start_age=65)
        result=audit_plan.evaluate(plan)
        self.assertEqual(first_row(result)['extra_draws'],{})
        row=first_row(result)
        tax=row['tax']
        self.assertGreater(tax['taxable_social_security'],1000)
        top=tax['ordinary_bracket_lines'][-1]
        saved=round(1000*top['rate'],2)
        for key in ('taxable_social_security','gross_ordinary','adjusted_gross_income',
                    'niit_magi_assumed_equal_agi','ordinary_taxable'):
            tax[key]-=1000
        top['taxable']-=1000
        top['tax']=round(top['tax']-saved,2)
        for key in ('ordinary_tax','federal_income_tax','total_federal_income_and_niit'):
            tax[key]=round(tax[key]-saved,2)
        for key in ('tax_due_total','tax_paid'):
            row[key]=round(row[key]-saved,2)
        row['account_flows']['cash']['cash_tax_and_spending_outflow']-=saved
        shift_cash(row,saved)
        with self.assertRaisesRegex(VerifyFailure,'taxable Social Security worksheet'):
            verify(result)

    def test_wage_base_and_additional_medicare_are_retyped(self):
        plan,result=self.wage_result(300000)
        row=first_row(result)
        payroll=row['payroll_tax']
        self.assertEqual(payroll['oasdhi_taxable_wages_by_person'],[192300])
        self.assertTrue(verify(result,plan)['passed'])
        for field,change,tax_change,message in (
                ('wage_base_per_person',1000,62.,'OASDI wage base'),
                ('additional_medicare_taxable_wages',-1000,-9.,'Additional Medicare wages')):
            with self.subTest(field=field):
                forged=copy.deepcopy(result)
                row=first_row(forged)
                payroll=row['payroll_tax']
                payroll[field]+=change
                if field=='wage_base_per_person':
                    payroll['oasdhi_taxable_wages_by_person'][0]+=change
                    payroll['social_security_tax']=round(payroll['social_security_tax']+tax_change,2)
                else:
                    payroll['additional_medicare_tax']=round(payroll['additional_medicare_tax']+tax_change,2)
                payroll['total']=round(payroll['total']+tax_change,2)
                for key in ('tax_due_total','tax_paid'):
                    row[key]=round(row[key]+tax_change,2)
                row['account_flows']['cash']['cash_tax_and_spending_outflow']+=tax_change
                shift_cash(row,-tax_change)
                with self.assertRaisesRegex(VerifyFailure,message):
                    verify(forged)

    def understate_oasdi_wages(self,row,person,amount):
        payroll=row['payroll_tax']
        saved=round(amount*.062,2)
        payroll['oasdhi_taxable_wages_by_person'][person]-=amount
        payroll['social_security_tax']=round(payroll['social_security_tax']-saved,2)
        payroll['total']=round(payroll['total']-saved,2)
        for key in ('tax_due_total','tax_paid'):
            row[key]=round(row[key]-saved,2)
        row['account_flows']['cash']['cash_tax_and_spending_outflow']-=saved
        shift_cash(row,saved)

    def test_understated_oasdi_wages_without_plan(self):
        # Single filer: covered wages are exactly min(gross wages, wage base).
        plan,result=self.wage_result()
        self.understate_oasdi_wages(first_row(result),0,100000)
        with self.assertRaisesRegex(VerifyFailure,'OASDI wages for a single filer'):
            verify(result)
        # Joint filers: the household total is at least min(gross wages, wage base).
        def joint(wages_b):
            plan=household(birth=1961,wages=150000,cash=10000,living=60000)
            plan['members'].append(dict(plan['members'][0],id='b',annual_wages_2026=wages_b,
                                        retirement_age=90 if wages_b else 40))
            plan['tax_policy']['filing_status']='mfj'
            return plan,audit_plan.evaluate(plan)
        plan,result=joint(0)
        self.understate_oasdi_wages(first_row(result),0,1000)
        with self.assertRaisesRegex(VerifyFailure,'OASDI wages below the lesser of gross wages and the wage base'):
            verify(result)
        # Above that bound the split between spouses needs the plan.
        plan,result=joint(150000)
        self.understate_oasdi_wages(first_row(result),1,100000)
        self.assertTrue(verify(result)['passed'])
        with self.assertRaisesRegex(VerifyFailure,'OASDI wages for member 1'):
            verify(result,plan)

    def test_stacking_label_when_ordinary_cap_is_lower(self):
        # MFJ $100,000 ordinary taxable + $800 gain straddling the 0% zone top.
        plan=household(birth=1970,wages=132200,brokerage=10000,basis=0,living=111286.70)
        plan['members'].append(dict(plan['members'][0],id='b',annual_wages_2026=0,retirement_age=40))
        plan['tax_policy']['filing_status']='mfj'
        plan['accounts']=[a for a in plan['accounts'] if a['kind'] in ('cash','taxable')]
        plan['withdrawal_order']=['cash','brokerage']
        result=audit_plan.evaluate(plan)
        row=first_row(result)
        tax=row['tax']
        self.assertEqual(tax['income_tax_method'],'ordinary_rate_cap')
        self.assertTrue(verify(result,plan)['passed'])
        extra=round(.15*800-96,2)
        tax['income_tax_method']='stacked_capital_gains'
        tax['capital_gain_rate_lines']=[{'rate':0.,'taxable':0.,'tax':0.},
                                        {'rate':.15,'taxable':800.,'tax':120.},
                                        {'rate':.2,'taxable':0.,'tax':0.}]
        for key in ('capital_gains_tax','federal_income_tax','total_federal_income_and_niit'):
            tax[key]=round(tax[key]+extra,2)
        row['tax_due_total']=round(row['tax_due_total']+extra,2)
        row['tax_paid']=round(row['tax_paid']+extra,2)
        row['living_expenses_paid']=round(row['living_expenses_paid']-extra,2)
        row['unmet_spending']=round(row['unmet_spending']+extra,2)
        result['deterministic_annual_ledger'].update(failed=True,first_failure_year=2027)
        with self.assertRaisesRegex(VerifyFailure,'preferential stacking chosen although the ordinary-rate cap is lower'):
            verify(result)

    def test_bracket_index_must_follow_policy(self):
        plan,result=self.wage_result()
        first_row(result)['tax']['rule_multiplier']=1.1
        with self.assertRaisesRegex(VerifyFailure,'hypothetical bracket index'):
            verify(result)


class TracedPathChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan=copy.deepcopy(EXAMPLE)
        cls.plan.update(end_year=2036)
        cls.plan['assumptions']['trials']=8
        cls.result=audit_plan.evaluate(cls.plan)

    def test_every_traced_path_verifies_against_manifest(self):
        for index in range(self.plan['assumptions']['trials']):
            with self.subTest(index=index):
                status=verify_trace(audit_plan.trace(self.plan,index),self.plan,self.result)
                self.assertTrue(status['passed'] and status['returns_regenerated'] and status['manifest_entry_checked'])

    def test_relabelled_or_altered_returns_rejected(self):
        trace=audit_plan.trace(self.plan,3)
        relabelled=copy.deepcopy(trace)
        relabelled['trial_index']=4
        with self.assertRaisesRegex(VerifyFailure,'regenerated from seed'):
            verify_trace(relabelled,self.plan)
        altered=copy.deepcopy(trace)
        altered['annual_returns'][0]+=.01
        with self.assertRaisesRegex(VerifyFailure,'regenerated from seed'):
            verify_trace(altered,self.plan)
        for index in (-1,8,True):
            bad=copy.deepcopy(trace)
            bad['trial_index']=index
            with self.assertRaisesRegex(VerifyFailure,'trace path index'):
                verify_trace(bad,self.plan)

    def test_manifest_entry_must_match_trace(self):
        result=copy.deepcopy(self.result)
        manifest=result['simulated_path_manifest']
        manifest[2]['terminal_real']+=1
        finals=sorted(path['terminal_real'] for path in manifest)
        def quant(q):
            pos=(len(finals)-1)*q;lo=int(pos);hi=min(lo+1,len(finals)-1)
            return round(finals[lo]*(1-pos+lo)+finals[hi]*(pos-lo),2)
        result['terminal_real_p10_p50_p90']=[quant(q) for q in (.1,.5,.9)]
        result['annual_real_percentiles'][-1].update(zip(('p10','p50','p90'),result['terminal_real_p10_p50_p90']))
        self.assertTrue(verify(result,self.plan)['passed'])
        with self.assertRaisesRegex(VerifyFailure,'trace disagrees with its Monte Carlo manifest entry'):
            verify_trace(audit_plan.trace(self.plan,2),self.plan,result)

    def test_trace_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)
            (out/'plan.json').write_text(json.dumps(self.plan))
            (out/'result.json').write_text(json.dumps(self.result))
            (out/'trace.json').write_text(json.dumps(audit_plan.trace(self.plan,5)))
            command=[sys.executable,str(ROOT/'scripts/verify_outputs.py'),str(out/'trace.json'),'--plan',str(out/'plan.json')]
            ok=subprocess.run(command+['--trace','--trace-result',str(out/'result.json'),'--output',str(out/'status.json')],
                              capture_output=True,text=True)
            self.assertEqual(ok.returncode,0,ok.stdout+ok.stderr)
            self.assertTrue(json.loads((out/'status.json').read_text())['manifest_entry_checked'])
            missing=subprocess.run([sys.executable,str(ROOT/'scripts/verify_outputs.py'),str(out/'trace.json'),'--trace'],
                                   capture_output=True,text=True)
            self.assertEqual(missing.returncode,2)
            self.assertIn('--trace requires --plan',missing.stderr)


def generated_plan(rng,n):
    """Varied valid fictional plans; the engine's own validation rejects the rest."""
    two=rng.random()<.5
    members=[]
    for i in range(2 if two else 1):
        m=dict(id=f'p{i}',birth_year=rng.randint(1951,1990),retirement_age=rng.randint(40,80),
               annual_wages_2026=rng.choice([0,rng.uniform(1,400000)]),wage_growth=rng.uniform(-.03,.06),
               ss_claim_age=rng.randint(62,70),ss_annual_2026_real_at_chosen_claim_age=rng.choice([0,rng.uniform(5000,50000)]),
               ss_estimate_basis='2026_real_at_selected_claim_age')
        if rng.random()<.3:
            m.update(annual_pension_2026_real=rng.uniform(1,40000),pension_start_age=rng.randint(55,75))
        members.append(m)
    value=rng.choice([0,rng.uniform(0,2e6)])
    accounts=[dict(id='cash',kind='cash',balance=rng.choice([0,rng.uniform(0,3e5)])),
              dict(id='brokerage',kind='taxable',balance=value,basis=value*rng.uniform(0,1.5),
                   gain_treatment='long_term_proportional_no_loss_offset')]
    for m in members:
        accounts.append(dict(id='ira_'+m['id'],kind='traditional_ira',owner=m['id'],balance=rng.uniform(0,2e6),
                             rmd_table='uniform',fully_pretax_confirmed=True))
        accounts.append(dict(id='k_'+m['id'],kind='traditional_401k',owner=m['id'],balance=rng.uniform(0,1e6),
                             still_working_exception=False,fully_pretax_confirmed=True))
        accounts.append(dict(id='roth_'+m['id'],kind='roth_ira',owner=m['id'],balance=rng.uniform(0,5e5),
                             qualified_distributions_confirmed=True))
        if m['annual_wages_2026'] and rng.random()<.6:
            m.update(annual_pretax_401k_2026_real=min(m['annual_wages_2026']*.5,rng.uniform(0,15000)),
                     pretax_401k_target='k_'+m['id'])
    for m in members:
        # Accepted and ignored by the engine: a target without a contribution.
        if 'pretax_401k_target' not in m and rng.random()<.3:
            m['pretax_401k_target']=rng.choice(['k_'+x['id'] for x in members])
    end=min(2026+rng.choice([1,3,10,30]),min(m['birth_year'] for m in members)+120)
    order=[a['id'] for a in accounts[1:]]
    rng.shuffle(order)
    conversions=[dict(year=rng.randint(2027,end),amount_nominal=rng.choice([rng.uniform(1,2e5),5e6]),
                      **{'from':'ira_p0','to':'roth_p0'}) for _ in range(rng.choice([0,1,2]))]
    p=copy.deepcopy(EXAMPLE)
    p.update(name=f'generated-{n}',end_year=end,members=members,accounts=accounts,
             withdrawal_order=['cash']+order,roth_conversions=conversions,events=[],
             living_expenses_annual_real=rng.uniform(0,3e5),terminal_target_2026_real=rng.choice([0,1e5]))
    p['tax_policy'].update(filing_status='mfj' if two else 'single',future_bracket_inflation=rng.uniform(0,.05))
    p['assumptions'].update(inflation=rng.uniform(0,.06),equity_weight=rng.random(),
        equity_mean=rng.uniform(-.5,.3),equity_volatility=rng.uniform(0,.7),bond_mean=rng.uniform(-.5,.3),
        bond_volatility=rng.uniform(0,.5),equity_bond_correlation=rng.uniform(-1,1),
        annual_investment_fee=rng.uniform(0,.02),cash_yield=rng.uniform(0,.08),trials=4,seed=rng.randint(0,2**32-1))
    p['input_provenance']={'mode':'fictional_demo','register':[]}
    return p


class GeneratedOutputsAndSingleFieldMutations(unittest.TestCase):
    def test_valid_outputs_pass_and_every_numeric_field_is_checked(self):
        # Larger local sweeps: HFA_VERIFIER_FUZZ_PLANS=1000 HFA_VERIFIER_FUZZ_SEED=7.
        plans=int(os.environ.get('HFA_VERIFIER_FUZZ_PLANS','40'))
        rng=random.Random(int(os.environ.get('HFA_VERIFIER_FUZZ_SEED','20261029')))
        verified=traced=mutated=0
        for n in range(plans):
            plan=generated_plan(rng,n)
            try:
                result=audit_plan.evaluate(plan)
            except audit_plan.ModelError:
                continue
            with self.subTest(plan=n):
                self.assertTrue(verify(result,plan,ROOT/'scripts')['passed'])
                verified+=1
                for index in range(plan['assumptions']['trials']):
                    self.assertTrue(verify_trace(audit_plan.trace(plan,index),plan,result)['passed'])
                    traced+=1
            if n%5:
                continue
            rows=result['deterministic_annual_ledger']['rows']
            row_index=rng.randrange(len(rows))
            for path in leaves(rows[row_index]):
                forged=copy.deepcopy(result)
                target=forged['deterministic_annual_ledger']['rows'][row_index]
                for part in path[:-1]:
                    target=target[part]
                target[path[-1]]+=1e-6 if path[-1] in ('rate','rule_multiplier','niit_rate','market_return','inflation_factor','divisor') else 1
                with self.subTest(plan=n,field='.'.join(map(str,path))):
                    with self.assertRaises(VerifyFailure):
                        verify(forged,plan)
                mutated+=1
        self.assertGreater(verified,plans*3//4)
        self.assertGreater(traced,plans*3)
        self.assertGreater(mutated,plans*7)
        print(f'\ngenerated plans={plans} verified={verified} traced={traced} mutations={mutated}',file=sys.stderr)

    def test_m1_reference_and_report_scenarios_pass(self):
        from render_audit import create_scenarios
        cases=json.loads((ROOT/'tests/golden/m1-cases.json').read_text())['cases']
        plans=[case['plan'] for case in cases]+create_scenarios(copy.deepcopy(EXAMPLE))
        for plan in plans:
            with self.subTest(plan=plan['name']):
                result=audit_plan.evaluate(plan)
                self.assertTrue(verify(result,plan,ROOT/'scripts')['passed'])
                self.assertTrue(verify_trace(audit_plan.trace(plan,0),plan,result)['passed'])


def leaves(value,path=()):
    if isinstance(value,bool):
        return
    if isinstance(value,(int,float)):
        yield path
    elif isinstance(value,dict):
        for key,item in value.items():
            yield from leaves(item,path+(key,))
    elif isinstance(value,list):
        for index,item in enumerate(value):
            yield from leaves(item,path+(index,))


if __name__=='__main__':
    unittest.main()
