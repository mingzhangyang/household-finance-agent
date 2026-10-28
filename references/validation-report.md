# Validation summary — engine v2.1 (2026-10-27)

This is a repeatable QA record, not an independent CPA/CFP attestation. Execute the entire test suite and save the generated result and verifier JSON before claiming any count of passing tests. Output in `model_validation_report.md` outside the skill contains the latest complete fixture-specific numbers.

## Implemented checks

- Independent IRS table fixtures for 2026 regular and preferential tax, Social Security published benefits example, enhanced senior deduction, 2026/2027 employee FICA, and income tax reference-year projection labels.
- Hand-worked $100k gross wage / $20k pretax 401(k) / $60k spending example.
- RMD 73 with 26.5 divisor, 1959/1960 birth-year demarcation, Roth conversion tax handling and pro-rata taxable gain.
- Reject invalid schemas, missing 401(k)/IRA ownership, undocumented IRA after-tax basis, malformed input evidence, early retirement distributions, misleading SSA claim age reuse, and real-account gaps.
- Reconcile every account and overall household to <=$0.01 in *unrounded* computation; expose minor rounding effects in displayed data.
- Independent `verify_outputs.py` recomputes progressive tax lines, pref-rate lines, total tax, all account transfers, RMD, stochastic success count and terminal quantiles from saved output; tampering checks verify it fails when numbers or input fingerprints are altered.
- Complete 300-path fictional scenario plus interactive desktop/mobile report browser acceptance (if Playwright/Chromium available).

## Interpretation

All passing tests validate a bounded mathematical implementation, **not** the correctness of future market assumptions, legal applicability to a particular household, or readiness for use as financial/tax advice. Unimplemented domains must be explicitly disclosed and routed to professional review.