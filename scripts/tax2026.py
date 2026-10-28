#!/usr/bin/env python3
"""Restricted 2026 US federal planning estimates. Not a Form 1040 engine.

Each coefficient is traceable to references/rules-provenance.md.
Later years use assumed inflation of 2026 brackets, NOT future legislation.
"""
from __future__ import annotations
from math import isfinite

REFERENCE_YEAR = 2026
SOURCES = {
    'brackets_standard_senior': 'https://www.irs.gov/irb/2025-45_IRB',
    'capital_gains': 'https://www.irs.gov/irb/2025-45_IRB',
    'social_security_tax': 'https://www.irs.gov/publications/p915',
    'payroll': 'https://www.ssa.gov/cola/factsheets/2026.html',
    'payroll_2027': 'https://www.ssa.gov/cola/factsheets/2027.html',
    'additional_medicare': 'https://www.irs.gov/taxtopics/tc560',
    'senior_enhanced': 'https://www.irs.gov/newsroom/working-families-tax-cuts-individuals-and-workers',
    '401k_elective_limit_2026':'https://www.irs.gov/retirement-plans/plan-participant-employee/retirement-topics-401k-and-profit-sharing-plan-contribution-limits',
    'rmd_uniform_lifetime':'https://www.irs.gov/publications/p590b',
    'rmd_birth_1959':'https://www.irs.gov/irb/2024-33_IRB',
}
BRACKETS = {
    'single': ((12400,.10),(50400,.12),(105700,.22),(201775,.24),(256225,.32),(640600,.35),(float('inf'),.37)),
    'mfj': ((24800,.10),(100800,.12),(211400,.22),(403550,.24),(512450,.32),(768700,.35),(float('inf'),.37)),
}
STANDARD = {'single':16100., 'mfj':32200.}
LTCG = {'single':(49450.,545500.),'mfj':(98900.,613700.)}
SS_THRESHOLDS = {'single':(25000.,34000.,4500.),'mfj':(32000.,44000.,6000.)}
WAGE_BASE_2026 = 184500.
CONTRIB_401K_LIMIT = 24500.

def progressive_tax(income, status, multiplier=1.0):
    if status not in BRACKETS or not isfinite(income) or income < 0 or multiplier <= 0:
        raise ValueError('invalid progressive tax inputs')
    tax = 0.
    last = 0.
    for ceiling, rate in BRACKETS[status]:
        top = ceiling * multiplier
        portion = max(0., min(income,top)-last)
        tax += portion*rate
        last=top
        if income <= top: break
    return tax

def progressive_tax_breakdown(income, status, multiplier=1.0):
    if status not in BRACKETS or not isfinite(income) or income<0 or multiplier<=0:
        raise ValueError('invalid tax breakdown inputs')
    prev=0.; lines=[]
    for ceil,rate in BRACKETS[status]:
        hi=ceil*multiplier
        amount=max(0.,min(income,hi)-prev)
        if amount>0:
            lines.append({'from':prev,'to':hi if isfinite(hi) else None,'rate':rate,'taxable':amount,'tax':amount*rate})
        prev=hi
        if income<=hi:break
    return lines

def taxable_social_security(benefits, other_income, status):
    """Simplified Pub 915 method; no special worksheets."""
    if status not in SS_THRESHOLDS or min(benefits,other_income)<0:
        raise ValueError('invalid Social Security calculation')
    lower,upper,plateau = SS_THRESHOLDS[status]
    provisional = other_income + .5*benefits
    if provisional <= lower: return 0.
    if provisional <= upper: return min(.5*benefits,.5*(provisional-lower))
    return min(.85*benefits,.85*(provisional-upper)+min(.5*benefits,plateau))

def payroll_tax(wages_by_person, status, wage_base_multiplier=1., year=2026):
    if status not in BRACKETS or not all(isfinite(w) and w>=0 for w in wages_by_person):
        raise ValueError('invalid payroll wages')
    gross=sum(wages_by_person)
    if year == 2026:
        wage_base=WAGE_BASE_2026
    elif year == 2027:
        wage_base=192300.
    else:
        wage_base=192300.*wage_base_multiplier
    ss_tax=sum(min(w,wage_base)*.062 for w in wages_by_person)
    medicare=gross*.0145
    threshold=250000. if status=='mfj' else 200000.
    additional=max(0.,gross-threshold)*.009
    return {'wage_base_per_person':wage_base,
            'oasdhi_taxable_wages_by_person':[min(w,wage_base) for w in wages_by_person],
            'additional_medicare_taxable_wages':max(0.,gross-threshold),
            'social_security_tax':ss_tax,'medicare_tax':medicare,'additional_medicare_tax':additional,
            'total':ss_tax+medicare+additional}

def federal_tax(*, wages_taxable, pension, ira_distributions, roth_conversions, cash_interest,
                ltcg, ss_benefits, status, ages, year, bracket_inflation=0.):
    """Federal income tax: no credits, itemization, state tax or NIIT."""
    if status not in BRACKETS or year < 2026 or not 0 <= bracket_inflation <= .1:
        raise ValueError('unsupported tax policy')
    values=(wages_taxable,pension,ira_distributions,roth_conversions,cash_interest,ltcg,ss_benefits)
    if any(not isfinite(x) or x<0 for x in values): raise ValueError('negative or nonfinite taxable income')
    if len(ages)!=(2 if status=='mfj' else 1): raise ValueError('household/filing mismatch')
    idx=(1.+bracket_inflation)**(year-2026)
    other=wages_taxable+pension+ira_distributions+roth_conversions+cash_interest+ltcg
    ss_taxable=taxable_social_security(ss_benefits,other,status)
    ordinary=wages_taxable+pension+ira_distributions+roth_conversions+cash_interest+ss_taxable
    agi=ordinary+ltcg
    elderly=sum(age>=65 for age in ages)
    senior_std=elderly*(1650. if status=='mfj' else 2050.)*idx
    std_deduction=(STANDARD[status]*idx)+senior_std
    enhanced=0.
    if 2026<=year<=2028 and elderly:
        threshold=150000. if status=='mfj' else 75000.
        enhanced=elderly*max(0.,6000.-.06*max(0.,agi-threshold))
    deduction=std_deduction+enhanced
    taxable_ordinary=max(0.,ordinary-deduction)
    taxable_pref=max(0.,ltcg-max(0.,deduction-ordinary))
    ord_tax=progressive_tax(taxable_ordinary,status,idx)
    zerothr,mid_thr=(t*idx for t in LTCG[status])
    zero_gain=max(0.,min(taxable_pref,zerothr-taxable_ordinary))
    mid_gain=max(0.,min(taxable_pref-zero_gain,mid_thr-max(zerothr,taxable_ordinary)))
    high_gain=max(0.,taxable_pref-zero_gain-mid_gain)
    pref_tax=mid_gain*.15+high_gain*.20
    return {'gross_ordinary':ordinary,'taxable_social_security':ss_taxable,
        'adjusted_gross_income':agi,'standard_plus_age_deduction':std_deduction,
        'enhanced_senior_deduction':enhanced,'deduction_total':deduction,
        'ordinary_taxable':taxable_ordinary,'long_term_gain_taxable':taxable_pref,
        'ordinary_tax':ord_tax,'capital_gains_tax':pref_tax,
        'ss_provisional_income':other+.5*ss_benefits,
        'ordinary_bracket_lines':progressive_tax_breakdown(taxable_ordinary,status,idx),
        'capital_gain_rate_lines':[{'rate':0.0,'taxable':zero_gain,'tax':0.0},
                    {'rate':0.15,'taxable':mid_gain,'tax':mid_gain*.15},
                    {'rate':0.20,'taxable':high_gain,'tax':high_gain*.20}],
        'federal_income_tax':ord_tax+pref_tax,'tax_law_year':2026,
        'year':year,'rule_multiplier':idx,
        'policy':'2026 rates indexed hypothetically; NOT a future-year statute',
        'unmodeled':['state/local income taxes','NIIT','tax credits','itemized deductions',
            'AMT','special retirement deductions','capital-loss offset',
            'taxable dividends','ACA/IRMAA','early-withdrawal exceptions']}
