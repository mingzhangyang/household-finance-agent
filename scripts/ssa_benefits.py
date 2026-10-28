#!/usr/bin/env python3
"""SSA retirement-worker benefit arithmetic; no eligibility or survivor certification.

AIME is supplied from verified, SSA-indexed earnings. Amounts are in the
eligibility year's dollars; future COLA, recomputation and actual payments are
outside this module. All ages are month-granular; birthday-day exceptions need
manual review. See references/professional-model-gates.md.
"""
from math import floor, isfinite

BEND_POINTS = {2026: (1286, 7749), 2027: (1340, 8077)}
SOURCES = {
    'aime': 'https://www.ssa.gov/OACT/COLA/Benefits.html',
    'pia': 'https://www.ssa.gov/OACT/COLA/piaformula.html',
    'fra': 'https://www.ssa.gov/oact/quickcalc/earlyretire.html',
    'claim': 'https://www.ssa.gov/oact/quickcalc/early_late.html',
}

class SSAUnsupported(ValueError):
    pass


def _finite(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value) or value < 0:
        raise SSAUnsupported(f'{label} must be a finite nonnegative number')
    return float(value)


def aime_from_indexed_earnings(indexed_annual_earnings):
    """Top 35 years, with zero-years, truncation to whole-dollar AIME.

    Input is *already indexed* to the eligibility reference wage year.
    Not an earnings-record indexing or insured-status calculator.
    """
    if not isinstance(indexed_annual_earnings, (list, tuple)):
        raise SSAUnsupported('indexed_annual_earnings must be an array')
    amounts = [_finite(v, 'indexed annual earnings') for v in indexed_annual_earnings]
    if len(amounts) > 90:
        raise SSAUnsupported('unreasonable earnings history length')
    return floor(sum(sorted(amounts, reverse=True)[:35]) / 420.)


def pia_from_aime(aime, eligibility_year):
    """SSA 90/32/15 percent bend-point formula; truncate down to a dime."""
    x = _finite(aime, 'AIME')
    if int(eligibility_year) != eligibility_year or eligibility_year not in BEND_POINTS:
        raise SSAUnsupported('only published eligibility years 2026 and 2027 supported')
    first, second = BEND_POINTS[eligibility_year]
    result = .90 * min(x, first) + .32 * max(0., min(x, second)-first) + .15 * max(0., x-second)
    return floor((result + 1e-9) * 10.) / 10.


def full_retirement_age_months(birth_year):
    """FRA 66-67 for birth years 1943 onward.

    January 1 birth-date special rule is NOT modeled. Pass SSA-adjusted birth
    year explicitly if it applies, and document the substitution.
    """
    if isinstance(birth_year, bool) or not isinstance(birth_year, int) or birth_year < 1943:
        raise SSAUnsupported('FRA for birth year before 1943 not implemented')
    if birth_year <= 1954:
        return 66 * 12
    if birth_year <= 1959:
        return 66 * 12 + 2 * (birth_year-1954)
    return 67 * 12


def retirement_claim_factor(birth_year, age_in_months):
    """Worker-only reduced/delayed monthly factor, before SSA dollar rounding."""
    fra = full_retirement_age_months(birth_year)
    if isinstance(age_in_months, bool) or not isinstance(age_in_months, int) or not 62*12 <= age_in_months <= 70*12:
        raise SSAUnsupported('claim age must be whole months between 62 and 70')
    if age_in_months < fra:
        early = fra - age_in_months
        reduction = min(36, early) * (5/900) + max(0, early-36) * (5/1200)
        return 1.-reduction
    return 1. + (age_in_months-fra)*(2/300)


def retirement_worker_estimate(*, birth_year, claim_age_months, pia, pia_reference_year):
    """Claim-age factor on PIA in reference-year dollars, not an actual award."""
    amount = _finite(pia, 'PIA')
    if pia_reference_year not in BEND_POINTS:
        raise SSAUnsupported('PIA reference year must be 2026 or 2027')
    if birth_year+62 != pia_reference_year:
        raise SSAUnsupported('PIA must use the worker age-62 eligibility-year bend points')
    factor = retirement_claim_factor(birth_year, claim_age_months)
    return {'pia_monthly_reference_dollars':amount, 'factor':round(factor,10),
            'modeled_monthly_reference_dollars':round(amount*factor,2),
            'full_retirement_age_months':full_retirement_age_months(birth_year),
            'eligibility_year':pia_reference_year, 'rules_sources':SOURCES,
            'verified_payment_amount':False,
            'unsupported':['future COLA','post-62 earnings recomputation','earnings test',
                           'spousal and survivor benefits','SSA monthly payment rounding']}
