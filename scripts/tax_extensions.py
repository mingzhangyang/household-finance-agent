#!/usr/bin/env python3
"""Versioned 2026 reference-rule NIIT for externally established MAGI/NII.

This module does NOT infer MAGI or net investment income from asset balances.
Retirement account distributions are generally excluded from net investment
income but can affect MAGI. No Form 8960 or state-tax preparation is performed.
"""
from math import isfinite

NIIT_RATE=.038
THRESHOLDS={"single":200000.,"mfj":250000.,"mfs":125000.,"hoh":200000.}
SOURCE="https://www.irs.gov/individuals/net-investment-income-tax"

class TaxExtensionError(ValueError):pass

def net_investment_income_tax(*,modified_agi,net_investment_income,filing_status,tax_year=2026):
    if isinstance(tax_year,bool) or not isinstance(tax_year,int) or tax_year<2026:raise TaxExtensionError("unsupported tax year")
    if filing_status not in THRESHOLDS:raise TaxExtensionError("unsupported filing status")
    # AGI, and so MAGI, is negative when an allowed capital loss exceeds other income.
    for label,value,floor in (("modified_agi",modified_agi,float("-inf")),("net_investment_income",net_investment_income,0.)):
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not isfinite(value) or value<floor:
            raise TaxExtensionError(f"{label} must be finite" + (" and nonnegative" if floor==0. else ""))
    threshold=THRESHOLDS[filing_status]
    excess=max(0.,modified_agi-threshold)
    base=min(net_investment_income,excess)
    return {"tax_year":tax_year,"reference_tax_year":2026,"modified_agi":modified_agi,
            "net_investment_income":net_investment_income,
            "filing_status":filing_status,"threshold":threshold,
            "modified_agi_above_threshold":excess,"niit_tax_base":base,
            "niit_rate":NIIT_RATE,"niit_due":base*NIIT_RATE,
            "sources":[SOURCE],"policy":"2026 NIIT law carried forward hypothetically" if tax_year>2026 else "2026 reference tax law",
            "limitations":["caller must independently establish MAGI and net investment income; projection assumes MAGI=AGI (no excluded foreign income)",
                           "does not model Form 8960 allocation/deductions or special adjustments"]}


# Standalone signed-NII API retained for existing research callers.
class TaxExtensionUnsupported(ValueError): pass


def niit_core(*, modified_agi, net_investment_income, filing_status):
    """NIIT = 3.8% * min(positive NII, positive MAGI excess over fixed threshold).

    Caller must already establish Form 8960 NII and MAGI including deductions,
    carryovers and applicable adjustments; don't pass an unverified 1040 AGI.
    """
    thresholds={'single':200000.,'mfj':250000.,'mfs':125000.,'hoh':200000.}
    if filing_status not in thresholds:raise TaxExtensionUnsupported('unsupported NIIT filing status')
    for n,v in [('MAGI',modified_agi),('NII',net_investment_income)]:
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not isfinite(v):
            raise TaxExtensionUnsupported(f'{n} must be finite and documented')
    excess=max(0.,modified_agi-thresholds[filing_status])
    tax_base=min(max(0.,net_investment_income),excess)
    return {'niit_tax_base':tax_base,'niit':tax_base*.038,'magi_threshold':thresholds[filing_status],
            'source':'https://www.irs.gov/individuals/net-investment-income-tax',
            'full_form_8960_validated':False}
