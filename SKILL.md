---
name: household-finance-agent
description: Evidence-first US household finance research using ChatGPT to orchestrate independently checked calculations. In the initial GitHub repository, use the available standalone SSA retirement claiming and PIA formulas, explicit lifecycle scenarios, isolated NIIT calculation, and reproducible historical-return stress testing. Trigger for retirement claiming questions, source-backed formula audits, historical scenario comparisons, and verification workflows. Do not infer complete tax, SSA survivor, or retirement simulation capability from this incomplete source checkout.
---

# Household Finance Agent — repository foundation

This repository is **not yet the complete v2.1 installable Skill** previously provided in ChatGPT. The older annual household simulator, independent annual ledger verifier, browser templates and their original tests remain in the separately distributed Skill ZIP. Do not attempt to execute commands for missing files.

## Available modules

- Use scripts/ssa_benefits.py for published 2026/2027 PIA bend point arithmetic and worker claiming factors. AIME input must already be SSA-indexed, or provided from a documented SSA source. Never state that this returns an official benefit award.
- Use scripts/lifecycle_rules.py for explicit end-of-year death status transitions. Do not invent survivor benefits. The output is a planning simplification and not a tax-filing status determination.
- Use scripts/tax_extensions.py only when modified adjusted gross income and net investment income are externally and correctly established under Form 8960. The NIIT formula does not mean a Form 1040 engine exists.
- Use scripts/market_history.py to ingest source-labelled CSV annual total returns, compute summary statistics and run contiguous historical windows or seeded paired block-bootstrap tests. Flag unverified provenance and do not call a resampled path fraction a validated probability.

## Verification gate

Run:

    python -m unittest discover -s tests -p test_professional_modules.py -v

Read references/professional-model-gates.md before any financial interpretation. Cite authoritative SSA, IRS and dataset versions. Attach every assumption and numeric outcome to a source or an explicit hypothesis. Reject missing essential inputs rather than inventing them. All calculations remain research-only and require professional review before consequential decisions.

Never commit or disclose private account numbers, statements, tax records, Social Security documents or customer-identifiable financial information.

## Remaining work

Import the original v2.1 full source, reconcile tax extensions with each annual ledger, implement documented SSA earnings indexing and survivor rules, pin independent historical datasets, and reconcile against external professional software under identical assumptions. Until these gates are passed, do not characterize the project as professional-grade or RightCapital-equivalent.
