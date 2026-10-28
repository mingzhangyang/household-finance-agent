#!/usr/bin/env python3
"""Independent output-only verifier. No audit_plan or tax2026 imports.

Checks accounting conservation, per-account journals, tax components, RMDs,
Monte Carlo aggregation, data fingerprint, and code fingerprint.
Arithmetic consistency is not a tax-law certification or market calibration.
"""
import argparse
import hashlib
import json
from math import isfinite, sqrt
from pathlib import Path

class VerifyFailure(ValueError):
    pass

def close(a,b,desc,tol=.05):
    if not abs(float(a)-float(b))<=tol:
        raise VerifyFailure(f'{desc}: got {a} expected {b} (tol {tol})')

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

def verify(x,plan=None,engine_dir=None):
    if x.get('engine_version')!='2.2-auditable-restricted':
        raise VerifyFailure('unexpected or unaudited engine')
    count=x['trials']
    if type(count) is not int or count<=0:
        raise VerifyFailure('MC trial count must be a positive integer')
    if plan is not None and count!=plan['assumptions']['trials']:
        raise VerifyFailure('MC trial count mismatched to plan')
    first_year,last_year=x['year_range']
    if type(first_year) is not int or type(last_year) is not int or first_year>last_year:
        raise VerifyFailure('invalid projection year range')
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
    if x['success_paths']!=successes:
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
    ledger=x['deterministic_annual_ledger']['rows']
    checks=0
    max_residual=0
    if not ledger:
        raise VerifyFailure('empty ledger')
    if plan is not None:
        if [first_year,last_year]!=[plan['as_of_year']+1,plan['end_year']]:
            raise VerifyFailure('year range mismatched to plan')
        previous_accounts={a['id']:a['balance'] for a in plan['accounts']}
        previous_total=sum(previous_accounts.values())
    else:
        previous_accounts=ledger[0]['opening_accounts']
        previous_total=ledger[0]['opening_total']
    if len(ledger)!=last_year-first_year+1:
        raise VerifyFailure('year count mismatched to range')
    failure_years=[]
    for index,row in enumerate(ledger):
        y=row['year']
        if y!=first_year+index:
            raise VerifyFailure('ledger years must be consecutive and ordered')
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
        if tax['niit_threshold'] != (250000. if x['tax_policy']['filing_status']=='mfj' else 200000.):
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
            close(item['required'],item['previous_dec31_balance']/item['divisor'],f'{y}: RMD {item["account"]}')
            close(item['taken']+item['unmet'],item['required'],f'{y}: RMD fulfillment')
        close(row['rmd_total'],round(sum(item['taken'] for item in row['rmd']),2),f'{y}: RMD taken aggregate',1e-8)
        close(row['unmet_rmd'],round(sum(item['unmet'] for item in row['rmd']),2),f'{y}: RMD unmet aggregate',1e-8)
        for aid,flows in row['account_flows'].items():
            expected=(row['opening_accounts'][aid]+row['growth_by_account'][aid]+flows['contribution']
                +flows['roth_conversion_in']+flows['cash_external_inflow']+flows['cash_received_rmd']
                +flows['cash_received_draws']-flows['required_distribution']-flows['roth_conversion_out']
                -flows['optional_draw']-flows['cash_tax_and_spending_outflow'])
            close(row['closing_accounts'][aid],expected,f'{y}: account {aid}')
            close(row['account_reconciliation_residuals'][aid],0,f'{y}: {aid} residual',.01)
            checks+=2
            max_residual=max(max_residual,abs(row['closing_accounts'][aid]-expected))
        checks+=25+(plan is not None)+len(row['rmd'])*2
        previous_accounts=row['closing_accounts']
        previous_total=row['closing_total']
    summary=x['deterministic_annual_ledger']
    if type(summary['failed']) is not bool or summary['failed']!=bool(failure_years):
        raise VerifyFailure('deterministic failed summary disagrees with annual rows')
    first_failure=failure_years[0] if failure_years else None
    if summary['first_failure_year']!=first_failure:
        raise VerifyFailure('deterministic first failure year disagrees with annual rows')
    checks+=2
    if plan is not None:
        raw=json.dumps(plan,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
        if x['input_sha256']!=hashlib.sha256(raw).hexdigest():
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
            'verified_input_hash':plan is not None,'verified_engine_hash':engine_dir is not None}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('result',type=Path)
    ap.add_argument('--plan',type=Path)
    ap.add_argument('--engine-dir',type=Path)
    ap.add_argument('--output',type=Path)
    a=ap.parse_args()
    try:
        result=verify(json.loads(a.result.read_text()),
            json.loads(a.plan.read_text()) if a.plan else None,a.engine_dir)
        if a.output:a.output.write_text(json.dumps(result,indent=2)+'\n')
        print('PASS independent output verification:',json.dumps(result))
    except (ValueError,KeyError,OSError,TypeError) as e:
        ap.exit(2,'FAIL independent output verification: '+str(e)+'\n')
if __name__=='__main__':
    main()
