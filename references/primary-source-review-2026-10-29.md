# Direct primary-document review of the rule register (2026-10-29)

Follow-up to the [search-extract re-check](source-check-2026-10-29.md). This time the
official documents themselves were downloaded and read: `www.irs.gov` and `www.govinfo.gov`
became reachable from the build environment. Scope: every coefficient in
[rules-provenance.md](rules-provenance.md), the values retyped in `scripts/verify_outputs.py`,
and the SSA values used by the research modules.

**Result: no mismatches.** Every engine, verifier and register value equals the primary text.
No engine number changes. The review found one register wording error (the Social Security
row named Example 3, while only Example 1 was tested; Example 3 is now a golden case too).

## Method and limits

- Each document was downloaded once on 2026-10-29, converted to text (`pdftotext`, or the
  plain-text Federal Register and CFR renditions on govinfo) and read at the locator shown.
  SHA256 values identify the exact file that was read; re-downloads of IRS HTML pages are not
  byte-stable, so only fixed files are hashed.
- The 49-row Uniform Lifetime Table was compared mechanically: regulation text, Publication
  590-B, `audit_plan.RMD_DENOMINATORS` and `verify_outputs.UNIFORM_LIFETIME` agree on every row.
- `www.ssa.gov` answered 403 and `www.ecfr.gov` / federalregister.gov full-text pages answered
  with bot checks; they were not bypassed. SSA values were instead read from SSA's own Federal
  Register notices and the annual CFR edition on govinfo, which are the legal publications.
- This is an engineering reading of primary documents, not professional tax or legal review.
  Whether a rule applies to a given household still needs the reviewer named in M0.

## Documents read

| ID | Document | Retrieved file | SHA256 |
|---|---|---|---|
| RP | Rev. Proc. 2025-32 (2026 inflation adjustments), PDF dated 2025-10-17 | [rp-25-32.pdf](https://www.irs.gov/pub/irs-drop/rp-25-32.pdf) | `e9ada115fb43a4af5ea326ca91edd40ab0bf29b9be01d2c13d7b8fa96214635b` |
| P915 | Publication 915 (2025) | [p915.pdf](https://www.irs.gov/pub/irs-pdf/p915.pdf) | `44c4053dab046c737e4eadff7cf8a8d23fe55d6147bde995c6055b55af6db22b` |
| P505 | Publication 505 (2026) | [p505.pdf](https://www.irs.gov/pub/irs-pdf/p505.pdf) | `c69e87caa93cdefa4493f0ec1d8478b1ff9ec1329ee18c7b9d442f2dcb79c621` |
| S1A | Schedule 1-A (Form 1040) 2025 | [f1040s1a.pdf](https://www.irs.gov/pub/irs-pdf/f1040s1a.pdf) | `64f97b38ff4218e2f188fd55a8aab7043556687487c82bbefe0b6dd1a956ecd4` |
| PL | Pub. L. 119-21, 139 Stat. 72, §70103 | [PLAW-119publ21.htm](https://www.govinfo.gov/content/pkg/PLAW-119publ21/html/PLAW-119publ21.htm) | `84000b07c382db50ead04ce65b70983e2dcd699a931d80cd3d2edac584e9004d` |
| N67 | Notice 2025-67 (2026 plan limits) | [n-25-67.pdf](https://www.irs.gov/pub/irs-drop/n-25-67.pdf) | `1eea8f141b0cddd182f9f09b3bc8ffad683d27ceb806dfc6da126811dc0a1f8d` |
| P15 | Publication 15 (2026) | [p15.pdf](https://www.irs.gov/pub/irs-pdf/p15.pdf) | `b46c3622439d8521e3a0faca4cd5b5ece3451b526f65f06a5e38d5c9f804c88b` |
| SSA26 | SSA, Cost-of-Living Increase and Other Determinations for 2026, 90 FR 49047 (2025-11-03) | [2025-19763.htm](https://www.govinfo.gov/content/pkg/FR-2025-11-03/html/2025-19763.htm) | `48f2b220ff8ad647772f10f3c029237ff3c70c3e0df492aaa60383ac44a66433` |
| SSA27 | SSA, Cost-of-Living Increase and Other Determinations for 2027, 91 FR 67380 (2026-10-26) | [2026-21796.htm](https://www.govinfo.gov/content/pkg/FR-2026-10-26/html/2026-21796.htm) | `89b04bc216c7b616187ae611e614b43870116abcf3fb06536c0229c484bcef7c` |
| I8959 | Instructions for Form 8959 (2025) | [i8959.pdf](https://www.irs.gov/pub/irs-pdf/i8959.pdf) | `1d223be73b4bac959a00e9b55784297bafa73a986567987c083671abf687b68f` |
| I8960 | Instructions for Form 8960 (2025) | [i8960.pdf](https://www.irs.gov/pub/irs-pdf/i8960.pdf) | `b10fbb23ff4a053db197285497a00914c558e3ae0cdf5c956b7c0c7867376428` |
| NIITQA | IRS, Questions and answers on the NIIT (HTML) | [irs.gov page](https://www.irs.gov/newsroom/questions-and-answers-on-the-net-investment-income-tax) | page text, not hashed |
| TD9930 | T.D. 9930, 85 FR 72472 (2020-11-12), 26 CFR 1.401(a)(9)-9 | [2020-24723.htm](https://www.govinfo.gov/content/pkg/FR-2020-11-12/html/2020-24723.htm) | `b3156d4c2d89d3be8cd24608824d3bb13d6eacd25f83e995a01c016d1b0a4282` |
| P590B | Publication 590-B (2025) | [p590b.pdf](https://www.irs.gov/pub/irs-pdf/p590b.pdf) | `d18a592e55ce56d43953dc338272ece3984565792d6dca06989a6ca8121f7360` |
| TD10001 | T.D. 10001, 89 FR 58886 (2024-07-19), final RMD regulations | [2024-14542.htm](https://www.govinfo.gov/content/pkg/FR-2024-07-19/html/2024-14542.htm) | `ef17eab86e9fed32d25e8563f5b76ab39cde2801684d399393f0f0c60dc7e0c9` |
| NPRM24 | Proposed RMD regulations, 89 FR 58644 (2024-07-19) | [2024-14543.htm](https://www.govinfo.gov/content/pkg/FR-2024-07-19/html/2024-14543.htm) | `d7183e078b898d5de90bd71d0f2872e81370c24db3665233efbaa2cdd514aae5` |
| CFR20 | 20 CFR 404.212, 404.313, 404.409, 404.410 (edition of 2025-04-01) | [govinfo CFR-2025-title20-vol2](https://www.govinfo.gov/app/collection/cfr/2025/title20) | 404.212 `12f5bc9e…`, 404.313 `19c60271…`, 404.409 `2a4961ef…`, 404.410 `a318ad17…` |

## Results

| Register entry | Values checked | Primary text and locator | Result |
|---|---|---|---|
| `brackets_standard_senior` — brackets | Single tops 12,400 / 50,400 / 105,700 / 201,775 / 256,225 / 640,600; MFJ 24,800 / 100,800 / 211,400 / 403,550 / 512,450 / 768,700; rates 10–37% | RP §4.01 Tables 1 and 3 | Confirmed. The printed rows (for example $35,932 plus 24% over $211,400 MFJ) are now golden cases |
| `brackets_standard_senior` — deductions | Standard 16,100 single / 32,200 MFJ; age-65 addition 1,650, or 2,050 if unmarried and not a surviving spouse | RP §4.14(1) and §4.14(3) | Confirmed |
| `capital_gains` — thresholds | 0% top 49,450 / 98,900; 15% top 545,500 / 613,700 | RP §4.03; P505 Worksheet 2-7 lines 11 and 19 | Confirmed |
| `capital_gains` — method | Gain zones from lines 11–27; line 37 ordinary tax; line 38 total; line 39 tax on all taxable income; line 40 the smaller of 38 and 39 | P505 Worksheet 2-7 | Confirmed. The 2026 worksheet adds lines 13a–14 for 28% and unrecaptured §1250 gain; without those gains line 14 equals ordinary taxable income, as modeled |
| `social_security_tax` | Bases 25,000 / 32,000 (line 9); line 11 is 9,000 single / 12,000 MFJ, so the tier caps (line 14) are 4,500 / 6,000; 50% and 85% factors (lines 2, 14, 16, 18) | P915 Worksheet 1, lines 1–19 | Confirmed, including the line text the search extracts lacked. Fixed statutory amounts, not indexed |
| `social_security_tax` — known answers | Example 1: other income 28,990 (pension 18,600, wages 9,400, interest 990), benefits 5,980 → 2,990. Example 3 (MFJ): line 3 40,500, benefits 10,000 → 6,275 | P915 Examples 1 and 3 | Confirmed; Example 3 added to the golden cases |
| `senior_enhanced` | 6,000 per qualified individual aged 65 by year end; each reduced by 6% of MAGI over 75,000 / 150,000, not below zero; joint return required; taxable years beginning before 2029-01-01 | PL §70103 (IRC §151(d)(5)(C)); S1A Part V lines 31–37; P505 (2026) What's New | Confirmed. MAGI adds only §§911/931/933 exclusions, matching MAGI = AGI in scope. SSN requirement assumed met |
| `payroll` | 2026 OASDI wage base 184,500; employee 6.2% OASDI and 1.45% Medicare | SSA26 item (1); P15 (2026) "Tax rates and the social security wage base limit" | Confirmed |
| `payroll_2027` | 2027 OASDI wage base 192,300 | SSA27 item (1), "for remuneration paid in 2027" | Confirmed by the published Federal Register notice |
| `additional_medicare` | 0.9% above 200,000 single / 250,000 MFJ (125,000 MFS); not indexed | I8959 "Threshold Amounts for Additional Medicare Tax" | Confirmed |
| `niit` | 3.8% of the smaller of NII or MAGI over 200,000 single / 250,000 MFJ (125,000 MFS); not indexed | I8960 "Application to Individuals"; NIITQA | Confirmed |
| `401k_elective_limit_2026` | §402(g)(1) limit 24,500 (catch-ups 8,000 and 11,250 at ages 60–63 are not modeled) | N67 | Confirmed |
| `rmd_uniform_lifetime` | All 49 rows, ages 72 to 120+ | TD9930: 26 CFR 1.401(a)(9)-9(c) Table 2, applicable to distribution calendar years from 2022 (§1.401(a)(9)-9(f)(1)); P590B Appendix B Table III | Confirmed row by row in both sources |
| `rmd_birth_1959` | Applicable age 73 for births 1951–1958; 75 from 1960; 1959 reserved | TD10001: 26 CFR 1.401(a)(9)-2(b)(2)(iv)–(vi), for distribution calendar years from 2025 | Confirmed. Age 73 for 1959 rests only on proposed §1.401(a)(9)-2(b)(2)(v) (NPRM24). None of the 81 IRS final rules published in the Federal Register from 2024-07-20 to 2026-10-29 finalizes it, so the human-review flag stays |
| SSA FRA (gate, research modules) | 66 for births 1943–1954; +2 months per year 1955–1959; 67 from 1960 | CFR20 §404.409(a) table (January 1 birthdays follow the prior year) | Confirmed |
| SSA claim factors (research modules) | Early: 5/9 of 1% for 36 months, then 5/12 of 1%; delayed: 2/3 of 1% a month for births after 1943-01-01 | CFR20 §404.410(a); §404.313 credit table | Confirmed |
| SSA PIA (research modules) | 90% / 32% / 15%; bend points 1,286 / 7,749 (2026) and 1,340 / 8,077 (2027); round down to $0.10 | SSA26 and SSA27 "Computing the Primary Insurance Amount"; CFR20 §404.212(b) | Confirmed. The SSA web examples (AIME 5,825 → 2,609.80; 14,358 → 4,216.90) follow from this formula; the example pages themselves remain unread |

## Facts for later work

- **2027 rules.** No IRS release of 2027 brackets, standard deductions or retirement-plan limits
  appears in the IRS news releases through IR-2026-128 (2026-10-23). SSA has published its 2027
  values: wage base 192,300, bend points 1,340 / 8,077, COLA 3.6%.
- **Published indexing differs from the model's multiplier.** Pub. L. 119-21 §70101(b) indexes
  the 10% and 12% bracket tops from a different base year than the higher brackets, and IRS
  rounds every indexed amount before publishing it. The model applies one unrounded assumed
  rate to all amounts, so projected tables differ from future published ones by rounding and by
  the gap between assumed and actual inflation. It stays a labeled hypothetical convention.
- **Birthday edge cases.** Age-65 deductions use "attained age 65 before the close of the
  taxable year" (born before January 2, 1962 for 2026); FRA tables treat January 1 birthdays as
  the prior year. The whole-year age model cannot represent January 1 birthdays.
- **Links.** The register's SSA fact-sheet links could not be checked (403). The register now
  cites the SSA Federal Register notices, which are the legal publications of these amounts.

## Changes made from this review

- [rules-provenance.md](rules-provenance.md): status column records the primary document and
  locator; the Social Security row names Examples 1 and 3; SSA and RMD start-age rows cite the
  Federal Register notices and 26 CFR text.
- `tests/golden/reference-cases.json`: twelve cases from the printed rows of Rev. Proc. 2025-32
  Tables 1 and 3 (ten base amounts, two incomes above the top bracket) and Pub 915 Example 3.
  `test_golden.py` now checks the verifier's retyped schedules against every component case as
  well as the engine's. Changing any bracket top or rate in either copy fails these cases.
- [verification-matrix.md](verification-matrix.md) and verifier comments: "primary-document
  review pending" replaced by this record; the verifier still does not fetch sources at run time.

## Still required

- Professional reviewer sign-off on applicability (M0/M1 gates).
- The SSA web examples and `www.ssa.gov` pages, when reachable without a bot check.
- Re-reading when IRS publishes the 2027 revenue procedure and when the 1959 RMD rule is final.
