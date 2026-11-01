#!/usr/bin/env python3
"""Maryland resident income tax for the restricted planning engine (Form 502 subset).

Full-year residents filing single or jointly, with the county or Baltimore City
local income tax. Every coefficient is traceable to the Maryland section of
references/rules-provenance.md; the primary documents, hashes and locators are
in references/primary-source-review-2026-11-01-maryland.md. This is not a Form
502 engine: no additions, itemized deductions, dependents, disability or
blindness benefits, military or public safety retirement subtractions, U.S.
obligation interest subtraction, earned income or poverty level credits, local
credits or credits for taxes paid to other states.

Statutory amounts that are not indexed (rates, exemptions and their phaseout,
the $1,200 two-income subtraction, the senior tax credit, the capital gain
surtax) apply to every projected year as current law. Indexed amounts keep
published tax years apart from projections, as the federal registry does.
County rates continue until a county changes them (TG 10-106(a)(2)), so a
year after the latest published table carries those rates forward unchanged.
"""
from __future__ import annotations
from math import isfinite, inf
from tax2026 import rule_year

JURISDICTION = 'US-MD'
RESIDENCY = 'full_year_resident'
ERS = 'employee_retirement_system'
NOT_ERS = 'not_employee_retirement_system'
_STATUTE = 'https://mgaleg.maryland.gov/mgawebsite/Laws/StatuteText?article=gtg&section={}&enactments=false'
_DAM = 'https://www.marylandcomptroller.gov/content/dam/mdcomp/tax/'
SOURCES = {
    'md_income_tax_rates': _STATUTE.format('10-105'),
    'md_capital_gain_surtax': _DAM + 'legal-publications/technical-bulletins/tb-58.pdf',
    'md_standard_deduction_2025': _STATUTE.format('10-217'),
    'md_exemptions': _STATUTE.format('10-211'),
    'md_pension_exclusion': _STATUTE.format('10-209'),
    'md_pension_exclusion_2026': 'https://services.marylandcomptroller.gov/taxes/en/maryland-pension-exclusion?id=kb_article_view&sysparm_article=KB0010012',
    'md_subtractions': _STATUTE.format('10-207'),
    'md_senior_tax_credit': _STATUTE.format('10-754'),
    'md_local_income_tax': _STATUTE.format('10-106'),
    'md_local_rates_2026': 'https://services.marylandcomptroller.gov/taxes/en/maryland-income-tax-rates-and-brackets?sys_kb_id=940583761b97d290168d6424604bcb80&id=kb_article_view',
    'md_resident_instructions_2025': _DAM + 'instructions/2025/resident-booklet.pdf',
}
SOURCE_IDS = list(SOURCES)

# TG 10-105(a)(1)-(2), tax years after 2024: marginal brackets (top, rate).
STATE_BRACKETS = {
    'single': ((1000., .02), (2000., .03), (3000., .04), (100000., .0475), (125000., .05),
               (150000., .0525), (250000., .055), (500000., .0575), (1000000., .0625), (inf, .065)),
    'mfj': ((1000., .02), (2000., .03), (3000., .04), (150000., .0475), (175000., .05),
            (225000., .0525), (300000., .055), (600000., .0575), (1200000., .0625), (inf, .065)),
}
# TG 10-105(a)(3)-(4): 2% of net capital gain in Maryland AGI when FAGI > $350,000.
SURTAX_RATE = .02
SURTAX_FAGI = 350000.
# TG 10-211(b)-(c): $3,200 per personal exemption, limited by FAGI; $1,000 per person 65+.
PERSONAL_EXEMPTION = 3200.
AGE_65_EXEMPTION = 1000.
EXEMPTION_LIMITS = {'single': ((100000., 3200.), (125000., 1600.), (150000., 800.)),
                    'mfj': ((150000., 3200.), (175000., 1600.), (200000., 800.))}
# TG 10-207(r): lesser of $1,200 or the lower spouse's modified Maryland AGI.
TWO_INCOME_LIMIT = 1200.
# TG 10-754(b): FAGI limit; amount for one or two eligible (65+) taxpayers.
SENIOR_CREDIT = {'single': (100000., {1: 1000.}), 'mfj': (150000., {1: 1000., 2: 1750.})}

# Indexed amounts by published tax year (add a year only from its official
# publication). TG 10-217(c) indexes the standard deduction from 2026; the
# Comptroller has not published the 2026 amount, so 2026 onward is projected.
PUBLISHED_STANDARD_DEDUCTION = {
    2025: {'amounts': {'single': 3350., 'mfj': 6700.}, 'source_id': 'md_standard_deduction_2025'},
}
# TG 10-209(c): the Comptroller's maximum pension exclusion for the year.
PUBLISHED_PENSION_EXCLUSION = {
    2026: {'amount': 40600., 'source_id': 'md_pension_exclusion_2026'},
}
# County rates. ('flat', rate); ('brackets', {status: ((top, rate), ...)}) is
# marginal; ('income_band', {status: ...}) applies one rate to ALL taxable net
# income, chosen by the band that income falls in (Frederick County).
_FLAT_2026 = {
    'allegany_county': .032, 'baltimore_city': .032, 'baltimore_county': .032,
    'calvert_county': .032, 'caroline_county': .032, 'carroll_county': .0303,
    'cecil_county': .0274, 'charles_county': .0303, 'dorchester_county': .033,
    'garrett_county': .0265, 'harford_county': .0306, 'howard_county': .032,
    'kent_county': .033, 'montgomery_county': .032, 'prince_georges_county': .032,
    'queen_annes_county': .032, 'st_marys_county': .032, 'somerset_county': .032,
    'talbot_county': .024, 'washington_county': .0295, 'wicomico_county': .032,
    'worcester_county': .0225,
}
_LOCAL_2026 = {key: ('flat', rate) for key, rate in _FLAT_2026.items()}
_LOCAL_2026['anne_arundel_county'] = ('brackets', {
    'single': ((50000., .027), (400000., .0294), (inf, .032)),
    'mfj': ((75000., .027), (480000., .0294), (inf, .032))})
_LOCAL_2026['frederick_county'] = ('income_band', {
    'single': ((25000., .0225), (50000., .0275), (150000., .0296), (inf, .032)),
    'mfj': ((25000., .0225), (100000., .0275), (250000., .0296), (inf, .032))})
PUBLISHED_LOCAL_RATES = {2026: {'rates': _LOCAL_2026, 'source_id': 'md_local_rates_2026'}}
LOCAL_JURISDICTIONS = tuple(sorted(_LOCAL_2026))
# Rule family -> (published registry, projection of later years).
RULE_FAMILIES = {
    'md_standard_deduction': (PUBLISHED_STANDARD_DEDUCTION, 'indexed'),
    'md_pension_exclusion_limit': (PUBLISHED_PENSION_EXCLUSION, 'indexed'),
    'md_local_income_tax_rates': (PUBLISHED_LOCAL_RATES, 'carried_forward'),
}
SPEC_FIELDS = {'jurisdiction', 'residency', 'local_jurisdiction', 'pension_plan_types'}


def validate_spec(spec, plan, error):
    """Fail closed on anything this Form 502 subset cannot represent."""
    unknown = set(spec) - SPEC_FIELDS
    if unknown:
        raise error(f'state_income_tax: unsupported fields {sorted(unknown)}; do not silently ignore data')
    if spec.get('residency') != RESIDENCY:
        raise error('Maryland requires residency full_year_resident; part-year residents and nonresidents are not modeled')
    if spec.get('local_jurisdiction') not in LOCAL_JURISDICTIONS:
        raise error('Maryland requires local_jurisdiction: the county or baltimore_city of residence on December 31 '
                    f'(one of {", ".join(LOCAL_JURISDICTIONS)})')
    types = spec.get('pension_plan_types')
    if not isinstance(types, dict):
        raise error('Maryland requires pension_plan_types: each member with a pension mapped to '
                    f'{ERS} or {NOT_ERS} ({{}} if none)')
    pensioners = {m['id'] for m in plan['members'] if m.get('annual_pension_2026_real', 0) > 0}
    if set(types) != pensioners:
        raise error('pension_plan_types must name exactly the members with a pension amount '
                    f'(expected {sorted(pensioners)}, got {sorted(types)})')
    for member, kind in types.items():
        if kind not in (ERS, NOT_ERS):
            raise error(f'{member}: pension plan type must be {ERS} (qualified under 401(a), 403 or 457(b)) or {NOT_ERS}')


def rule_basis(year, assumed_rate):
    basis = {}
    for family, (published, projection) in RULE_FAMILIES.items():
        base, multiplier, status = rule_year(published, year, assumed_rate)
        if projection == 'carried_forward':
            multiplier = 1.
        basis[family] = {'status': status, 'base_year': base, 'multiplier': multiplier,
                         'source_id': published[base]['source_id']}
    return basis


def bracket_lines(income, brackets):
    """Marginal schedule: positive portion and tax of each bracket."""
    lines = []
    low = 0.
    for top, rate in brackets:
        amount = max(0., min(income, top) - low)
        if amount > 0:
            lines.append({'from': low, 'to': None if top == inf else top, 'rate': rate,
                          'taxable': amount, 'tax': amount * rate})
        if income <= top:
            break
        low = top
    return lines


def exemption_each(fagi_cents, status):
    for limit, amount in EXEMPTION_LIMITS[status]:
        if fagi_cents <= limit:
            return amount
    return 0.


def pension_exclusion(qualifying, social_security, limit, age):
    """Worksheet 13A: 65 or older on December 31; the limit less all Social Security."""
    return min(qualifying, max(0., limit - social_security)) if age >= 65 else 0.


def senior_credit(fagi_cents, status, eligible):
    limit, amounts = SENIOR_CREDIT[status]
    return amounts.get(eligible, 0.) if fagi_cents <= limit else 0.


def local_tax(income, local_jurisdiction, status, law):
    """(structure, lines) of the county tax on taxable net income."""
    kind, schedule = law[local_jurisdiction]
    if kind == 'flat':
        return 'flat', ([{'from': 0., 'to': None, 'rate': schedule, 'taxable': income,
                          'tax': income * schedule}] if income > 0 else [])
    if kind == 'brackets':
        return 'graduated_brackets', bracket_lines(income, schedule[status])
    # One rate on all taxable net income, by the cent-rounded income's band.
    cents = round(income, 2)
    rate = next(rate for top, rate in schedule[status] if cents <= top)
    return 'income_band_rate', ([{'from': 0., 'to': None, 'rate': rate, 'taxable': income,
                                  'tax': income * rate}] if income > 0 else [])


def maryland_tax(*, spec, year, status, assumed_rate, fagi, capital_gain_in_agi,
                 taxable_social_security, persons, joint_income):
    """Form 502 lines 1-34 for the modeled items.

    persons: one dict per member with id, age, wages_taxable, pension,
    ira_income (traditional IRA RMDs, draws and conversions), plan_401k_income
    (401(k) RMDs and draws) and social_security (gross benefits).
    joint_income: cash interest, taxable-account interest and dividends and
    Form 1040 line 7a, attributed half to each spouse (Instruction 8: jointly
    held property is divided evenly).

    Thresholds compare the cent-rounded amount that the row exports.
    """
    if status not in STATE_BRACKETS or len(persons) != (2 if status == 'mfj' else 1):
        raise ValueError('Maryland: unsupported filing status or household')
    values = [fagi, capital_gain_in_agi, taxable_social_security, joint_income]
    for person in persons:
        values += [person[key] for key in ('wages_taxable', 'pension', 'ira_income', 'plan_401k_income', 'social_security')]
    if any(not isfinite(v) for v in values) or taxable_social_security < 0:
        raise ValueError('Maryland: nonfinite or negative income')
    basis = rule_basis(year, assumed_rate)
    std_basis, pension_basis, local_basis = (basis[f] for f in RULE_FAMILIES)
    exclusion_limit = (PUBLISHED_PENSION_EXCLUSION[pension_basis['base_year']]['amount']
                       * pension_basis['multiplier'])
    types = spec['pension_plan_types']
    members = {}
    excluded = 0.
    for person in persons:
        # Worksheet 13A: qualifying pension and annuity income from an employee
        # retirement system; Social Security reduces the per-person limit.
        qualifying = (person['pension'] if types.get(person['id']) == ERS else 0.) + person['plan_401k_income']
        exclusion = pension_exclusion(qualifying, person['social_security'], exclusion_limit, person['age'])
        excluded += exclusion
        modified = None
        if status == 'mfj':
            # Worksheet 13D lines 1-5 without the Social Security that line 11
            # subtracts again: each spouse's income less their exclusion.
            modified = (person['wages_taxable'] + person['pension'] + person['ira_income']
                        + person['plan_401k_income'] + joint_income / 2 - exclusion)
        members[person['id']] = {'age': person['age'], 'qualifying_pension_income': qualifying,
                                 'social_security_benefits': person['social_security'],
                                 'pension_exclusion': exclusion, 'modified_maryland_agi': modified}
    two_income = 0.
    if status == 'mfj':
        two_income = min(TWO_INCOME_LIMIT, max(0., min(m['modified_maryland_agi'] for m in members.values())))
    subtractions = taxable_social_security + excluded + two_income
    md_agi = fagi - subtractions
    standard = PUBLISHED_STANDARD_DEDUCTION[std_basis['base_year']]['amounts'][status] * std_basis['multiplier']
    fagi_cents = round(fagi, 2)
    each = exemption_each(fagi_cents, status)
    older = sum(person['age'] >= 65 for person in persons)
    exemptions = len(persons) * each + older * AGE_65_EXEMPTION
    taxable = max(0., md_agi - standard - exemptions)
    lines = bracket_lines(taxable, STATE_BRACKETS[status])
    bracket_tax = sum(line['tax'] for line in lines)
    surtax_base = max(0., capital_gain_in_agi) if fagi_cents > SURTAX_FAGI else 0.
    surtax = surtax_base * SURTAX_RATE
    before_credits = bracket_tax + surtax
    credit = min(senior_credit(fagi_cents, status, older), before_credits)
    after_credits = before_credits - credit
    law = PUBLISHED_LOCAL_RATES[local_basis['base_year']]['rates']
    structure, local_lines = local_tax(taxable, spec['local_jurisdiction'], status, law)
    local = sum(line['tax'] for line in local_lines)
    return {'jurisdiction': JURISDICTION, 'residency': spec['residency'],
            'local_jurisdiction': spec['local_jurisdiction'],
            'federal_adjusted_gross_income': fagi, 'additions': 0.,
            'social_security_subtraction': taxable_social_security,
            'pension_exclusion_limit': exclusion_limit, 'members': members,
            'pension_exclusion': excluded, 'two_income_subtraction': two_income,
            'subtractions': subtractions, 'maryland_adjusted_gross_income': md_agi,
            'standard_deduction': standard, 'exemption_per_person': each,
            'age_65_exemptions': older * AGE_65_EXEMPTION, 'exemptions': exemptions,
            'taxable_net_income': taxable, 'state_bracket_lines': lines,
            'state_tax_before_surtax': bracket_tax, 'capital_gain_in_maryland_agi': capital_gain_in_agi,
            'capital_gain_surtax_base': surtax_base, 'capital_gain_surtax': surtax,
            'state_tax_before_credits': before_credits, 'senior_tax_credit': credit,
            'state_tax_after_credits': after_credits, 'local_rate_structure': structure,
            'local_tax_lines': local_lines, 'local_tax': local,
            'total_state_and_local_tax': after_credits + local,
            'funding_cliff_excess_cash': 0.}


def scope_lines():
    return [
        'Maryland (TG 10-105, 10-106, 10-207, 10-209, 10-211, 10-217, 10-754; Form 502): full-year residents filing '
        'single or jointly in one county or Baltimore City; FAGI less taxable Social Security, the pension exclusion '
        '(age 65+, employee-retirement-system pensions and 401(k) distributions, not IRAs, limit reduced by Social '
        'Security) and the two-income subtraction (jointly held income split evenly); standard deduction; $3,200 '
        'exemptions limited by FAGI plus $1,000 at 65+; marginal state rates; 2% surtax on Form 1040 line 7a gain '
        'when FAGI exceeds $350,000; senior tax credit assuming the TG 10-754(c) revenue trigger does not apply; '
        'county tax on taxable net income (Anne Arundel graduated, Frederick one rate by income band).',
        'Maryland not modeled: additions, itemized deductions, dependents, disability and blindness benefits, '
        'military and public safety retirement subtractions, U.S. obligation interest subtraction, earned income, '
        'poverty level and other credits, local credits, credits for taxes paid elsewhere, tax-table and whole-dollar '
        'rounding. Every other state is rejected, never taxed at zero.',
        'Maryland standard deduction published for 2025 and pension exclusion limit for 2026 project later years at the '
        'assumed rate; 2026 county rates carry forward unchanged. Maryland tax is not deducted on Form 8960 line 9b '
        '(the federal return takes the standard deduction); flagged for professional review.',
    ]
