# Advanced Modules: capability roadmap and boundaries

Keep these as modules of ONE agent. Do not invent another source-of-truth, database or API for each topic. All quantitative extensions should use a shared normalized household profile, auditable calculation functions and scenario versioning.

## 1. Tax planning (not yet implemented)

Research current federal and user-specific state tax rules for the *relevant year*. Needed engine upgrades: filing status, itemized/standard deductions, progressive ordinary brackets, qualified dividends and capital gains, Social Security provisional-income taxability, taxation of different income sources, ACA, AMT, NIIT, QBI, RMDs, IRMAA interactions, Roth conversion thresholds and carryovers. Tax plans must have explicit marginal bracket provenance and test fixtures from IRS documents. Until then, compare Roth conversions using only the supplied flat `roth_conversion_tax_rate` as a scenario assumption; **never label outputs 'optimal Roth conversion'.**

## 2. Social Security (not yet implemented)

Collect SSA benefit statement and distinguish benefit estimate in today's dollars versus future dollars, claim age, full retirement age, earnings history, spousal and survivor benefits, delayed credits and earnings test. Current engine accepts **already supplied** annual claim-age benefit values only. A different claim age with unchanged benefit amount is not a valid optimization exercise.

## 3. Education planning (basic one-off events only)

Collect child's college start/end, school type, cost estimates, scholarships, 529 account basis/balance and contribution rules; model multi-year inflation-adjusted outflows before suggesting a funding target. Model earnings and limitations of 529s separately. Current engine supports one-off education expenses only.

## 4. Investments / asset allocation (not yet implemented)

Add account-level holdings, asset classes, rebalancing, fees, correlations, concentrated equity risk, downside tails and tax-aware sales. Keep client holdings confidential. Portfolio risk analysis must not be inferred from one assumed average market return. Current engine models all invested accounts with a common annual return.

## 5. Insurance, healthcare, and protection (checklist only)

Collect household dependents, income replacement needs, term coverage, disability insurance, long-term care, health premiums, HSA, Medicare and claim data as authorized. Flag gaps for specialist review; do not model insurance sufficiency as a certified determination.

## 6. Estate / beneficiaries (checklist only)

Discuss will, trust, probate, beneficiary designations, durable powers, family-specific succession and transfer tax considerations. Laws vary significantly by jurisdiction and year. Do not draft or claim validity of legal documents from the calculator.

## 7. Mortgages and liabilities (snapshot only)

Later support debt schedules, principal/interest, refinancing, credit risk and real estate valuation. In current engine, liability balances do not amortize; debt payment belongs in expenses. Never present ending investable assets as complete household net worth.

## 8. Advisor/client workflow (future optional)

If the user later wants to serve multiple households: add data segregation, delegated consent, per-household access rights, disclosure, audit logs, data export/deletion, oversight and regulatory/compliance review. Do not treat a ChatGPT conversation or uploaded Skill as a secure multi-tenant financial-advice SaaS.

## Release gates for any new numeric module

1. Ground laws and numeric rules with official dated sources (IRS/SSA/CMS or jurisdictional bodies).
2. Implement isolated testable functions, typed inputs, provenance and edge-case tests.
3. Compare sample outputs to official calculators or independent trusted reference scenarios.
4. Demonstrate errors/uncertainties honestly and require human approval for consequential actions.
5. Document what is and isn't included before labeling module 'ready'.