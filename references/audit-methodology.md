# Model audit methodology and separate verification

## Two distinct requirements

1. **Software correctness**: arithmetic, tax reference tables, conditional logic and account transfers are deterministic, source-linked and tested. A separate `verify_outputs.py` verifies a saved output **without importing** financial-calculation modules.
2. **Professional planning validity**: user inputs, real-world market calibration, future legislation, SSA benefit projections, investment tax-lot accounting and household events must also be correct. **This second requirement is not met by v2.2.** A CPA/CFP may inspect the ledger but has not certified it.

## Annual computation (all nominal USD)

For year `t`:

1. Read every account balance at prior December 31. Apply same-year cash interest and hypothetical market return (year-end flow convention).
2. Determine who remains employed, wages, inflation-adjusted employee pretax 401(k) transfers to owned retirement accounts, pensions, supplied SSA retirement benefits and one-time net income/expenses.
3. Calculate RMD from *prior-year-end* fully pretax balance and the owner age's Uniform Lifetime Table divisor. Treat RMD as internal account-to-cash transfer and ordinary taxable income.
4. Apply scheduled same-owner traditional IRA -> Roth conversions as internal transfers and as **ordinary taxable income**. Do not allow RMD to count toward the conversion amount.
5. Iteratively solve for withdrawals to meet household expenditure **plus** resulting federal income tax, NIIT and payroll tax. Treat positive proportional long-term gains on taxable account sales as preferential gains; pretax IRA/401k sales as ordinary income. Block penalty-sensitive under-age-60 withdrawals rather than assume exceptions.
6. Set tax paid and spending paid to actual available cash. For funded status, round unpaid tax, unmet spending and unmet RMD to cents using Python's `round(amount, 2)`, exactly as exported in the ledger. Any positive rounded amount fails the year; sub-cent amounts rounding to zero do not. Any skipped requested conversion fails regardless of its amount. The engine, output verifier and report use this same policy; arithmetic conservation still uses unrounded amounts.
7. Verify the household equation and each account's complete journal entry, including deposits, RMD, conversion, optional draws, cash receipts and cash tax/spending. Raising an exception on mismatch > $0.01.

Whole-household balance equation:

`ending_total = opening_total + gains + gross_external_income - actual_living_spend - actual_tax_paid`

401(k) contributions, RMD distributions and Roth conversions are **internal transfers**, not new outside wealth. Pro-rata taxable basis decreases when a taxable investment is sold. The next year's basis is carried forward. The model assumes all sale proceeds above prorated basis are positive long-term gains, no loss offset or tax lot selection.

## Market paths and interpretation

For each year draw two independent standard normals `z1,z2`. Set hypothetical stock `R_e=mu_e+sigma_e*z1`; bond `R_b=mu_b+sigma_b*(rho*z1+sqrt(1-rho^2)*z2)`; blended return `R=equity_weight*R_e+(1-equity_weight)*R_b-fee`, floored at -99.9%. `random.Random(seed)` and fixed trial count permit exact replay. Path `i` succeeds iff there are no years with unpaid taxes, unmet living expenses, unmet RMDs or skipped requested conversions. Wilson 95% interval describes random sample error ONLY, not uncertainty in the market assumptions.

Every saved report contains `simulated_path_manifest` of `{path_index, funded, first_failure_year, terminal_real}` for all paths. The saved seed and `trace --path-index i` reconstruct all annual flows for any selected path. Percentiles are linear interpolations of sorted terminal **inflation-adjusted** balances. The display has P10/P50/P90 yearly marginal bands, which are **not** percentile trajectories of the same individual path.

With a plan supplied, independent verification requires the manifest's trial count to equal `assumptions.trials`. It derives deterministic `failed` and `first_failure_year` from annual cent-rounded shortfalls and skipped conversions. Restricted AGI is recomposed from taxable wages, pension, required and extra pretax distributions, Roth conversions, cash interest, taxable Social Security and realized LTCG; both reported AGI and NIIT MAGI must match this sum. Net-after-tax event income and gross Social Security are not substituted for taxable income. These checks establish output consistency, not an independent reconstruction of every Monte Carlo path; use `trace` with `verify_outputs.py --trace` for individual paths.

The verifier also anchors the entire output tax policy and the yearly inflation factor to the supplied plan, checks nominal-to-real closing balances, reconciles cent-rounded RMD detail sums to annual totals, recomputes Wilson interval endpoints, and requires all three terminal percentiles. Every path must have a boolean funded status and a failure year that is null exactly for funded paths, otherwise an integer in the projection horizon. Without a plan, real-balance checks use the reported eight-decimal factor with an allowance for factor rounding; they cannot authenticate the inflation assumption.

Income tax follows the lower-tax comparison in IRS 2026 Publication 505 Worksheet 2-7: preferential gain stacking versus ordinary-rate tax on all taxable income. If the ordinary-rate cap is lower, the ordinary-income component stays on its ordinary brackets and the gain component uses the incremental ordinary brackets above it. The report labels the selected method and displays those actual rates, so components still sum and multiply correctly.

Annual Monte Carlo bands must cover every projected year exactly once, contain finite ordered P10/P50/P90 values, and report funded-to-date counts reconstructed from each path's first failure year (the failure year itself is excluded). Final-year percentiles are recomputed from terminal manifest balances. **Intermediate-year percentile values cannot be independently recomputed from this manifest**, which does not save every path's annual balances; those values receive structural checks only.

Ordinary tax bands must cover the full reported ordinary taxable amount. Each RMD's prior-December balance is anchored to that account's opening balance, allowing one cent for displayed rounding. Completed conversion transfers must sum to the cent-rounded taxable conversion total and match each account's unrounded conversion inflow/outflow journal; skipped transfers are excluded.

The verifier also recomputes each restricted worksheet step every year from 2026 register values retyped in `verify_outputs.py`, not imported from `tax2026.py`: provisional income and the Publication 915 taxable benefit; with the plan, the indexed standard/age-65 deduction and the enhanced senior deduction; taxable ordinary income and gains; every ordinary bracket line's start, top, rate and amount; both the stacked gain zones and the ordinary-rate cap, requiring the reported method to be the lower; and FICA caps, rates and the Additional Medicare threshold, with covered wages equal to the lesser of gross wages and the base for a single filer and at least that for joint filers. Account journals must link to row totals and stay nonnegative; invested-account growth must equal opening balance times the reported return; proportional basis and realized gain are recomputed from the prior basis and the value at sale. Each RMD taken must be the lesser of the requirement and the account balance after growth and deferrals, before conversions and draws can empty it, and the unmet amount must be the remainder.

With the plan it re-derives wages, each member's deferral within own wages and the base elective limit, benefits, pensions, events and spending, the cash yield and deterministic return, RMD activation by start age, the conversion schedule with execute/skip legitimacy from the post-RMD balance, withdrawal order, under-60 blocks and their notices. A visible shortfall must coincide with exhausted cash and accessible accounts, any draw with exhausted cash, and taxes are paid before spending. `verify_outputs.py --trace` applies the same checks to any `trace` output after regenerating its returns from the seed and path index, and with `--trace-result` matches the path's manifest entry. These checks compare outputs with documented conventions and the dated register; they do not establish that either suits a household. RMD divisors are checked against the Uniform Lifetime Table retyped in the verifier after the [2026-10-29 source re-check](source-check-2026-10-29.md).

The earnings-test input gate checks only projected years containing positive wages and benefits, claimed status and an age below birth-year FRA. FRA follows the [SSA birth-year table](https://www.ssa.gov/benefits/retirement/planner/agereduction.html), rounded up to a whole year; this engine has no birth dates or partial-year earnings test. Early claims made before the projection do not by themselves invalidate a person already at FRA. A 401(k) may omit `rmd_table` (Uniform Lifetime default), but an explicitly supplied non-uniform table is rejected, as it is for IRAs.

## Independent test protocol

- Obtain official reference rules and compare individual tax breakpoints, marginal rates, SSA provisional income, 2026 SS wage base, official 2027 SSA wage base, LTCG stacking, enhanced senior deduction, 401(k) limits and Pub 590-B RMD divisors.
- Use hand calculations not copied from the implementation; e.g., $100k 2026 gross single wage, $20k traditional 401(k) deferral, $60k living expense, no interest/gains => $80k ordinary wage, 2026 standard deduction $16,100, modeled federal tax $8,770, FICA $7,650, cash after wage/deferral/expense/taxes $3,580, 401(k) closing +$20k.
- Independently recompose bracket and gains lines, all 2027 earnings, total tax and each account balance; reject a mutated amount, path summary or data SHA.
- Validate every scenario's stochastic paths and deterministic annual rows; browser tests must check that four scenes are independent payloads, year drilldown works, JSON/CSV downloads work, and mobile layout has no overflow.
- Calibrate real financial assumptions and cross-validate with independent professional planning packages before adopting this for actual family decisions. **No calibration or independent third-party professional sign-off currently exists.**

## Known critical gaps / deployment gates

- **2027+ projected US tax law:** except for specifically published SSA 2027 wage cap, 2026 federal brackets are indexed with an arbitrary planning input, not official 2027 or future IRS law.
- **Federal-only simplified income tax:** excludes state tax, NIIT on sources outside modeled cash interest and positive long-term gains, credits, AMT, Medicare IRMAA, ACA, charitable itemization, passive income, ordinary dividends and investment interest besides cash yield, plus inherited IRA and capital gains tax lots.
- **SSA estimates:** user-supplied amount for selected claim age; cannot optimize claiming age, family spousal/survivor benefits, earnings test or COLA reality.
- **Retirement timing:** years, not dates; 59½ is approximated with a conservative under-age-60 restriction, no early-withdrawal exemptions; first-year RMD deferral to April of next year omitted.
- **Monte Carlo:** no historical fit, dynamic correlations, fat tails, sequence-specific spending adjustments, tax-driven asset allocation or return-regime simulation.
- **Life events:** no mortality, death of one spouse, divorce, remarriage, inheritance, disability, changing filing status, pension optionality or long-term-care stochastic expenses.

Until these are addressed for a specific family's profile, describe outputs as **reproducible restricted-scope what-if estimates** rather than assured retirement probabilities, complete financial plans, or professionally approved tax calculations.
