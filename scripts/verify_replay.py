#!/usr/bin/env python3
"""Exact same-engine replay. Deliberately NOT called independent verification."""
import argparse
import json
from pathlib import Path
from audit_plan import evaluate
from verify_outputs import verify, VerifyFailure


def first_difference(actual, expected, path='$'):
    # JSON numbers can differ between int/float serialization; booleans cannot.
    if type(actual) is bool or type(expected) is bool:
        return None if type(actual) is type(expected) and actual == expected else path
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or actual.keys() != expected.keys():
            return path
        for key in expected:
            mismatch = first_difference(actual[key], expected[key], f'{path}.{key}')
            if mismatch:
                return mismatch
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            return path
        for index, value in enumerate(expected):
            mismatch = first_difference(actual[index], value, f'{path}[{index}]')
            if mismatch:
                return mismatch
    elif actual != expected:
        return path
    return None


def verify_replay(result, plan):
    verify(result, plan, Path(__file__).parent)
    mismatch = first_difference(result, evaluate(plan))
    if mismatch:
        raise VerifyFailure(f'same-engine replay mismatch at {mismatch}')
    return {'passed': True, 'validation_level': 'same_engine_replay',
            'independent_model_validation': False, 'paths_replayed': result['trials']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('result', type=Path)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        status = verify_replay(json.loads(args.result.read_text()), json.loads(args.plan.read_text()))
        if args.output:
            args.output.write_text(json.dumps(status, indent=2)+'\n')
        print(json.dumps(status))
    except (ValueError, OSError) as exc:
        parser.exit(2, f'FAIL replay: {exc}\n')


if __name__ == '__main__':
    main()
