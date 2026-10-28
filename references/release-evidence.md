# Reproducible engineering evidence and browser acceptance

This implements the roadmap's third engineering slice, not a release approval.
M0 scope confirmation, independent professional review and M1–M5 exit gates remain
open. Never convert “not run”, skipped or environment-blocked checks to passed.

## Collect evidence at an exact commit

Use a clean checkout, Python 3.10+ and Node.js. The collector has no user-input-file
option: only the checked-in fictional household is used. Choose a **new** local
folder outside the checkout, or under ignored `results/`:

```sh
python scripts/collect_evidence.py --output /tmp/finance-evidence-run1
# Require actual Chromium acceptance (nonzero exit if unavailable or failed):
python scripts/collect_evidence.py --output /tmp/finance-evidence-run2 --browser
```

The bundle contains the exact commit/tree, dirty-state indicator, tracked file hashes,
Python/platform identity, every command and exit code, complete logs, input/result
fingerprints, arithmetic status, same-engine replay status and SHA256 hashes of all
artifacts. It rechecks source identity after execution. A dirty run can be useful
for development, but `exact_clean_commit=false` prevents it being presented as
commit-level evidence. `release_approved` is always false: engineering checks cannot
supply missing scope decisions or independent professional sign-off.

Without `--browser`, the browser status is `not_run`. With the flag, missing Node,
Playwright or browser binaries are failures, not silent skips. GitHub Actions is
`not_checked` until a separate observed run is recorded. Do not retry quota-blocked
workflows to replace local evidence.

The manifest hashes engine, tests, golden metadata and report template separately.
The legacy result fingerprint covers only its three calculation files; it does not
cover the verifier or presentation layer. Use the full bundle for release provenance.

## Real-browser runner

Install a Playwright version supported by your environment and its Chromium binary.
Node must resolve `playwright` (`NODE_PATH` may point to an existing installation).
`HFA_BROWSER_EXECUTABLE` optionally selects an already installed Chromium; the runner
records the actual browser and Playwright versions. No npm install or browser download
runs automatically in the evidence collector.

```sh
node tests/browser_acceptance.cjs /tmp/finance-evidence-run1/report.html /tmp/browser-evidence
```

The suite opens the generated report through `file://` with network offline, and
records all attempted HTTP(S) requests as failures. It exercises all four scenarios
at desktop (1440×1000) and mobile (390×844) viewport sizes, year selection, account
details, chart paths, separated status labels, actual plan/JSON/CSV downloads,
replay of downloaded plans/results, horizontal overflow, screenshots, print CSS and
PDF output. It verifies invalid JSON, empty scenarios and failed-verification states
hide conclusions and disable exports.

Print-button interception checks the handler; PDF generation checks Chromium print
rendering. Neither is a physical printer test. Mobile emulation is **not** a physical
iPhone/Safari or Android acceptance result. Inspect the generated screenshots/PDFs
before declaring visual acceptance. `tests/report_ui.cjs` remains a minimal-DOM
handler regression; it must never be counted as real-browser acceptance.

## Privacy and operational boundary

- Input and exported JSON/HTML contain plaintext financial data. The application
  sends no financial data to a service and contains no remote report assets.
- Source links are external navigation when deliberately opened; the report itself
  works offline. Do not publish actual household HTML, JSON, screenshots or logs.
- This collector uses fictional data only. Its bundle may still disclose local paths
  and environment details; review before sharing. Report generation for real data
  stays local and separate from this collector.
- Deletion means deleting local report/export/evidence files and any copies or
  backups; no remote deletion or encryption guarantee is implied.
- Preserve the source commit and evidence bundle for rollback. Regenerate reports
  after rule or calculation changes; do not silently change old reports.

## Remaining acceptance

Record the actual exact-head run and environment in each PR. Missing browser runtime,
physical-device checks, professional-review roles, approved launch scope and any
unresolved numerical differences remain explicit open gates. No production deployment,
real-family trial, automatic tax filing or transaction is introduced by these tools.
