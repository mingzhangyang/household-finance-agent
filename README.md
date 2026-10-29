# Household Finance Agent — reproducible, auditable restricted v2.2

An installable ChatGPT Skill with an original interactive, offline financial planning report. **The v2.2 engine deliberately restricts supported tax and investment scenarios** to provide transparent, independently checkable calculations instead of broad but unverifiable claims.

See [ROADMAP.md](ROADMAP.md) for the phased plan, supported-scope decisions, deliverables and acceptance gates toward a validated planning assistant.

## Roadmap implementation status

M0 engineering now defines [supported scope](references/supported-scope.md) and the
[output contract](references/output-contract.md), with executable rejection tests
and separate report labels for accounting, input evidence, model scope and review.
The default remains offline federal-only research. Scope-owner/professional sign-off
is pending; passing arithmetic does not approve real household use.

M1 engineering adds [sourced golden cases](tests/golden/reference-cases.json),
closed-form Decimal withdrawal cross-checks and a [verification matrix](references/verification-matrix.md).
`verify_outputs.py` checks selected independent arithmetic; `verify_replay.py result.json
--plan plan.json` checks exact same-engine reproducibility, including intermediate
annual percentiles. Neither is full independent model validation.

The third slice adds [commit-level evidence collection and browser acceptance](references/release-evidence.md).
Run `python scripts/collect_evidence.py --output /tmp/hfa-evidence --browser`
from a clean checkout with Playwright/Chromium installed. Browser unavailability
is recorded as failure; omitting `--browser` records `not_run`. Neither is a pass.

The M1 acceptance follow-up adds [independent combined cases](references/m1-acceptance.md)
covering retirement/SS transitions, RMD/conversion/gains/NIIT, account depletion, and
stated returns with inflation distinct from hypothetical bracket indexing, over eleven
years. `python scripts/verify_m1_cases.py --output /tmp/m1-differences.json`
records 599 field/shape comparisons against case-specific Decimal equations.
CI installs pinned Playwright/Chromium and CJK fonts, then requires real desktop and
mobile-viewport acceptance, actual downloads/replay and print output in the supervised
evidence bundle. Physical devices, scope confirmation and professional sign-off remain pending.

The M1 verification-depth follow-up makes `verify_outputs.py` recompute every restricted
federal worksheet step and FICA each year from register values retyped in the verifier.
Given the plan, it also re-derives income timing, returns, RMD activation, conversion
schedules, withdrawal order, under-60 blocks and whether a reported shortfall is real.
`--trace` regenerates a traced Monte Carlo path's returns from the seed and checks its
ledger and manifest entry. See the [verification matrix](references/verification-matrix.md).
The year audit now lists blocked under-60 accounts, skipped conversions and unmet RMDs.
Engine numbers are unchanged; a pension amount now requires an explicit start age.
A [2026-10-29 source re-check](references/source-check-2026-10-29.md) found every register
value unchanged via search extracts, and the verifier now checks RMD divisors against the
confirmed Uniform Lifetime Table. A same-day [primary-document review](references/primary-source-review-2026-10-29.md)
read the IRS documents, statute, Federal Register notices and CFR text directly (with file
hashes and locators) and found no mismatches; printed Rev. Proc. 2025-32 rows and Pub 915
Example 3 are now golden cases for both the engine and the verifier.
Reviewers and the next maintainer should start from the [handover notes](references/handover-2026-10-29.md).

## Canonical offline verification (free, no Actions quota)

Run `sh scripts/verify_local.sh` from the repo. It checks syntax, all tracked Python tests, the 40-year fictional projection, 300 market paths, independent output verification, one independently verified traced path, the historical return fixture and offline HTML generation. This does **not** mean external tax/SSA certification or complete model calibration. GitHub Actions may be unavailable because the owner's quota is exhausted; do not repeatedly retry billing-blocked jobs. Keep the PR in Draft until exact-head review is complete.

## Quick start

```bash
python scripts/audit_plan.py validate examples/audited-household-2026.json
python scripts/audit_plan.py run examples/audited-household-2026.json --output result.json
python scripts/verify_outputs.py result.json --plan examples/audited-household-2026.json --engine-dir scripts --output verification.json
python scripts/render_audit.py examples/audited-household-2026.json --output financial_audit_dashboard.html
python scripts/audit_plan.py trace examples/audited-household-2026.json --path-index 17 --output monte_carlo_path_17.json
python scripts/verify_outputs.py monte_carlo_path_17.json --plan examples/audited-household-2026.json --trace --trace-result result.json
python -m unittest discover -s tests -v
```

Open `financial_audit_dashboard.html` locally in a browser. The tool can switch between four **Python-precomputed** scenarios, drill down by year into federal tax brackets and all account transfers, inspect Monte Carlo paths, and export annual cash flow CSV or audited JSON. The report is offline and contains its underlying private data in plaintext: **do not publish a real family's file**.

Each scenario's exact plan (including seed and return assumptions) is embedded in the report. **导出方案 JSON** downloads the selected plan as `financial-plan.json`, ready for `audit_plan.py run` or `trace`. **导出审计 JSON** downloads a bundle with `plan`, `result`, and `verification`; extract its `result` object when using the output verifier CLI. The lower-return comparison floors each adjusted mean at the supported -50% boundary; its exported plan records the actual assumptions used.

## What v2.2 improves

- Validate monetary types, dates, account ownership, contribution limits, IRA before-tax basis, selected RMD treatment, and SSA benefit assumptions; reject unsupported scenarios instead of inventing behavior.
- Apply 2026 official federal tax brackets, standard deductions and extra-senior-deduction assumptions, Social Security taxation, stacked long-term capital-gains rates, FICA, 2027 published Social Security wage base, uniform lifetime RMDs, 401(k) pre-tax deferrals and limited IRA-to-Roth conversions.
- Model cash/retirement-account transfers separately from external spending and tax flows; write double-entry conservation journal, tax-bracket breakdown and per-account residual per year.
- Use seeded two-asset correlated Gaussian Monte Carlo (unvalidated returns) with a path manifest, deterministic replay, Wilson sampling interval and code/input SHA256 identifiers.
- NIIT 3.8% is included in annual cash-funding and taxable dispositions, with modeled NII limited to bank interest and positive long-term realized gains. The verifier independently checks its income base and rate. The IRS $250k joint / $200k single MAGI thresholds are not inflated.
- The 2026 extra senior deduction phases out each eligible person’s $6,000 by 6% of joint MAGI over $150k before summing: two eligible spouses receive $10,800 at $160k MAGI and $0 at $250k.
- `verify_outputs.py` is a separately implemented output-only verifier; it recomputes arithmetic and the restricted worksheet steps from JSON and retyped register values without importing the main engine. Tampering tests intentionally change results, including coherent multi-field forgeries, to confirm detection.

## Limits and status

**Not approved or suitable by itself for making real retirement, tax or investment transactions.** Only a restricted subset of US federal personal finance rules is implemented. No state income tax, NIIT treatment for dividends/passive income or foreign exclusion, credits, Social Security benefit formula, survivor benefits, inherited retirement accounts, QCD, Roth qualification checking, IRMAA, ACA, real-world return calibration, mortality model, mortgage/debt schedules or robust tax-lot engine. Taxes in 2027 and later use a **hypothetical indexed 2026 tax schedule**, not enacted future tax law; SSA's 2027 wage cap is explicitly a separate published exception. Some yearly timing conventions use year-end approximations.

The legacy v1 engine and its browser suite are not present in this checkout. The v2.2 commands above refer to the actual checked-in engine.

Experimental professional reference modules `scripts/social_security.py`, `scripts/lifecycle.py`, and `scripts/market_history.py` are separately callable, but **are not yet integrated into the main projection engine**. The partial 2000–2018 return CSV is only a documented regression fixture, not adequate retirement calibration. No RightCapital numeric cross-validation has occurred.

See `references/professional-validation-gates.md` and `references/rules-provenance.md`, `references/audit-methodology.md`, and `references/validation-report.md`.


The merged foundation APIs remain available: `ssa_benefits.py`, `lifecycle_rules.py`, `tax_extensions.niit_core`, and `market_history.load_history`, `metrics`, `historical_windows`, and `paired_block_bootstrap`. Their existing tests run under the same full verification script. The historical loader accepts decimal-return columns; `load_annual_csv` continues to accept the percentage-return fixture schema. Neither API is automatically wired into the main projection.
