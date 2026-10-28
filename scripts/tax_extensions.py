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
    for label,value in (("modified_agi",modified_agi),("net_investment_income",net_investment_income)):
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not isfinite(value) or value<0:
            raise TaxExtensionError(f"{label} must be finite and nonnegative")
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
