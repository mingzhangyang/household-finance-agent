# Validation summary — engine v2.2 (2026-10-28)

This is a repeatable QA record, not an independent CPA/CFP attestation. Execute the entire test suite and save the generated result and verifier JSON before claiming any count of passing tests. Output in `model_validation_report.md` outside the skill contains the latest complete fixture-specific numbers.

## PR #12 review fixes (2026-10-30)

Three high-severity Copilot findings; each new test fails on `fda0f0f` and passes after the fix.

- Funding solve: with basis far above value (ratio 12 in the reported plan), tax fell $1.10
  per dollar sold and the fixed-point steps alternated between two guesses until the run
  aborted. A bisection fallback now finishes the solve inside the bracket those steps
  produce. The reported plan funds at $1,185.71 tax and a $185.71 sale (hand solution
  2,490 / 2.1). Plans that converged before are identical: the example, six M1 cases and
  393 generated plans compared field by field with `fda0f0f`. The plan generator now draws
  basis up to 30× value, which reaches the fallback.
- Report: an empty `taxable_accounts` object, a record on the cash account or a treatment
  differing from the plan now hides conclusions and exports.
- Verifier: a carryover beside a legacy-labeled record is rejected even without the plan.
- `sh scripts/verify_local.sh`: **236 tests**; 6,868 assertions on the example; traced
  path 17 passed (6,880). `verify_m1_cases.py`: 6 cases / 14 years / 818 comparisons.
- Seeded sweeps (500 plans, seeds 7, 8, 9, with the wider basis range): 1,469 valid results
  and 5,876 traced paths passed; all 57,199 single-field mutations were rejected; no plan
  failed to converge. Real Chromium: 44 checks passed.

## M2 group 1: taxable brokerage account (2026-10-29)

Local results on branch `claude/epic-maxwell-5xrz9u`; not a GitHub Actions run or professional review.
Details in the [handover](handover-2026-10-29-taxable-account.md).

- `sh scripts/verify_local.sh`: **233 tests**; the 40-year / 300-path example (now with a
  distributions-treatment brokerage account) receives **6,868 verifier assertions**; exact
  replay passed; traced path 17 passed (6,880 assertions).
- `python scripts/verify_m1_cases.py`: **6 cases / 14 years / 818 comparisons** passed; the two
  new taxable-account cases (144 and 75 comparisons) matched on the first engine run.
- Known answers: Pub 550 Bob and Shelly ($7,000 loss, $26,000 taxable income → $3,000 deducted,
  $4,000 carried); the Form 1040 capital gain worksheet for 2026 single values ($7,187.50);
  Pub 915 line 3 with dividends and a loss; the carryover worksheet's short/long split checked
  on 2,000 random cases to give the statutory total.
- Seeded sweeps (`HFA_VERIFIER_FUZZ_PLANS=500`, seeds 7, 8, 9; half the generated plans use the
  new treatment with random yields and carryovers): 1,460 valid results and 5,840 traced paths
  passed; all 56,299 single-field mutations were rejected. Earlier 1,000-plan sweeps of the same
  seeds exposed two verifier gaps (cent tolerances on loss-year taxable income; a whole-basis
  loss on a cents-sized account), both fixed before the final runs.
- Legacy plans: the example, the four earlier M1 cases and four variants give identical results
  and traces on the previous and the new engine, apart from added fields and text.
- Real Chromium (Playwright 1.56.1, Chromium 153.0.8010.12, Noto CJK): **44 checks passed**,
  including the new taxable-account block for every year of every scenario at both viewports.

## PR #10 second review round (2026-10-29)

Copilot's second review and a follow-up self-review; local results.

- An RMD requirement must equal the unrounded prior balance over the divisor (an empty
  IRA could report a 4-cent unmet requirement); the basis rounding bound now holds over
  the whole cent interval (valid sales from a few-cent balance were rejected); notices
  must be the exact documented message (an `ira:spouse` notice satisfied the `ira:`
  prefix); paid plus unpaid tax and spending must match the amount due within one cent
  instead of five (self-review: a 4-cent fake shortfall passed after an exact draw).
  The new tests fail on the previous verifier.
- `sh scripts/verify_local.sh`: **184 tests**; 5,775 verifier assertions on the
  40-year / 300-path run; traced path 17 passed (5,790 assertions).
- Seeded sweeps (500 plans, seeds 7, 8, 9): 1,458 valid results and 5,832 traced paths
  passed; all 47,931 single-field mutations were rejected.

## PR #10 review fixes (2026-10-29)

Fixes for the four Copilot review findings; local results, not a GitHub Actions run.

- RMD taken must be the lesser of required and the balance before conversions and
  draws, with unmet = required − taken; a non-contributing member's unused 401(k)
  target no longer fails valid results; covered OASDI wages are bounded without the
  plan; the report rejects duplicate or out-of-ledger notice years. The tests for the
  four findings fail on the previous verifier or template; two more confirm that the
  per-person limit and a fake four-cent RMD shortfall are still rejected.
- `sh scripts/verify_local.sh`: **180 tests**; the 40-year / 300-path run receives
  **5,775 verifier assertions**; traced path 17 passed (5,790 assertions).
- `python scripts/verify_m1_cases.py`: 4 cases / 11 years / 599 comparisons passed.
- Seeded sweeps (500 plans, seeds 7, 8, 9; the generator now adds unused 401(k)
  targets): 1,458 valid results and 5,832 traced paths passed; all 47,931
  single-field mutations were rejected.

## M1 verification-depth follow-up (2026-10-29)

Local results for this change; not a GitHub Actions run, professional review or
statutory re-check of the register values.

- `sh scripts/verify_local.sh`: **175 tests**; the 40-year / 300-path fictional run
  now receives **5,715 verifier assertions** (previously 2,990); exact replay passed;
  traced path 17 passed with regenerated returns and its manifest entry (5,730 assertions).
- `python scripts/verify_m1_cases.py`: **4 cases / 11 years / 599 comparisons** passed,
  including the new growth, inflation and hypothetical-indexing case.
- Seeded generated-plan sweeps (`HFA_VERIFIER_FUZZ_PLANS=500`, seeds 7, 8, 9):
  1,466 valid results and 5,864 traced paths passed; all 49,208 single-field ledger
  mutations (USD 1, or 1e-6 for rates, returns, factors and RMD divisors) were rejected.
- [Source re-check](source-check-2026-10-29.md): every register value, all 49 Uniform
  Lifetime rows and the SSA research values matched official pages via search extracts
  (direct retrieval blocked); the verifier now checks RMD divisors against that table.
- [Primary-document review](primary-source-review-2026-10-29.md), same day: the IRS
  documents, statute, Federal Register notices and CFR text themselves confirmed every
  register value and all 49 table rows; twelve printed Rev. Proc. 2025-32 rows and Pub 915
  Example 3 became golden cases checked against both the engine and the verifier.
- Real Chromium with the pinned Playwright 1.56.1 (Chromium 153.0.8010.12, Noto CJK
  fonts): **36 checks passed**, including year-audit notice lists for every year and scenario.
- A sweep exposed one verifier tolerance error (basis rounding after small taxable
  sales) during development; the bound was corrected before commit. Engine numbers are unchanged.

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
