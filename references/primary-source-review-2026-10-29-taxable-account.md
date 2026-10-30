# Primary-document review: taxable brokerage account rules (2026-10-29)

Scope: the rules M2 group 1 adds for a taxable brokerage account (annual dividends and
interest, capital gain distributions, realized losses, the capital-loss limit and
carryover, and their effect on Social Security taxation and NIIT). Each document was
downloaded directly from the official host on 2026-10-29 and read as text; hashes are of
the downloaded bytes. The IRS forms and instructions are the latest published editions
(tax year 2025). The rules taken from them are statutory and not indexed, except the 0%/15%
rate thresholds, which already come from Rev. Proc. 2025-32 for 2026
([earlier review](primary-source-review-2026-10-29.md)). Professional review of
applicability is still pending.

## Documents

| Document | URL | SHA256 | Locator |
|---|---|---|---|
| 26 U.S.C. §1211 (US Code 2023 ed.) | https://www.govinfo.gov/content/pkg/USCODE-2023-title26/html/USCODE-2023-title26-subtitleA-chap1-subchapP-partII-sec1211.htm | `58607626579398f8dbb6a03272188fa412fe880daffb6faa110f12b6d5703d64` | §1211(b) |
| 26 U.S.C. §1212 (US Code 2023 ed.) | https://www.govinfo.gov/content/pkg/USCODE-2023-title26/html/USCODE-2023-title26-subtitleA-chap1-subchapP-partII-sec1212.htm | `e6bc8e583d2f99fca5ecf98030915d6f746791c0b23c890d9c8284ff43f2f01b` | §1212(b)(1), (2)(A), (2)(B) |
| Pub. L. 119-21 | https://www.govinfo.gov/content/pkg/PLAW-119publ21/html/PLAW-119publ21.htm | (HTML page, not hashed) | §70103(a)(3), new IRC §151(d)(5)(C) |
| Instructions for Schedule D (2025) | https://www.irs.gov/pub/irs-pdf/i1040sd.pdf | `650643a686378b7573e4f4476ee4e7c9f9bab1384314dca32dc336f7b2276002` | p. 2 “Capital Losses”; p. 10 Capital Loss Carryover Worksheet lines 1–13; p. 14 “Line 21” |
| Schedule D (Form 1040) (2025) | https://www.irs.gov/pub/irs-pdf/f1040sd.pdf | `90564c8b7e49280363612639b804d113ebedb516c2e87c70649f29c844da1d2e` | lines 6, 7, 13–16, 21 |
| Instructions for Form 1040 (2025) | https://www.irs.gov/pub/irs-pdf/i1040gi.pdf | `482e9c487c608f1bbeaceef35bc3c0933e8b35443cfff447e4279d590468364a` | p. 38 Qualified Dividends and Capital Gain Tax Worksheet lines 1–25 |
| Instructions for Form 8960 (2025) | https://www.irs.gov/pub/irs-pdf/i8960.pdf | `b10fbb23ff4a053db197285497a00914c558e3ae0cdf5c956b7c0c7867376428` | p. 7 lines 1 and 2; p. 9 line 5a |
| Form 8960 (2025) | https://www.irs.gov/pub/irs-pdf/f8960.pdf | `9b323b7166b5845a776f781b8c82eef94ccd998354e88fc33a1051c3b3789731` | lines 8, 12–17 |
| Publication 550 (2025) | https://www.irs.gov/pub/irs-pdf/p550.pdf | `83552968a07e63d1c81e5b4f311fc0e54728b5ff9654b5a0d2ba6292c5574317` | p. 30 “Dividends Used To Buy More Stock”; p. 83 “Reinvested distributions”; pp. 101–102 “Limit on deduction”, “Capital loss carryover”, Worksheet 4-1, Bob and Shelly example |
| Publication 915 (2025) | https://www.irs.gov/pub/irs-pdf/p915.pdf | `44c4053dab046c737e4eadff7cf8a8d23fe55d6147bde995c6055b55af6db22b` | Worksheet 1 line 3 (pp. 7–16 filled-in examples) |
| Instructions for Form 1099-DIV (Rev. 01-2024) | https://www.irs.gov/pub/irs-pdf/i1099div.pdf | `af89ec14c288df70092cc2439e0bf215bab9704fc0b70ba3f9bd7d420067e607` | p. 4 boxes 1a, 1b, 2a |

## Findings applied by the engine

| Rule | What the documents say | How the model applies it |
|---|---|---|
| Reinvested distributions are income | Pub 550 p. 30: dividends used to buy more stock must still be reported as income. 1099-DIV box 1a includes reinvested dividends | Each year's distributions are taxed whether or not they are reinvested; reinvested amounts are added to cost basis |
| Ordinary vs qualified dividends | 1099-DIV: box 1a total ordinary dividends includes box 1b qualified dividends; box 1a also includes net short-term gains paid by mutual funds | Input states qualified and non-qualified yields separately; non-qualified dividends are ordinary income; Form 1040 line 3b = their sum |
| Capital gain distributions | 1099-DIV box 2a: long-term; includes boxes 2b (unrecaptured §1250), 2c (§1202) and 2d (28% collectibles) | Modeled as long-term gain on Schedule D line 13. Distributions with 2b/2c/2d portions are **not supported** (different rates) |
| Netting | Schedule D lines 7, 15, 16; §1212(b)(1) | All modeled gains are long-term: line 16 = sale gain or loss + capital gain distributions − carryover in |
| Loss limit | §1211(b): losses allowed to the extent of gains plus the lower of $3,000 ($1,500 MFS) or the excess loss. Pub 550 p. 101 and Schedule D line 21 | Deduction = min($3,000, net loss); MFS is outside scope. Not indexed |
| Carryover | §1212(b)(2): the amount treated as used is the lesser of the allowed deduction or adjusted taxable income; (2)(B) adjusted taxable income = taxable income + the §1211(b) amount + the deduction allowed under §151; deductions exceeding gross income count as negative taxable income. Worksheet 4-1 / Schedule D worksheet line 1 uses taxable income as if it could be negative and line 3 floors at zero. Pub 550 Bob and Shelly: $7,000 loss, taxable income $26,000 → $3,000 deducted, $4,000 carried | Carryover out = net loss − min(deduction, max(0, taxable income before the zero floor + deduction + §151 deduction)). Character (short/long) is not tracked: with no short-term gains in the model, the worksheet's split always sums to the same total (derivation in `tests/test_taxable_account.py`) |
| §151 add-back and the 2025–2028 senior deduction | Pub. L. 119-21 §70103 placed the $6,000 senior deduction in IRC §151(d)(5)(C)(i) (“there shall be allowed a deduction”). Personal exemptions are otherwise zero | The model adds the enhanced senior deduction back in adjusted taxable income. **Open question for the reviewer**: the latest IRS worksheet (2025 instructions, carryover from 2024) predates the deduction and uses taxable income only; the 2026 Schedule D instructions that will carry 2025 losses forward are not yet published. The difference matters only when taxable income before the zero floor is negative in a loss year with a senior deduction |
| Preferential rates | Form 1040 instructions p. 38 worksheet: line 4 = qualified dividends + the smaller of Schedule D lines 15 and 16 (zero if either is a loss); lines 5–25 stack it above ordinary income and take the smaller of that tax and the regular tax on all taxable income | Preferential income = qualified dividends + max(0, line 16) (lines 15 and 16 are equal in this model). Stacking and the ordinary-rate cap reuse the existing worksheet code |
| AGI | Form 1040 line 7a: capital gain, or the allowed loss as a negative amount | AGI includes line 7a; a net loss lowers ordinary income by the deduction |
| Social Security | Pub 915 Worksheet 1 line 3 combines Form 1040 lines 1z, 2b, 3b, 4b, 5b, 7a and 8; line 8 stops when the result does not exceed adjustments | Provisional income includes interest, all ordinary dividends and line 7a; it may now be negative, which yields no taxable benefits |
| NIIT | Form 8960 line 1 = Form 1040 line 2b; line 2 = line 3b; line 5a = line 7a (plus Schedule 1 line 4, none here); line 12 net investment income floors at zero | NII = max(0, cash interest + account interest + all ordinary dividends + line 7a). Part II deductions (investment expenses, state income tax) are not modeled |

## Limitations recorded for review

- Holding periods: Pub 550 p. 83 says reinvested shares start a new holding period, so a year-end sale can include short-term lots. The model treats every sale as long-term, consistent with its existing proportional-basis convention.
- Wash sales, specific-lot identification, return of capital (1099-DIV box 3), foreign tax credit, §199A REIT dividends, exempt-interest dividends, investment interest expense and Form 8960 Part II deductions are not modeled.
- Qualified-dividend holding-period tests are the user's classification, not checked.
