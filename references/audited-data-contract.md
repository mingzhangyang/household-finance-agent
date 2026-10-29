# Audited v2.2 household input contract (schema v2.0)

The input schema is deliberately strict and enforced by `python scripts/audit_plan.py validate examples/audited-household-2026.json`. Unknown fields fail validation; silently guessing missing amounts is prohibited. The result engine version is `2.2-auditable-restricted` while the independent input schema version is `"2.0"`.

## Required household and dated balances

- `currency: "USD"`, `as_of_year: 2026`, future `end_year`; source balances represent December 31, 2026. As of October 28, 2026 those balances must be **projected**, never falsely described as existing year-end bank statements. Use `opening_balance_status: "projected_2026_12_31"` until a dated verified statement exists.
- `members`: one single filer or two married-joint filing adults, each with birth year, retirement age, wages and wage growth, Social Security selected claim age **and an age-specific 2026-real annual benefit estimate**, with `ss_estimate_basis: "2026_real_at_selected_claim_age"`. SSA amount is not dynamically computed from the new reference PIA/claim module.
- Optional `annual_pension_2026_real` is fully taxable, in 2026 dollars and inflation-indexed; a positive amount requires an explicit `pension_start_age` (no default start age is assumed).
- `accounts`: exactly one cash account; taxable account must supply market value and cost basis under proportional long-term-gain assumption; all IRA and 401(k) amounts must have known owners and fully pretax confirmation. Roth distributions require an explicit qualified assumption. Modeling tax lots, ordinary dividends and foreign exclusions is unsupported.
- `tax_policy`: `jurisdiction: "US_federal"`, `reference_year: 2026`, `filing_status: "single"|"mfj"`, `state_income_tax: "excluded_with_disclosure"`, `future_bracket_inflation` hypothetical rate used to project indexed amounts from the latest published tax year (labeled per row in `rule_basis`). NIIT is computed on modeled cash interest + positive realized LTCG and **MAGI=AGI assumption**, using $200k/$250k threshold. No Form 8960 deductions or unmodeled investment income.
- `living_expenses_annual_real`, optional event income/expenses (event income only with explicit `tax_status: "net_after_all_taxes"`), `roth_conversions` from a named same-owner traditional IRA into Roth, `withdrawal_order` listing accounts once with cash first, and `assumptions` (cash yield, portfolio mean/volatility, correlation, equity allocation, fees, inflation, trials and seed).
- RMD uses prior December 31 fully pretax balances and supported tables; ages beyond or special inherited/working circumstances fail closed. Withdrawal before age 60 is blocked instead of being assumed penalty-free.

## Evidence and privacy

`input_provenance` supports `mode: fictional_demo|unverified_user_data|documented_verified` with entries holding `json_pointer`, `evidence_id`, `source_type`, `as_of_date`, and `confidence`. Verified mode requires references covering materially relevant balances, basis, wages, expenses and age-specific SSA amounts. A reference is **not** proof that the external documents were professionally reviewed.

Do not commit sensitive user statements, account numbers, SSNs, or real family exports to Git. Offline interactive HTML embeds the input and audited output in plaintext and is **not encrypted**.

## Audit output

- Exact canonical input JSON SHA256, engine source fingerprint of `audit_plan.py` + `tax2026.py` + `tax_extensions.py`, explicit reference sources and 2026 policy assumptions.
- Annual accounts and cash conservation ledger, regular tax brackets, NIIT 3.8% base/rate/tax, FICA, withdrawals and RMD records, seeded Monte Carlo path manifest. Monetary presentation rounds to cents; independent verifier tolerates small summed rounding differences while verifying unrounded conservation.
- For `trace`, re-run a chosen Monte Carlo path with the supplied random seed and index. Never call a sampling interval a real-world retirement success confidence interval.
