# Connectors, Permissions, Privacy and Ongoing Operation

## First-party workflow

The host agent (Codex or Claude Code, per the [M0 decision record](m0-scope-decision.md)) is the conversational agent and planning coordinator. A reusable Skill supplies a workflow and bundled code; it is **not** a permanent server, database, autonomous scheduler, licensed advisor, or generic API client. Do not imply that installing the Skill automatically grants access to financial accounts, executes Python in every client, or ensures data persists forever.

## Where the data goes

The scripts run on the user's machine or in the host's session container. The model does not: whatever the agent reads into the conversation — plan JSON, results, statement excerpts, chat text — is sent to the host's model provider (OpenAI for Codex, Anthropic for Claude Code) and handled under the user's account and retention settings. In a cloud session, the checkout and generated files also live in the provider's container. So this Skill is not "fully offline": minimize what the agent reads (aliases, no full account numbers, SSNs or credentials), prefer having scripts read files and print only the needed fields, and keep real household files out of Git. The generated HTML report holds its data in plaintext.

## Data acquisition tiers

1. **Manual**: user supplies annual balances, ages, spending, estimates in chat or a local JSON file; ideal for a proof of concept.
2. **User-provided exports**: CSV/XLSX/PDF bank, brokerage and payroll/tax documents. Parse only necessary fields using permitted tools; track as-of date, currency, owner, and account ID hash or alias. Avoid exporting full account numbers in analysis artifacts.
3. **Explicitly connected plugins**: If a suitable Finances connector is installed and user authorizes, use its returned data only within its real permissions. A Skill cannot assume an unpublished connector schema or receive hidden tokens. Read-only by default. Don't automatically expand to unrelated accounts.
4. **Ongoing refresh**: User may authorize a scheduled summary or reminder separately where an automation tool exists. The Skill itself does not execute background tasks. State what data is expected to refresh and the cadence, and distinguish fresh observed facts from stale statements.

## Suggested normalized evidence register (not an engine input)

Maintain a separate file, not secret tokens:

| Field | Example |
|---|---|
| `fact_id` | `cash_balance_1` |
| `source_type` | `user`, `statement`, `connector`, `assumption` |
| `observed_at` | ISO date |
| `value` | Numeric / categorical value |
| `confidence` | `verified`, `approximate`, `unknown` |
| `account_alias` | `checking_A`, not full number |
| `notes` | Source page, statement date, unit caveat |

No permanent upload or synced storage should be promised without an actual user-approved destination.

## Privacy principles

- Ask before connecting to banks, searching private files, retaining data beyond the immediate task, transmitting sensitive data or sharing with advisers.
- Do not request passwords, access tokens, full account numbers, SSNs, login challenge codes or complete tax identifiers.
- Minimize PII in sample data, logs, temp files, output paths and reports.
- Prefer redacted tax statements and minimal excerpts over full-document replication.
- Separate read permissions and financial actions. Treat trades, transfers, communications, tax filings and changing beneficiary data as explicitly gated actions, not agent default behavior.
- Clearly disclose reliance on third-party tools, potential data staleness and limitations.