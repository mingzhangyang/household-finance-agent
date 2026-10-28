#!/usr/bin/env python3
"""Offline audited report: Python-precomputed outcomes, no browser tax engine."""
import argparse
import copy
import json
from pathlib import Path
from audit_plan import validate, evaluate, ModelError
from verify_outputs import verify, VerifyFailure

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / 'assets' / 'audit-template.html'

def create_scenarios(base):
    validate(base)
    early = copy.deepcopy(base)
    early['name'] = 'Early retirement (first member -3 years)'
    early['members'][0]['retirement_age'] = max(40, early['members'][0]['retirement_age'] - 3)
    expensive = copy.deepcopy(base)
    expensive['name'] = 'Annual spending +10%'
    expensive['living_expenses_annual_real'] *= 1.10
    conservative = copy.deepcopy(base)
    conservative['name'] = 'Lower return assumptions'
    conservative['assumptions']['equity_mean'] -= 0.02
    conservative['assumptions']['bond_mean'] -= 0.01
    return [base, early, expensive, conservative]

def render(base,output):
    plans=create_scenarios(base)
    results=[evaluate(p) for p in plans]
    verification=[verify(result,plan,ROOT/'scripts') for result,plan in zip(results,plans)]
    if not all(status['passed'] for status in verification):
        raise VerifyFailure('independent pre-render verification failed')
    data={'labels':['当前基准','提前退休三年','家庭支出增加 10%','降低收益预期'],
          'results':results,'verification':verification,
          'source':'All numbers precomputed by audit_plan.py and checked by verify_outputs.py; no browser tax calculations'}
    raw=json.dumps(data,separators=(',',':'),ensure_ascii=False,allow_nan=False)
    raw=raw.replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    html=TEMPLATE.read_text(encoding='utf-8').replace('__AUDIT_DATA__',raw)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(html,encoding='utf-8')
    return output

def main():
    ap=argparse.ArgumentParser(description='Render offline traceable financial audit dashboard')
    ap.add_argument('plan',type=Path)
    ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args()
    try:
        data=json.loads(a.plan.read_text(encoding='utf-8'))
        path=render(data,a.output)
        print('Generated private auditable dashboard:',path)
    except (ValueError,ModelError,VerifyFailure,OSError) as exc:
        ap.exit(2,f'ERROR: {exc}\n')
if __name__=='__main__':
    main()
