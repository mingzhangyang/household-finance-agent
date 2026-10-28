# Professional model validation gates (2026-10-28)

Incremental research foundation, NOT a complete RightCapital-equivalent system or tax preparation engine.

## 1. Year-by-year tax

- Original v2.1 engine uses a 2026 US federal reference table with assumed future indexing. Source: https://www.irs.gov/irb/2025-45_IRB
- The foundation API `niit_core` provides an isolated NIIT base formula: 3.8% of smaller of proper net investment income and excess MAGI. IRS thresholds: single/HOH $200k; MFJ $250k; MFS $125k. https://www.irs.gov/individuals/net-investment-income-tax
- The v2.2 annual engine now includes restricted NIIT on bank interest and positive realized LTCG, assuming MAGI equals AGI. The standalone `niit_core` API remains available. Other MAGI/NII adjustments, deductible expenses, state tax, Form 8960 special rules and future-year legislation remain unsupported.
- Admission gate: tax-year-pinned tables, complete cost basis and tax forms, independently checked official cases, reconciled accounts, and no silently assumed zeroes.

## 2. SSA retirement and lifecycle

- SSA PIA formula: https://www.ssa.gov/OACT/COLA/piaformula.html. 2026 bend points $1,286/$7,749; 2027 $1,340/$8,077. Rates 90%/32%/15%; PIA floor to a dime.
- AIME comes from fully indexed earnings record, not a guess. Indexed earnings may be provided externally; this model does not index raw earnings.
- SSA early/late formula: https://www.ssa.gov/oact/quickcalc/early_late.html. First 36 early months reduce 5/9 of 1% per month; later early months reduce 5/12 of 1% each. 1943+ delayed credits 8% per year up to 70.
- Timeline assumes a person remains alive through December 31 of declared death year. Require external documented survivor income; no inferred spousal benefit, filing status entitlement or estate tax calculation.
- Admission gate: SSA earnings record, 35-year AIME audit, year-specific COLA/recomputations, earnings test, spouse/survivor rules, official SSA examples and retirement calendar checks.

## 3. Market data and external comparison

- Source candidate: https://pages.stern.nyu.edu/adamodar/New_Home_Page/datafile/histretSPX.html (Damodaran/NYU historical stocks, bonds and bills). Source data must be downloaded, independently inspected and pinned by SHA256 before a calibration claim.
- CSV importer preserves same-year equity/bond pairing. Historical windows are contiguous and do not wrap; block bootstrap is seeded and resamples paired moving blocks. Neither establishes a future success probability.
- External model comparison is NOT yet completed. Require aligned starting date, withdrawal timing, Social Security COLAs, tax rules and identical return sequences; reconcile material dollar discrepancies.

## Evidence levels

A. Published official formula and independent known-answer calculation
B. Automated conservation tests and deterministic reproduction
C. Independently source-verified historical data
D. Material discrepancies resolved against a professional external model
E. Qualified professional sign-off

A/B do NOT imply C/D/E. Never label this work certified or validated beyond the actual tests.

Run standalone new tests: python -m unittest discover -s tests -p test_professional_modules.py -v