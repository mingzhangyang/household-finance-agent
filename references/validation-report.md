# Validation summary — engine v2.2 (2026-10-28)

This is a repeatable QA record, not an independent CPA/CFP attestation. Execute the entire test suite and save the generated result and verifier JSON before claiming any count of passing tests. Output in `model_validation_report.md` outside the skill contains the latest complete fixture-specific numbers.

## PR #2 review-fix verification (2026-10-28)

Fourth review: the `c88607c` checkout plus these six fixes passed **105 tests**, the **40-year / 300-path** fictional run, **2,990 annual ledger verifier assertions**, historical-fixture checks and all four HTML scenarios through `sh scripts/verify_local.sh`. The 17 new tests in `test_review_round4.py` cover:

- Annual MC year coverage, finite ordered bands, final percentiles and funded-to-date counts, including exclusion of the failure year itself.
- Omitted ordinary-tax bands even when tax totals and cash payments are consistently lowered.
- RMD opening-balance anchors even when source balances and shortfall summaries are consistently lowered.
- Conversion transfer totals, taxable conversion income and each account's journals, including multiple unrounded transfers and consistently understated conversion tax/cash entries.
- Working early claimants already at birth-year FRA, overlap outside/inside the horizon and retirement/claim boundaries.
- Explicit unsupported 401(k) RMD tables, while accepting omitted/default or explicit uniform tables.

Existing synthetic trial-count and Wilson tests now also supply internally consistent annual MC summaries. The plan's year-range anchor runs before annual-series checks. Intermediate-year percentiles receive structural checks only: the manifest does not include all annual path balances needed for independent numerical reconstruction. The maximum displayed account residual remained $0.013647. These are local results; real-browser and GitHub Actions limitations below still apply.

Third review and conflict resolution: merged `main` at `76f43a6` into the PR based on `bc44f0f`, retaining both research API families and all 14 foundation tests. The resolved working tree passed **88 tests**, the 40-year / 300-path fictional run, **2,400 annual verifier assertions**, and all four HTML scenarios through `sh scripts/verify_local.sh`. The 17 new tests in `test_review_round3.py` cover all eight findings in Copilot's summary-only review:

- Real balances and inflation factors reconciled to the supplied plan.
- The entire output tax policy anchored before selecting NIIT thresholds.
- RMD taken/unmet aggregates checked against cent-rounded detail sums.
- Pre-1943 workers permitted to claim exactly at FRA without a delayed-credit schedule.
- Capital-gains tax capped by ordinary-rate tax on all taxable income, with selected-rate ledger and cash-funding tests; IRS 2026 Publication 505 Worksheet 2-7, lines 38–40.
- Both Wilson interval endpoints independently recomputed and malformed intervals rejected.
- Monte Carlo funded flags required to be boolean and consistent with failure years.
- Exactly three finite terminal percentiles required before quantile verification.

README and Skill instructions now describe the checked-in v2 engine and retained foundation APIs instead of referencing missing legacy commands. The four conflicts in README, SKILL, market-history and NIIT modules were reconciled without discarding main's existing interfaces. These are local results; the previously stated browser and Actions limitations still apply.

Second review pass: the `4c33969` checkout plus the follow-up verifier fixes passed **57 tests**, the 40-year / 300-path fictional run, **2,200 verifier assertions**, and all four HTML scenarios via `sh scripts/verify_local.sh`. The 12 added regression tests reject plan/manifest trial-count mismatches, falsified deterministic failure summaries, and consistently understated AGI/NIIT/cash entries. They also cover all supported taxable-income components, one-path plans, invalid counts, and the shared cent-rounding policy for shortfalls. Reports generated with the earlier sub-cent failure policy should be regenerated with the updated engine. Browser-testing and GitHub Actions limitations below still apply.

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
