# M1 verification matrix

Engineering preparation; independent professional review and full M1 acceptance
remain pending. Field-level units/derivations are in [output-contract.md](output-contract.md).
No metric is allowed to inherit “verified” merely because another metric passed.

| Output-contract field group | Evidence | Mutation / replay | Remaining limit |
|---|---|---|---|
| Identity, input provenance and evidence status | verify_outputs plan/hash/metadata match; scope tests | Policy, provenance and false professional approval mutations | Documents not authenticated; no signature |
| Annual household/account totals, transfers and conservation | Independent arithmetic identities; nonnegative balances and flows; account journals linked to row deferrals, draws, RMDs and cash receipts/payments; test_ledger_contract; test_golden closed-form account balances | Missing row/account, reordered years, conversion/flow mutations; inflated cash receipts and payments, negative draw, moved draws; full replay | Correct balancing cannot prove every flow came from a correct rule |
| Income/spending timing, investment growth, optional draws and basis | Growth = opening × reported return; proportional basis and realized gain recomputed. With the plan: wages, each member's deferral within own wages and the base elective limit, benefits, pensions, events, spending, cash yield and deterministic return re-derived; growth-indexing M1 case | Coherent wage→pension relabeling passes output-only checks but fails the plan schedule; early Social Security, cash interest above yield, moved growth, raised basis, understated gain, deferral above the limit; a non-contributor's unused 401(k) target must pass | Checks documented conventions, not their real-world fit; first-year basis needs the plan |
| Federal tax bases, deductions, rates and method | Every year: provisional income and Publication 915 taxable benefit, taxable bases, each ordinary bracket line (start, top, rate, amount), stacked zones versus ordinary-rate cap, recomputed from register values retyped in the verifier; with the plan, indexed standard/age-65 and enhanced senior deductions. IRS table boundaries; official SS worksheet; analytical funding cases | Moved bracket boundary, understated taxable benefit, inflated deduction, mislabeled method, altered index; senior/NIIT regressions | Register values read against the primary documents on 2026-10-29; the verifier never fetches sources at run time; restricted scope only; no complete Form 1040 |
| Published versus projected rule basis | Each row's `rule_basis` and `tax.tax_law_year`/`rule_multiplier`/`policy` recomputed from the verifier's retyped registry: own published year, else the latest published year indexed at the plan rate; trace rows too | Projected year labeled published, published labeled projected, changed base year, source ID or index, missing or extra family, altered disclosure; one-sided registry update (`test_rule_years.py`) | Labels follow the dated register; whether IRS has since published a year is a manual check ([rules-provenance.md](rules-provenance.md)) |
| FICA | Published 2026/2027 OASDI caps and later caps projected from the latest published cap, employee rates and Additional Medicare threshold recomputed; covered wages equal min(gross wages, base) for a single filer and are at least that for joint filers; with the plan, per-person covered wages | Wage-base and Additional Medicare forgeries; understated covered wages; relabeled wages exceed covered wages | Household-level Additional Medicare; no employer withholding timing |
| RMD and Roth transfers | Two-year independent RMD/account-continuity case; IRA conversion case. Required = unrounded prior balance ÷ divisor exactly; taken = lesser of required and the balance after growth and deferrals, before conversions and draws; unmet = required − taken. With the plan: RMD records exactly for owners at start age 73/75 with matching ages; conversions matched to the schedule in order, execute/skip judged against the post-RMD balance | Omitted RMD, wrong-age divisor, understated RMD moved into a draw that empties the account, four-cent fake RMD shortfall beside a balance, fake requirement on an empty account, removed conversion, executable conversion reported as skipped; unmet/transfer regressions | Divisors match 26 CFR 1.401(a)(9)-9(c) and Pub 590-B (2025) Table III row by row ([primary review](primary-source-review-2026-10-29.md)) |
| Failed / first_failure_year | Recomputed from rounded annual shortfalls and skipped conversions; a shortfall requires exhausted cash and (with the plan) exhausted accessible accounts; any draw requires exhausted cash; taxes paid before spending; an RMD shortfall only when the balance before conversions and draws was below the requirement; paid + unpaid tax and paid + unmet spending match the amount due within one cent | Forged summaries, cent shortfall beside remaining cash, four-cent shortfall after an exact draw, fake RMD failure, blocked account drawn | No actual lifetime guarantee; cent-rounded balances leave a one-cent ambiguity in shortfall amounts |
| MC funded fraction / target fraction / Wilson | Independent aggregate and Wilson calculations | Changed counts, interval and path metadata; replay | Path truth depends on same engine; sampling interval only |
| Terminal P10/P50/P90 | Independent sorted manifest quantiles | Numeric/array/endpoint mutations; replay | Same engine supplies terminals |
| Intermediate annual P10/P50/P90 | Structure, ordering, years; full same-engine replay | Three coherently shifted percentiles pass arithmetic but FAIL replay | Not independently calculated by another model |
| Individual path funded/failure/terminal | Structure/aggregate; any `trace` output verified with `--trace`: returns regenerated from seed and path index, full ledger checks, manifest entry cross-checked; full seeded replay | Reorder/truncate/false flags; relabeled path index, altered return, manifest terminal mismatch; replay | Only traced paths are checked independently; replay is reproducibility, not calibration |
| Notices, rule links, source IDs, human-readable limitations | Notice structure; with the plan, every blocked account reached by funding is listed with its exact documented message and no other message is allowed (IDs may contain ':'); output catalog and source review; exact replay | Removed, invented or altered notices, including a notice hidden by an ID prefix; whole-result comparison | Not live source monitoring or professional review |
| UI sums, rounding, chart, CSV and JSON/plan exports | Handler regression and real Chromium suite required in CI; year audit lists notices, skipped conversions and unmet RMDs verbatim; notice years must be unique ledger years | All years at two viewports; plan/bundle replay; CSV, notices and errors; duplicate or out-of-ledger notice years hide conclusions | Chromium mobile emulation is not physical Safari/Android acceptance |
| Verifier counts/status | Re-run verifier; validation_level `output_arithmetic_and_restricted_rule_steps`, `verified_plan_conventions` and limitations | Malformed output raises VerifyFailure; seeded single-field mutation sweep | Assertion count is neither coverage nor probability of correctness |

## Golden-case independence and tolerances

`tests/golden/reference-cases.json` records source URL, source edition/year, locator,
input conventions, derivation and predeclared tolerance. Component answers come from
published tables/worksheets or recorded arithmetic. Projection answers were derived
from equations, not snapshots of engine output. `test_golden.py` additionally solves
multi-year tax-funded IRA withdrawals using Decimal closed-form equations, unlike
the main iterative funding loop. Future-year projections explicitly freeze the 2026
schedule as a hypothetical convention. They do not assert future enacted tax law.

Component unrounded rate arithmetic: absolute $0.000001; worksheet benefit: $0.005;
cent-exported integration balances/taxes: $0.01. Failure years and booleans must match
exactly. Existing output-verifier rounding tolerances remain field-specific; account
reconstruction residuals can exceed $0.01 because independently rounded exported
components are summed (this differs from the engine's unrounded residual gate).

## Run and interpretation

```
python -m unittest discover -s tests -v
python scripts/verify_outputs.py result.json --plan plan.json --engine-dir scripts
python scripts/verify_replay.py result.json --plan plan.json
python scripts/verify_outputs.py trace.json --plan plan.json --trace --trace-result result.json
```

`verify_outputs` imports no engine: it verifies arithmetic identities, recomputes
each restricted worksheet step from register values retyped in the verifier and,
with the plan, re-derives timing, returns, RMD/conversion schedules, funding order
and shortfall legitimacy. `--trace` applies the same checks to one traced path.
`verify_replay` deliberately imports and reruns the main engine and compares every
field; it never claims independent model validation. The mutation suite includes
coordinated changes that preserve arithmetic, documenting why both checks are needed.
Neither pass upgrades input authentication, market calibration or professional review.

Remaining M1 gate: broaden independent cross-function cases to the final approved
scope, obtain independent reviewer sign-off, and resolve any substantive differences.
No external commercial planning-tool comparison is claimed.

## M1 combined-case acceptance follow-up

[M1 acceptance](m1-acceptance.md) adds four frozen fictional plans with eleven annual
rows and 599 comparisons against independent Decimal equations. The references cover
MFJ retirement/pension/SS timing with a tax-funded IRA draw, two years of RMD and
conversion with both NIIT limiting bases, cash/taxable/IRA/Roth exhaustion with
an exact first-failure year, and stated returns with 3% inflation, a distinct 2%
hypothetical bracket index, wages above the OASDI cap, NIIT and appreciated sales. Monetary tolerance is USD 0.01; years, status, divisor
and the zero-return funded fraction are exact. The collector saves all differences
to `independent-cases.json`. These cases strengthen the rows above; they do not
remove the general model/coverage limits or substitute for professional review.

## Independent rule-step and plan-convention verification (2026-10-29)

Engineering strengthening of M1 evidence; no engine numbers changed and no M0/M1
sign-off is implied. The verifier's 2026 constants are retyped from
[rules-provenance.md](rules-provenance.md); they were not re-checked against the
primary sources when this verifier was extended. Tolerances follow cent-rounding
propagation; the method choice allows a one-cent tie.

`tests/test_verifier_independence.py` builds coherent forgeries that keep
conservation and AGI identities intact, then names the check that rejects each.
Its seeded generator produces single/MFJ plans with blocked early retirees, RMDs,
conversions, unused 401(k) targets, sales at a gain or loss and extreme returns. Every valid deterministic
ledger and traced path must pass; every numeric leaf of sampled rows, changed by
USD 1 (1e-6 for rates, returns, factors and RMD divisors), must be rejected with the
plan. RMD divisors are checked against the Uniform Lifetime Table retyped after the
[2026-10-29 source re-check](source-check-2026-10-29.md) and since matched row by row to the
regulation text in the [primary-document review](primary-source-review-2026-10-29.md).
Set `HFA_VERIFIER_FUZZ_PLANS` and `HFA_VERIFIER_FUZZ_SEED` for larger local sweeps.

Without the plan the verifier cannot check ages, RMD activation, conversion
schedules, first-year basis, cash yield, the deterministic return or how joint
filers' covered wages split between spouses; small rate or
factor changes on small balances can stay within rounding tolerance.
