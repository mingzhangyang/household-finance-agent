# Validation summary — engine v2.2 (2026-10-28)

This is a repeatable QA record, not an independent CPA/CFP attestation. Execute the entire test suite and save the generated result and verifier JSON before claiming any count of passing tests. Output in `model_validation_report.md` outside the skill contains the latest complete fixture-specific numbers.

## PR #2 review-fix verification (2026-10-28)

The reviewed checkout at `d818183` plus these fixes passed `sh scripts/verify_local.sh`: **45 tests**, a 40-year fictional projection with 300 seeded paths, independent output verification, historical-fixture checks and all four HTML scenarios. The verifier reported 2,038 annual assertions and a maximum account residual of $0.013647 from rounded output (within its $0.05 journal tolerance; the engine also checks unrounded accounting).

Regression coverage includes per-person senior deduction phaseout, reordered/duplicate/missing years, initial-plan and inter-year balance anchors, account totals and IDs, per-bracket multiplication, omitted 401(k) contributions, survivor-interval boundaries, minimum return assumptions, and exact reproduction from every embedded scenario plan. Node.js handler tests execute the report's JavaScript against a minimal DOM to check skipped-conversion status and selected-scenario plan/audit downloads. These tests skip explicitly if Node.js is unavailable. A real-browser layout test was not run: Chromium was absent and its download failed. These are local results, not a successful GitHub Actions run or professional certification.

## Implemented checks

- Independent IRS table fixtures for 2026 regular and preferential tax, Social Security published benefits example, enhanced senior deduction including joint-return 6% phaseout, 2026/2027 employee FICA, and income tax reference-year projection labels.
- Hand-worked $100k gross wage / $20k pretax 401(k) / $60k spending example.
- RMD 73 with 26.5 divisor, 1959/1960 birth-year demarcation, Roth conversion tax handling and pro-rata taxable gain.
- Reject invalid schemas, missing 401(k)/IRA ownership, undocumented IRA after-tax basis, malformed input evidence, early retirement distributions, misleading SSA claim age reuse, and real-account gaps.
- Reconcile every account and overall household to <=$0.01 in *unrounded* computation; expose minor rounding effects in displayed data.
- Independent `verify_outputs.py` recomputes progressive tax lines, pref-rate lines, NIIT MAGI/NII/base, total tax, all account transfers, RMD, stochastic success count and terminal quantiles from saved output; tampering checks verify it fails when numbers or input fingerprints are altered.
- Complete 300-path fictional scenario plus interactive desktop/mobile report browser acceptance (if Playwright/Chromium available).

## Interpretation

All passing tests validate a bounded mathematical implementation, **not** the correctness of future market assumptions, legal applicability to a particular household, or readiness for use as financial/tax advice. Unimplemented domains must be explicitly disclosed and routed to professional review.
## New v2.2 scoped checks

- IRS 2026 enhanced senior deduction: MFJ two seniors $12,000 maximum; apply 6% of joint MAGI above $150,000 to **each person’s $6,000** before summing, giving $10,800 at $160,000 and $0 at $250,000; source: 26 USC 151 / IRS Schedule 1-A.
- IRS NIIT (restricted): 3.8% times the lesser of modeled net investment income or MAGI above single $200k / MFJ $250k; tax enters the iterative annual cash funding loop. Rate remains 0.038 in audit records, never truncated to 0.04.
- NIIT verifier does not import the tax function; it rederives MAGI, modeled interest + LTCG, threshold, base and tax; tampering tests reject altered rates/bases.
- Lifecycle supports a surviving partner whose assumed death year occurs after the projection horizon; death timing remains an assumption, not a mortality table.
- 2026/2027 SSA bend-point tests and historical rolling return checks are standalone reference tests. The Gaussian core market model is still uncalibrated.
- GitHub Actions execution is blocked by the owner's consumed free quota; local tests do not count as an exact-head GitHub CI run. Do not auto-merge until code review and independent verification.
