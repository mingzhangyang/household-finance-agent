#!/usr/bin/env python3
"""Compare six frozen fictional scenarios with independent Decimal worksheets.

Exit 1 on any difference outside predeclared tolerances. Does not grant M1
professional sign-off, validate market assumptions or implement a tax return.
"""
import argparse
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tests/golden'))
from m1_reference import references
from audit_plan import evaluate

CASES_PATH = ROOT/'tests/golden/m1-cases.json'
# These fields are structural or rule selectors, not monetary amounts.
EXACT_NUMERIC = {'year', 'age', 'divisor', 'first_failure_year',
                 'modeled_all_obligations_funded_fraction'}
EXACT_MAPS = {'opening_accounts', 'closing_accounts', 'extra_draws', 'taxable_basis_end'}


def reference_json(value):
    """Preserve exact Decimal spelling even in missing compound references."""
    if isinstance(value,Decimal): return str(value)
    if isinstance(value,dict): return {key:reference_json(item) for key,item in value.items()}
    if isinstance(value,list): return [reference_json(item) for item in value]
    return value


def compare(actual, expected, path='$'):
    """Each reference leaf is checked, including shape for account/draw maps."""
    checks=[]
    def check(where, want, got, passed, difference=None, tolerance=None):
        checks.append(dict(field=where,expected=reference_json(want),
                           actual=got,passed=passed,difference=difference,tolerance=tolerance))
    def visit(got,want,where):
        key=where.rsplit('.',1)[-1]
        if isinstance(want,dict):
            if not isinstance(got,dict):
                check(where,'object',got,False); return
            if key in EXACT_MAPS:
                check(where+'.keys',sorted(want),sorted(got),set(want)==set(got))
            for field,value in want.items():
                if field not in got:
                    check(where+'.'+field,value,None,False)
                else: visit(got[field],value,where+'.'+field)
        elif isinstance(want,list):
            if not isinstance(got,list):
                check(where,'array',got,False); return
            check(where+'.length',len(want),len(got),len(want)==len(got))
            for i,(g,w) in enumerate(zip(got,want)): visit(g,w,f'{where}[{i}]')
        elif want is None or isinstance(want,(str,bool)):
            check(where,want,got,type(got) is type(want) and got==want)
        else:
            valid=type(got) in (int,float) and math.isfinite(got)
            delta=abs(Decimal(str(got))-Decimal(want)) if valid else None
            tolerance=Decimal(0) if key in EXACT_NUMERIC else Decimal('.01')
            check(where,want,got,valid and delta<=tolerance,
                  str(delta) if delta is not None else None,str(tolerance))
    visit(actual,expected,path)
    return checks


def verify_cases():
    fixtures=json.loads(CASES_PATH.read_text())
    expected=references()
    ids=[c['id'] for c in fixtures['cases']]
    if len(set(ids))!=len(ids) or set(ids)!=set(expected):
        raise ValueError('Reference/fixture case IDs must agree exactly')
    reports=[]
    for case in fixtures['cases']:
        result=evaluate(case['plan'])
        ref=expected[case['id']]
        checks=compare(result['deterministic_annual_ledger'],ref)
        # All trials have exactly zero returns; no estimated probability claim.
        checks+=compare(result,dict(modeled_all_obligations_funded_fraction=0 if ref['failed'] else 1))
        reports.append(dict(id=case['id'],plan_sha256=hashlib.sha256(
            json.dumps(case['plan'],sort_keys=True).encode()).hexdigest(),
            years=len(ref['rows']),passed=all(c['passed'] for c in checks),checks=checks))
    return dict(schema_version=1,validation_level='selected_independent_case_equations',
        professional_review='not_recorded',release_approved=False,
        fixture_sha256=hashlib.sha256(CASES_PATH.read_bytes()).hexdigest(),
        reference_sha256=hashlib.sha256((ROOT/'tests/golden/m1_reference.py').read_bytes()).hexdigest(),
        passed=all(c['passed'] for c in reports),cases=reports,
        limitations=['Six fictional cases: three zero-return/zero-inflation, one stated return/inflation/indexing case, '
                     'two taxable-account cases (distributions, loss limit, carryover, NIIT).',
                     'Future-year federal tables are hypothetical 2026 rates, frozen or indexed as each case states.',
                     'Not independent professional review or external planning-tool validation.'])


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path)
    args=ap.parse_args()
    report=verify_cases()
    if args.output: args.output.write_text(json.dumps(report,indent=2)+'\n')
    for case in report['cases']:
        print(f'{case["id"]}: {"PASS" if case["passed"] else "FAIL"}; {case["years"]} years; {len(case["checks"])} comparisons')
        for check in case['checks']:
            if not check['passed']: print(json.dumps(check))
    return 0 if report['passed'] else 1


if __name__=='__main__': raise SystemExit(main())
