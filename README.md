# Household Finance Agent

An evidence-first ChatGPT Skill and financial-planning research toolkit. **Not a certified planner, tax-return preparer, or substitute for a Social Security benefit statement.**

Repository initialized October 28, 2026. The original v2.1 audited planner was distributed separately as a Skill archive. Its full engine, original UI templates and 64-test suite **have not yet been imported into this repository**. Do not assume this GitHub branch contains a runnable end-to-end v2.1 financial report.

## Current code in feat/professional-model-foundation

Standalone Python modules in scripts/:

- ssa_benefits.py: published 2026/2027 PIA bend points, AIME computation for *already-indexed* earnings, and worker retirement claim-age factors.
- lifecycle_rules.py: explicit family-status timeline and survivor-income fail-closed gate; no spouse/survivor benefit award calculation.
- market_history.py: strict stock/bond return CSV ingestion, SHA256, historical windows and deterministic paired block-bootstrap stress tests.
- tax_extensions.py: IRS NIIT base formula when NII and MAGI are already independently and correctly determined.

To run included tests:

    python -m unittest discover -s tests -p test_professional_modules.py -v

See references/professional-model-gates.md for official source links, scope, limitations, and release gates.

## Incomplete and deliberately not asserted

- The previous audited engine, its templates, and legacy regression suite are **not present yet**.
- NIIT is not wired into a complete Form 1040 / 8960 projection.
- No SSA earnings-history indexing, annual COLA, spouse, survivor, or dual-entitlement calculation.
- No pinned independent 1928-present dataset or third-party professional model comparison.
- Passing module tests is not proof of correct household retirement success predictions.

Do not commit actual account balances, Social Security records, tax returns, credentials or identifiable household information. This code is research-only until independently reviewed.
