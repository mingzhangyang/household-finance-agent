> **Legacy v1 note:** The default report is now rendered by `scripts/render_audit.py` from verified Python v2.1 results. This older document describes the v1 in-browser reimplementation only.

# Interactive HTML Financial Report — Layout, Interactions, Print and QA

## Primary output

Whenever the household needs a **numerical financial plan or comparison**, deliver a self-contained `.html` report as the first-class artifact, plus a short chat summary. Do not replace the interactive report with a prose-only Markdown report. The HTML is a standalone client-side, professional report-style financial planning dashboard; it does not require deploying a competing website or creating a backend.

### Generation

```bash
python scripts/plan.py validate examples/sample-household.json
python scripts/render_dashboard.py examples/sample-household.json \
  --compare examples/earlier-retirement.json \
  --output financial_dashboard.html
```

`render_dashboard.py` uses `plan.py` input validation; it embeds the two schema-v1.0 scenarios, deterministic Python-seeded standard-normal paths, and expected initial statistics. Its browser JS implements the same annual accounting semantics: returns, income, benefits, inflation, contributions, taxable withdrawal gross-up, flat assumed Roth conversion tax, and unmet spending. Shared market assumptions affect *both* scenarios, whereas retirement-age, spending and savings sliders affect the alternative only. This preserves fair comparisons.

If no `--compare` argument is given, create an alternative by decreasing the primary household member's retirement age by five years. Set the same snapshot year, end year, Monte Carlo trials and random seed in both scenarios. For responsive offline use, the interactive renderer currently supports no more than 90 modeled years and 2,000 trial paths. The full CLI engine allows larger input models separately.


## Report-first visual language (RightCapital-informed, independently branded)

The reference is the *structure* of publicly documented RightCapital Snapshot and sample financial planning reports, not their proprietary marks or pixel-accurate appearance. Use our own neutral Compass branding and never imply this is a RightCapital report.

Design for a financial-adviser-quality document that also works as a live browser dashboard: restrained navy/blue/teal typography, generous white page panels, compact summary tiles and numbered report chapters. Default report sequence:

1. **Snapshot**: planning-period metadata, explicit fictional/demo label, a ring for the fraction of Monte Carlo paths funding every year's spending, investable assets, baseline and changed-plan percentages, terminal-asset median. Label these as **model-conditional path proportions**, not forecast certainties.
2. **Retirement Analysis**: blue baseline median and teal alternative median, shaded baseline p10–p90 band, hover/touch year readout, Current/Proposed plan comparison; sliders for retirement ages, annual expenses, contributions and common market parameters.
3. **Stress & Sensitivity**: three deterministic (constant-return) tests vs **the baseline**: mean market return -2 percentage points, inflation +2 percentage points, spending +15%. Each shows last-year assets in starting-year purchasing power and first unmet-spending year. The numbers here are **not Monte Carlo successes**.
4. **Balance Sheet & Cash Flow**: four investable account/tax-treatment categories, imported recorded liabilities, *partial* recorded net amount, sampled-year income/spending bars. Avoid claiming total household net worth when assets such as real estate are not in the model.
5. **Annual Cash Flow**: full year-by-year baseline or alternative income, spending, savings, assets and gaps; download CSV.
6. **Assumptions & Disclosures**: provenance of demo or user-imported data, simplified tax and Social Security assumptions, no remote sharing, and model blind spots.

**Print view:** the `打印 / PDF` control calls `window.print()` and uses an `@media print` stylesheet with the navigation, live controls and buttons hidden. Include the model/disclosure section and allow annual table rows to continue to later pages; never position data inside clipped fixed-height containers on paper. The printed PDF is a static snapshot of the current live inputs, and does not retain sliders.

**Sources for the structural reference:** official RightCapital Snapshot and Reports Help Center pages and the publicly available 17-page 2023 Joe & Jane Sample report. Do not copy those sources into the Skill package.

## What the end user can actually do

- Open the `.html` directly in a desktop or mobile browser. No service, internet access, login or CDN required.
- Drag retirement ages for the first two household members, annual spending, retirement contributions, mean market return, volatility and inflation; see *live recomputation* of the funded-spending rate, asset trajectories and detailed cash-flow table.
- Inspect median and 10–90th percentile bands and hover/touch any year for values.
- Toggle between baseline / alternative annual rows, including unmet spending.
- Download both scenarios in a `financial-scenarios.json` file, or the full annual cash flow and percentiles in `financial-cashflows.csv`.
- Import a schema-v1.0 single scenario or two-scenario export from the local computer. The imported scenario must use the same horizon, seed and number of trial paths; otherwise regenerate the HTML via the Skill. Imported files are not uploaded anywhere.
- Print or save a PDF from the browser with the built-in `打印 / PDF` button. The printable six-section report adapts to paper size and hides interactive inputs; printed content is **not** interactive.

## QA checklist

1. Python CLI validates both plans, and `python -m unittest discover -s tests` passes.
2. Generate the HTML with `scripts/render_dashboard.py`; ensure content is one UTF-8 HTML file with no external resources.
3. Use a real browser to confirm zero JavaScript errors and a readable narrow-screen viewport; ensure no horizontal page overflow.
4. Confirm baseline and alternative funded percentages match `plan.py`; allow up to a few cents of percentile rounding divergence between Python and JS.
5. Change a slider: alternative computed values must change; restore: values must match original. Shared market assumptions must affect both.
6. Confirm both report files download, all stress tiles and the recorded-balance values update, and the annual table selection changes rows. Test browser print output as well.
7. Confirm `import` rejects broken schemas and mismatching horizons; avoid silent mutation of the underlying plan when import fails.

## Privacy and limits

No network I/O is coded into the report. All calculations execute in the browser; no remote dependencies, login, tracking or financial account polling. **This is not encryption**: opening or sharing the HTML exposes the embedded household JSON (as do exported CSV/JSON files). Keep files in private storage, redact personally identifying information, and obtain explicit permission before publishing.

Simulation percentages are conditional on a deliberately simplified model, fixed supplied effective tax rates, annual independent normal market returns and static initial assets. Not a substitute for live account aggregation, detailed IRS/SSA calculations, fiduciary review or trading tools. The word "interactive" refers to local browser controls, not hosted service deployment.