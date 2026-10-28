#!/usr/bin/env python3
"""Explicit deterministic household lifecycle scenarios; NOT a mortality forecast.

All income and survivor assumptions are caller-supplied. A death occurring
during year Y is treated as end-of-year for this coarse timeline. If a two-
adult household becomes one adult, the TOTAL post-death Social Security
benefit must be provided; benefits are never guessed or double-counted.
No tax-filing status calculation, Medicare, estate or survivor eligibility.
"""
from math import isfinite

class LifecycleError(ValueError): pass

def money(x,label):
    if isinstance(x,bool) or not isinstance(x,(int,float)) or not isfinite(x) or x<0:
        raise LifecycleError(f"{label} must be finite and nonnegative")
    return float(x)

def timeline(members,start_year,end_year,*,annual_spending,
             survivor_spending_fraction=None,survivor_total_ss_annual=None):
    if not isinstance(start_year,int) or not isinstance(end_year,int) or end_year<start_year or end_year-start_year>110:
        raise LifecycleError("invalid date range")
    if not isinstance(members,list) or len(members) not in (1,2):
        raise LifecycleError("one or two adults required")
    annual_spending=money(annual_spending,"annual_spending")
    rows=[]
    names=set()
    for m in members:
        if not isinstance(m,dict) or not isinstance(m.get("id"),str) or not m["id"] or m["id"] in names:
            raise LifecycleError("unique person ID required")
        names.add(m["id"])
        for k in ("birth_year","retirement_age","claim_age","death_year"):
            if not isinstance(m.get(k),int):
                raise LifecycleError(f"{m['id']} missing integer {k}")
        if not 20<=m["retirement_age"]<=90 or not 62<=m["claim_age"]<=70:
            raise LifecycleError("invalid retirement/claim age")
        if m["death_year"]<m["birth_year"] or m["death_year"]>m["birth_year"]+125:
            raise LifecycleError("invalid death year")
        for k in ("annual_wages","annual_pension","annual_social_security"):
            money(m.get(k),k)
    first_death=min(m["death_year"] for m in members)
    last_death=max(m["death_year"] for m in members)
    # Deaths take effect at year end: one survivor exists only during
    # [first_death + 1, last_death], intersected with the modeled interval.
    may_survive_one=(len(members)==2 and
                     max(start_year,first_death+1)<=min(end_year,last_death))
    if may_survive_one:
        if survivor_spending_fraction is None or survivor_total_ss_annual is None:
            raise LifecycleError("post-death spending fraction and TOTAL survivor-household SS must be supplied")
        money(survivor_total_ss_annual,"survivor_total_ss_annual")
        if not isinstance(survivor_spending_fraction,(int,float)) or not 0<survivor_spending_fraction<=1.5:
            raise LifecycleError("survivor_spending_fraction must be in (0,1.5]")
    for year in range(start_year,end_year+1):
        alive=[m for m in members if year<=m["death_year"]]
        wage=sum(m["annual_wages"] for m in alive if year-m["birth_year"]<m["retirement_age"])
        pension=sum(m["annual_pension"] for m in alive)
        individual_ss=sum(m["annual_social_security"] for m in alive if year-m["birth_year"]>=m["claim_age"])
        survivor=len(members)==2 and len(alive)==1
        ss=float(survivor_total_ss_annual) if survivor else individual_ss
        spending=0. if not alive else annual_spending*(survivor_spending_fraction if survivor else 1)
        rows.append({"year":year,"alive":[m["id"] for m in alive],"gross_wages":wage,
                     "gross_pension":pension,"gross_social_security":ss,
                     "assumed_living_expenses":spending,
                     "filing_status":"REQUIRES_TAX_REVIEW" if survivor or not alive else "NOT_MODELED",
                     "notes":["end-of-year death convention","nominal amounts only",
                              "survivor SS uses explicit TOTAL household override if applicable"]})
    return {"rows":rows,"model":"deterministic-lifecycle-scenario",
            "not_modeled":["date-of-death prorating","actuarial survival probabilities",
                           "filing status after death","survivor eligibility and SSA formulas",
                           "insurance/Medicare/estate taxes","COLA and inflation"]}

if __name__=="__main__":
    print("Use timeline(members, start_year, end_year, annual_spending=...) with explicit death-year scenarios.")
