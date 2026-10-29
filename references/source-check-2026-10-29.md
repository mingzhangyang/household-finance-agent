# Official-source re-check of the rule register (2026-10-29)

Scope: every coefficient in [rules-provenance.md](rules-provenance.md), the values
retyped in `scripts/verify_outputs.py`, the SSA values in the research modules and
the inputs of M1 case 4. Result: **no mismatches**. Every checked value equals the
engine, verifier and register values.

## Method and its limits

Direct retrieval of `www.irs.gov` and `www.ecfr.gov` was blocked by the build
environment's network policy. Values were therefore checked through a web-search
service that returned extracts of official pages on irs.gov, ssa.gov,
federalregister.gov and govinfo.gov, plus Cornell LII's reproduction of 26 CFR.
A value counts as confirmed only when an extract stated it and attributed it to
the official page. Figures the search service derived itself were not counted.
Most table rows and thresholds came from queries that did not contain the expected
number. Some queries did contain it; those items were counted only when the extract
added source wording or detail absent from the query (form line numbers, derivations,
neighbouring rows). Extracts that could not find a value said so, and those values
were re-queried until found or left unconfirmed.

This is weaker than reading the primary document. Direct document review and
professional sign-off are still required before decision-grade use.

## Results

| Register entry | Values checked | Official source (as returned) | Result |
|---|---|---|---|
| `brackets_standard_senior` — ordinary brackets 2026 | Single tops 12,400 / 50,400 / 105,700 / 201,775 / 256,225 / 640,600; MFJ 24,800 / 100,800 / 211,400 / 403,550 / 512,450 / 768,700; rates 10–37% | [Rev. Proc. 2025-32](https://www.irs.gov/pub/irs-drop/rp-25-32.pdf); [IRS Working Families Tax Cuts](https://www.irs.gov/newsroom/working-families-tax-cuts-individuals-and-workers) | Confirmed |
| `brackets_standard_senior` — deductions 2026 | Standard 16,100 single / 32,200 MFJ; age-65 addition 2,050 unmarried / 1,650 married | [Rev. Proc. 2025-32](https://www.irs.gov/pub/irs-drop/rp-25-32.pdf); [IRB 2025-45](https://www.irs.gov/irb/2025-45_IRB) | Confirmed |
| `capital_gains` | 0% top 49,450 / 98,900; 15% top 545,500 / 613,700 | [Rev. Proc. 2025-32](https://www.irs.gov/pub/irs-drop/rp-25-32.pdf); [Publication 505 (2026)](https://www.irs.gov/publications/p505) | Confirmed |
| `capital_gains` — method | Worksheet 2-7 line 39 is tax on all taxable income; line 40 is the smaller of lines 38 and 39 | [Publication 505 (2026)](https://www.irs.gov/publications/p505) | Confirmed |
| `social_security_tax` | Base 25,000 / 32,000; 85% tier above 34,000 / 44,000 | [Publication 915](https://www.irs.gov/publications/p915) (2025; 2026 draft) | Confirmed; tier caps 4,500 / 6,000 are half the gap between those amounts (worksheet line text not retrieved) |
| `social_security_tax` — golden case | Example: benefits 5,980, taxable 2,990 | [Publication 915](https://www.irs.gov/publications/p915) | Result confirmed; the 28,990 other-income input was not in the extract |
| `senior_enhanced` | 6,000 per eligible person, less 6% of MAGI over 75,000 / 150,000, floor zero; 12,000 maximum for two; 2025–2028 | [Schedule 1-A (2025)](https://www.irs.gov/pub/irs-pdf/f1040s1a.pdf) Part V lines 31–35; [IRS seniors deduction notice](https://www.irs.gov/newsroom/irs-published-schedule-taxpayers-will-use-to-claim-deductions-on-no-tax-on-tips-no-tax-on-overtime-no-tax-on-car-loans-no-tax-on-seniors) | Confirmed |
| `payroll` | 2026 OASDI wage base 184,500; employee 6.2% OASDI, 7.65% total | [SSA 2026 fact sheet](https://www.ssa.gov/news/en/cola/factsheets/2026.html); [contribution and benefit base](https://ssa.gov/oact/cola/cbb.html) | Confirmed |
| `payroll_2027` | 2027 OASDI wage base 192,300 | [SSA 2027 fact sheet](https://www.ssa.gov/news/en/cola/factsheets/2027.html) | Confirmed |
| `additional_medicare` | 0.9% above 200,000 single / 250,000 MFJ; not indexed | [Topic 560](https://www.irs.gov/taxtopics/tc560); [Additional Medicare Q&A](https://www.irs.gov/businesses/small-businesses-self-employed/questions-and-answers-for-the-additional-medicare-tax) | Confirmed |
| `niit` | 3.8%; 200,000 single / 250,000 MFJ / 125,000 MFS; not indexed | [NIIT Q&A](https://www.irs.gov/newsroom/questions-and-answers-on-the-net-investment-income-tax); [Topic 559](https://www.irs.gov/taxtopics/tc559) | Confirmed |
| `401k_elective_limit_2026` | Base deferral 24,500 | [IR-2025-111](https://www.irs.gov/newsroom/401k-limit-increases-to-24500-for-2026-ira-limit-increases-to-7500); [Notice 2025-67](https://www.irs.gov/pub/irs-drop/n-25-67.pdf) | Confirmed |
| `rmd_uniform_lifetime` | All 49 rows, ages 72 to 120+ | 26 CFR 1.401(a)(9)-9(c), T.D. 9930: [85 FR 72472](https://www.federalregister.gov/documents/2020/11/12/2020-24723/updated-life-expectancy-and-distribution-period-tables-used-for-purposes-of-determining-minimum), [Cornell LII](https://www.law.cornell.edu/cfr/text/26/1.401(a)(9)-9); [Publication 590-B](https://www.irs.gov/publications/p590b) | Confirmed for distribution years from 2022; older Publication 590-B tables are superseded |
| `rmd_birth_1959` | Start age 73 for 1951–1958 births, 75 from 1960; 1959 ambiguous in statute | [RMD FAQs](https://www.irs.gov/retirement-plans/retirement-plan-and-ira-required-minimum-distributions-faqs); [2024 RMD regulations](https://www.federalregister.gov/documents/2024/07/19/2024-14542/required-minimum-distributions) | Confirmed; 73 for 1959 rests on a proposed rule, so keep the review flag |
| SSA FRA (gate, research modules) | 66 for 1943–1954, two months more per year 1955–1959, 67 from 1960 | [SSA NRA table](https://www.ssa.gov/oact/progdata/nra.html); [20 CFR 404.409](https://www.ssa.gov/OP_Home/cfr20/404/404-0409.htm) | Confirmed; January 1 birthdays follow the prior year, outside the whole-year model |
| SSA claim factors (research modules) | Early 5/9 of 1% for 36 months then 5/12 of 1%; delayed 2/3 of 1% a month for 1943+ births, to 70 | [SSA early or late retirement](https://www.ssa.gov/oact/quickcalc/early_late.html) | Confirmed |
| SSA bend points (research modules) | 2026: 1,286 / 7,749; 2027: 1,340 / 8,077 | [PIA formula](https://www.ssa.gov/oact/COLA/piaformula.html); [bend points](https://www.ssa.gov/oact/cola/bendpoints.html) | Confirmed |
| SSA examples (research tests) | Case A AIME 5,825 → PIA 2,609.80; maximum AIME 14,358 → 4,216.90 | [2026 benefit examples](https://www.ssa.gov/oact/ProgData/retirebenefit2.html); [benefit amounts](https://www.ssa.gov/OACT/cola/Benefits.html) | Confirmed |

## Facts found for later work

- SSA announced a **3.6% COLA for 2027** ([SSA, 2026-10-14](https://www.ssa.gov/blog/en/posts/2026-10-14.html)).
  The model escalates supplied benefits with assumed inflation.
- No IRS release of **2027 individual brackets, standard deductions or retirement-plan
  limits** was found on 2026-10-29. Some 2027 items (HSA, premium tax credit) are
  published. Re-check before replacing the hypothetical 2027 tables with enacted values.
- 2026 catch-up limits (8,000; 11,250 at ages 60–63) and the Roth catch-up rule for
  prior-year wages over 150,000 exist; the model rejects catch-up contributions.
- Search results list the SSA fact sheets at `ssa.gov/news/en/cola/factsheets/`. The
  register still cites `ssa.gov/cola/factsheets/`; check for a redirect and update links.
- A 2024 proposed RMD rule mentions an updated Uniform Lifetime Table (ages 10 to 120+);
  it was not confirmed as final. Watch it before changing the table.

## Changes made from this check

- `verify_outputs.py` now retypes the confirmed Uniform Lifetime Table and rejects any
  RMD divisor that differs from the row for the reported owner age.
- [rules-provenance.md](rules-provenance.md) records the re-check.

## Still required

Superseded on the same day by the [direct primary-document review](primary-source-review-2026-10-29.md),
which read the IRS documents, the statute, the Federal Register notices and the CFR text
(including the Publication 915 worksheet lines) and found no mismatches. Still open: the SSA
web pages and examples (`www.ssa.gov` refused the request) and an independent professional
reviewer's sign-off.
