#!/usr/bin/env python3
"""Restricted US federal planning estimates by tax year. Not a Form 1040 engine.

Each coefficient is traceable to references/rules-provenance.md. Published
tax-year values are kept apart from projections: a year without published
values is projected from the latest published year at the plan's assumed
rate and labeled 'projected'; it is NOT future legislation.
"""
from __future__ import annotations
from math import isfinite

REFERENCE_YEAR = 2026
SOURCES = {
    'brackets_standard_senior': 'https://www.irs.gov/irb/2025-45_IRB',
    'capital_gains': 'https://www.irs.gov/publications/p505',
    'social_security_tax': 'https://www.irs.gov/publications/p915',
    'payroll': 'https://www.govinfo.gov/content/pkg/FR-2025-11-03/html/2025-19763.htm',
    'payroll_2027': 'https://www.govinfo.gov/content/pkg/FR-2026-10-26/html/2026-21796.htm',
    'additional_medicare': 'https://www.irs.gov/taxtopics/tc560',
    'senior_enhanced': 'https://www.irs.gov/newsroom/working-families-tax-cuts-individuals-and-workers',
    '401k_elective_limit_2026':'https://www.irs.gov/pub/irs-drop/n-25-67.pdf',
    'rmd_uniform_lifetime':'https://www.irs.gov/publications/p590b',
    'rmd_birth_1959':'https://www.irs.gov/irb/2024-33_IRB',
}
# Published values by tax year. Add a year only from its official publication
# (references/rules-provenance.md), never from a projection or forecast.
PUBLISHED_INCOME_TAX = {
    2026: {'source_id': 'brackets_standard_senior',
           'brackets': {
               'single': ((12400,.10),(50400,.12),(105700,.22),(201775,.24),(256225,.32),(640600,.35),(float('inf'),.37)),
               'mfj': ((24800,.10),(100800,.12),(211400,.22),(403550,.24),(512450,.32),(768700,.35),(float('inf'),.37)),
           },
           'standard': {'single':16100., 'mfj':32200.},
           'age_65_addition': {'single':2050., 'mfj':1650.},
           'ltcg': {'single':(49450.,545500.),'mfj':(98900.,613700.)}},
}
PUBLISHED_OASDI_WAGE_BASE = {
    2026: {'amount': 184500., 'source_id': 'payroll'},
    2027: {'amount': 192300., 'source_id': 'payroll_2027'},
}
PUBLISHED_ELECTIVE_DEFERRAL = {
    2026: {'amount': 24500., 'source_id': '401k_elective_limit_2026'},
}
RULE_FAMILIES = {
    'income_tax_tables': PUBLISHED_INCOME_TAX,
    'oasdi_wage_base': PUBLISHED_OASDI_WAGE_BASE,
    'elective_deferral_limit': PUBLISHED_ELECTIVE_DEFERRAL,
}
# 2026 aliases for existing callers.
BRACKETS = PUBLISHED_INCOME_TAX[2026]['brackets']
STANDARD = PUBLISHED_INCOME_TAX[2026]['standard']
LTCG = PUBLISHED_INCOME_TAX[2026]['ltcg']
# Fixed statutory amounts (Publication 915): not indexed.
SS_THRESHOLDS = {'single':(25000.,34000.,4500.),'mfj':(32000.,44000.,6000.)}
WAGE_BASE_2026 = PUBLISHED_OASDI_WAGE_BASE[2026]['amount']
CONTRIB_401K_LIMIT = PUBLISHED_ELECTIVE_DEFERRAL[2026]['amount']

def rule_year(published, year, assumed_rate):
    """(base_year, multiplier, status) of one rule family for one tax year.

    A published year uses its own values. A later year indexes the latest
    published values at the assumed rate. Earlier or skipped years fail.
    """
    if year in published:
        return year, 1., 'published'
    latest = max(published)
    if year < latest or not 0 <= assumed_rate <= .1:
        raise ValueError(f'no published or projectable rules for tax year {year}')
    return latest, (1.+assumed_rate)**(year-latest), 'projected'

def rule_basis(year, assumed_rate):
    """Per-family label: which published year each rule comes from, and how."""
    basis = {}
    for family, published in RULE_FAMILIES.items():
        base, multiplier, status = rule_year(published, year, assumed_rate)
        basis[family] = {'status': status, 'base_year': base, 'multiplier': multiplier,
                         'source_id': published[base]['source_id']}
    return basis

def elective_deferral_limit(year, assumed_rate):
    """Base elective deferral limit; catch-up contributions are not modeled."""
    base, multiplier, _ = rule_year(PUBLISHED_ELECTIVE_DEFERRAL, year, assumed_rate)
    return PUBLISHED_ELECTIVE_DEFERRAL[base]['amount']*multiplier

def progressive_tax(income, status, multiplier=1.0, base_year=REFERENCE_YEAR):
    if status not in BRACKETS or not isfinite(income) or income < 0 or multiplier <= 0:
        raise ValueError('invalid progressive tax inputs')
    tax = 0.
    last = 0.
    for ceiling, rate in PUBLISHED_INCOME_TAX[base_year]['brackets'][status]:
        top = ceiling * multiplier
        portion = max(0., min(income,top)-last)
        tax += portion*rate
        last=top
        if income <= top: break
    return tax

def progressive_tax_breakdown(income, status, multiplier=1.0, base_year=REFERENCE_YEAR):
    if status not in BRACKETS or not isfinite(income) or income<0 or multiplier<=0:
        raise ValueError('invalid tax breakdown inputs')
    prev=0.; lines=[]
    for ceil,rate in PUBLISHED_INCOME_TAX[base_year]['brackets'][status]:
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

def payroll_tax(wages_by_person, status, year=2026, assumed_rate=0.):
    if status not in BRACKETS or not all(isfinite(w) and w>=0 for w in wages_by_person):
        raise ValueError('invalid payroll wages')
    gross=sum(wages_by_person)
    base,multiplier,_=rule_year(PUBLISHED_OASDI_WAGE_BASE,year,assumed_rate)
    wage_base=PUBLISHED_OASDI_WAGE_BASE[base]['amount']*multiplier
    ss_tax=sum(min(w,wage_base)*.062 for w in wages_by_person)
    medicare=gross*.0145
    threshold=250000. if status=='mfj' else 200000.
    additional=max(0.,gross-threshold)*.009
    return {'wage_base_per_person':wage_base,
            'oasdhi_taxable_wages_by_person':[min(w,wage_base) for w in wages_by_person],
            'additional_medicare_taxable_wages':max(0.,gross-threshold),
            'social_security_tax':ss_tax,'medicare_tax':medicare,'additional_medicare_tax':additional,
            'total':ss_tax+medicare+additional}

def rule_policy(law_year, year, status):
    """Disclosure text for one year's income-tax tables."""
    if status == 'published':
        return f'{law_year} published federal tables'
    return f'{law_year} published federal tables indexed hypothetically to {year}; NOT published {year} law'

def federal_tax(*, wages_taxable, pension, ira_distributions, roth_conversions, cash_interest,
                ltcg, ss_benefits, status, ages, year, bracket_inflation=0.):
    """Federal income tax: no credits, itemization, state tax or NIIT."""
    if status not in BRACKETS or year < 2026 or not 0 <= bracket_inflation <= .1:
        raise ValueError('unsupported tax policy')
    values=(wages_taxable,pension,ira_distributions,roth_conversions,cash_interest,ltcg,ss_benefits)
    if any(not isfinite(x) or x<0 for x in values): raise ValueError('negative or nonfinite taxable income')
    if len(ages)!=(2 if status=='mfj' else 1): raise ValueError('household/filing mismatch')
    law_year,idx,rule_status=rule_year(PUBLISHED_INCOME_TAX,year,bracket_inflation)
    law=PUBLISHED_INCOME_TAX[law_year]
    other=wages_taxable+pension+ira_distributions+roth_conversions+cash_interest+ltcg
    ss_taxable=taxable_social_security(ss_benefits,other,status)
    ordinary=wages_taxable+pension+ira_distributions+roth_conversions+cash_interest+ss_taxable
    agi=ordinary+ltcg
    elderly=sum(age>=65 for age in ages)
    senior_std=elderly*law['age_65_addition'][status]*idx
    std_deduction=(law['standard'][status]*idx)+senior_std
    enhanced=0.
    if 2026<=year<=2028 and elderly:
        threshold=150000. if status=='mfj' else 75000.
        # Schedule 1-A lines 35–37: phase out each person's $6,000,
        # then add the amounts for eligible spouses.
        enhanced=elderly*max(0.,6000.-.06*max(0.,agi-threshold))
    deduction=std_deduction+enhanced
    taxable_ordinary=max(0.,ordinary-deduction)
    taxable_pref=max(0.,ltcg-max(0.,deduction-ordinary))
    ord_tax=progressive_tax(taxable_ordinary,status,idx,law_year)
    zerothr,mid_thr=(t*idx for t in law['ltcg'][status])
    zero_gain=max(0.,min(taxable_pref,zerothr-taxable_ordinary))
    mid_gain=max(0.,min(taxable_pref-zero_gain,mid_thr-max(zerothr,taxable_ordinary)))
    high_gain=max(0.,taxable_pref-zero_gain-mid_gain)
    pref_tax=mid_gain*.15+high_gain*.20
    gain_lines=[{'rate':0.0,'taxable':zero_gain,'tax':0.0},
                {'rate':0.15,'taxable':mid_gain,'tax':mid_gain*.15},
                {'rate':0.20,'taxable':high_gain,'tax':high_gain*.20}]
    method='stacked_capital_gains'
    # Pub. 505 (2026), Worksheet 2-7 lines 38–40: use the smaller
    # stacked tax or ordinary-rate tax on all taxable income.
    all_ordinary=progressive_tax(taxable_ordinary+taxable_pref,status,idx,law_year)
    if all_ordinary<ord_tax+pref_tax:
        method='ordinary_rate_cap'
        gain_lines=[]
        for line in progressive_tax_breakdown(taxable_ordinary+taxable_pref,status,idx,law_year):
            top=line['from']+line['taxable']
            amount=max(0.,top-max(line['from'],taxable_ordinary))
            if amount:
                gain_lines.append({'rate':line['rate'],'taxable':amount,'tax':amount*line['rate']})
        pref_tax=sum(line['tax'] for line in gain_lines)
    return {'gross_ordinary':ordinary,'taxable_social_security':ss_taxable,
        'adjusted_gross_income':agi,'standard_plus_age_deduction':std_deduction,
        'enhanced_senior_deduction':enhanced,'deduction_total':deduction,
        'ordinary_taxable':taxable_ordinary,'long_term_gain_taxable':taxable_pref,
        'ordinary_tax':ord_tax,'capital_gains_tax':pref_tax,
        'income_tax_method':method,
        'ss_provisional_income':other+.5*ss_benefits,
        'ordinary_bracket_lines':progressive_tax_breakdown(taxable_ordinary,status,idx,law_year),
        'capital_gain_rate_lines':gain_lines,
        'federal_income_tax':ord_tax+pref_tax,'tax_law_year':law_year,
        'year':year,'rule_multiplier':idx,
        'policy':rule_policy(law_year,year,rule_status),
        'unmodeled':['state/local income taxes','NIIT','tax credits','itemized deductions',
            'AMT','special retirement deductions','capital-loss offset',
            'taxable dividends','ACA/IRMAA','early-withdrawal exceptions']}
