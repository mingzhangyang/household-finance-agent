#!/usr/bin/env python3
"""State income tax jurisdiction interface (ROADMAP M2 group 2).

A plan either keeps the federal-only research scope with the explicit string
'excluded_with_disclosure', or names a registered jurisdiction object. Adding a
state means a rule module exposing what maryland_tax does (JURISDICTION,
SOURCES, SOURCE_IDS, validate_spec, rule_basis, scope_lines and a calculation
registered in compute below), its retyped verifier copy, report labels and
independent cases; the funding solver and ledger do not change. Unregistered
states, part-year residence and missing local jurisdictions fail closed;
nothing is ever taxed at zero by default.
"""
from __future__ import annotations
import maryland_tax

EXCLUDED = 'excluded_with_disclosure'
REGISTRY = {maryland_tax.JURISDICTION: maryland_tax}


def module(spec):
    """The rule module for a validated spec, or None for the federal-only scope."""
    return None if spec == EXCLUDED else REGISTRY[spec['jurisdiction']]


def validate(spec, plan, error):
    if spec == EXCLUDED:
        return
    if not isinstance(spec, dict):
        raise error(f'state_income_tax must be "{EXCLUDED}" or a registered jurisdiction object; '
                    'state income taxes are never assumed to be zero')
    jurisdiction = spec.get('jurisdiction')
    if jurisdiction not in REGISTRY:
        raise error(f'state jurisdiction {jurisdiction!r} is not registered (modeled: {sorted(REGISTRY)}); '
                    f'other states are rejected, never taxed at zero; use "{EXCLUDED}" for federal-only research')
    REGISTRY[jurisdiction].validate_spec(spec, plan, error)


def rule_basis(spec, year, assumed_rate):
    rules = module(spec)
    return {} if rules is None else rules.rule_basis(year, assumed_rate)


def compute(spec, **facts):
    rules = module(spec)
    if rules is None:
        return None
    if rules is maryland_tax:
        return maryland_tax.maryland_tax(spec=spec, **facts)
    raise ValueError(f'no calculation registered for {spec["jurisdiction"]}')


def sources(spec):
    rules = module(spec)
    return {} if rules is None else dict(rules.SOURCES)


def source_ids(spec):
    rules = module(spec)
    return [] if rules is None else list(rules.SOURCE_IDS)


def scope_lines(spec):
    rules = module(spec)
    return [] if rules is None else rules.scope_lines()
