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
import signal
import time
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def group_exists(pgid):
    # Use the same process namespace as Popen/killpg. A mounted /proc may
    # expose different PID/group IDs inside containers or sandbox runtimes.
    # Treat even an unreaped zombie conservatively: no manifest until the
    # group disappears, rather than risk overlooking a live writer.
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    return True


def stop_group(process):
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait()
    deadline = time.monotonic() + 5
    while group_exists(process.pid):
        if time.monotonic() >= deadline:
            # Fail closed: never publish hashes if writers may still be alive.
            raise RuntimeError('Command descendants did not stop; evidence not collected')
        time.sleep(.01)


def run_command(command, log, env, timeout=300):
    with log.open('w') as stream:
        try:
            process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=stream,
                stderr=subprocess.STDOUT, start_new_session=True)
        except OSError as exc:
            stream.write(str(exc)+'\n')
            return -1
        try:
            code = process.wait(timeout=timeout)
            # A successful parent exit does not prove its background work is
            # finished. Settle the entire group before logs/artifacts can be
            # hashed, and never report a command needing cleanup as passed.
            if group_exists(process.pid):
                stop_group(process)
                stream.write(f'Command exited {code} with live background descendants; '
                             'process group stopped; command failed.\n')
                return -1
            return code
        except subprocess.TimeoutExpired as exc:
            stop_group(process)
            stream.write(str(exc)+'\n')
            return -1
        except BaseException:
            stop_group(process)
            raise


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True, help='new private local directory')
    ap.add_argument('--browser', action='store_true', help='require actual Chromium acceptance')
    args = ap.parse_args()
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
