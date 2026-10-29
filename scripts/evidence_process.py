#!/usr/bin/env python3
"""Isolated Linux subreaper for one evidence command (not a security sandbox)."""
import argparse
import ctypes
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def children_path():
    # Refuse mismatched proc mounts before starting any command. Never signal
    # PIDs from a different namespace than waitpid/kill use.
    if sys.platform != 'linux':
        raise RuntimeError('Evidence supervision requires Linux')
    if int(Path('/proc/self/stat').read_text().split(' ', 1)[0]) != os.getpid():
        raise RuntimeError('Evidence supervision requires /proc in the current PID namespace')
    path = Path(f'/proc/self/task/{os.getpid()}/children')
    path.read_text()  # Require this kernel interface before spawning work.
    return path


def enable_subreaper():
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(36, 1, 0, 0, 0) != 0:  # PR_SET_CHILD_SUBREAPER
        raise OSError(ctypes.get_errno(), 'Cannot enable evidence subreaper')
    enabled = ctypes.c_int()
    if libc.prctl(37, ctypes.byref(enabled), 0, 0, 0) != 0 or enabled.value != 1:
        raise RuntimeError('Cannot confirm evidence subreaper')


def settle_children(path, timeout=5):
    """Kill/reap adopted descendants, including setsid/double-fork children.

    /proc enumeration is only for finding children to stop. ECHILD from waitpid
    is the completion gate; an empty or racing /proc snapshot is never proof.
    This runs in a private single-threaded supervisor with no unrelated children.
    """
    deadline = time.monotonic() + timeout
    found = False
    while True:
        try:
            pid, _ = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            return found
        found = True
        if pid:  # Reap zombies; live descendants will be adopted as parents die.
            continue
        if time.monotonic() >= deadline:
            raise RuntimeError('Descendant cleanup unconfirmed; no evidence receipt')
        for pid in map(int, path.read_text().split()):
            try:
                reaped, _ = os.waitpid(pid, os.WNOHANG)
                if not reaped:
                    # It is our unreaped child: its PID cannot be reused before
                    # we reap it, even if it exits between waitpid and kill.
                    os.kill(pid, signal.SIGKILL)
            except (ChildProcessError, ProcessLookupError):
                continue
        time.sleep(.01)


def supervise(command, timeout):
    path = children_path()
    signal.signal(signal.SIGCHLD, signal.SIG_DFL)
    enable_subreaper()
    if path.read_text().strip():
        raise RuntimeError('Supervisor unexpectedly has existing children')
    try:
        process = subprocess.Popen(command, start_new_session=True)
    except OSError as exc:
        print(str(exc), flush=True)
        settle_children(path)
        return -1
    try:
        code = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        # Kill the direct parent first, so detached children are adopted here.
        process.kill()
        process.wait()
        settle_children(path)
        print('Command timed out; descendants stopped and reaped', flush=True)
        return -1
    except BaseException:
        process.kill()
        process.wait()
        settle_children(path)
        raise
    if settle_children(path):
        print(f'Command exited {code} with background descendants; stopped and reaped; command failed', flush=True)
        return -1
    return code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--receipt', required=True, type=Path)
    parser.add_argument('--timeout', required=True, type=float)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command or args.timeout <= 0:
        raise ValueError('Command and positive timeout required')
    code = supervise(command, args.timeout)
    # Written only after waitpid proves no children remain. Missing receipt or
    # any supervisor failure must abort collection, never merely fail a check.
    args.receipt.write_text(json.dumps({'settled': True, 'exit_code': code}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
