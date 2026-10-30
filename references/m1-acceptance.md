# M1 engineering acceptance: combined cases and real Chromium

Date: 2026-10-28 (America/New_York). This slice completes the three selected
engineering checks, not M0 scope approval, independent professional sign-off,
market calibration, a complete tax-return calculation or M5 physical-device acceptance.
Exact source revision and run results belong to the PR and CI artifact manifest.

## Independent inputs, method and acceptance rules

`tests/golden/m1-cases.json` contains six complete **fictional** plans (cases 5 and 6
added 2026-10-29 for the taxable account, M2 group 1). No real
household documents are needed. `tests/golden/m1_reference.py` derives the answers
with 40-digit Decimal, case-specific algebra and explicit segment/range assertions.
It imports only Python's decimal module. It does not import production tax tables,
funding functions, engine-generated expected results or the output verifier.
The existing iterative funding engine is evaluated separately by
`scripts/verify_m1_cases.py`; that command records every comparison and difference.
This is implementation independence, not a separate person's professional review.

Cases 1–3 assume zero investment returns, cash yield, fees and inflation; case 4
states its returns, inflation and index. All assume qualified Roth withdrawals and
fully pretax traditional accounts. Monetary inputs and balances are nominal USD.
Projection years 2027–2030 use **hypothetical 2026 federal rates/deductions**,
frozen in cases 1–3 and indexed 2% a year in case 4, including the modeled
expiration of the enhanced senior deduction after 2028. They do not assert enacted 2027–2030 tax tables. Events use whole-year
ages; RMD is taken in the modeled year, before conversion, with no first-year deferral.
No state tax, death, spousal entitlement calculation or market-risk inference is added.

Predeclared tolerances: absolute USD 0.01 for monetary comparisons; year, RMD divisor,
funded status, first failure year and the zero-return funded fraction must match
exactly. Every yearly account opening/closing balance, tax total, draw, spending
shortfall and the selected tax bases are compared. Missing rows/fields, extra
account/draw entries, booleans masquerading as amounts and non-finite values fail.
The JSON report identifies each checked field; it is not a claim that every field
of the general engine has an independent reference.

## Source register

Sources checked 2026-10-28. Answers below are derived examples, not official IRS
household examples. Changing a fixture requires reviewing its equations and ranges.

| Source | Edition / locator | Used for |
|---|---|---|
| [Rev. Proc. 2025-32](https://www.irs.gov/irb/2025-45_IRB) | §4.01 Tables 1/3; §4.03; §4.14 | 2026 single/MFJ brackets, gain thresholds, standard and age deductions |
| [IRS senior deduction](https://www.irs.gov/newsroom/working-families-tax-cuts-individuals-and-workers) | Enhanced deduction for seniors, 2025–2028 | Case 1: two eligible spouses below phaseout; case 2: single deduction fully phased out |
| [Publication 915](https://www.irs.gov/publications/p915) | 2025 edition, Worksheet 1 lines 9–19 | MFJ provisional income and the 85% benefit cap |
| [Publication 590-B](https://www.irs.gov/publications/p590b) | 2025 edition, owner RMD calculation and Appendix B Table III ages 73/74 | Prior December 31 IRA balance divided by 26.5 / 25.5 |
| [IRS Topic 751](https://www.irs.gov/taxtopics/tc751) | Social Security and Medicare withholding rates | Employee 6.2% + 1.45%; case wage is below the reference wage cap |
| [IRS NIIT](https://www.irs.gov/individuals/net-investment-income-tax) | Individual calculation and threshold table | 3.8% of the lesser of NII or positive MAGI excess; single threshold USD 200,000 |
| [SSA 2027 fact sheet](https://www.ssa.gov/cola/factsheets/2027.html), [IRS Topic 560](https://www.irs.gov/taxtopics/tc560), [IRS 401(k) limits](https://www.irs.gov/retirement-plans/plan-participant-employee/retirement-topics-401k-and-profit-sharing-plan-contribution-limits) | Register entries `payroll_2027`, `additional_medicare`, `401k_elective_limit_2026` | Case 4: 192,300 OASDI cap, 0.9% above 200,000, base deferral limit 24,500 |

Case 4 (added 2026-10-29) reuses values already recorded in
[rules-provenance.md](rules-provenance.md); those sources were not re-opened when
the case was added.

## Case 1: wages → retirement → Social Security

MFJ, both born in 1962; opening cash 10,000, IRA 500,000, all other accounts zero.
One spouse earns 120,000, defers 10,000 to a 401(k), retires at 66, and receives
20,000 annual pension from 66. Both claim at 67; **supplied** annual benefits are
24,000 and 12,000. Spending is 80,000. These are separate assumed benefits, not
calculated spouse entitlements. Cash funds first, followed by IRA as needed.

- 2027: taxable wages = 110,000. Deduction = 32,200 + 2×1,650 + 12,000 = 47,500.
  Income tax = 2,480 + 12%×(62,500−24,800) = 7,004; payroll tax = 9,180.
  Closing cash = 10,000 + 110,000 − 80,000 − 16,184 = 23,816; 401(k) = 10,000.
- 2028: let D be IRA funding. D = 80,000−23,816−20,000 + 10%×(20,000+D−47,500).
  Therefore D = 33,434/0.90 = 37,148.888…; tax = 964.888….
- 2029: supplied SS totals 36,000. Taxable SS = 0.85D+900 in the selected segment.
  Ordinary tax T = 2,480 + 12%×(20,000+D+0.85D+900−35,500−24,800)
  = 0.222D−2,248. D = 24,000+T, hence D = 21,752/0.778 = 27,958.868….
  The reference checks the ordinary-bracket range and that taxable SS is below 30,600.

This catches wage/deferral timing, FICA versus income-tax bases, pension/SS start
years, the 2029 deduction change and the SS/withdrawal feedback loop.

## Case 2: RMD + conversion + gains + NIIT

Single, born 1954; cash 10,000, IRA 1,060,000, taxable 500,000 with basis 250,000,
Roth zero; spending 180,000. Convert 200,000 in 2027 and 100,000 in 2028.
With no market growth, half of every taxable sale is gain and half reduces basis.

2027: RMD = 1,060,000/26.5 = 40,000. Ordinary taxable income is 221,850;
ordinary tax O = 41,024 + 32%×(221,850−201,775) = 47,448.
For taxable sale X, all gain X/2 is taxed at 15%; NIIT applies to all gain because
ordinary income alone exceeds 200,000. X = 130,000+O+0.188X/2,
so X = 177,448/0.906. Closing IRA = 820,000, Roth = 200,000.

2028: RMD R = 820,000/25.5. Ordinary taxable = R+100,000−18,150;
O = 17,966 + 24%×(R+100,000−18,150−105,700).
NIIT now uses **MAGI excess**, R+100,000+X/2−200,000, which is less than NII.
Thus X = [180,000−R+O+0.038×(R−100,000)]/0.906.
The reference asserts each bracket, deduction, gain and NIIT segment and available
sale balance before returning the answers. It also compares RMD details, conversion
transfers, both years' basis and all account balances.

## Case 3: cash → taxable → IRA → Roth → shortfall

Single, born 1967; cash 10,000, taxable 20,000 with basis 10,000, IRA 40,000,
qualified Roth 5,000; spending 30,000, no income.

2027 uses all cash and taxable assets. Gain 10,000 is absorbed by unused deduction.
2028 uses IRA funding D: D = 30,000+1,240+0.12×(D−16,100−12,400),
so D = 27,820/0.88 = 31,613.636…; tax = 1,613.636….
2029 consumes the remaining IRA 8,386.363… plus Roth 5,000, pays no income tax,
and leaves 16,613.636… spending unmet. **First failure year must be 2029.**
2030 remains unfunded with 30,000 unmet. Total depletion cannot erase the earlier
failure or create negative account balances.

| Case | Year | Total taxes | Closing assets | Unmet spending |
|---|---:|---:|---:|---:|
| Retirement transition | 2027 | 16,184.00 | 533,816.00 | 0.00 |
| Retirement transition | 2028 | 964.89 | 472,851.11 | 0.00 |
| Retirement transition | 2029 | 3,958.87 | 444,892.24 | 0.00 |
| RMD/conversion/NIIT | 2027 | 65,858.72 | 1,324,141.28 | 0.00 |
| RMD/conversion/NIIT | 2028 | 34,524.13 | 1,109,617.15 | 0.00 |
| Depletion | 2027 | 0.00 | 45,000.00 | 0.00 |
| Depletion | 2028 | 1,613.64 | 13,386.36 | 0.00 |
| Depletion | 2029 | 0.00 | 0.00 | 16,613.64 |
| Depletion | 2030 | 0.00 | 0.00 | 30,000.00 |

## Case 4: growth, inflation and hypothetical indexing

Single, born 1966; works in 2027 (age 61) and retires at 62. Wages 220,000 grow 5%;
a 20,000 real 401(k) deferral escalates with **3% plan inflation**, below the base
limit 24,500 × 1.02. Portfolio return 6% − 1% fee = 5%; cash yield 2%. Federal
tables use a **hypothetical 2% index** (1.02, then 1.0404), deliberately different
from plan inflation, so each amount must use the correct index. Cash 20,000,
taxable 50,000 (basis 30,000), IRA 300,000; spending 120,000 real plus a one-time
60,000 real expense in 2027.

- 2027: ordinary taxable income 210,800 − 16,422 = 194,378 in the indexed 24%
  bracket; OASDI on the published 192,300 cap, Medicare on 231,000 and 0.9% above
  200,000. Pre-sale tax T0 = 54,666.98. The expense forces a partial sale X of the
  appreciated account (gain fraction 3/7). Each gain dollar bears 15% plus 3.8%
  NIIT, because MAGI exceeds 200,000 by more than NII, so
  X = (185,400 + T0 − 230,800) / (1 − 0.188 × 3/7) = 10,079.06.
- 2028: no wages or cash. The taxable balance 44,541.98 is sold, realizing
  20,301.45 at 15% above the indexed 0% zone. IRA draw D solves
  0.78D = spending − V + 12%-bracket tax − 0.22 × (deduction + 12% top) + 0.15G,
  so D = 98,236.54 in the indexed 22% bracket. The hypothetical OASDI cap is
  192,300 × 1.02 although no wages are paid.

Range assertions confirm every bracket, zone, NIIT limiting base and available
balance, and that stacking is below the ordinary-rate alternative.

| Case | Year | Total taxes | Closing assets | Unmet spending |
|---|---|---:|---:|---:|
| Growth and indexing | 2027 | 55,479.06 | 378,020.94 | 0.00 |
| Growth and indexing | 2028 | 15,470.52 | 254,143.46 | 0.00 |

## Case 5: taxable distributions, loss limit and carryover (added 2026-10-29)

Single, born 1957 (70 in 2027), pension 40,000 from 60, no wages or Social Security.
Cash 0; brokerage 200,000 with basis 260,000 and stated yields: qualified 2%,
non-qualified 0.5%, interest 1%, capital gain distributions 0.5%, reinvested. Carryover
in 5,000; spending 60,000; 25% return, no inflation, frozen 2026 tables. Deductions are
16,100 + 2,050 + 6,000 senior = 24,150 in both years.

2027: distributions on 200,000 are 4,000 / 1,000 / 2,000 / 1,000, so basis is 268,000
against a value of 250,000 (ratio 1.072): every sale loses money. Assuming the
3,000 limit binds, AGI = 40,000 + 2,000 + 1,000 + 4,000 − 3,000 = 44,000 and ordinary
taxable income = 43,000 − 3,000 − 24,150 = 15,850; the 4,000 qualified dividends stay
in the 0% zone, so tax = 1,240 + .12 × 3,450 = 1,654 and the sale is 21,654. Net loss =
.072 × 21,654 − 1,000 + 5,000 = 5,559.088 (limit binds, as assumed). Adjusted taxable
income 19,850 + 3,000 + 6,000 is above 3,000, so 3,000 is used and 2,559.088 carries over.

2028: value 1.25 × 228,346 now exceeds basis 244,786.912 + 9,133.84 reinvested, so the
sale realizes a gain. Ordinary income 40,000 + 2,283.46 + 1,141.73 gives taxable ordinary
income in the 12% bracket and tax 2,065.0228; qualified dividends plus the net gain
(sale gain + 1,141.73 − 2,559.088 carryover) stay in the 0% zone, so the sale is 22,065.0228.
Range assertions check the 0% zone, the 12% bracket, the senior phaseout and the sign
of each year's net. Sources: §1211(b), §1212(b), Schedule D instructions worksheet, Form
1040 instructions p. 38, Pub 550 p. 30 ([taxable-account review](primary-source-review-2026-10-29-taxable-account.md)).

## Case 6: dividends, interest and the allowed loss in NIIT (added 2026-10-29)

Single, 50 in 2027, wages 300,000 equal to spending; zero returns. Brokerage 500,000
with basis 600,000; qualified 3% and interest 1%, reinvested: basis 620,000, ratio 1.24.
AGI = 300,000 + 5,000 + 15,000 − 3,000 = 317,000; ordinary taxable income 285,900 in
the 35% bracket (tax 58,448 + .35 × 29,675); the 15,000 qualified dividends at 15%
(below the 35% ordinary rate). NII = 5,000 + 15,000 − 3,000 = 17,000, below the 117,000
MAGI excess, so NIIT = 646. FICA uses the published 2027 cap 192,300, 1.45% and 0.9%
above 200,000: 17,172.60. The sale equals the tax, 88,902.85; its loss .24 × 88,902.85
exceeds 3,000, and 18,336.684 carries over. Form 8960 lines 1, 2, 5a and 12 are the source
of the NII composition.

## Browser and evidence reproduction

```sh
npm ci --ignore-scripts
npx --no-install playwright install --with-deps chromium
# Linux screenshots require Chinese glyph support:
sudo apt-get install -y fonts-noto-cjk
python scripts/verify_m1_cases.py --output /tmp/m1-differences.json
python scripts/collect_evidence.py --output /tmp/m1-evidence --browser
```

Use a fresh output directory and a clean checkout. The collector requires native
Linux process supervision; a sandbox with a mismatched `/proc` PID namespace may
run ordinary tests and Chromium separately but cannot claim a successful supervised
bundle. CI runs the collector with native supervision mandatory and uploads the
manifest, differences, logs, four-scenario screenshots, actual downloads and PDFs.

The pinned Playwright suite exercises all four existing report scenarios at
1440×1000 and 390×844, every yearly cash-flow/tax/account table and notice list, both downloaded
plan and audit-bundle replay paths, CSV, offline requests, printing, overflow and
19 corrupted/empty/error variants. It checks an actual CJK font is rendering the
heading; text nodes alone do not prove Chinese glyphs are visible. Inspect generated
screenshots and print PDFs separately before recording visual acceptance.

JSON export may spell monetary negative zero as zero. Browser comparison normalizes
**only signed zero**; all other values, types and keys remain strict. Original plan
bytes are still compared exactly, preserving Python numeric spelling for fingerprints.

Real PDF inspection exposed clipped closing-balance/residual columns in the
14-column account table. Print CSS
now lays out each account as a labeled two-column block on A4, using the screen
table's headings as labels, and removes scroll height limits from printed tables. Browser assertions
check paper-width fit, visible closing/residual labels and untruncated visible row containers.
The Monte Carlo path list remains screen/export-only, explicitly hidden in print.
Screen tables and calculation behavior are unchanged.

## Remaining scope and acceptance limits

The three-case engineering check and Chromium acceptance do not confirm the launch
scope or supply an independent professional reviewer. Physical iPhone/Safari,
Android, accessibility assistive-technology checks, general tax/SSA coverage,
nonzero-return scenarios beyond case 4 and commercial-tool benchmarking remain
outside this slice. Keep the verification matrix explicit and do not label all M0–M5 gates
complete. No real-family trial, production deployment or transaction is authorized
by these tests.
