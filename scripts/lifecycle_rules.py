#!/usr/bin/env python3
"""Explicit year-end death/survival timeline; no inferred survivor entitlements.

Death-year end convention is a scenario assumption, not an actuarial mortality
forecast. Requires externally supplied survivor benefits for post-death output.
"""
class LifecycleUnsupported(ValueError): pass


def lifecycle_year(members, year, *, verified_survivor_annual=None):
    if not isinstance(year,int) or not (1900<=year<=2150):
        raise LifecycleUnsupported('invalid year')
    if not isinstance(members,list) or len(members) not in (1,2):
        raise LifecycleUnsupported('only one or two adults supported')
    seen=set();alive=[];deceased=[]
    for m in members:
        if not isinstance(m,dict) or not isinstance(m.get('id'),str) or m['id'] in seen:
            raise LifecycleUnsupported('invalid/duplicate member identifier')
        seen.add(m['id'])
        birth=m.get('birth_year'); death=m.get('death_year')
        if not isinstance(birth,int) or birth>year or (death is not None and
                (not isinstance(death,int) or death<birth or death>2150)):
            raise LifecycleUnsupported('invalid birth/death year')
        (deceased if death is not None and year>death else alive).append(m['id'])
    if len(members)==2 and len(alive)==1 and verified_survivor_annual is None:
        raise LifecycleUnsupported('surviving spouse benefits must be supplied and independently documented')
    if len(alive)==0:
        return {'year':year,'alive_ids':[],'filing_status':'not_modeled_deceased_estate',
                'earnings_people':[],'benefits_source':'not_modeled'}
    return {'year':year,'alive_ids':alive,'filing_status':'single' if len(alive)==1 else 'mfj',
            'earnings_people':alive,
            'survivor_benefit_annual':verified_survivor_annual if len(alive)==1 and len(members)==2 else None,
            'death_convention':'member alive through December 31 in declared death year',
            'tax_filing_is_planning_simplification':True}
