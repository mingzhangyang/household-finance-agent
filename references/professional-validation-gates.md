# Professional-model integration gates (not yet completed)

Current branch provides independently testable **reference modules**, not a complete tax-return or certified financial planning system.

1. Tax: scripts/tax2026.py is a restricted 2026 federal reference model; scripts/tax_extensions.py adds a standalone 2026 NIIT computation with caller-established MAGI and net investment income. **NIIT is not yet injected into audit_plan's tax-funding loop.** State taxes, itemization, credits, AMT, 1099 flows, Social Security/Medicare nuances, tax-year table changes and special cases remain unsupported.
2. Social Security: scripts/social_security.py computes dated PIA and claiming factors for eligible cases; lifecycle.py produces explicitly assumed death/spending/benefit schedules. **Neither automatically replaces audit_plan's user-supplied SSA benefit estimates nor models real mortality, married filing transitions or survivor SSA eligibility.**
3. Market: scripts/market_history.py checks user-supplied dated return CSVs, computes descriptive sample moments and historical rolling sequence outcomes. **It does not calibrate audit_plan's Gaussian simulations yet.** The 2000–2018 sample is 19 rounded rows, not enough for 30–40 year retirement simulations.
4. External validation: scripts/verify_outputs.py checks annual arithmetic independently but is not a second economic/SSA/IRS algorithm. Test_professional_models.py includes the official SSA AIME 5825 case and NIIT threshold examples. **No licensed RightCapital numeric-output cross-validation has been performed.**

Before enabling decision-grade mode, require:
- source-controlled yearly federal/state tax tables, independent government examples, and verified filing-status transitions;
- SSA earnings-record/AIME indexing, COLA and actual benefit verification;
- actuarial mortality table, documented survivor benefits and dynamic family spending;
- complete 1928-present adjusted market dataset with SHA256, real historical out-of-sample holdouts, and market/fee sensitivity;
- tax-funding-loop integration tests, independent spreadsheet/solver replication, and professional external review;
- review of CI/test status. A green CI never certifies planning assumptions.

Data policy: only fictitious data in Git, no personal statements, SSNs, credentials or decrypted reports. Local HTML is not encrypted.
