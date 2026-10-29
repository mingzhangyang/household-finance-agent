#!/usr/bin/env python3
"""Collect reproducible evidence using ONLY the checked-in fictional household.

Exit 0: requested checks passed; exit 1: a check failed; browser skipped is recorded
as not_run (never pass). This does not approve a professional release.
"""
import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_command(command, log, env, timeout=300):
    # The private supervisor owns timeout/cleanup. An abnormal supervisor exit
    # or missing receipt aborts main before any artifact manifest is published.
    with tempfile.TemporaryDirectory(prefix='finance-command-') as temp:
        receipt = Path(temp)/'settled.json'
        with log.open('w') as stream:
            result = subprocess.run([sys.executable, str(ROOT/'scripts/evidence_process.py'),
                '--receipt', str(receipt), '--timeout', str(timeout), '--', *command],
                cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT)
        if result.returncode != 0 or not receipt.is_file():
            raise RuntimeError('Command supervision unconfirmed; evidence collection aborted; see '+str(log))
        status = json.loads(receipt.read_text())
        if status.get('settled') is not True or type(status.get('exit_code')) is not int:
            raise RuntimeError('Invalid command supervision receipt; evidence collection aborted')
        return status['exit_code']


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True, help='new private local directory')
    ap.add_argument('--browser', action='store_true', help='require actual Chromium acceptance')
    args = ap.parse_args()
    # Report handler and download/replay tests need Node even without --browser.
    # unittest skips those tests when Node is missing; zero exit is not enough.
    if shutil.which('node') is None:
        ap.error('Node.js is required for evidence collection, including offline report checks')
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    tracked = git('ls-files').splitlines()
    dirty = git('status', '--porcelain')
    files = {p: sha(ROOT/p) if (ROOT/p).is_file() else None for p in tracked}
    evidence = {'schema_version':1, 'created_at_utc':datetime.now(timezone.utc).isoformat(),
        'source_commit':git('rev-parse','HEAD'), 'source_tree':git('rev-parse','HEAD^{tree}'),
        'dirty':bool(dirty), 'working_tree_status':dirty, 'tracked_file_sha256':files,
        'python':sys.version, 'platform':platform.platform(), 'commands':[],
        'github_actions':'not_checked', 'professional_review':'not_recorded',
        'physical_mobile_browser':'not_run', 'browser':'not_run', 'release_approved':False,
        'input':'examples/audited-household-2026.json', 'data_classification':'fictional_only'}
    env = os.environ.copy(); env['PYTHON'] = sys.executable
    # NODE_PATH may be supplied by the runtime; no host-specific paths in repo.
    if not env.get('NODE_PATH') and env.get('CODEX_PRIMARY_RUNTIME_NODE_MODULES'):
        env['NODE_PATH'] = env['CODEX_PRIMARY_RUNTIME_NODE_MODULES']

    def run(name, command):
        log = out/(name+'.log')
        code = run_command(command, log, env)
        evidence['commands'].append({'name':name,'argv':command,'exit_code':code,
                                     'status':'passed' if code==0 else 'failed','log':log.name})
        return code==0

    ok = run('offline', ['sh','scripts/verify_local.sh'])
    fixture = 'examples/audited-household-2026.json'
    generated = run('result',[sys.executable,'scripts/audit_plan.py','run',fixture,'--output',str(out/'result.json')])
    ok = generated and ok
    if generated:
        ok = run('arithmetic',[sys.executable,'scripts/verify_outputs.py',str(out/'result.json'),
                  '--plan',fixture,'--engine-dir','scripts','--output',str(out/'arithmetic.json')]) and ok
        ok = run('replay',[sys.executable,'scripts/verify_replay.py',str(out/'result.json'),
                  '--plan',fixture,'--output',str(out/'replay.json')]) and ok
    rendered = run('report',[sys.executable,'scripts/render_audit.py',fixture,'--output',str(out/'report.html')])
    ok = rendered and ok
    if args.browser:
        if rendered:
            passed = run('browser',['node','tests/browser_acceptance.cjs',str(out/'report.html'),str(out/'browser')])
            evidence['browser'] = 'passed' if passed else 'failed'
            ok = passed and ok
        else:
            evidence['browser'] = 'blocked_by_report_failure'; ok = False
    evidence['source_unchanged_during_run'] = (
        git('rev-parse','HEAD') == evidence['source_commit'] and
        git('status','--porcelain') == dirty and
        files == {p:sha(ROOT/p) if (ROOT/p).is_file() else None for p in tracked})
    ok = ok and evidence['source_unchanged_during_run']
    evidence['checks_passed'] = ok
    evidence['exact_clean_commit'] = not evidence['dirty'] and evidence['source_unchanged_during_run']
    evidence['artifacts_sha256'] = {str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()}
    (out/'manifest.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(json.dumps({k:evidence[k] for k in ('source_commit','exact_clean_commit','checks_passed','browser','release_approved')}))
    return 0 if ok else 1


if __name__=='__main__':
    raise SystemExit(main())
