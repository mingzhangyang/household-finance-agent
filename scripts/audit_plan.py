#!/usr/bin/env python3
"""Auditable, deliberately restricted household projection v2.0.

This is not a US tax-return engine, fiduciary advice, or a verified distribution strategy.
No quiet fallback from unknown basis/ownership/benefit estimates to guessed values.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import math
import random
import statistics
import sys
from pathlib import Path
from datetime import date
from tax2026 import federal_tax, payroll_tax, elective_deferral_limit, rule_basis, RULE_FAMILIES, SOURCES
from tax_extensions import net_investment_income_tax, SOURCE as NIIT_SOURCE

RULESET = 'US_FEDERAL_2026_RESTRICTED_v2.2'
KINDS = {'cash','taxable','traditional_ira','traditional_401k','roth_ira'}
RMD_DENOMINATORS = {
    72:27.4,73:26.5,74:25.5,75:24.6,76:23.7,77:22.9,78:22.0,79:21.1,
    80:20.2,81:19.4,82:18.5,83:17.7,84:16.8,85:16.0,86:15.2,87:14.4,
    88:13.7,89:12.9,90:12.2,91:11.5,92:10.8,93:10.1,94:9.5,95:8.9,
    96:8.4,97:7.8,98:7.3,99:6.8,100:6.4,101:6.0,102:5.6,103:5.2,
    104:4.9,105:4.6,106:4.3,107:4.1,108:3.9,109:3.7,110:3.5,
    111:3.4,112:3.3,113:3.1,114:3.0,115:2.9,116:2.8,117:2.7,
    118:2.5,119:2.3,120:2.0,
}

class ModelError(ValueError):
    """A rejected input/model run never produces a valid planning conclusion."""
    code = 'INVALID_OR_UNSUPPORTED_PLAN'


def _num(v,label,lo=0,hi=1e15):
    # Compare integers before converting to float (isfinite can overflow).
    if isinstance(v,bool) or not isinstance(v,(float,int)) or not lo<=v<=hi or not math.isfinite(v):
        raise ModelError(f'{label} must be a finite number in [{lo},{hi}]')
    return float(v)


def _int(v,label,lo,hi):
    if isinstance(v,bool) or not isinstance(v,int) or not lo<=v<=hi:
        raise ModelError(f'{label} must be an integer in [{lo},{hi}]')
    return v


def rmd_age(birth_year):
    if birth_year < 1951:
        raise ModelError('RMD before 1951 birth year is outside v2.0 modeled scope')
    return 73 if birth_year <= 1959 else 75


def _allowed(obj,keys,context):
    if not isinstance(obj,dict): raise ModelError(f'{context} must be an object')
    unknown=set(obj)-set(keys)
    if unknown:raise ModelError(f'{context}: unsupported fields {sorted(unknown)}; do not silently ignore data')


def validate(p):
    """Normalize malformed nested data into the public fail-closed exception."""
    try:
        return _validate(p)
    except ModelError:
        raise
    except (KeyError, TypeError, AttributeError, IndexError, OverflowError) as exc:
        raise ModelError('missing or malformed required plan data') from exc


def _validate(p):
    if not isinstance(p,dict) or p.get('version')!='2.0':
        raise ModelError('audited model requires version 2.0; v1.0 is legacy illustrative only')
    _allowed(p,['version','name','currency','as_of_year','end_year','members','accounts',
                'tax_policy','living_expenses_annual_real','events','roth_conversions',
                'terminal_target_2026_real','withdrawal_order','assumptions','liabilities',
                'input_provenance','opening_balance_status'], 'plan')
    if not isinstance(p.get('name'),str) or not p['name'].strip():
        raise ModelError('nonempty name required')
    evidence=p.get('input_provenance')
    if 'input_provenance' in p:
        _allowed(evidence,['mode','register'],'input_provenance')
        if evidence.get('mode') not in ('fictional_demo','unverified_user_data','documented_verified'):
            raise ModelError('input_provenance.mode must be fictional_demo/unverified_user_data/documented_verified')
        reg=evidence.get('register')
        if not isinstance(reg,list):raise ModelError('input_provenance.register must be a list')
        if evidence['mode']=='documented_verified':
            required={'/living_expenses_annual_real'}
            required.update(f'/accounts/{i}/balance' for i,_ in enumerate(p.get('accounts',[])))
            required.update(f'/accounts/{i}/basis' for i,a in enumerate(p.get('accounts',[])) if a.get('kind')=='taxable')
            required.update(f'/members/{i}/annual_wages_2026' for i,_ in enumerate(p.get('members',[])))
            required.update(f'/members/{i}/ss_annual_2026_real_at_chosen_claim_age' for i,_ in enumerate(p.get('members',[])))
            registered={item.get('json_pointer') for item in (reg or []) if item.get('confidence')=='documented'}
            missing=sorted(required-registered)
            if missing:raise ModelError(f'documented_verified missing documented evidence for material fields: {missing}')
        for item in reg:
            _allowed(item,['json_pointer','evidence_id','source_type','as_of_date','confidence'],'evidence entry')
            if not isinstance(item.get('json_pointer'),str) or not item['json_pointer'].startswith('/'):
                raise ModelError('evidence register requires JSON Pointer')
            if not isinstance(item.get('evidence_id'),str) or not item['evidence_id']:
                raise ModelError('evidence requires nonempty evidence_id')
            if item.get('source_type') not in ('user_statement','statement','tax_form','ssa_statement','estimate','fictional_fixture'):
                raise ModelError('unrecognized evidence source_type')
            if item.get('confidence') not in ('documented','supplied','assumed'):
                raise ModelError('evidence confidence must be documented/supplied/assumed')
            dt=item.get('as_of_date')
            try:
                if not isinstance(dt,str) or len(dt)!=10:raise ValueError('not ISO date')
                date.fromisoformat(dt)
            except ValueError as e:
                raise ModelError('evidence as_of_date must be a valid YYYY-MM-DD') from e
            # Verify pointer actually resolves into the user's normalized model.
            pos=p
            try:
                for part in item['json_pointer'].split('/')[1:]:
                    part=part.replace('~1','/').replace('~0','~')
                    pos=pos[int(part)] if isinstance(pos,list) else pos[part]
            except (KeyError,IndexError,ValueError,TypeError) as e:
                raise ModelError('evidence pointer does not identify any input') from e
    if p.get('opening_balance_status') not in ('projected_2026_12_31','documented_2026_12_31'):
        raise ModelError('opening balances must explicitly be projected_2026_12_31 or documented_2026_12_31')
    if p['opening_balance_status']=='documented_2026_12_31' and evidence is not None and evidence.get('mode')=='fictional_demo':
        raise ModelError('fictional data cannot be a documented 2026 year-end balance')
    y0=_int(p.get('as_of_year'),'as_of_year',2026,2026)
    y1=_int(p.get('end_year'),'end_year',2027,2110)
    if p.get('currency')!='USD': raise ModelError('currency must be USD')
    members=p.get('members')
    if not isinstance(members,list) or len(members) not in (1,2):
        raise ModelError('v2 supports 1 single filer or 2 joint-filing adults')
    filing=p.get('tax_policy',{})
    _allowed(filing,['jurisdiction','reference_year','filing_status',
                     'state_income_tax','future_bracket_inflation'],'tax_policy')
    status=filing.get('filing_status')
    if status!=('single' if len(members)==1 else 'mfj'):
        raise ModelError('filing_status must match household: single or mfj')
    if filing.get('reference_year')!=2026 or filing.get('jurisdiction')!='US_federal':
        raise ModelError('tax_policy requires US_federal reference year 2026')
    if filing.get('state_income_tax')!='excluded_with_disclosure':
        raise ModelError('state income taxes excluded; explicit disclosure required')
    rate=_num(filing.get('future_bracket_inflation'),'future_bracket_inflation',0,.1)
    a=p.get('assumptions',{})
    if not isinstance(a,dict): raise ModelError('assumptions must be object')
    _allowed(a,['inflation','equity_mean','equity_volatility','bond_mean','bond_volatility',
                'equity_bond_correlation','equity_weight','annual_investment_fee',
                'cash_yield','trials','seed'],'assumptions')
    for k,lo,hi in [('inflation',0,.1),('equity_mean',-.5,.3),('equity_volatility',0,.7),
                    ('bond_mean',-.5,.3),('bond_volatility',0,.5),('equity_bond_correlation',-1,1),
                    ('equity_weight',0,1),('annual_investment_fee',0,.1),('cash_yield',0,.2)]:
        _num(a.get(k),f'assumptions.{k}',lo,hi)
    _int(a.get('trials'),'trials',1,10000)
    _int(a.get('seed'),'seed',0,2**32-1)
    _num(p.get('living_expenses_annual_real'),'living_expenses_annual_real')
    if p.get('liabilities') not in (None,{}):
        raise ModelError('liability amortization unsupported; cash debt payments must be in expenses and no net-worth claims')
    seen=set()
    member_map={}
    for m in members:
        if not isinstance(m,dict): raise ModelError('member must be an object')
        _allowed(m,['id','birth_year','retirement_age','annual_wages_2026','wage_growth',
                    'ss_claim_age','ss_annual_2026_real_at_chosen_claim_age','ss_estimate_basis',
                    'annual_pension_2026_real','pension_start_age',
                    'annual_pretax_401k_2026_real','pretax_401k_target'],'member')
        name=m.get('id')
        if not isinstance(name,str) or not name or name in seen:
            raise ModelError('member id must be unique and nonempty')
        seen.add(name); member_map[name]=m
        _int(m.get('birth_year'),f'{name}.birth_year',1951,2006)
        _int(m.get('retirement_age'),f'{name}.retirement_age',40,90)
        _num(m.get('annual_wages_2026'),f'{name}.annual_wages_2026')
        _num(m.get('wage_growth'),f'{name}.wage_growth',-.2,.2)
        _int(m.get('ss_claim_age'),f'{name}.ss_claim_age',62,70)
        _num(m.get('ss_annual_2026_real_at_chosen_claim_age'),f'{name}.ss_annual_2026_real_at_chosen_claim_age')
        if m.get('ss_estimate_basis')!='2026_real_at_selected_claim_age':
            raise ModelError('SS estimate must be 2026 dollars for exact selected claim age; no automatic claim-age adjustment')
        pension=_num(m.get('annual_pension_2026_real',0),f'{name}.annual_pension_2026_real')
        _num(m.get('annual_pretax_401k_2026_real',0),f'{name}.annual_pretax_401k_2026_real')
        if pension>0 and 'pension_start_age' not in m:
            raise ModelError(f'{name}: pension amount requires explicit pension_start_age; no default start age is assumed')
        _int(m.get('pension_start_age',65),f'{name}.pension_start_age',40,100)
        # SSA birth-year FRA, rounded up for this whole-year age schema.
        # https://www.ssa.gov/benefits/retirement/planner/agereduction.html
        # Birth dates and partial-year earnings tests remain outside this model.
        birth=m['birth_year']
        fra_months=792 if birth<=1954 else (792+2*(birth-1954) if birth<1960 else 804)
        fra_age=(fra_months+11)//12
        working_before_fra=any(m['ss_claim_age']<=year-birth<min(fra_age,m['retirement_age'])
                               for year in range(y0+1,y1+1))
        if (working_before_fra and m['annual_wages_2026']>0
                and m['ss_annual_2026_real_at_chosen_claim_age']>0):
            raise ModelError('Social Security claimed while still working before FRA needs earnings-test model; unsupported')
    accounts=p.get('accounts')
    if not isinstance(accounts,list) or not accounts: raise ModelError('accounts must be list')
    names=set(); count={'cash':0,'taxable':0}
    for acc in accounts:
        if not isinstance(acc,dict): raise ModelError('each account must be object')
        _allowed(acc,['id','kind','balance','basis','gain_treatment','owner',
                      'rmd_table','still_working_exception','qualified_distributions_confirmed','fully_pretax_confirmed'],'account')
        aid=acc.get('id'); kind=acc.get('kind')
        if not isinstance(aid,str) or not aid or aid in names:raise ModelError('unique account id required')
        names.add(aid)
        if kind not in KINDS: raise ModelError(f'unsupported account kind {kind}')
        _num(acc.get('balance'),f'{aid}.balance')
        if kind in count:count[kind]+=1
        if kind=='taxable':
            _num(acc.get('basis'),f'{aid}.basis')
            if acc.get('gain_treatment')!='long_term_proportional_no_loss_offset':
                raise ModelError('taxable basis and explicitly simplified long-term gain treatment required')
        if kind in ('traditional_ira','traditional_401k','roth_ira'):
            if acc.get('owner') not in member_map: raise ModelError(f'{aid}: owner must be identified')
        if kind in ('traditional_ira','traditional_401k') and acc.get('fully_pretax_confirmed') is not True:
            raise ModelError('traditional account must confirm no nondeductible basis; Form 8606 basis unsupported')
        if kind=='traditional_ira' and acc.get('rmd_table')!='uniform':
            raise ModelError('traditional IRA must confirm uniform RMD table applicability')
        if kind=='traditional_401k' and acc.get('rmd_table','uniform')!='uniform':
            raise ModelError('traditional 401k only supports uniform RMD table')
        if kind=='traditional_401k' and acc.get('still_working_exception') is not False:
            raise ModelError('traditional 401k: still-working RMD exception not modeled; explicitly confirm false')
        if kind=='roth_ira' and acc.get('qualified_distributions_confirmed') is not True:
            raise ModelError('roth_ira requires affirmative qualified-distribution assumption')
    if count['cash']!=1 or count['taxable']>1:
        raise ModelError('v2 requires exactly 1 cash account and <= 1 taxable account')
    if any(y1 - m['birth_year']>120 for m in members):
        raise ModelError('planning horizon exceeds supported age 120 RMD table')
    for m in members:
        target=m.get('pretax_401k_target')
        if m.get('annual_pretax_401k_2026_real',0)>0:
            if target not in names or next(a for a in accounts if a['id']==target)['kind']!='traditional_401k':
                raise ModelError('pretax 401k contribution requires matching owned 401k account')
            if next(a for a in accounts if a['id']==target)['owner']!=m['id']:
                raise ModelError('401k contribution target owner mismatch')
    p_order=p.get('withdrawal_order')
    if not isinstance(p_order,list) or not p_order or p_order[0] != next(x['id'] for x in accounts if x['kind']=='cash') or len(p_order)!=len(accounts) or set(p_order)!=names:
        raise ModelError('withdrawal_order must list all account ids exactly once')
    events=p.get('events',[])
    if not isinstance(events,list):raise ModelError('events must be list')
    for e in events:
        _allowed(e,['year','amount','kind','dollars','tax_status','description'],'event')
        _int(e.get('year'),'event.year',2027,y1)
        _num(e.get('amount'),'event.amount')
        if e.get('kind') not in ('expense','income') or e.get('dollars') not in ('2026_real','year_nominal'):
            raise ModelError('invalid event type/units')
        if e.get('kind')=='income' and e.get('tax_status')!='net_after_all_taxes':
            raise ModelError('event income needs explicit net_after_all_taxes confirmation')
    conversions=p.get('roth_conversions',[])
    if not isinstance(conversions,list):raise ModelError('roth_conversions must be list')
    for c in conversions:
        _allowed(c,['year','amount_nominal','from','to'],'conversion')
        _int(c.get('year'),'conversion.year',2027,y1)
        _num(c.get('amount_nominal'),'conversion.amount_nominal')
        if c.get('from') not in names or c.get('to') not in names:raise ModelError('unknown conversion account')
        af=next(a for a in accounts if a['id']==c['from'])
        at=next(a for a in accounts if a['id']==c['to'])
        if af['kind']!='traditional_ira' or at['kind']!='roth_ira' or af['owner']!=at['owner']:
            raise ModelError('only same-owner traditional IRA to Roth IRA conversions supported')
    _num(p.get('terminal_target_2026_real',0),'terminal_target_2026_real')
    return True


def _tax_calc(p,year,retail,wages_by_person,wage_taxable,pension,ss,interest,rmd,conversion,ira_extra,gain):
    ages=[year-m['birth_year'] for m in p['members']]
    fed=federal_tax(wages_taxable=wage_taxable,pension=pension,ira_distributions=rmd+ira_extra,
            roth_conversions=conversion,cash_interest=interest,ltcg=gain,
            ss_benefits=ss,status=p['tax_policy']['filing_status'],ages=ages,year=year,
            bracket_inflation=p['tax_policy']['future_bracket_inflation'])
    payroll=payroll_tax(wages_by_person,p['tax_policy']['filing_status'],
                       year=year,assumed_rate=p['tax_policy']['future_bracket_inflation'])
    # No foreign income exclusion, separate investment deductions or passive revenue
    # are supported. In this restricted scope, MAGI equals AGI and modeled NII
    # consists only of cash interest and realized positive long-term gains.
    niit=net_investment_income_tax(modified_agi=fed['adjusted_gross_income'],
        net_investment_income=interest+gain,filing_status=p['tax_policy']['filing_status'],tax_year=year)
    fed['niit_magi_assumed_equal_agi']=niit['modified_agi']
    fed['niit_net_investment_income']=niit['net_investment_income']
    fed['niit_threshold']=niit['threshold']
    fed['niit_tax_base']=niit['niit_tax_base']
    fed['niit_rate']=niit['niit_rate']
    fed['niit_due']=niit['niit_due']
    fed['total_federal_income_and_niit']=fed['federal_income_tax']+niit['niit_due']
    fed['unmodeled']=[item for item in fed['unmodeled'] if item!='NIIT']
    return fed,payroll, fed['total_federal_income_and_niit']+payroll['total']


def run_path(p, annual_portfolio_returns, verify=True):
    """End-of-year transactions; RMD uses PRIOR year-end account balance."""
    validate(p)
    y0,y1=p['as_of_year'],p['end_year']
    if len(annual_portfolio_returns)!=(y1-y0):raise ModelError('exactly one return per future year required')
    for ret in annual_portfolio_returns:
        _num(ret,'annual return',-1,5)
    amap={x['id']:x for x in p['accounts']}
    bal={a['id']:float(a['balance']) for a in p['accounts']}
    basis={a['id']:float(a['basis']) for a in p['accounts'] if a['kind']=='taxable'}
    cash_id=next(x['id'] for x in p['accounts'] if x['kind']=='cash')
    rows=[]; fail_years=[]; notices=[]
    for n,year in enumerate(range(y0+1,y1+1),start=1):
        factor=(1+p['assumptions']['inflation'])**n
        basis_by_rule=rule_basis(year,p['tax_policy']['future_bracket_inflation'])
        start=bal.copy(); growth={}
        r=max(-.999,annual_portfolio_returns[n-1])
        for aid,acc in amap.items():
            ret=p['assumptions']['cash_yield'] if acc['kind']=='cash' else r
            delta=bal[aid]*ret
            bal[aid]+=delta
            growth[aid]=delta
        cash_interest=growth[cash_id]
        wages_by_person=[]; wage_taxable=0.; pension=0.; ss=0.; contribs={}
        for m in p['members']:
            age=year-m['birth_year']
            wages=m['annual_wages_2026']*(1+m['wage_growth'])**n if age < m['retirement_age'] else 0.
            contrib=m.get('annual_pretax_401k_2026_real',0)*factor if wages else 0.
            max_limit=elective_deferral_limit(year,p['tax_policy']['future_bracket_inflation'])
            # Catch-up limits are NOT modeled; fail closed when above base elective limit.
            if contrib>min(wages,max_limit)+1e-7:
                limit_year=basis_by_rule['elective_deferral_limit']['base_year']
                raise ModelError(f'{year}: {m["id"]} pretax 401k contribution exceeds modeled wage/{limit_year}-base limit; catch-up unsupported')
            wages_by_person.append(wages)
            wage_taxable += wages-contrib
            bal[cash_id]+=wages-contrib
            if contrib:
                target=m['pretax_401k_target'];bal[target]+=contrib;contribs[target]=contribs.get(target,0)+contrib
            if age>=m['ss_claim_age']:
                ss+=m['ss_annual_2026_real_at_chosen_claim_age']*factor
            if age>=m.get('pension_start_age',65):
                pension+=m.get('annual_pension_2026_real',0)*factor
        bal[cash_id]+=ss+pension
        ev_in=ev_out=0.
        for e in p.get('events',[]):
            if e['year']!=year:continue
            v=e['amount']*(factor if e['dollars']=='2026_real' else 1)
            if e['kind']=='income':ev_in+=v
            else:ev_out+=v
        bal[cash_id]+=ev_in
        living=p['living_expenses_annual_real']*factor+ev_out
        rmd_detail=[]; rmd_total=0.; rmd_unmet=0.
        for aid,acc in amap.items():
            if acc['kind'] not in ('traditional_ira','traditional_401k'):continue
            owner=next(m for m in p['members'] if m['id']==acc['owner'])
            age=year-owner['birth_year']
            if age<rmd_age(owner['birth_year']):continue
            if age>120:raise ModelError('RMD table not defined above age 120')
            required=start[aid]/RMD_DENOMINATORS[age]
            taken=min(required,bal[aid])
            bal[aid]-=taken;bal[cash_id]+=taken
            rmd_unmet+=required-taken;rmd_total+=taken
            rmd_detail.append({'account':aid,'age':age,'previous_dec31_balance':start[aid],
                               'divisor':RMD_DENOMINATORS[age],'required':required,'taken':taken,
                               'unmet':required-taken})
        converted=0.; skipped=[]; conversion_transfers=[]
        for c in p.get('roth_conversions',[]):
            if c['year']!=year:continue
            src,dst=c['from'],c['to'];amount=c['amount_nominal']
            if bal[src]+1e-9<amount:
                skipped.append({'year':year,'from':src,'amount':amount,'reason':'insufficient source balance after RMD'})
                continue
            bal[src]-=amount;bal[dst]+=amount;converted+=amount
            conversion_transfers.append({'from':src,'to':dst,'amount':amount})
        # Iterative funding: tax depends on taxable dispositions and IRA withdrawals.
        # Each iteration restarts from the same pre-withdrawal balances/basis.
        pre_draw=bal.copy();pre_basis=basis.copy()
        tax_guess=_tax_calc(p,year,None,wages_by_person,wage_taxable,pension,ss,cash_interest,rmd_total,converted,0.,0.)[2]
        final=None
        for attempt in range(150):
            working=pre_draw.copy();wbasis=pre_basis.copy()
            required=max(0.,living+tax_guess-working[cash_id])
            draws={};gain=0.;ira_extra=0.;blocks=[]
            for aid in p['withdrawal_order']:
                if required<=1e-8:break
                kind=amap[aid]['kind']
                if kind=='cash':continue
                if kind in ('traditional_ira','traditional_401k','roth_ira'):
                    owner=next(m for m in p['members'] if m['id']==amap[aid]['owner'])
                    if year-owner['birth_year']<60:
                        blocks.append(f'{aid}: early distributions before 60 not modeled')
                        continue
                if working[aid]<=0:continue
                draw=min(working[aid],required)
                if kind=='taxable':
                    ratio=wbasis[aid]/working[aid] if working[aid]>0 else 0.
                    realized_basis=draw*ratio
                    gain+=max(0.,draw-realized_basis)
                    wbasis[aid]=max(0.,wbasis[aid]-realized_basis)
                if kind in ('traditional_ira','traditional_401k'):
                    ira_extra+=draw
                working[aid]-=draw;required-=draw;draws[aid]=draw
            fed,payroll,tax_new=_tax_calc(p,year,None,wages_by_person,wage_taxable,pension,ss,cash_interest,rmd_total,converted,ira_extra,gain)
            final=(working,wbasis,draws,gain,ira_extra,fed,payroll,tax_new,blocks)
            if abs(tax_new-tax_guess)<.00001:break
            tax_guess=tax_new
        else:raise ModelError(f'{year}: tax funding iteration failed to converge')
        working,wbasis,draws,gain,ira_extra,fed,payroll,tax_due,blocks=final
        proceeds=sum(draws.values())
        total_cash=pre_draw[cash_id]+proceeds
        tax_paid=min(tax_due,max(0.,total_cash))
        spending_paid=min(living,max(0.,total_cash-tax_paid))
        unpaid_tax=max(0.,tax_due-tax_paid)
        unmet_spend=max(0.,living-spending_paid)
        working[cash_id]=max(0.,total_cash-tax_paid-spending_paid)
        bal=working;basis=wbasis
        # Account for any remaining starting cash invested in taxable after funding only when explicitly elected.
        external=sum(wages_by_person)+ss+pension+ev_in
        paid_out=tax_paid+spending_paid
        start_total=sum(start.values());end_total=sum(bal.values())
        residual=end_total-(start_total+sum(growth.values())+external-paid_out)
        # Independent, account-by-account double-entry check: no transfer creates wealth.
        acct_delta={k:start[k]+growth[k]+contribs.get(k,0) for k in bal}
        acct_delta[cash_id]+=external-sum(contribs.values())-paid_out
        for entry in rmd_detail:
            acct_delta[entry['account']]-=entry['taken']
            acct_delta[cash_id]+=entry['taken']
        for entry in conversion_transfers:
            acct_delta[entry['from']]-=entry['amount']
            acct_delta[entry['to']]+=entry['amount']
        for acct,v in draws.items():
            acct_delta[acct]-=v
            acct_delta[cash_id]+=v
        account_residuals={k:bal[k]-acct_delta[k] for k in bal}
        if verify and (abs(residual)>.01 or any(abs(v)>.01 for v in account_residuals.values())):
            raise ModelError(f'{year}: double-entry conservation failure ${residual:,.5f}, {account_residuals}')
        # Funded status uses the same cent-rounded shortfalls as the exported
        # ledger: any displayed cent is a failure; sub-cent amounts rounding
        # to zero are ignored. Skipped conversions always fail, at any amount.
        if any(round(value,2)>0 for value in (unmet_spend,unpaid_tax,rmd_unmet)) or skipped:
            fail_years.append(year)
        if blocks: notices.append({'year':year,'blocks':blocks})
        rows.append({'year':year,'age_primary':year-p['members'][0]['birth_year'],
            'opening_total':round(start_total,2),
            'opening_accounts':{k:round(v,2) for k,v in start.items()},
            'market_return':r,'inflation_factor':round(factor,8),'investment_growth_total':round(sum(growth.values()),2),
            'growth_by_account':{k:round(v,2) for k,v in growth.items()},
            'wages_gross':round(sum(wages_by_person),2),'wages_taxable':round(wage_taxable,2),
            'pretax_contributions':round(sum(contribs.values()),2),
            'pretax_contribution_by_account':{k:round(v,2) for k,v in contribs.items()},
            'cash_account_id':cash_id,
            'social_security_gross':round(ss,2),'pension_gross':round(pension,2),
            'other_after_tax_income':round(ev_in,2),'living_expenses_due':round(living,2),
            'living_expenses_paid':round(spending_paid,2),'unmet_spending':round(unmet_spend,2),
            'rmd':rmd_detail,'rmd_total':round(rmd_total,2),'unmet_rmd':round(rmd_unmet,2),
            'roth_converted':round(converted,2),'conversion_transfers':conversion_transfers,'skipped_conversions':skipped,
            'extra_draws':{k:round(v,2) for k,v in draws.items()},
            'realized_ltcg':round(gain,2),'ira_extra_taxable':round(ira_extra,2),
            'rule_basis':{rule:{**entry,'multiplier':round(entry['multiplier'],8)} for rule,entry in basis_by_rule.items()},
            'tax':{k:(round(v,8) if k in ('rule_multiplier','niit_rate') else round(v,2) if isinstance(v,(float,int)) and not isinstance(v,bool)
                else [{j:(round(n,2) if isinstance(n,float) else n) for j,n in line.items()} for line in v] if k in ('ordinary_bracket_lines','capital_gain_rate_lines')
                else v) for k,v in fed.items()},
            'payroll_tax':{k:([round(x,2) for x in v] if isinstance(v,list) else round(v,2)) for k,v in payroll.items()},
            'tax_due_total':round(tax_due,2),'tax_paid':round(tax_paid,2),
            'unpaid_tax':round(unpaid_tax,2),'closing_total':round(end_total,2),
            'closing_total_real':round(end_total/factor,2),
            'closing_accounts':{k:round(v,2) for k,v in bal.items()},
            'taxable_basis_end':{k:round(v,2) for k,v in basis.items()},
            'reconciliation_residual':round(residual,6),
            'account_reconciliation_residuals':{k:round(v,6) for k,v in account_residuals.items()},
            'source_ids':['brackets_standard_senior','capital_gains','social_security_tax','payroll',
                          'payroll_2027','senior_enhanced','additional_medicare','niit',
                          '401k_elective_limit_2026','rmd_uniform_lifetime','rmd_birth_1959'],
            'account_flows':{aid:{'contribution':contribs.get(aid,0.),
                'required_distribution':sum(d['taken'] for d in rmd_detail if d['account']==aid),
                'roth_conversion_out':sum(t['amount'] for t in conversion_transfers if t['from']==aid),
                'roth_conversion_in':sum(t['amount'] for t in conversion_transfers if t['to']==aid),
                'optional_draw':draws.get(aid,0),
                'cash_external_inflow':external-sum(contribs.values()) if aid==cash_id else 0.,
                'cash_tax_and_spending_outflow':paid_out if aid==cash_id else 0.,
                'cash_received_rmd':rmd_total if aid==cash_id else 0.,
                'cash_received_draws':sum(draws.values()) if aid==cash_id else 0.
                } for aid in bal}})
    return {'rows':rows,'failed':bool(fail_years),'first_failure_year':min(fail_years) if fail_years else None,
            'notices':notices}


def _market_paths(p):
    a=p['assumptions']; rng=random.Random(a['seed']); years=p['end_year']-p['as_of_year']
    for _ in range(a['trials']):
        path=[]
        for _y in range(years):
            z1=rng.gauss(0,1);z2=rng.gauss(0,1)
            correl=a['equity_bond_correlation']
            ret_eq=a['equity_mean']+z1*a['equity_volatility']
            ret_bond=a['bond_mean']+a['bond_volatility']*(correl*z1+math.sqrt(max(0.,1-correl*correl))*z2)
            ret=a['equity_weight']*ret_eq+(1-a['equity_weight'])*ret_bond-a['annual_investment_fee']
            path.append(max(-.999,ret))
        yield path


def trace(p,index):
    """Replay one seeded Monte Carlo path with its complete annual ledger."""
    validate(p)
    if isinstance(index,bool) or not isinstance(index,int) or not 0<=index<p['assumptions']['trials']:
        raise ModelError('trace path index must be between zero and trials-1')
    path=next(path for i,path in enumerate(_market_paths(p)) if i==index)
    return {'engine_version':'2.2-auditable-restricted','trial_index':index,
            'input_sha256':hashlib.sha256(json.dumps(p,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
            'annual_returns':path,'path_ledger':run_path(p,path,verify=True)}


def wilson_interval(success,total,z=1.96):
    if total<=0:raise ModelError('total paths must be positive')
    p=success/total
    d=1+z*z/total
    mid=(p+z*z/(2*total))/d
    margin=z*math.sqrt(p*(1-p)/total+z*z/(4*total*total))/d
    return [round(max(0.,mid-margin),4),round(min(1.,mid+margin),4)]


def evidence_status(p):
    """Separate scope and provenance from arithmetic or professional approval."""
    return {
        'contract_version': '1.1',
        'model': 'restricted_research',
        'input': p.get('input_provenance', {}).get('mode', 'not_provided'),
        'input_independently_verified': False,
        'professional_review': 'not_recorded',
        'market_calibration': 'not_validated',
        'tax_rules': 'published_tax_year_rules_with_labeled_hypothetical_projection',
        'full_household_conclusion': False,
    }


def published_rules_scope():
    """Disclosure generated from the published-value registry, so it cannot go stale."""
    names={'income_tax_tables':'income tax tables','oasdi_wage_base':'OASDI wage base',
           'elective_deferral_limit':'base elective deferral limit'}
    spans=[]
    for rule,published in RULE_FAMILIES.items():
        years=sorted(published)
        spans.append(f'{names[rule]} {years[0]}' if len(years)==1 else f'{names[rule]} {years[0]}-{years[-1]}')
    return ('Published federal values by tax year ('+'; '.join(spans)+'); each later year indexes the latest '
            'published values at an ASSUMED rate and is labeled projected in rule_basis; not future legislation.')


def evaluate(p):
    validate(p)
    canonical=json.dumps(p,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
    plan_sha=hashlib.sha256(canonical).hexdigest()
    a=p['assumptions']; years=p['end_year']-p['as_of_year']
    median_return=a['equity_weight']*a['equity_mean']+(1-a['equity_weight'])*a['bond_mean']-a['annual_investment_fee']
    deterministic=run_path(p,[median_return]*years)
    successes=0; terminal=[]; target_success=0; annual_quantiles=[[] for _ in range(years)]; annual_funded=[0]*years
    path_manifest=[]
    for path_ix,path in enumerate(_market_paths(p)):
        result=run_path(p,path,verify=True)
        path_manifest.append({'path_index':path_ix,'funded':not result['failed'],
            'first_failure_year':result['first_failure_year'],
            'terminal_real':result['rows'][-1]['closing_total_real']})
        if not result['failed']:successes+=1
        if not result['failed'] and result['rows'][-1]['closing_total_real']>=p.get('terminal_target_2026_real',0):
            target_success+=1
        terminal.append(result['rows'][-1]['closing_total_real'])
        for ix,row in enumerate(result['rows']):
            annual_quantiles[ix].append(row['closing_total_real'])
            if (result['first_failure_year'] is None or row['year']<result['first_failure_year']):
                annual_funded[ix]+=1
    terminal.sort(); num=len(terminal)
    def quant(q):
        pos=(num-1)*q;lo=int(pos);hi=min(num-1,lo+1)
        return round(terminal[lo]*(1-(pos-lo))+terminal[hi]*(pos-lo),2)
    def q_from(values,q):
        values=sorted(values)
        pos=(len(values)-1)*q; lo=int(pos); hi=min(len(values)-1,lo+1)
        return round(values[lo]*(1-(pos-lo))+values[hi]*(pos-lo),2)
    bands=[{'year':p['as_of_year']+j+1,'p10':q_from(vals,.1),
            'p50':q_from(vals,.5),'p90':q_from(vals,.9),
            'paths_funded_to_date':annual_funded[j]} for j,vals in enumerate(annual_quantiles)]
    engine_source_hash=hashlib.sha256((Path(__file__).read_bytes()+
                           (Path(__file__).parent/'tax2026.py').read_bytes()+
                           (Path(__file__).parent/'tax_extensions.py').read_bytes())).hexdigest()
    return {
        'engine_version':'2.2-auditable-restricted','policy':RULESET,'input_sha256':plan_sha,
        'evidence_status':evidence_status(p),
        'input_provenance':p.get('input_provenance',{'mode':'not_provided','register':[]}),
        'engine_source_sha256':engine_source_hash,
        'scenario':p['name'],'opening_balance_status':p['opening_balance_status'],'tax_policy':p['tax_policy'],'year_range':[p['as_of_year']+1,p['end_year']],
        'success_paths':successes,'trials':a['trials'],
        'modeled_all_obligations_funded_fraction':round(successes/a['trials'],5),
        'mc_sampling_wilson95':wilson_interval(successes,a['trials']),
        'funded_and_target_fraction':round(target_success/a['trials'],5),
        'terminal_real_p10_p50_p90':[quant(.1),quant(.5),quant(.9)],
        'annual_real_percentiles':bands,'simulated_path_manifest':path_manifest,
        'deterministic_annual_ledger':deterministic,'rules_sources':{**SOURCES,'niit':NIIT_SOURCE},
        'rule_scope':[
            published_rules_scope(),
            '2026 federal progressive ordinary tax, simplified Social Security taxation, standard/senior deductions, long-term gains, FICA (2027 SSA wage base actual), and selected RMDs modeled.',
            '2026 NIIT on modeled cash interest and positive realized long-term gains; MAGI assumes no foreign exclusions; thresholds unindexed.',
            'No state tax, AMT, itemization, tax credits, IRMAA/ACA, inherited accounts, income limits, QCD or employer matching.',
            'Taxable sales use average proportional basis and assume all positive gains long-term; no harvested loss offsets or lot selection.',
            'Social Security benefit amount is supplied for the selected claiming age, with flat assumed COLA; no SSA earnings record, spouse or survivor optimization.',
            'No mortality, divorce, changes of filing status, half-year ages, early distribution penalties/exceptions, Social Security earnings test, or Roth qualification verification.',
            'All invested accounts share an annual rebalanced stock/bond blend; Gaussian joint returns are hypothetical, not empirically calibrated.',
            'All incomes, expenses, distributions and tax payments occur at year-end, with prior December 31 balances for RMD.',
            'Monte Carlo Wilson interval captures only finite-path sampling error, NOT input uncertainty, policy risk or model misspecification.'
        ]}


def main():
    ap=argparse.ArgumentParser(description='Auditable but scoped 2026 federal household retirement projection')
    ap.add_argument('command',choices=['validate','run','compare','trace'])
    ap.add_argument('--path-index',type=int,default=0,help='for trace: zero-based Monte Carlo path index')
    ap.add_argument('plans',nargs='+',type=Path)
    ap.add_argument('--output',type=Path)
    args=ap.parse_args()
    if (args.command=='compare' and len(args.plans)<2) or (args.command!='compare' and len(args.plans)!=1):
        ap.error('validate/run/trace require one scenario; compare requires 2+')
    try:
        plans=[json.loads(x.read_text(encoding='utf-8')) for x in args.plans]
        for plan in plans:validate(plan)
        if args.command=='validate':print('PASS v2 schema and restricted-rule gates');return
        if args.command=='trace':
            output=trace(plans[0],args.path_index)
        elif args.command=='compare':
            keys=[(p['as_of_year'],p['end_year'],p['assumptions']['seed'],p['assumptions']['trials']) for p in plans]
            if len(set(keys))!=1:raise ModelError('comparison must have same years, trials and random seed')
            output={'comparison':[evaluate(p) for p in plans]}
        else: output=evaluate(plans[0])
        if args.output:
            args.output.write_text(json.dumps(output,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
        print(f'PASS: {args.command}; reproducible audit result generated')
    except (OSError,ValueError,KeyError,TypeError,json.JSONDecodeError) as exc:
        ap.exit(2,f'ERROR: {exc}\n')

if __name__=='__main__':main()
