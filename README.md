# Household Finance Agent — reproducible, auditable restricted v2.1

An installable ChatGPT Skill with an original interactive, offline financial planning report. **The v2.1 engine deliberately restricts supported tax and investment scenarios** to provide transparent, independently checkable calculations instead of broad but unverifiable claims.

## Quick start

```bash
python scripts/audit_plan.py validate examples/audited-household-2026.json
python scripts/audit_plan.py run examples/audited-household-2026.json --output result.json
python scripts/verify_outputs.py result.json --plan examples/audited-household-2026.json --engine-dir scripts --output verification.json
python scripts/render_audit.py examples/audited-household-2026.json --output financial_audit_dashboard.html
python scripts/audit_plan.py trace examples/audited-household-2026.json --path-index 17 --output monte_carlo_path_17.json
python -m unittest discover -s tests -v
```

Open `financial_audit_dashboard.html` locally in a browser. The tool can switch between four **Python-precomputed** scenarios, drill down by year into federal tax brackets and all account transfers, inspect Monte Carlo paths, and export annual cash flow CSV or audited JSON. The report is offline and contains its underlying private data in plaintext: **do not publish a real family's file**.

## What v2.1 improves

- Validate monetary types, dates, account ownership, contribution limits, IRA before-tax basis, selected RMD treatment, and SSA benefit assumptions; reject unsupported scenarios instead of inventing behavior.
- Apply 2026 official federal tax brackets, standard deductions and extra-senior-deduction assumptions, Social Security taxation, stacked long-term capital-gains rates, FICA, 2027 published Social Security wage base, uniform lifetime RMDs, 401(k) pre-tax deferrals and limited IRA-to-Roth conversions.
- Model cash/retirement-account transfers separately from external spending and tax flows; write double-entry conservation journal, tax-bracket breakdown and per-account residual per year.
- Use seeded two-asset correlated Gaussian Monte Carlo (unvalidated returns) with a path manifest, deterministic replay, Wilson sampling interval and code/input SHA256 identifiers.
- `verify_outputs.py` is a separately implemented output-only verifier; it recomputes arithmetic from JSON without importing the main engine. Tampering tests intentionally change results to confirm detection.

## Limits and status

**Not approved or suitable by itself for making real retirement, tax or investment transactions.** Only a restricted subset of US federal personal finance rules is implemented. No state income tax, NIIT, credits, Social Security benefit formula, survivor benefits, inherited retirement accounts, QCD, Roth qualification checking, IRMAA, ACA, real-world return calibration, mortality model, mortgage/debt schedules or robust tax-lot engine. Taxes in 2027 and later use a **hypothetical indexed 2026 tax schedule**, not enacted future tax law; SSA's 2027 wage cap is explicitly a separate published exception. Some yearly timing conventions use year-end approximations.

The legacy v1 engine (`scripts/plan.py` and `scripts/render_dashboard.py`) remains available for historical compatibility **only**, and is not the default.

See `references/rules-provenance.md`, `references/audit-methodology.md`, and `references/validation-report.md`.