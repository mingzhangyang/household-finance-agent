# Professional-model integration gates (not yet completed)

Current branch provides independently testable **reference modules**, not a complete tax-return or certified financial planning system.

1. Tax: scripts/tax2026.py is a restricted 2026 federal reference model. **NIIT is included in audit_plan's yearly tax-funding iteration** for modeled interest, ordinary dividends and the Form 1040 line 7a capital gain or allowed loss, assuming MAGI equals AGI and ignoring foreign exclusions/allocable expenses. Taxable-account dividends, interest, capital gain distributions, losses and carryovers are modeled from user-stated yields (M2 group 1). State taxes, itemization, credits, AMT, tax lots, rental/passive income, SSA/Medicare complexities and future-year enacted tables remain unsupported. The 2026 enhanced senior deduction phases out each eligible person’s $6,000 by 6% of joint MAGI over $150,000, then sums the spouses’ amounts ($10,800 at $160,000 MAGI for two seniors; zero at $250,000).
2. Social Security: scripts/social_security.py computes dated PIA and claiming factors for eligible cases; lifecycle.py produces explicitly assumed death/spending/benefit schedules. **Neither automatically replaces audit_plan's user-supplied SSA benefit estimates nor models real mortality, married filing transitions or survivor SSA eligibility.**
3. Market: scripts/market_history.py checks user-supplied dated return CSVs, computes descriptive sample moments and historical rolling sequence outcomes. **It does not calibrate audit_plan's Gaussian simulations yet.** The 2000–2018 sample is 19 rounded rows, not enough for 30–40 year retirement simulations.
4. External validation: scripts/verify_outputs.py checks annual arithmetic and recomputes the restricted federal worksheet steps from register values retyped in the verifier; it is not an SSA, market or complete IRS algorithm, and it shares the engine's dated register rather than an external source. tests/test_professional_models.py includes the official SSA AIME 5825 case and NIIT threshold examples. **No licensed RightCapital numeric-output cross-validation has been performed.**

Before enabling decision-grade mode, require:
- source-controlled yearly federal/state tax tables, independent government examples, and verified filing-status transitions;
- SSA earnings-record/AIME indexing, COLA and actual benefit verification;
- actuarial mortality table, documented survivor benefits and dynamic family spending;
- complete 1928-present adjusted market dataset with SHA256, real historical out-of-sample holdouts, and market/fee sensitivity;
- tax-funding-loop integration tests, independent spreadsheet/solver replication, and professional external review;
- review of CI/test status. A green CI never certifies planning assumptions.

Data policy: only fictitious data in Git, no personal statements, SSNs, credentials or decrypted reports. Local HTML is not encrypted.

Current offline command: `sh scripts/verify_local.sh`. GitHub Actions runs may be blocked by exhausted account quota. This does not prove the PR passed CI. Keep as Draft until exact-head and third-party checks are reviewed.
