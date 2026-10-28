#!/usr/bin/env python3
"""Separate 2026 NIIT component for externally established MAGI and net income.

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
    if tax_year!=2026:raise TaxExtensionError("reference-year calculation only; verify rules for other tax years")
    if filing_status not in THRESHOLDS:raise TaxExtensionError("unsupported filing status")
    for label,value in (("modified_agi",modified_agi),("net_investment_income",net_investment_income)):
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not isfinite(value) or value<0:
            raise TaxExtensionError(f"{label} must be finite and nonnegative")
    threshold=THRESHOLDS[filing_status]
    excess=max(0.,modified_agi-threshold)
    base=min(net_investment_income,excess)
    return {"tax_year":tax_year,"modified_agi":modified_agi,
            "net_investment_income":net_investment_income,
            "filing_status":filing_status,"threshold":threshold,
            "modified_agi_above_threshold":excess,"niit_tax_base":base,
            "niit_rate":NIIT_RATE,"niit_due":base*NIIT_RATE,
            "sources":[SOURCE],
            "limitations":["caller must independently establish MAGI and net investment income",
                           "does not model Form 8960 allocation/deductions or special adjustments"]}
