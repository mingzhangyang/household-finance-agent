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

With a plan supplied, independent verification requires the manifest's trial count to equal `assumptions.trials`. It derives deterministic `failed` and `first_failure_year` from annual cent-rounded shortfalls and skipped conversions. Restricted AGI is recomposed from taxable wages, pension, required and extra pretax distributions, Roth conversions, cash interest, taxable Social Security and realized LTCG; both reported AGI and NIIT MAGI must match this sum. Net-after-tax event income and gross Social Security are not substituted for taxable income. These checks establish output consistency, not an independent reconstruction of tax law or every Monte Carlo path; use `trace` to replay individual paths.

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
