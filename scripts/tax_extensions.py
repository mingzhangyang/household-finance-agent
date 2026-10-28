#!/usr/bin/env python3
"""Isolated Form 8960 NIIT base calculation; NOT a complete return or AGI engine."""
import math

class TaxExtensionUnsupported(ValueError): pass


def niit_core(*, modified_agi, net_investment_income, filing_status):
    """NIIT = 3.8% * min(positive NII, positive MAGI excess over fixed threshold).

    Caller must already establish Form 8960 NII and MAGI including deductions,
    carryovers and applicable adjustments; don't pass an unverified 1040 AGI.
    """
    thresholds={'single':200000.,'mfj':250000.,'mfs':125000.,'hoh':200000.}
    if filing_status not in thresholds:raise TaxExtensionUnsupported('unsupported NIIT filing status')
    for n,v in [('MAGI',modified_agi),('NII',net_investment_income)]:
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v):
            raise TaxExtensionUnsupported(f'{n} must be finite and documented')
    excess=max(0.,modified_agi-thresholds[filing_status])
    tax_base=min(max(0.,net_investment_income),excess)
    return {'niit_tax_base':tax_base,'niit':tax_base*.038,'magi_threshold':thresholds[filing_status],
            'source':'https://www.irs.gov/individuals/net-investment-income-tax',
            'full_form_8960_validated':False}
