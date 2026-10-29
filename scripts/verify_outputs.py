#!/usr/bin/env python3
"""Independent output-only verifier. No audit_plan or tax2026 imports.

Checks accounting conservation, per-account journals, tax components, RMDs,
Monte Carlo aggregation, data fingerprint, and code fingerprint. It recomputes
each restricted federal worksheet step from constants retyped from
references/rules-provenance.md and, given the plan, re-derives the documented
income timing, funding order, basis and shortfall conventions.
Rule consistency is not a tax-law certification or market calibration.
"""
import argparse
import hashlib
import json
import random
from datetime import date
from math import isfinite, sqrt
from pathlib import Path

ENGINE_VERSION='2.2-auditable-restricted'
# 2026 reference values retyped from references/rules-provenance.md (snapshot
# 2026-10-28), deliberately not imported from tax2026.py. Later years apply the
# documented hypothetical indexing convention; they are not enacted law.
ORDINARY_2026={'single':((12400,.10),(50400,.12),(105700,.22),(201775,.24),(256225,.32),(640600,.35),(None,.37)),
               'mfj':((24800,.10),(100800,.12),(211400,.22),(403550,.24),(512450,.32),(768700,.35),(None,.37))}
STANDARD_2026={'single':16100.,'mfj':32200.}
AGE_65_ADDITION_2026={'single':2050.,'mfj':1650.}
GAIN_ZONES_2026={'single':(49450.,545500.),'mfj':(98900.,613700.)}
# Unindexed statutory amounts: Publication 915 bases, Schedule 1-A, Topic 560.
SS_BASES={'single':(25000.,34000.),'mfj':(32000.,44000.)}
SENIOR_YEARS=(2025,2028)
SENIOR_AMOUNT=6000.
SENIOR_PHASEOUT_RATE=.06
SENIOR_MAGI={'single':75000.,'mfj':150000.}
OASDI_RATE=.062
MEDICARE_RATE=.0145
EXTRA_MEDICARE_RATE=.009
EXTRA_MEDICARE_WAGES={'single':200000.,'mfj':250000.}
OASDI_WAGE_BASE={2026:184500.,2027:192300.}
ELECTIVE_DEFERRAL_2026=24500.
# Uniform Lifetime Table, 26 CFR 1.401(a)(9)-9(c) as amended by T.D. 9930
# (85 FR 72472), distribution years from 2022; row values re-checked 2026-10-29
# (references/source-check-2026-10-29.md). Age 120 means 120 and over.
UNIFORM_LIFETIME={72:27.4,73:26.5,74:25.5,75:24.6,76:23.7,77:22.9,78:22.0,79:21.1,
    80:20.2,81:19.4,82:18.5,83:17.7,84:16.8,85:16.0,86:15.2,87:14.4,88:13.7,89:12.9,
    90:12.2,91:11.5,92:10.8,93:10.1,94:9.5,95:8.9,96:8.4,97:7.8,98:7.3,99:6.8,
    100:6.4,101:6.0,102:5.6,103:5.2,104:4.9,105:4.6,106:4.3,107:4.1,108:3.9,109:3.7,
    110:3.5,111:3.4,112:3.3,113:3.1,114:3.0,115:2.9,116:2.8,117:2.7,118:2.5,119:2.3,120:2.0}
PRETAX_KINDS=('traditional_ira','traditional_401k')
RETIREMENT_KINDS=PRETAX_KINDS+('roth_ira',)
FLOW_KEYS={'contribution','required_distribution','roth_conversion_out','roth_conversion_in',
           'optional_draw','cash_external_inflow','cash_tax_and_spending_outflow',
           'cash_received_rmd','cash_received_draws'}
CASH_ONLY_FLOWS=('cash_external_inflow','cash_tax_and_spending_outflow','cash_received_rmd','cash_received_draws')

class VerifyFailure(ValueError):
    pass

def close(a,b,desc,tol=.05):
    if (type(a) not in (int,float) or type(b) not in (int,float)
            or not isfinite(a) or not isfinite(b) or not abs(a-b)<=tol):
        raise VerifyFailure(f'{desc}: got {a} expected {b} (tol {tol})')

def nonnegative(value,desc):
    if type(value) not in (int,float) or not isfinite(value) or value<0:
        raise VerifyFailure(f'{desc}: expected a finite nonnegative amount, got {value}')

def quant(vals,q):
    vals=sorted(vals)
    pos=(len(vals)-1)*q
    lo=int(pos)
    hi=min(lo+1,len(vals)-1)
    return vals[lo]*(1-pos+lo)+vals[hi]*(pos-lo)

def numeric_vector(value,length,description):
    if (not isinstance(value,list) or len(value)!=length or
        any(type(v) not in (int,float) or not isfinite(v) for v in value)):
        raise VerifyFailure(f'{description}: expected {length} finite numeric entries')

def plan_sha256(plan):
    return hashlib.sha256(json.dumps(plan,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def bracket_portions(low_income,high_income,status,multiplier):
    """Portion of (low_income, high_income] in each retyped ordinary bracket."""
    portions=[]
    low=0.
    for ceiling,rate in ORDINARY_2026[status]:
        high=None if ceiling is None else ceiling*multiplier
        top=high_income if high is None else min(high_income,high)
        portions.append((low,high,rate,max(0.,top-max(low_income,low))))
        if high is None:
            break
        low=high
    return portions

def taxable_benefits(benefits,provisional,status):
    """Publication 915 Worksheet 1 in the simplified form registered for this model."""
    first,second=SS_BASES[status]
    if provisional<=first:
        return 0.
    if provisional<=second:
        return min(.5*benefits,.5*(provisional-first))
    return min(.85*benefits,.85*(provisional-second)+min(.5*benefits,.5*(second-first)))

def oasdi_wage_base(year,indexing):
    """Published 2026/2027 caps; later caps index the 2027 cap hypothetically."""
    if year in OASDI_WAGE_BASE:
        return OASDI_WAGE_BASE[year]
    return OASDI_WAGE_BASE[2027]*(1+indexing)**(year-2027)

def rmd_start_age(birth_year):
    # Register entry rmd_birth_1959: age 73 for 1951-1959 births, 75 from 1960.
    return 73 if birth_year<=1959 else 75

def scheduled_income(plan,year):
    """Documented year-end timing from the plan: whole-year ages, 2026-real escalation."""
    n=year-plan['as_of_year']
    factor=(1+plan['assumptions']['inflation'])**n
    wages=[]
    deferrals={}
    benefits=pension=0.
    for member in plan['members']:
        age=year-member['birth_year']
        pay=member['annual_wages_2026']*(1+member['wage_growth'])**n if age<member['retirement_age'] else 0.
        wages.append(pay)
        deferral=member.get('annual_pretax_401k_2026_real',0)*factor if pay else 0.
        if deferral:
            target=member['pretax_401k_target']
            deferrals[target]=deferrals.get(target,0.)+deferral
        if age>=member['ss_claim_age']:
            benefits+=member['ss_annual_2026_real_at_chosen_claim_age']*factor
        if member.get('annual_pension_2026_real',0):
            if 'pension_start_age' not in member:
                raise VerifyFailure(f'{member["id"]}: plan pension requires an explicit pension_start_age')
            if age>=member['pension_start_age']:
                pension+=member['annual_pension_2026_real']*factor
    inflows=outflows=0.
    for event in plan.get('events',[]):
        if event['year']!=year:
            continue
        amount=event['amount']*(factor if event['dollars']=='2026_real' else 1)
        if event['kind']=='income':
            inflows+=amount
        else:
            outflows+=amount
    return {'wages':wages,'deferrals':deferrals,'benefits':benefits,'pension':pension,
            'inflows':inflows,'living':plan['living_expenses_annual_real']*factor+outflows}

def deterministic_return(plan):
    a=plan['assumptions']
    return max(-.999,a['equity_weight']*a['equity_mean']+(1-a['equity_weight'])*a['bond_mean']-a['annual_investment_fee'])

def regenerated_returns(plan,index):
    """Documented generator (audit-methodology.md): one seeded stream; each path
    and year draws z1 then z2; correlated stock/bond blend less fee, floored."""
    a=plan['assumptions']
    stream=random.Random(a['seed'])
    rho=a['equity_bond_correlation']
    years=plan['end_year']-plan['as_of_year']
    for _path in range(index+1):
        returns=[]
        for _year in range(years):
            z1=stream.gauss(0,1)
            z2=stream.gauss(0,1)
            equity=a['equity_mean']+a['equity_volatility']*z1
            bond=a['bond_mean']+a['bond_volatility']*(rho*z1+sqrt(max(0.,1-rho*rho))*z2)
            returns.append(max(-.999,a['equity_weight']*equity+(1-a['equity_weight'])*bond-a['annual_investment_fee']))
    return returns

def verify(x,plan=None,engine_dir=None):
    """Public gate: malformed outputs are failures, never uncaught schema errors."""
    try:
        if not isinstance(x,dict):
            raise VerifyFailure('result must be an object')
        return _verify(x,plan,engine_dir)
    except VerifyFailure:
        raise
    except (KeyError,TypeError,AttributeError,IndexError,ZeroDivisionError,ValueError,OverflowError) as exc:
        raise VerifyFailure(f'malformed output: {exc}') from exc


def verify_trace(trace,plan,result=None):
    """Check one `audit_plan.py trace` path against the plan, never the engine."""
    try:
        if not isinstance(trace,dict) or not isinstance(plan,dict):
            raise VerifyFailure('trace and plan must be objects')
        return _verify_trace(trace,plan,result)
    except VerifyFailure:
        raise
    except (KeyError,TypeError,AttributeError,IndexError,ZeroDivisionError,ValueError,OverflowError) as exc:
        raise VerifyFailure(f'malformed trace: {exc}') from exc


def verify_provenance(provenance):
    """Check output metadata independently, even when no input plan is supplied.

    This checks register syntax, not source documents or pointer resolution.
    A supplied plan is still needed to compare the actual provenance values.
    """
    if not isinstance(provenance,dict) or set(provenance)!={'mode','register'}:
        raise VerifyFailure('input_provenance must contain mode and register')
    mode=provenance['mode']
    if mode not in ('not_provided','fictional_demo','unverified_user_data','documented_verified'):
        raise VerifyFailure('unsupported input_provenance mode')
    register=provenance['register']
    if not isinstance(register,list):
        raise VerifyFailure('input_provenance register must be a list')
    if mode=='not_provided' and register:
        raise VerifyFailure('not_provided provenance must have an empty register')
    if mode=='documented_verified' and not register:
        raise VerifyFailure('documented provenance requires a register')
    for item in register:
        if not isinstance(item,dict) or set(item)!={'json_pointer','evidence_id','source_type','as_of_date','confidence'}:
            raise VerifyFailure('invalid input_provenance register entry')
        if not isinstance(item['json_pointer'],str) or not item['json_pointer'].startswith('/'):
            raise VerifyFailure('input_provenance entry requires JSON Pointer')
        if not isinstance(item['evidence_id'],str) or not item['evidence_id']:
            raise VerifyFailure('input_provenance entry requires evidence_id')
        if item['source_type'] not in ('user_statement','statement','tax_form','ssa_statement','estimate','fictional_fixture'):
            raise VerifyFailure('unsupported input_provenance source_type')
        if item['confidence'] not in ('documented','supplied','assumed'):
            raise VerifyFailure('unsupported input_provenance confidence')
        dt=item['as_of_date']
        if not isinstance(dt,str) or len(dt)!=10:
            raise VerifyFailure('input_provenance date must be YYYY-MM-DD')
        try:
            date.fromisoformat(dt)
        except ValueError as exc:
            raise VerifyFailure('invalid input_provenance date') from exc


def _verify(x,plan=None,engine_dir=None):
    if x.get('engine_version')!=ENGINE_VERSION:
        raise VerifyFailure('unexpected or unaudited engine')
    # Added by M0; older v2.2 outputs without metadata remain arithmetically
    # verifiable, but no evidence claims may be invented or upgraded.
    if 'input_provenance' in x:
        verify_provenance(x['input_provenance'])
    if 'evidence_status' in x:
        expected={'contract_version':'1.0','model':'restricted_research',
            'input':x['input_provenance']['mode'],'input_independently_verified':False,
            'professional_review':'not_recorded','market_calibration':'not_validated',
            'tax_rules':'2026_reference_with_hypothetical_future_indexing',
            'full_household_conclusion':False}
        if (x['evidence_status']!=expected or
            type(x['evidence_status']['input_independently_verified']) is not bool or
            type(x['evidence_status']['full_household_conclusion']) is not bool):
            raise VerifyFailure('unsupported evidence or professional-approval claim')
    if plan is not None:
        for key,expected in [('scenario',plan['name']),
                             ('opening_balance_status',plan['opening_balance_status']),
                             ('input_provenance',plan.get('input_provenance',{'mode':'not_provided','register':[]}))]:
            if (key=='input_provenance' and 'input_provenance' not in x
                    and 'evidence_status' not in x):
                continue  # Legacy v2.2: no provenance or evidence claims to compare.
            if x[key]!=expected:
                raise VerifyFailure(f'{key} mismatched to plan')
    count=x['trials']
    if type(count) is not int or count<=0:
        raise VerifyFailure('MC trial count must be a positive integer')
    if plan is not None and count!=plan['assumptions']['trials']:
        raise VerifyFailure('MC trial count mismatched to plan')
    first_year,last_year=x['year_range']
    if type(first_year) is not int or type(last_year) is not int or first_year>last_year:
        raise VerifyFailure('invalid projection year range')
    if plan is not None and [first_year,last_year]!=[plan['as_of_year']+1,plan['end_year']]:
        raise VerifyFailure('year range mismatched to plan')
    if plan is not None and x['tax_policy']!=plan['tax_policy']:
        raise VerifyFailure('output tax policy mismatched to plan')
    if x['tax_policy']['filing_status'] not in ('single','mfj'):
        raise VerifyFailure('unsupported output filing status')
    manifest=x['simulated_path_manifest']
    if count!=len(manifest):
        raise VerifyFailure('missing Monte Carlo paths')
    for index,z in enumerate(manifest):
        if type(z['path_index']) is not int or z['path_index']!=index:
            raise VerifyFailure('misordered MC paths')
        if type(z['funded']) is not bool:
            raise VerifyFailure('MC funded status must be boolean')
        failure=z['first_failure_year']
        if z['funded']:
            if failure is not None:
                raise VerifyFailure('funded MC path must have no failure year')
        elif type(failure) is not int or not first_year<=failure<=last_year:
            raise VerifyFailure('unfunded MC path needs a failure year within the horizon')
    successes=sum(z['funded'] for z in manifest)
    if type(x['success_paths']) is not int or x['success_paths']!=successes:
        raise VerifyFailure('MC funded path count wrong')
    close(x['modeled_all_obligations_funded_fraction'],successes/count,'MC success fraction',.00001)
    interval=x['mc_sampling_wilson95']
    numeric_vector(interval,2,'Wilson interval')
    if not 0<=interval[0]<=interval[1]<=1:
        raise VerifyFailure('Wilson interval must be ordered within [0,1]')
    # Solve the binomial score interval independently from the saved path counts.
    zscore=1.96
    denominator=count+zscore*zscore
    center=(successes+zscore*zscore/2)/denominator
    radius=zscore*sqrt(successes*(count-successes)/count+zscore*zscore/4)/denominator
    for actual,expected in zip(interval,(max(0.,center-radius),min(1.,center+radius))):
        close(actual,round(expected,4),'Wilson interval endpoint',.00005)
    finals=[z['terminal_real'] for z in manifest]
    numeric_vector(finals,count,'MC terminal balances')
    numeric_vector(x['terminal_real_p10_p50_p90'],3,'terminal percentiles')
    for q,n in zip((.1,.5,.9),x['terminal_real_p10_p50_p90']):
        close(n,quant(finals,q),f'MC quantile {q}',.02)
    annual=x['annual_real_percentiles']
    if not isinstance(annual,list) or len(annual)!=last_year-first_year+1:
        raise VerifyFailure('annual MC percentiles must cover the projection horizon')
    for index,band in enumerate(annual):
        year=first_year+index
        if type(band['year']) is not int or band['year']!=year:
            raise VerifyFailure('annual MC years must be consecutive and ordered')
        values=[band[key] for key in ('p10','p50','p90')]
        numeric_vector(values,3,'annual MC percentiles')
        if not values[0]<=values[1]<=values[2]:
            raise VerifyFailure('annual MC percentiles must be ordered')
        funded=sum(z['first_failure_year'] is None or z['first_failure_year']>year
                   for z in manifest)
        if type(band['paths_funded_to_date']) is not int or band['paths_funded_to_date']!=funded:
            raise VerifyFailure(f'{year}: annual MC funded count disagrees with manifest')
        if year==last_year:
            for value,q in zip(values,(.1,.5,.9)):
                close(value,quant(finals,q),'annual MC terminal percentile',.02)
    ledger=x['deterministic_annual_ledger']['rows']
    checks,max_residual=_verify_ledger(x['deterministic_annual_ledger'],x['tax_policy'],
                                       first_year,last_year,plan)
    if plan is not None:
        if x['input_sha256']!=plan_sha256(plan):
            raise VerifyFailure('input SHA mismatch')
        if len(ledger)!=plan['end_year']-plan['as_of_year']:
            raise VerifyFailure('year count mismatched to plan')
        threshold=plan.get('terminal_target_2026_real',0)
        both=sum(z['funded'] and z['terminal_real']>=threshold for z in manifest)
        close(x['funded_and_target_fraction'],both/count,'terminal target fraction',.00001)
    if engine_dir is not None:
        actual=hashlib.sha256((engine_dir/'audit_plan.py').read_bytes()+
                              (engine_dir/'tax2026.py').read_bytes()+(engine_dir/'tax_extensions.py').read_bytes()).hexdigest()
        if x['engine_source_sha256']!=actual:
            raise VerifyFailure('engine source SHA mismatch')
    return {'passed':True,'annual_rows':len(ledger),'mc_paths':count,
            'assertions_checked':checks,'max_account_residual_dollars':round(max_residual,6),
            'verified_input_hash':plan is not None,'verified_engine_hash':engine_dir is not None,
            'verified_plan_conventions':plan is not None,
            'validation_level':'output_arithmetic_and_restricted_rule_steps',
            'limitations':['Intermediate annual percentiles and untraced path ledgers require engine replay.',
                           'Rule constants are retyped from the dated source register; statutory currency and applicability are not re-verified.',
                           'Without the plan, income timing, funding order and RMD activation are not checked.',
                           'Supplied benefit amounts and input documents are not independently sourced.',
                           'Not a complete independent tax-return or input-evidence verification.']}


def _verify_trace(trace,plan,result):
    if set(trace)!={'engine_version','trial_index','input_sha256','annual_returns','path_ledger'}:
        raise VerifyFailure('trace fields changed')
    if trace['engine_version']!=ENGINE_VERSION:
        raise VerifyFailure('unexpected or unaudited engine')
    index=trace['trial_index']
    if type(index) is not int or not 0<=index<plan['assumptions']['trials']:
        raise VerifyFailure('trace path index outside the plan trial count')
    if trace['input_sha256']!=plan_sha256(plan):
        raise VerifyFailure('input SHA mismatch')
    first_year,last_year=plan['as_of_year']+1,plan['end_year']
    returns=trace['annual_returns']
    numeric_vector(returns,last_year-first_year+1,'trace annual returns')
    for year,actual,expected in zip(range(first_year,last_year+1),returns,regenerated_returns(plan,index)):
        close(actual,expected,f'{year}: trace return regenerated from seed and path index',1e-12)
    checks,max_residual=_verify_ledger(trace['path_ledger'],plan['tax_policy'],
                                       first_year,last_year,plan,returns)
    if result is not None:
        verify(result,plan)
        entry=result['simulated_path_manifest'][index]
        ledger=trace['path_ledger']
        if (entry['funded']!=(not ledger['failed']) or
                entry['first_failure_year']!=ledger['first_failure_year'] or
                entry['terminal_real']!=ledger['rows'][-1]['closing_total_real']):
            raise VerifyFailure('trace disagrees with its Monte Carlo manifest entry')
        checks+=3
    return {'passed':True,'trial_index':index,'annual_rows':len(returns),
            'assertions_checked':checks,'max_account_residual_dollars':round(max_residual,6),
            'returns_regenerated':True,'manifest_entry_checked':result is not None,
            'validation_level':'traced_path_arithmetic_and_restricted_rule_steps',
            'limitations':['Returns follow the documented hypothetical generator; no market calibration.',
                           'Only this path is checked; other paths and intermediate percentiles require replay.',
                           'Rule constants are retyped from the dated source register; not a tax return or professional review.']}


def _notice_blocks(notices,first_year,last_year):
    """Year -> blocked-account messages; at most one non-empty notice per year."""
    if not isinstance(notices,list):
        raise VerifyFailure('notices must be a list')
    blocks={}
    for notice in notices:
        if not isinstance(notice,dict) or set(notice)!={'year','blocks'}:
            raise VerifyFailure('invalid funding notice')
        year=notice['year']
        if type(year) is not int or not first_year<=year<=last_year or year in blocks:
            raise VerifyFailure('funding notices need unique years within the horizon')
        messages=notice['blocks']
        if not isinstance(messages,list) or not messages or not all(isinstance(m,str) and m for m in messages):
            raise VerifyFailure(f'{year}: funding notice needs nonempty messages')
        blocks[year]=messages
    return blocks


def _verify_ledger(summary,policy,first_year,last_year,plan=None,returns=None):
    """Annual checks shared by the deterministic ledger and traced paths.

    returns=None selects the deterministic plan-mean path; otherwise the
    traced path's annual returns, already regenerated by the caller.
    """
    if not isinstance(summary,dict) or set(summary)!={'rows','failed','first_failure_year','notices'}:
        raise VerifyFailure('annual ledger fields changed')
    ledger=summary['rows']
    status=policy['filing_status']
    label='deterministic' if returns is None else 'traced path'
    checks=0
    max_residual=0
    def expect(actual,expected,desc,tol):
        nonlocal checks
        close(actual,expected,desc,tol)
        checks+=1
    if not ledger:
        raise VerifyFailure('empty ledger')
    if plan is not None:
        previous_accounts={a['id']:a['balance'] for a in plan['accounts']}
        previous_total=sum(previous_accounts.values())
        previous_basis={a['id']:a['basis'] for a in plan['accounts'] if a['kind']=='taxable'}
    else:
        previous_accounts=ledger[0]['opening_accounts']
        previous_total=ledger[0]['opening_total']
        previous_basis=None
    if len(ledger)!=last_year-first_year+1:
        raise VerifyFailure('year count mismatched to range')
    notices=_notice_blocks(summary['notices'],first_year,last_year)
    failure_years=[]
    for index,row in enumerate(ledger):
        y=row['year']
        if type(y) is not int or y!=first_year+index:
            raise VerifyFailure('ledger years must be consecutive and ordered')
        numeric_fields=('age_primary','market_return','inflation_factor','opening_total',
            'investment_growth_total','wages_gross','wages_taxable','pretax_contributions',
            'social_security_gross','pension_gross','other_after_tax_income','living_expenses_due',
            'living_expenses_paid','rmd_total','roth_converted',
            'realized_ltcg','ira_extra_taxable','tax_due_total','tax_paid',
            'closing_total','closing_total_real','reconciliation_residual')
        numeric_vector([row[key] for key in numeric_fields],len(numeric_fields),'annual numeric fields')
        for field in ('rmd','conversion_transfers','skipped_conversions','source_ids'):
            if not isinstance(row[field],list):
                raise VerifyFailure(f'{y}: {field} must be a list')
        for field in ('opening_accounts','closing_accounts','growth_by_account','extra_draws',
                      'taxable_basis_end','pretax_contribution_by_account','account_reconciliation_residuals'):
            if not isinstance(row[field],dict):
                raise VerifyFailure(f'{y}: {field} must be an object')
            numeric_vector(list(row[field].values()),len(row[field]),field)
        for flows in row['account_flows'].values():
            numeric_vector(list(flows.values()),len(flows),'account flows')
        shortfalls=[row[field] for field in ('unmet_spending','unpaid_tax','unmet_rmd')]
        if any(type(value) not in (int,float) or not isfinite(value) or value<0
               or value!=round(value,2) for value in shortfalls):
            raise VerifyFailure(f'{y}: shortfalls must be nonnegative whole-cent amounts')
        if any(value>0 for value in shortfalls) or row['skipped_conversions']:
            failure_years.append(y)
        for field in ('opening_accounts','closing_accounts','growth_by_account',
                      'account_flows','account_reconciliation_residuals'):
            if set(row[field])!=set(previous_accounts):
                raise VerifyFailure(f'{y}: {field} account IDs changed')
        for aid,balance in previous_accounts.items():
            close(row['opening_accounts'][aid],balance,f'{y}: opening continuity {aid}',.01)
        close(row['opening_total'],previous_total,f'{y}: opening total continuity',.01)
        # Each account and its independently rounded total can differ by half
        # a cent per account; do not let that hide material missing balances.
        total_tol=max(.01,.005*(len(previous_accounts)+1)+1e-8)
        close(row['opening_total'],sum(row['opening_accounts'].values()),f'{y}: opening account sum',total_tol)
        close(row['closing_total'],sum(row['closing_accounts'].values()),f'{y}: closing account sum',total_tol)
        checks+=9+len(previous_accounts)
        external=row['wages_gross']+row['social_security_gross']+row['pension_gross']+row['other_after_tax_income']
        expected=row['opening_total']+row['investment_growth_total']+external-row['living_expenses_paid']-row['tax_paid']
        close(row['closing_total'],expected,f'{y}: whole-household conservation')
        factor=row['inflation_factor']
        if type(factor) not in (int,float) or not isfinite(factor) or factor<1:
            raise VerifyFailure(f'{y}: invalid inflation factor')
        if plan is not None:
            factor=(1+plan['assumptions']['inflation'])**(y-plan['as_of_year'])
            close(row['inflation_factor'],factor,f'{y}: inflation factor mismatched to plan',.0000000051)
            real_tolerance=.01
        else:
            # Exported factors have eight decimals, so allow their rounding
            # uncertainty when no plan is available to reconstruct the factor.
            real_tolerance=.01+abs(row['closing_total'])*.0000000051/(factor*max(factor-.0000000051,1e-12))
        close(row['closing_total_real'],row['closing_total']/factor,f'{y}: real closing balance',real_tolerance)
        close(row['reconciliation_residual'],0,f'{y}: output residual',.01)
        for field in ('ordinary_bracket_lines','capital_gain_rate_lines'):
            for band,line in enumerate(row['tax'][field]):
                close(line['tax'],line['taxable']*line['rate'],f'{y}: {field} {band} multiplication',.01)
                checks+=1
        close(row['tax']['ordinary_tax'],sum(z['tax'] for z in row['tax']['ordinary_bracket_lines']),f'{y}: ordinary brackets')
        close(row['tax']['ordinary_taxable'],sum(z['taxable'] for z in row['tax']['ordinary_bracket_lines']),f'{y}: ordinary taxable coverage')
        close(row['tax']['capital_gains_tax'],sum(z['tax'] for z in row['tax']['capital_gain_rate_lines']),f'{y}: gains brackets')
        close(row['tax']['federal_income_tax'],row['tax']['ordinary_tax']+row['tax']['capital_gains_tax'],f'{y}: federal tax')
        pf=row['payroll_tax']
        close(pf['total'],pf['social_security_tax']+pf['medicare_tax']+pf['additional_medicare_tax'],f'{y}: payroll tax')
        # Independent recomputation of statutory reference NIIT; no tax engine import.
        tax=row['tax']
        cash_interest=row['growth_by_account'][row['cash_account_id']]
        close(row['wages_taxable'],row['wages_gross']-row['pretax_contributions'],f'{y}: taxable wages')
        ordinary=(row['wages_taxable']+row['pension_gross']+row['rmd_total']+
                  row['ira_extra_taxable']+row['roth_converted']+cash_interest+
                  tax['taxable_social_security'])
        agi=ordinary+row['realized_ltcg']
        close(tax['gross_ordinary'],ordinary,f'{y}: ordinary income components')
        close(tax['adjusted_gross_income'],agi,f'{y}: AGI income components')
        if tax['niit_rate'] != .038:
            raise VerifyFailure(f'{y}: NIIT rate changed')
        if tax['niit_threshold'] != (250000. if status=='mfj' else 200000.):
            raise VerifyFailure(f'{y}: NIIT threshold changed')
        close(tax['niit_magi_assumed_equal_agi'],agi,f'{y}: NIIT MAGI income components')
        close(tax['niit_net_investment_income'],row['realized_ltcg']+row['growth_by_account'][row['cash_account_id']],f'{y}: NIIT income')
        close(tax['niit_tax_base'],min(tax['niit_net_investment_income'],max(0.,tax['adjusted_gross_income']-tax['niit_threshold'])),f'{y}: NIIT base')
        close(tax['niit_due'],tax['niit_tax_base']*.038,f'{y}: NIIT due')
        close(tax['total_federal_income_and_niit'],tax['federal_income_tax']+tax['niit_due'],f'{y}: federal/NIIT')
        close(row['tax_due_total'],tax['total_federal_income_and_niit']+pf['total'],f'{y}: total due')
        close(row['tax_paid']+row['unpaid_tax'],row['tax_due_total'],f'{y}: unpaid tax')
        close(row['living_expenses_paid']+row['unmet_spending'],row['living_expenses_due'],f'{y}: unmet living')
        close(row['tax']['long_term_gain_taxable'],sum(z['taxable'] for z in row['tax']['capital_gain_rate_lines']),f'{y}: LTCG bands')
        for item in row['rmd']:
            if item['account'] not in row['opening_accounts']:
                raise VerifyFailure(f'{y}: unknown RMD account')
            close(item['previous_dec31_balance'],row['opening_accounts'][item['account']],f'{y}: RMD opening balance',.01)
            close(item['required'],item['previous_dec31_balance']/item['divisor'],f'{y}: RMD {item["account"]}')
            close(item['taken']+item['unmet'],item['required'],f'{y}: RMD fulfillment')
        close(row['rmd_total'],round(sum(item['taken'] for item in row['rmd']),2),f'{y}: RMD taken aggregate',1e-8)
        close(row['unmet_rmd'],round(sum(item['unmet'] for item in row['rmd']),2),f'{y}: RMD unmet aggregate',1e-8)
        conversion_in=dict.fromkeys(previous_accounts,0.)
        conversion_out=dict.fromkeys(previous_accounts,0.)
        converted=0.
        for transfer in row['conversion_transfers']:
            source,target,amount=transfer['from'],transfer['to'],transfer['amount']
            if source not in previous_accounts or target not in previous_accounts or source==target:
                raise VerifyFailure(f'{y}: invalid conversion transfer accounts')
            if type(amount) not in (int,float) or not isfinite(amount) or amount<0:
                raise VerifyFailure(f'{y}: invalid conversion transfer amount')
            conversion_out[source]+=amount
            conversion_in[target]+=amount
            converted+=amount
        close(row['roth_converted'],round(converted,2),f'{y}: conversion taxable aggregate',1e-8)
        for aid,flows in row['account_flows'].items():
            close(flows['roth_conversion_in'],conversion_in[aid],f'{y}: conversion inflow {aid}',1e-7)
            close(flows['roth_conversion_out'],conversion_out[aid],f'{y}: conversion outflow {aid}',1e-7)
            expected=(row['opening_accounts'][aid]+row['growth_by_account'][aid]+flows['contribution']
                +flows['roth_conversion_in']+flows['cash_external_inflow']+flows['cash_received_rmd']
                +flows['cash_received_draws']-flows['required_distribution']-flows['roth_conversion_out']
                -flows['optional_draw']-flows['cash_tax_and_spending_outflow'])
            close(row['closing_accounts'][aid],expected,f'{y}: account {aid}')
            close(row['account_reconciliation_residuals'][aid],0,f'{y}: {aid} residual',.01)
            checks+=4
            max_residual=max(max_residual,abs(row['closing_accounts'][aid]-expected))
        checks+=27+(plan is not None)+len(row['rmd'])*3
        _journal_checks(row,previous_basis,expect)
        _rule_checks(row,policy,plan,expect)
        if plan is not None:
            path_return=deterministic_return(plan) if returns is None else returns[index]
            _plan_checks(row,plan,path_return,notices.get(y,[]),expect)
        previous_accounts=row['closing_accounts']
        previous_total=row['closing_total']
        previous_basis=row['taxable_basis_end']
    if type(summary['failed']) is not bool or summary['failed']!=bool(failure_years):
        raise VerifyFailure(f'{label} failed summary disagrees with annual rows')
    first_failure=failure_years[0] if failure_years else None
    if summary['first_failure_year']!=first_failure:
        raise VerifyFailure(f'{label} first failure year disagrees with annual rows')
    checks+=2
    return checks,max_residual


def _journal_checks(row,previous_basis,expect):
    """Output-only links between row totals, account journals and balances."""
    y=row['year']
    accounts=row['account_flows']
    cash_id=row['cash_account_id']
    if cash_id not in accounts:
        raise VerifyFailure(f'{y}: cash account journal missing')
    for aid,flows in accounts.items():
        if set(flows)!=FLOW_KEYS:
            raise VerifyFailure(f'{y}: {aid} account journal fields changed')
        for key,value in flows.items():
            nonnegative(value,f'{y}: {aid} {key}')
    for field in ('opening_accounts','closing_accounts','extra_draws','pretax_contribution_by_account','taxable_basis_end'):
        for aid,value in row[field].items():
            if aid not in accounts:
                raise VerifyFailure(f'{y}: {field} names unknown account {aid}')
            nonnegative(value,f'{y}: {field} {aid}')
    for field in ('wages_gross','wages_taxable','pretax_contributions','social_security_gross','pension_gross',
                  'other_after_tax_income','living_expenses_due','living_expenses_paid','rmd_total',
                  'roth_converted','realized_ltcg','ira_extra_taxable','tax_due_total','tax_paid'):
        nonnegative(row[field],f'{y}: {field}')
    taken={}
    for item in row['rmd']:
        for key in ('previous_dec31_balance','required','taken','unmet','divisor'):
            nonnegative(item[key],f'{y}: RMD {key}')
        if item['account'] in taken:
            raise VerifyFailure(f'{y}: duplicate RMD record for {item["account"]}')
        if type(item['age']) is not int or min(item['age'],120) not in UNIFORM_LIFETIME:
            raise VerifyFailure(f'{y}: RMD age {item["age"]} is outside the Uniform Lifetime Table')
        expect(item['divisor'],UNIFORM_LIFETIME[min(item['age'],120)],
               f'{y}: RMD divisor for age {item["age"]} differs from the Uniform Lifetime Table',0)
        taken[item['account']]=item['taken']
    drawn=0.
    for aid,flows in accounts.items():
        expect(flows['contribution'],row['pretax_contribution_by_account'].get(aid,0.),f'{y}: {aid} deferral journal',.0051)
        expect(flows['optional_draw'],row['extra_draws'].get(aid,0.),f'{y}: {aid} draw journal',.0051)
        expect(flows['required_distribution'],taken.get(aid,0.),f'{y}: {aid} RMD journal',1e-6+1e-12*taken.get(aid,0.))
        drawn+=flows['optional_draw']
        if aid!=cash_id and any(flows[key] for key in CASH_ONLY_FLOWS):
            raise VerifyFailure(f'{y}: {aid} carries cash-account receipts or payments')
    cash=accounts[cash_id]
    if any(cash[key] for key in ('contribution','required_distribution','optional_draw','roth_conversion_in','roth_conversion_out')):
        raise VerifyFailure(f'{y}: cash account cannot receive deferrals, RMDs, draws or conversions')
    expect(cash['cash_received_rmd'],sum(taken.values()),f'{y}: cash RMD receipts',1e-6+1e-12*cash['cash_received_rmd'])
    expect(cash['cash_received_draws'],drawn,f'{y}: cash draw receipts',1e-6+1e-12*drawn)
    expect(cash['cash_external_inflow'],row['wages_gross']+row['social_security_gross']+row['pension_gross']
           +row['other_after_tax_income']-row['pretax_contributions'],f'{y}: cash external receipts',.0251)
    expect(cash['cash_tax_and_spending_outflow'],row['tax_paid']+row['living_expenses_paid'],
           f'{y}: cash tax and spending payments',.0151)
    expect(row['investment_growth_total'],sum(row['growth_by_account'].values()),f'{y}: growth total',
           .005*(len(accounts)+1)+1e-8)
    # Invested accounts share the reported portfolio return; cash yield needs the plan.
    rate=row['market_return']
    if not -.999<=rate<=5:
        raise VerifyFailure(f'{y}: market return outside the supported -99.9% floor and range')
    for aid,growth in row['growth_by_account'].items():
        if aid!=cash_id:
            opening=row['opening_accounts'][aid]
            expect(growth,opening*rate,f'{y}: {aid} growth at reported return',.0051+.005*abs(rate)+1e-12*abs(opening))
    # Draws stop once cash covers spending plus tax; unpaid amounts need exhausted cash.
    closing=row['closing_accounts']
    shortfall=row['unmet_spending']>0 or row['unpaid_tax']>0
    if (drawn>.005 or shortfall) and closing[cash_id]>.01:
        raise VerifyFailure(f'{y}: cash remained while accounts were drawn or obligations went unpaid')
    if row['unpaid_tax']>0 and row['living_expenses_paid']>0:
        raise VerifyFailure(f'{y}: spending was paid before taxes were fully paid')
    for item in row['rmd']:
        if item['unmet']>.005 and closing[item['account']]>.01:
            raise VerifyFailure(f'{y}: unmet RMD reported while {item["account"]} kept a balance')
    # Average proportional basis: realized basis = draw x prior basis / value at sale.
    basis=row['taxable_basis_end']
    if previous_basis is None:
        return
    if set(basis)!=set(previous_basis):
        raise VerifyFailure(f'{y}: taxable basis accounts changed')
    gains=0.
    slack=.0051
    for aid,prior in previous_basis.items():
        flows=accounts[aid]
        if any(flows[key] for key in ('contribution','required_distribution','roth_conversion_in','roth_conversion_out')):
            raise VerifyFailure(f'{y}: taxable account {aid} has retirement-account flows')
        draw=flows['optional_draw']
        value=row['opening_accounts'][aid]+row['growth_by_account'][aid]
        if draw<=0:
            expect(basis[aid],prior,f'{y}: {aid} basis carried forward',.0051+1e-12*abs(prior))
            continue
        if value<=.02:
            # Cent-rounded balances cannot support a ratio check this small.
            if basis[aid]>prior+.0051:
                raise VerifyFailure(f'{y}: {aid} basis increased on a sale')
            slack+=draw
            continue
        # Propagate the cent rounding of prior basis (0.005) and of value at sale
        # (opening + growth, 0.01): d(used) = (draw/value) dB + (draw*B/value^2) dV.
        used=draw*prior/value
        value_error=draw*prior*.0100001/(value*value)
        expect(basis[aid],max(0.,prior-used),f'{y}: {aid} proportional basis after sale',
               .0051+.0050001*abs(1-draw/value)+value_error+1e-12*prior)
        gains+=max(0.,draw-used)
        slack+=.0050001*draw/value+value_error
    expect(row['realized_ltcg'],gains,f'{y}: realized long-term gain from proportional basis',slack+1e-12*gains)


def _rule_checks(row,policy,plan,expect):
    """Recompute each restricted federal worksheet step from the retyped register."""
    y=row['year']
    tax=row['tax']
    status=policy['filing_status']
    multiplier=(1+policy['future_bracket_inflation'])**(y-2026)
    if tax['year']!=y or tax['tax_law_year']!=2026:
        raise VerifyFailure(f'{y}: tax record year or reference law year changed')
    expect(tax['rule_multiplier'],multiplier,f'{y}: hypothetical bracket index',.0000000051)
    benefits=row['social_security_gross']
    other=(row['wages_taxable']+row['pension_gross']+row['rmd_total']+row['ira_extra_taxable']
           +row['roth_converted']+row['growth_by_account'][row['cash_account_id']]+row['realized_ltcg'])
    expect(tax['ss_provisional_income'],other+.5*benefits,f'{y}: Social Security provisional income',.0451)
    expect(tax['taxable_social_security'],taxable_benefits(benefits,tax['ss_provisional_income'],status),
           f'{y}: taxable Social Security worksheet',.0151)
    if plan is not None:
        elderly=sum(y-member['birth_year']>=65 for member in plan['members'])
        expect(tax['standard_plus_age_deduction'],(STANDARD_2026[status]+elderly*AGE_65_ADDITION_2026[status])*multiplier,
               f'{y}: indexed standard and age-65 deduction',.0051)
        senior=0.
        if SENIOR_YEARS[0]<=y<=SENIOR_YEARS[1]:
            senior=elderly*max(0.,SENIOR_AMOUNT-SENIOR_PHASEOUT_RATE*max(0.,tax['adjusted_gross_income']-SENIOR_MAGI[status]))
        expect(tax['enhanced_senior_deduction'],senior,f'{y}: enhanced senior deduction phaseout',.0061)
    expect(tax['deduction_total'],tax['standard_plus_age_deduction']+tax['enhanced_senior_deduction'],
           f'{y}: deduction total',.0151)
    ordinary=tax['gross_ordinary']
    expect(tax['ordinary_taxable'],max(0.,ordinary-tax['deduction_total']),f'{y}: ordinary taxable income',.0151)
    expect(tax['long_term_gain_taxable'],max(0.,row['realized_ltcg']-max(0.,tax['deduction_total']-ordinary)),
           f'{y}: taxable long-term gain after unused deduction',.0201)
    base=tax['ordinary_taxable']
    gains=tax['long_term_gain_taxable']
    portions=bracket_portions(0.,base,status,multiplier)
    lines=tax['ordinary_bracket_lines']
    if len(lines)>len(portions):
        raise VerifyFailure(f'{y}: extra ordinary bracket lines')
    for k,(low,high,rate,amount) in enumerate(portions):
        if k>=len(lines):
            if amount>.0101:
                raise VerifyFailure(f'{y}: ordinary bracket {k} missing')
            continue
        line=lines[k]
        if line['rate']!=rate or (line['to'] is None)!=(high is None):
            raise VerifyFailure(f'{y}: ordinary bracket {k} rate or top changed')
        expect(line['from'],low,f'{y}: ordinary bracket {k} start',.0051+1e-12*low)
        if high is not None:
            expect(line['to'],high,f'{y}: ordinary bracket {k} top',.0051+1e-12*high)
        expect(line['taxable'],amount,f'{y}: ordinary bracket {k} amount',.0101)
    expect(tax['ordinary_tax'],sum(rate*amount for _,_,rate,amount in portions),f'{y}: ordinary tax from schedule',.0101)
    # Publication 505 Worksheet 2-7 lines 38-40: lower of stacked gain rates or
    # ordinary rates on all taxable income, gains taking the top of the stack.
    zero_top,fifteen_top=(threshold*multiplier for threshold in GAIN_ZONES_2026[status])
    zero=max(0.,min(gains,zero_top-base))
    fifteen=max(0.,min(gains-zero,fifteen_top-max(zero_top,base)))
    twenty=max(0.,gains-zero-fifteen)
    stacked=.15*fifteen+.20*twenty
    capped_lines={rate:amount for _,_,rate,amount in bracket_portions(base,base+gains,status,multiplier) if amount>0}
    capped=sum(rate*amount for rate,amount in capped_lines.items())
    method=tax['income_tax_method']
    reported=tax['capital_gain_rate_lines']
    if method=='stacked_capital_gains':
        if stacked>capped+.0101:
            raise VerifyFailure(f'{y}: preferential stacking chosen although the ordinary-rate cap is lower')
        if [line['rate'] for line in reported]!=[0.,.15,.2]:
            raise VerifyFailure(f'{y}: preferential gain rates changed')
        for line,amount,zone in zip(reported,(zero,fifteen,twenty),('0%','15%','20%')):
            expect(line['taxable'],amount,f'{y}: {zone} long-term gain zone',.0151)
        expect(tax['capital_gains_tax'],stacked,f'{y}: preferential gain tax',.0101)
    elif method=='ordinary_rate_cap':
        if capped>stacked+.0101:
            raise VerifyFailure(f'{y}: ordinary-rate cap chosen although stacking is lower')
        by_rate={}
        for line in reported:
            if line['rate'] in by_rate:
                raise VerifyFailure(f'{y}: duplicate capped gain rate')
            by_rate[line['rate']]=line['taxable']
        for rate in set(by_rate)|set(capped_lines):
            expect(by_rate.get(rate,0.),capped_lines.get(rate,0.),f'{y}: gain taxed at ordinary rate {rate}',.0151)
        expect(tax['capital_gains_tax'],capped,f'{y}: ordinary-rate cap gain tax',.0101)
    else:
        raise VerifyFailure(f'{y}: unsupported income tax method')
    payroll=row['payroll_tax']
    cap=oasdi_wage_base(y,policy['future_bracket_inflation'])
    expect(payroll['wage_base_per_person'],cap,f'{y}: OASDI wage base',.0051+1e-12*cap)
    covered=payroll['oasdhi_taxable_wages_by_person']
    numeric_vector(covered,1 if status=='single' else 2,f'{y}: OASDI wages by person')
    for value in covered:
        nonnegative(value,f'{y}: OASDI wages')
        if value>payroll['wage_base_per_person']+.0051:
            raise VerifyFailure(f'{y}: OASDI wages exceed the wage base')
    if sum(covered)>row['wages_gross']+.0101:
        raise VerifyFailure(f'{y}: OASDI wages exceed gross wages')
    expect(payroll['social_security_tax'],sum(covered)*OASDI_RATE,f'{y}: OASDI employee tax',.0061)
    expect(payroll['medicare_tax'],row['wages_gross']*MEDICARE_RATE,f'{y}: Medicare employee tax',.0052)
    expect(payroll['additional_medicare_taxable_wages'],max(0.,row['wages_gross']-EXTRA_MEDICARE_WAGES[status]),
           f'{y}: Additional Medicare wages',.0101)
    expect(payroll['additional_medicare_tax'],payroll['additional_medicare_taxable_wages']*EXTRA_MEDICARE_RATE,
           f'{y}: Additional Medicare tax',.0052)


def _plan_checks(row,plan,path_return,blocks,expect):
    """Plan-anchored conventions: timing, return, RMD activation, conversions, funding order."""
    y=row['year']
    accounts={a['id']:a for a in plan['accounts']}
    births={m['id']:m['birth_year'] for m in plan['members']}
    cash_id=next(aid for aid,a in accounts.items() if a['kind']=='cash')
    if row['cash_account_id']!=cash_id:
        raise VerifyFailure(f'{y}: cash account mismatched to plan')
    if row['age_primary']!=y-plan['members'][0]['birth_year']:
        raise VerifyFailure(f'{y}: primary age mismatched to plan')
    flows=row['account_flows']
    closing=row['closing_accounts']
    scheduled=scheduled_income(plan,y)
    expect(row['wages_gross'],sum(scheduled['wages']),f'{y}: wages scheduled by plan',.0051+1e-12*row['wages_gross'])
    for aid in set(scheduled['deferrals'])|set(row['pretax_contribution_by_account']):
        expect(row['pretax_contribution_by_account'].get(aid,0.),scheduled['deferrals'].get(aid,0.),
               f'{y}: {aid} deferral scheduled by plan',.0051)
    expect(row['pretax_contributions'],sum(scheduled['deferrals'].values()),f'{y}: deferrals scheduled by plan',.0051)
    # Base elective limit only (no catch-up), indexed by the hypothetical policy rate.
    limit=ELECTIVE_DEFERRAL_2026*(1+plan['tax_policy']['future_bracket_inflation'])**(y-2026)
    for member,pay in zip(plan['members'],scheduled['wages']):
        deferral=scheduled['deferrals'].get(member.get('pretax_401k_target'),0.)
        if deferral>min(pay,limit)+1e-7:
            raise VerifyFailure(f'{y}: {member["id"]} deferral exceeds wages or the indexed base elective limit')
    expect(row['social_security_gross'],scheduled['benefits'],f'{y}: Social Security scheduled by plan',.0051+1e-12*scheduled['benefits'])
    expect(row['pension_gross'],scheduled['pension'],f'{y}: pension scheduled by plan',.0051+1e-12*scheduled['pension'])
    expect(row['other_after_tax_income'],scheduled['inflows'],f'{y}: event income scheduled by plan',.0051+1e-12*scheduled['inflows'])
    expect(row['living_expenses_due'],scheduled['living'],f'{y}: spending scheduled by plan',.0051+1e-12*scheduled['living'])
    payroll=row['payroll_tax']
    for person,(covered,pay) in enumerate(zip(payroll['oasdhi_taxable_wages_by_person'],scheduled['wages'])):
        expect(covered,min(pay,payroll['wage_base_per_person']),f'{y}: OASDI wages for member {person}',.0101)
    cash_yield=plan['assumptions']['cash_yield']
    opening_cash=row['opening_accounts'][cash_id]
    expect(row['growth_by_account'][cash_id],opening_cash*cash_yield,f'{y}: cash interest at plan yield',
           .0051+.005*cash_yield+1e-12*abs(opening_cash))
    expect(row['market_return'],path_return,f'{y}: portfolio return of the plan path',1e-12)
    def owner_age(aid):
        return y-births[accounts[aid]['owner']]
    active={aid for aid,a in accounts.items()
            if a['kind'] in PRETAX_KINDS and owner_age(aid)>=rmd_start_age(births[a['owner']])}
    recorded={item['account'] for item in row['rmd']}
    if recorded!=active:
        raise VerifyFailure(f'{y}: RMD accounts {sorted(recorded)} differ from plan start ages {sorted(active)}')
    for item in row['rmd']:
        if type(item['age']) is not int or item['age']!=owner_age(item['account']):
            raise VerifyFailure(f'{y}: RMD owner age mismatched to plan')
    # Scheduled conversions run in plan order after RMD; each executes or is skipped.
    executed=list(row['conversion_transfers'])
    skipped=list(row['skipped_conversions'])
    available={}
    for request in (c for c in plan.get('roth_conversions',[]) if c['year']==y):
        source=request['from']
        amount=request['amount_nominal']
        if source not in available:
            available[source]=(row['opening_accounts'][source]+row['growth_by_account'][source]
                               -flows[source]['required_distribution'])
        if executed and executed[0]=={'from':source,'to':request['to'],'amount':amount}:
            if available[source]+.011<amount:
                raise VerifyFailure(f'{y}: conversion exceeds the {source} balance left after RMD')
            available[source]-=amount
            executed.pop(0)
        elif (skipped and isinstance(skipped[0],dict) and isinstance(skipped[0].get('reason'),str)
              and {key:skipped[0].get(key) for key in ('year','from','amount')}=={'year':y,'from':source,'amount':amount}):
            if available[source]-.011>=amount:
                raise VerifyFailure(f'{y}: conversion skipped although {source} had the balance')
            skipped.pop(0)
        else:
            raise VerifyFailure(f'{y}: conversions differ from the plan schedule')
    if executed or skipped:
        raise VerifyFailure(f'{y}: conversions differ from the plan schedule')
    # Funding order: blocked under-60 retirement accounts are skipped and disclosed;
    # a later draw or a shortfall requires every earlier accessible account exhausted.
    blocked={aid for aid,a in accounts.items() if a['kind'] in RETIREMENT_KINDS and owner_age(aid)<60}
    for aid in blocked:
        if flows[aid]['optional_draw']!=0:
            raise VerifyFailure(f'{y}: {aid} drawn before its owner reached age 60')
    expect(row['ira_extra_taxable'],sum(flows[aid]['optional_draw'] for aid,a in accounts.items() if a['kind'] in PRETAX_KINDS),
           f'{y}: pretax draws taxed as ordinary income',.0051)
    for block in blocks:
        if not any(block.startswith(aid+':') for aid in blocked):
            raise VerifyFailure(f'{y}: funding notice names an account that was not blocked')
    order=[aid for aid in plan['withdrawal_order'] if accounts[aid]['kind']!='cash']
    shortfall=row['unmet_spending']>0 or row['unpaid_tax']>0
    for position,aid in enumerate(order):
        later_draw=any(flows[later]['optional_draw']>0 for later in order[position+1:])
        if not (shortfall or later_draw):
            continue
        if aid in blocked:
            if not any(block.startswith(aid+':') for block in blocks):
                raise VerifyFailure(f'{y}: blocked account {aid} missing from funding notices')
        elif closing[aid]>.01:
            if later_draw:
                raise VerifyFailure(f'{y}: {aid} kept a balance although the withdrawal order draws it first')
            raise VerifyFailure(f'{y}: shortfall reported while {aid} kept an accessible balance')


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('result',type=Path,help='evaluate result JSON, or trace JSON with --trace')
    ap.add_argument('--plan',type=Path)
    ap.add_argument('--engine-dir',type=Path)
    ap.add_argument('--trace',action='store_true',help='verify audit_plan.py trace output (requires --plan)')
    ap.add_argument('--trace-result',type=Path,help='with --trace: cross-check this result manifest entry')
    ap.add_argument('--output',type=Path)
    a=ap.parse_args()
    if a.trace and not a.plan:
        ap.error('--trace requires --plan')
    if a.trace_result and not a.trace:
        ap.error('--trace-result requires --trace')
    try:
        data=json.loads(a.result.read_text())
        plan=json.loads(a.plan.read_text()) if a.plan else None
        if a.trace:
            result=verify_trace(data,plan,json.loads(a.trace_result.read_text()) if a.trace_result else None)
        else:
            result=verify(data,plan,a.engine_dir)
        if a.output:a.output.write_text(json.dumps(result,indent=2)+'\n')
        print('PASS independent output verification:',json.dumps(result))
    except (ValueError,KeyError,OSError,TypeError) as e:
        ap.exit(2,'FAIL independent output verification: '+str(e)+'\n')
if __name__=='__main__':
    main()
