# M1 verification matrix

Engineering preparation; independent professional review and full M1 acceptance
remain pending. Field-level units/derivations are in [output-contract.md](output-contract.md).
No metric is allowed to inherit “verified” merely because another metric passed.

| Output-contract field group | Evidence | Mutation / replay | Remaining limit |
|---|---|---|---|
| Identity, input provenance and evidence status | verify_outputs plan/hash/metadata match; scope tests | Policy, provenance and false professional approval mutations | Documents not authenticated; no signature |
| Annual household/account totals, transfers and conservation | Independent arithmetic identities; test_ledger_contract; test_golden closed-form account balances | Missing row/account, reordered years, conversion/flow mutations; full replay | Correct balancing cannot prove every flow came from a correct rule |
| Income/spending timing, investment growth, optional draws and basis | Fixed cash-exhaustion, IRA and taxable funding cases; whole-result replay | Consistent wage→pension relabeling demonstrated; replay catches it | General source-income, basis and timing rules not independently validated |
| Federal tax bases, deductions, rates and method | IRS table boundaries; official SS worksheet; analytical conversion+LTCG funding | Existing senior/NIIT regressions; component and full-result mutation tests | Selected cases only; no complete independent Form 1040 calculator |
| FICA | Component arithmetic and existing fixtures; replay | Amount/type changes; consistent relabeling needs replay | No comprehensive independent cap/threshold validation |
| RMD and Roth transfers | Two-year independent RMD/account-continuity case; IRA conversion case | Existing unmet/transfer regressions and skipped-conversion failure checks | No broad independent RMD eligibility/lifecycle reference |
| Failed / first_failure_year | Recomputed from rounded annual shortfalls and skipped conversions | Forged summaries, shortfalls, cent boundaries in test_verifier_regressions | No actual lifetime guarantee |
| MC funded fraction / target fraction / Wilson | Independent aggregate and Wilson calculations | Changed counts, interval and path metadata; replay | Path truth depends on same engine; sampling interval only |
| Terminal P10/P50/P90 | Independent sorted manifest quantiles | Numeric/array/endpoint mutations; replay | Same engine supplies terminals |
| Intermediate annual P10/P50/P90 | Structure, ordering, years; full same-engine replay | Three coherently shifted percentiles pass arithmetic but FAIL replay | Not independently calculated by another model |
| Individual path funded/failure/terminal | Structure/aggregate; full seeded replay | Reorder/truncate/false flags; replay | Replay is reproducibility, not calibration |
| Notices, rule links, source IDs, human-readable limitations | Output catalog and source review; exact replay | Whole-result comparison | Not live source monitoring or professional review |
| UI sums, rounding, chart, CSV and JSON/plan exports | Handler regression, report round trip; M1/M5 browser evidence next | Export comparison and replay; UI numeric comparisons | Browser acceptance and offline arithmetic are distinct checks |
| Verifier counts/status | Re-run verifier; explicit validation_level and limitations | Malformed output raises VerifyFailure | Assertion count is neither coverage nor probability of correctness |

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
```

`verify_outputs` imports no engine: it verifies selected arithmetic identities.
`verify_replay` deliberately imports and reruns the main engine and compares every
field; it never claims independent model validation. The mutation suite includes
coordinated changes that preserve arithmetic, documenting why both checks are needed.
Neither pass upgrades input authentication, market calibration or professional review.

Remaining M1 gate: broaden independent cross-function cases to the final approved
scope, obtain independent reviewer sign-off, and resolve any substantive differences.
No external commercial planning-tool comparison is claimed.
