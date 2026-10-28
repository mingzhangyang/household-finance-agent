#!/bin/sh
# Canonical offline verification. Uses fictional data; requires Python 3.10+.
set -eu
cd "$(dirname "$0")/.."
PYTHON="${PYTHON:-python3}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT HUP INT TERM
"$PYTHON" -m compileall -q scripts tests
"$PYTHON" -m unittest discover -s tests -p 'test_*.py' -v
"$PYTHON" scripts/audit_plan.py validate examples/audited-household-2026.json
"$PYTHON" scripts/audit_plan.py run examples/audited-household-2026.json --output "$TMP/result.json"
"$PYTHON" scripts/verify_outputs.py "$TMP/result.json" --plan examples/audited-household-2026.json --engine-dir scripts --output "$TMP/verification.json"
"$PYTHON" scripts/verify_replay.py "$TMP/result.json" --plan examples/audited-household-2026.json --output "$TMP/replay.json"
"$PYTHON" scripts/market_history.py examples/nyu_2000_2018_partial.csv --horizon 10 --output "$TMP/market.json"
"$PYTHON" scripts/render_audit.py examples/audited-household-2026.json --output "$TMP/report.html"
test -s "$TMP/report.html"
if grep -q '__AUDIT_DATA__' "$TMP/report.html"; then
  echo 'FAIL: HTML placeholder remained unrendered' >&2
  exit 1
fi
"$PYTHON" - "$TMP" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1])
r=json.loads((p/'result.json').read_text())
v=json.loads((p/'verification.json').read_text())
m=json.loads((p/'market.json').read_text())
assert v['passed'] and v['verified_engine_hash'] and v['verified_input_hash']
assert len(r['simulated_path_manifest'])==r['trials']
assert m['calibration']['observations']==19
print('PASS: offline fictional household verification, tax/SSA and history smoke tests')
print('NOTE: passing tests are not external professional certification')
PY
