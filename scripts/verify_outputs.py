#!/usr/bin/env python3
"""Independent output-only verifier. No audit_plan or tax2026 imports.

Checks accounting conservation, per-account journals, tax components, RMDs,
Monte Carlo aggregation, data fingerprint, and code fingerprint.
Arithmetic consistency is not a tax-law certification or market calibration.
"""
import argparse
import hashlib
import json
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

def verify(x,plan=None,engine_dir=None):
    if x.get('engine_version')!='2.2-auditable-restricted':
        raise VerifyFailure('unexpected or unaudited engine')
    count=x['trials']
    manifest=x['simulated_path_manifest']
    if count!=len(manifest):
        raise VerifyFailure('missing Monte Carlo paths')
    successes=sum(z['funded'] for z in manifest)
    if x['success_paths']!=successes:
        raise VerifyFailure('MC funded path count wrong')
    close(x['modeled_all_obligations_funded_fraction'],successes/count,'MC success fraction',.00001)
    for index,z in enumerate(manifest):
        if z['path_index']!=index:
            raise VerifyFailure('misordered MC paths')
    finals=[z['terminal_real'] for z in manifest]
    for q,n in zip((.1,.5,.9),x['terminal_real_p10_p50_p90']):
        close(n,quant(finals,q),f'MC quantile {q}',.02)
    ledger=x['deterministic_annual_ledger']['rows']
    checks=0
    max_residual=0
    if not ledger:
        raise VerifyFailure('empty ledger')
    first_year,last_year=x['year_range']
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
    for index,row in enumerate(ledger):
        y=row['year']
        if y!=first_year+index:
            raise VerifyFailure('ledger years must be consecutive and ordered')
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
        if tax['niit_rate'] != .038:
            raise VerifyFailure(f'{y}: NIIT rate changed')
        if tax['niit_threshold'] != (250000. if x['tax_policy']['filing_status']=='mfj' else 200000.):
            raise VerifyFailure(f'{y}: NIIT threshold changed')
        close(tax['niit_magi_assumed_equal_agi'],tax['adjusted_gross_income'],f'{y}: NIIT MAGI')
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
        for aid,flows in row['account_flows'].items():
            expected=(row['opening_accounts'][aid]+row['growth_by_account'][aid]+flows['contribution']
                +flows['roth_conversion_in']+flows['cash_external_inflow']+flows['cash_received_rmd']
                +flows['cash_received_draws']-flows['required_distribution']-flows['roth_conversion_out']
                -flows['optional_draw']-flows['cash_tax_and_spending_outflow'])
            close(row['closing_accounts'][aid],expected,f'{y}: account {aid}')
            close(row['account_reconciliation_residuals'][aid],0,f'{y}: {aid} residual',.01)
            checks+=2
            max_residual=max(max_residual,abs(row['closing_accounts'][aid]-expected))
        checks+=17+len(row['rmd'])*2
        previous_accounts=row['closing_accounts']
        previous_total=row['closing_total']
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
