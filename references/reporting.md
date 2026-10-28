> **Legacy v1 note:** This guidance predates the audited v2.1 default. Use the v2.1 reproducibility checklist in `audit-methodology.md` for all numeric conclusions.

# Decision Report Protocol

Write user-facing responses in the user's language. Default to clear Chinese if conversation is Chinese. Use only evidence available from user input, executed engine output, or current authoritative sources.

## Artifact precedence

For numerical retirement/cashflow scenario comparisons, produce **interactive HTML** using `scripts/render_dashboard.py` as the default primary deliverable. Supply a link to the HTML and 2–4 sentences in chat with the principal outcomes, data provenance and caveat. Generate Markdown only when expressly requested or as an optional accessible companion; it is not a substitute for the webpage. See `references/interactive-dashboard.md`.

## Default concise output

1. **Question and answer**: one paragraph focused on the exact decision; do not bury the answer behind a long feature introduction.
2. **Data provenance**: documented vs user provided vs assumptions vs unknowns, as-of dates and account coverage.
3. **Scenario table**: baseline and at least one material alternative; include objective, retirement age, spending and tax assumptions. Ensure conditions are comparable.
4. **Risk output**: model-funded spending rate, tail scenarios, median / p10 and p90 inflation-adjusted asset levels, failure years if relevant, and horizon.
5. **Key drivers / confidence**: what changes when return mean, volatility, inflation or spending changes; name missing tax/healthcare or insurance assumptions and model's limits.
6. **Actions**: 1–3 practical next steps, separating data-gathering, scenario testing and decisions requiring qualified advice.

## Important distinctions

- Investment account assets != household net worth.
- 'Probability spending was fully funded in a Monte Carlo model' != real-world probability of a successful retirement.
- 'Tax-effective-rate what-if' != detailed federal / state tax or Roth conversion optimization.
- 'SSA benefit amount supplied by household' != SSA benefits calculation or claim optimization.
- Historical statements != today's prices or account values.
- A financial hypothesis != a recommendation to trade or change taxes.

## Formatting numbers

- Show currency, as-of-year real purchasing-power basis and horizon.
- Explain annual vs monthly and gross vs after tax.
- Round big forecasts to sensible precision; avoid cents for multidecade projections.
- Quote the actual assumptions and their sources; do not invent decimal precision or confidence intervals not computed by the engine.

## Red flags requiring special review

- Unfunded basic spending in many modeled paths, missing major accounts, unspecified tax rates, large expected one-off expenses, unrealistic return assumptions, inconsistent claiming-age benefit inputs, or illiquid assets counted as spendable.
- Missing spouse/dependents, life expectancy, healthcare or insurance costs can significantly distort a household plan.
- Cases involving high leverage, complex business ownership, special needs, cross-border tax residency or advanced trusts need bespoke professional review and are not modeled adequately.