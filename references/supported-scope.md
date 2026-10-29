# M0 supported scope — engineering baseline, not launch approval

Contract 1.0, 2026-10-28. Scope owner and independent professional reviewer:
**not assigned / acceptance pending**. Until they confirm scope, this remains a
local, offline, USD, federal-only research tool. No state is certified as supported;
excluding state tax does not imply a household owes none. No complete retirement
feasibility, tax-return, transaction or optimal-strategy conclusion is permitted.

## Executable boundaries

`audit_plan.validate` is the public input gate; `run_path` applies dynamic gates.
Unknown keys are rejected at every modeled object. See `tests/test_scope_contract.py`
and the pre-existing ledger/review tests. “Limited” means an explicit model assumption,
not proof of real-world applicability.

| Dimension | Status and precise boundary | Enforcement / evidence |
|---|---|---|
| Household | Limited: one single adult or two MFJ adults; constant membership and status | member count / filing-status match |
| Ages | Limited: birth years 1951–2006 (20–75 at 2026 year-end); horizon age ≤120; whole-year ages | birth / horizon validation |
| Calendar | Limited: opening balances at 2026-12-31; projection 2027 through end year ≤2110 | as_of_year, end_year, opening_balance_status |
| Rules | Limited: published values by tax year (income tax tables 2026, OASDI wage base 2026–2027, elective limit 2026); later years projected from the latest published year at an assumed rate and labeled per row | tax_policy; rule_basis; rules-provenance.md |
| State/local/non-US tax | Excluded from research, no supported-state claim | explicit excluded_with_disclosure; unknown jurisdiction rejected |
| Accounts | Exactly one cash, at most one taxable, owned traditional IRA / 401(k) / Roth IRA | kind, owner and withdrawal-order checks |
| Traditional accounts | Limited: entirely pretax, uniform RMD table, no still-working exception | affirmative confirmations; no inherited accounts or Form 8606 basis |
| Roth | Limited: user affirmatively assumes qualified distributions; no qualification calculation | qualified_distributions_confirmed |
| Early distributions | Rejected as a source of funding before whole-year age 60; other accounts may fund | run_path notices listed in the year audit; resulting shortfall stays visible |
| Contributions | Limited: owned pretax 401(k), base elective limit (published 2026, later years projected), ≤wages | runtime contribution gate; no catch-up, match or IRA contribution |
| Conversion | Limited: specified year and amount, same-owner traditional IRA → Roth | validation; unavailable source recorded as skipped and failed path |
| Wages/pension | Limited: supplied wages/growth/retirement age; fully taxable pension indexed with assumed inflation, from an explicit start age | numeric validation; pension amount without start age rejected; no self-employment/rental income |
| Social Security | Limited: supplied annual benefit in 2026 dollars for exact claim age 62–70; assumed inflation | basis required; work before FRA with benefits rejected |
| Investments | Limited: cash interest; positive proportional long-term gains; common portfolio returns | basis and gain-treatment required; no dividends, loss offsets, lots |
| NIIT | Limited: modeled cash interest + positive LTCG, MAGI=AGI, no adjustments | tax_extensions integration; test_niit_integration.py |
| Spending/events | Supplied 2026-real recurring expenses; dated real/nominal expense or already-net income | event income explicitly net_after_all_taxes |
| Debt | No amortization or net-worth claim; payments may be included in expenses | nonempty liabilities rejected |
| Lifecycle | Rejected: death, survivor, divorce, membership/status transitions | unknown fields/event kinds rejected; reference modules not integrated |
| Market | Limited: seeded two-asset Gaussian draws, common annual allocation/fees; return floor -99.9% | assumptions and seed limits; not empirical calibration |
| Evidence | Optional register; missing register is never “verified”; documented_verified is a user-supplied label | pointers/metadata checked; no external documents inspected |

## Errors and degraded results

- Missing, malformed, out-of-range and unsupported input: `ModelError`, code
  `INVALID_OR_UNSUPPORTED_PLAN`; CLI exit 2. No new result/report is written.
- A non-2026 reference or opening year is rejected. Years without published values
  carry `projected` status in each row's `rule_basis`, never an assertion of enacted
  future law. There is
  no automatic rule refresh or clock-based tax certification.
- Non-convergent funding / accounting failure: stop calculation with `ModelError`.
- Insufficient assets: retain explicit unpaid tax, unmet spending/RMD and skipped
  conversion; mark first failure year. Do not confuse this with invalid input.
- Any valid output remains `restricted_research`, `full_household_conclusion=false`.
  Missing evidence or registered documents cannot upgrade this status. Successful
  arithmetic verification cannot change professional-review status.
- If a CLI fails while a prior output exists, that file belongs to the earlier run;
  use the exit code and input fingerprint, never the mere existence of a file.

## Interface consolidation plan (no algorithm rewrite in M0)

| API | Role now | Migration decision |
|---|---|---|
| audit_plan / tax2026 / tax_extensions | Projection and selected federal calculations | Preserve CLI, schema 2.0 and output version 2.2; evidence metadata additive |
| ssa_benefits | Retained SSA foundation API | Candidate canonical module for M3 after sourced-case parity review |
| social_security | Separate experimental API | Preserve; adapter only after differences in rounding and scope documented |
| lifecycle_rules / lifecycle | Separate event research interfaces | M3 selects one event representation, tests both before adapting |
| market_history | Both decimal and percentage CSV interfaces retained | M4 adds governed datasets, never promotes the 19-row fixture to calibration |

No reference module can silently change the annual main engine.

## Decisions remaining before milestone acceptance

Proposed engineering scope is individual research, no certified state, external
age-specific SS estimates, offline-only delivery. Launch audience, state scope,
professional-review resources, approved independent comparison tools/data licensing
and responsible people remain unconfirmed. M0 engineering artifacts may be reviewed
now; M0 sign-off and downstream launch gates remain pending. M1 test infrastructure
can be prepared without claiming these decisions have been made. A draft
[decision record](m0-scope-decision.md) lists each decision's options, the current
baseline and the downstream effect, for the scope owner to confirm or change.
