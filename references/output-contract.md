# Output contract 1.0

This catalog covers report numbers, JSON exports, CSV and trace output. `R` means
one evaluate result; `L` = R.deterministic_annual_ledger; `Y` = L.rows[*]; `T` = Y.tax;
`P` = Y.payroll_tax; `A` = any account ID. The report embeds four exact plans/results
and output-verifier reports. The export contract is `{plan,result,verification}`.
An exported plan is a schema 2.0 input. A bare result is the verifier CLI input.

The HTML bundle also carries `plan_json`, one Python-serialized JSON string per
scenario. Both standalone plan downloads and the `plan` member of audit downloads
use this text verbatim. JavaScript must not reserialize the plan: `143000.0` and
`143000` have equal numeric values but different Python input fingerprints. Missing,
malformed or value-inconsistent export text fails the report gate. The input hash
algorithm is unchanged; prior fingerprints remain valid. Regression tests read the
actual JavaScript download blobs in Python and replay both exported plan forms.

## Units, timing and presentation

USD nominal at year-end unless marked real (2026 purchasing power). Input opening
balances are 2026-12-31; output begins 2027. Rates/fractions are decimals, not percent.
Engine arithmetic uses Python floats and `round` (ties to even); standard exported
amounts use 2 decimals; account-flow, RMD and conversion records retain precision;
residuals use 6 decimals; inflation/rule multipliers and NIIT rate use 8 decimals;
simulation fractions use 5 decimals, Wilson endpoints 4. `null` first-failure means
no modeled failure within the horizon, not infinite solvency.

UI summary/cashflow/path amounts use Intl USD whole-dollar rounding; year details
and account tables use cents. Rates and fractions show one percentage decimal.
Chart axes are scaled $K/$M, coordinates rounded to 2 decimals. CSV preserves JSON
values. No calculation should be reconstructed from rounded chart coordinates.

## Source, calculation and validation catalog

“Arithmetic” below means `verify_outputs.verify` against saved outputs, not independent
rule selection. “Replay” means same-code reproducibility, not independent correctness.
The M1 verification matrix further records gaps and mutation evidence.

| Fields | Unit / derivation | Validation or explicit limit |
|---|---|---|
| R.engine_version, policy, scenario, opening_balance_status, tax_policy, year_range | Version / input copy; start = as_of_year+1 | Policy/range checks; input hash; no proof that a policy is appropriate |
| R.input_sha256, engine_source_sha256 | SHA256 canonical sorted compact UTF-8 input / concatenated audit_plan, tax2026, tax_extensions bytes | Recomputed with supplied plan / source directory; no signature |
| R.input_provenance, evidence_status | Supplied register plus fixed research-status metadata | Structural input validation; original documents and professional review not verified |
| R.rules_sources, rule_scope | Source links and model limitations | Version-controlled disclosures, not live external-source verification |
| R.success_paths, trials | Count of funded paths / input trial count | Manifest count and boolean aggregation |
| R.modeled_all_obligations_funded_fraction | success_paths/trials | Arithmetic, 0.00001 tolerance |
| R.funded_and_target_fraction | Paths funded AND terminal_real ≥ input target, divided by trials | Arithmetic with plan, 0.00001 tolerance |
| R.mc_sampling_wilson95[0,1] | 95% binomial Wilson interval, z=1.96 | Independent interval formula, 0.00005 tolerance; sampling only |
| R.terminal_real_p10_p50_p90 | USD 2026 real, sorted path terminals; linear rank (N−1)q | Recompute from manifest, $0.02 tolerance |
| R.annual_real_percentiles[*].year,p10,p50,p90,paths_funded_to_date | Year, real USD ranks, funded through that year | Year/order/count/end-quantile checks; intermediate amounts require replay, not independently verified |
| R.simulated_path_manifest[*].path_index,funded,first_failure_year,terminal_real | Zero-based index, boolean, year/null, real USD | Structure and aggregation checked; path truth requires replay, not independent modeling |
| L.failed,first_failure_year | Any rounded positive spending/tax/RMD shortfall OR skipped conversion | Recomputed from annual rows; exact decision equality |
| L.notices[*].year,blocks | Year and blocked-under-60 account messages | Runtime disclosure; not a penalty calculation |
| Y.year,age_primary,market_return,inflation_factor | Year, whole age, portfolio decimal return, (1+inflation)^(year−2026) | Year continuity and inflation checked; age/return replay |
| Y.opening_total,opening_accounts[A] | Prior closing / plan initial balances | Per-account/total continuity and sums |
| Y.investment_growth_total,growth_by_account[A] | Opening balance × portfolio return or cash yield | Conservation checked; return application requires independent case / replay |
| Y.wages_gross,wages_taxable,pretax_contributions,pretax_contribution_by_account[A] | Wages grown until retirement, less eligible contributions | Gross−contributions relation checked; income timing / contribution legality needs selected cases or replay |
| Y.social_security_gross,pension_gross,other_after_tax_income | Input amounts escalated and activated at age/year | Included in conservation; source benefits not independently verified |
| Y.living_expenses_due,living_expenses_paid,unmet_spending | Indexed living + events; paid subject to cash after taxes | Due=paid+unmet; input timing replay |
| Y.rmd[*].account,age,previous_dec31_balance,divisor,required,taken,unmet | Account / age; USD nominal, divisor in years; prior balance/divisor | Balance, division and taken+unmet checked; table selection not independently verified |
| Y.rmd_total,unmet_rmd | Sum of taken / unmet | Cent-rounded sums; $1e-8 equality tolerance |
| Y.roth_converted,conversion_transfers[*].from,to,amount | Internal same-owner transfers, USD nominal | Account IDs, amount, summed taxable conversion checked; availability needs replay |
| Y.skipped_conversions[*].year,from,amount,reason | Requested transfer not executed | Failure flag checked; source-funding truth needs replay |
| Y.extra_draws[A],realized_ltcg,ira_extra_taxable,taxable_basis_end[A] | USD nominal; account funding and proportional basis | Included in tax / conservation; basis and withdrawal ordering require independent cases / replay |
| T.gross_ordinary,taxable_social_security,adjusted_gross_income,ss_provisional_income | USD nominal; ordinary components and simplified SS formula | Ordinary/AGI components checked; SS rule needs golden cases |
| T.standard_plus_age_deduction,enhanced_senior_deduction,deduction_total | USD nominal; indexed standard/age plus temporary senior deduction | Selected golden cases / replay; not full deduction eligibility verification |
| T.ordinary_taxable,long_term_gain_taxable | USD nominal; deductions applied to ordinary then gains | Bracket coverage checked; deductions need selected cases |
| T.ordinary_bracket_lines[*].from,to,rate,taxable,tax | USD thresholds (to may be null), decimal rate, portion and product | Product/sum checked; statutory rate and boundary selection not independently verified for all inputs |
| T.capital_gain_rate_lines[*].rate,taxable,tax | Decimal rate, USD portion and tax | Product/sum checked; stacking versus ordinary cap selected-case validation |
| T.ordinary_tax,capital_gains_tax,federal_income_tax,income_tax_method | USD; chosen lesser ordinary-rate-cap / preferred method | Component sums; selected independent tax cases; not all tax law verified |
| T.niit_magi_assumed_equal_agi,niit_net_investment_income,niit_threshold,niit_tax_base,niit_rate,niit_due,total_federal_income_and_niit | USD except decimal rate; restricted income base and threshold | Independently recomputed NIIT from modeled components; no unsupported income/adjustments |
| T.tax_law_year,year,rule_multiplier,policy,unmodeled | 2026 reference; projected year; hypothetical index; disclosures | Input/version/replay; not future legislation |
| P.wage_base_per_person,oasdhi_taxable_wages_by_person,additional_medicare_taxable_wages,social_security_tax,medicare_tax,additional_medicare_tax,total | USD nominal, employee FICA only | Component sum; selected cases/replay for caps and rate selection |
| Y.tax_due_total,tax_paid,unpaid_tax | USD nominal, federal+NIIT+FICA and cash settlement | Components and paid+unpaid checked |
| Y.closing_total,closing_accounts[A],closing_total_real | USD nominal; real = nominal / inflation factor | Conservation, account sums, deflation; account-count-dependent rounding tolerance |
| Y.reconciliation_residual,account_reconciliation_residuals[A] | USD, closing minus reconstructed closing | $0.01 residual gate; exported rounded-account reconstruction generally $0.05 |
| Y.account_flows[A].contribution,required_distribution,roth_conversion_out,roth_conversion_in,optional_draw,cash_external_inflow,cash_tax_and_spending_outflow,cash_received_rmd,cash_received_draws | USD nominal positive flow magnitudes | Per-account conservation, conversion cross-check; not every individual flow independently sourced |
| Y.cash_account_id,source_ids | Input account / rule-source identifiers | Schema and traceability; not independent source certification |
| verification.passed,annual_rows,mc_paths,assertions_checked,max_account_residual_dollars,verified_input_hash,verified_engine_hash,validation_level,limitations | Boolean, counts, USD residual, booleans | Verifier diagnostics; assertion count is not coverage or accuracy |
| trace.engine_version,trial_index,input_sha256,annual_returns,path_ledger | Same version/input identity; decimal returns; L-shaped ledger | Seed/path-index replay; identical engine, not independent reference |

## UI-derived numbers and aliases

- Snapshot and comparison: funded fraction, terminal P50, first-row
  `tax.federal_income_tax` (excludes NIIT/FICA), first failure year.
- Annual table: `social_security_gross+pension_gross`, and monetary gap
  `unmet_spending+unpaid_tax+unmet_rmd`; a skipped conversion is a separate failure
  and can coexist with a zero monetary gap.
- Detail conservation equation: external income = wages+SS+pension+net events;
  other displayed amounts map directly to Y/T/P/flows above.
- Plot: annual P10/P50/P90 and deterministic real closing; labels P10/P50/P90 and
  95% describe fixed quantile/interval choices, not predictive confidence.
- Evidence count = input_provenance.register.length; neither this count nor
  `documented_verified` authenticates source documents.
- Scenario “+10%” multiplies real living expense by 1.10. “Early retirement” uses
  max(40, age−3), so the label is a requested change and the exported plan is exact.
  Lower means floor at −0.5. This is comparison of assumptions, not optimization.

Any new report field must receive a unit, source, rounding rule and verification
path or explicit limitation here before it is presented as a validated metric.

Replay output contains passed, validation_level=same_engine_replay, independent_model_validation=false and paths_replayed. It certifies reproducibility of all exported fields against the same local engine, not independent model correctness.

Present output provenance is validated even without `--plan`: supported mode, register list, entry fields, source/confidence enums and valid dates. `not_provided` requires an empty register. This is metadata syntax checking, not document authentication or proof that pointers resolve; comparison with supplied input remains a separate check. Legacy results with neither provenance nor evidence status remain supported.
