# SSA calculations: scope and source verification

Reference date: 2026-10-28. SSA official sources:
- https://www.ssa.gov/oact/cola/piaformula.html (2026 and 2027 PIA bend points)
- https://www.ssa.gov/oact/ProgData/retirebenefit2.html (independent official 2026 case A; AIME $5,825 -> PIA $2,609.80)
- https://www.ssa.gov/oact/quickcalc/early_late.html (5/9 of 1% up to first 36 early months, 5/12 of 1% thereafter; delayed credits for 1943+ births 8% per year to age 70)
- https://www.ssa.gov/oact/ProgData/nra.html (full retirement ages)

Implemented in scripts/social_security.py:
- PIA for first-eligibility-year 2026 (bend points 1,286/7,749) or 2027 (1,340/8,077) from *externally established AIME*; final PIA rounded down to a dime.
- Worker-only claiming adjustment at whole-month ages 62–70 with birth-year FRA mapping and no guessed future bend points.
- Explicit PIA-at-claim-date input; does not silently apply early/late adjustment to a years-old PIA without COLA.

NOT implemented: reconstructing the 35 highest wage-indexed years and AIME from SSA earnings record, future COLA, deemed filing, family maximum, spousal/survivor benefits, disability, earnings tests, Medicare withholdings, exact month-specific payment timing, WEP/GPO edge cases or special SSA rounding. Results must not be marketed as an official benefit estimate. Use the original SSA statement for personalized values and an SSA calculator for independent verification.

The lifecycle module is a *deterministic scenario calendar*, not a mortality distribution. A surviving spouse requires an explicitly provided TOTAL household benefit; the engine does not sum the deceased and survivor benefits. Tax filing status changes after death require an additional separately validated tax engine.
