#!/usr/bin/env python3
"""SSA retirement arithmetic. NOT a full SSA benefit determination.

AIME is supplied and validated externally. 2026/2027 bend points apply
ONLY to workers whose eligibility year is the same as the formula year.
PIA at claim time must already include applicable COLAs; do not use an
eligibility-year PIA as a future nominal payment without COLA adjustments.
See references/ssa-methodology.md.
"""
from math import floor, isfinite

BEND_POINTS = {2026:(1286.,7749.), 2027:(1340.,8077.)}
PIA_SOURCE = "https://www.ssa.gov/oact/cola/piaformula.html"
CLAIM_SOURCE = "https://www.ssa.gov/oact/quickcalc/early_late.html"

class SSARuleError(ValueError):
    pass

def full_retirement_age_months(birth_year):
    if not isinstance(birth_year,int) or birth_year<1900:
        raise SSARuleError("valid birth year required")
    if birth_year<=1937:return 780
    if birth_year<=1942:return 780+(birth_year-1937)*2
    if birth_year<=1954:return 792
    if birth_year<=1959:return 792+(birth_year-1954)*2
    return 804

def pia_from_aime(aime, eligibility_year):
    """PIA rounded down to nearest 10 cents, for eligible years 2026/2027 only."""
    if eligibility_year not in BEND_POINTS:
        raise SSARuleError("only 2026/2027 eligibility-year bend points are versioned")
    if isinstance(aime,bool) or not isinstance(aime,(int,float)) or not isfinite(aime) or aime<0:
        raise SSARuleError("AIME must be finite and nonnegative")
    lo,hi=BEND_POINTS[eligibility_year]
    raw=.90*min(aime,lo)+.32*max(0.,min(aime,hi)-lo)+.15*max(0.,aime-hi)
    return floor((raw+1e-9)*10)/10

def claiming_factor(birth_year, claim_age_months):
    """Original worker retirement factor; not a spousal/survivor factor."""
    if not isinstance(claim_age_months,int) or not 744<=claim_age_months<=840:
        raise SSARuleError("claim age must be whole months from 62 to 70")
    fra=full_retirement_age_months(birth_year)
    delta=claim_age_months-fra
    if delta<0:
        early=-delta
        cut=min(early,36)*(5/9/100)+max(0,early-36)*(5/12/100)
        return 1.-cut
    delayed=min(delta,840-fra)
    if birth_year<1943:
        raise SSARuleError("pre-1943 delayed retirement credit schedule not implemented")
    return 1.+delayed*(2/3/100)

def benefit_from_pia_at_claim(pia_at_claim_month,birth_year,claim_age_months):
    """Apply only claiming factor to COLA-adjusted PIA supplied for claim month."""
    if isinstance(pia_at_claim_month,bool) or not isinstance(pia_at_claim_month,(int,float)) or not isfinite(pia_at_claim_month) or pia_at_claim_month<0:
        raise SSARuleError("monthly claim-date PIA must be nonnegative and finite")
    return {'pia_at_claim_month':float(pia_at_claim_month),
            'claim_age_months':claim_age_months,
            'fra_months':full_retirement_age_months(birth_year),
            'claim_factor':claiming_factor(birth_year,claim_age_months),
            'unrounded_monthly_benefit':pia_at_claim_month*claiming_factor(birth_year,claim_age_months),
            'limitations':['SSA whole-dollar payment rounding not applied','eligibility-year COLA not calculated',
                           'earnings test, spousal/survivor benefits, Medicare withholding and taxes excluded'],
            'source':CLAIM_SOURCE}

if __name__=="__main__":
    print({'official_2026_case_A_pia':pia_from_aime(5825,2026),
           'fra_1960_or_later':full_retirement_age_months(1960)/12,
           'factor_at_62':claiming_factor(1960,744),
           'factor_at_70':claiming_factor(1960,840)})
