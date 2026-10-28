"""Evidence commands cannot leave writers behind on any exit path."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import collect_evidence
from collect_evidence import run_command, sha
import evidence_process

try:
    evidence_process.children_path()
    SUPERVISION_UNAVAILABLE = None
except (OSError, RuntimeError) as exc:
    SUPERVISION_UNAVAILABLE = str(exc)

if SUPERVISION_UNAVAILABLE and os.environ.get('HFA_REQUIRE_SUPERVISION') == '1':
    raise RuntimeError(SUPERVISION_UNAVAILABLE)


class SupervisionFailure(unittest.TestCase):
    def test_namespace_mismatch_prevents_command_launch(self):
        with patch.object(evidence_process.os, 'getpid', return_value=-1), \
             patch.object(evidence_process.subprocess, 'Popen') as launch:
            with self.assertRaises(RuntimeError):
                evidence_process.supervise(['unused'], 1)
            launch.assert_not_called()

    def test_missing_receipt_aborts_collection_without_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp)/'evidence'
            # A supervisor returning zero without proving cleanup is not a pass.
            with patch.object(sys,'argv',['collect_evidence','--output',str(out)]), \
                 patch.object(collect_evidence,'git',return_value=''), \
                 patch.object(collect_evidence.platform,'platform',return_value='test'), \
                 patch.object(collect_evidence.subprocess,'run',return_value=subprocess.CompletedProcess([],0)):
                with self.assertRaisesRegex(RuntimeError,'supervision unconfirmed'):
                    collect_evidence.main()
            self.assertFalse((out/'manifest.json').exists())

    def test_empty_proc_snapshot_does_not_prove_children_exited(self):
        with tempfile.TemporaryDirectory() as temp:
            children=Path(temp)/'children'; children.write_text('')
            with patch.object(evidence_process.os,'waitpid',return_value=(0,0)), \
                 patch.object(evidence_process.time,'monotonic',side_effect=[0,0,6]), \
                 patch.object(evidence_process.time,'sleep'):
                with self.assertRaisesRegex(RuntimeError,'cleanup unconfirmed'):
                    evidence_process.settle_children(children)


@unittest.skipIf(SUPERVISION_UNAVAILABLE is not None, SUPERVISION_UNAVAILABLE or '')
class EvidenceCommands(unittest.TestCase):
    def test_exit_codes_and_launch_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            log=Path(temp)/'command.log'
            self.assertEqual(run_command([sys.executable,'-c','print("done")'],log,os.environ),0)
            self.assertIn('done',log.read_text())
            self.assertEqual(run_command([sys.executable,'-c','raise SystemExit(3)'],log,os.environ),3)
            self.assertEqual(run_command(['/nonexistent/evidence-command'],log,os.environ),-1)

    def check_writer(self, exit_code, detached, grandchild):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp); log=out/'command.log'; artifact=out/'artifact'; trigger=out/'trigger'
            child='''import pathlib, signal, sys, time
signal.signal(signal.SIGTERM, signal.SIG_IGN)
p=pathlib.Path(sys.argv[1]); trigger=pathlib.Path(sys.argv[2])
p.write_text('')  # Deliberately widen the old file-existence readiness race.
time.sleep(.1)
print('child ready', flush=True)
p.write_text('ready')
deadline=time.monotonic()+10
while not trigger.exists() and time.monotonic()<deadline: time.sleep(.005)
p.write_text('late write')
print('late log', flush=True)
'''
            if grandchild:
                child='import subprocess, sys; subprocess.Popen([sys.executable, "-c", '+repr(child)+', *sys.argv[1:]], start_new_session='+repr(detached)+')'
            parent='''import pathlib, subprocess, sys, time
subprocess.Popen([sys.executable, '-c', sys.argv[1], sys.argv[2], sys.argv[3]], start_new_session=sys.argv[5]=='True')
p=pathlib.Path(sys.argv[2])
deadline=time.monotonic()+5
while not p.exists() or p.read_text()!='ready':
    if time.monotonic()>deadline: raise RuntimeError('writer never became ready')
    time.sleep(.005)
if sys.argv[4]=='timeout': time.sleep(30)
else: raise SystemExit(int(sys.argv[4]))
'''
            code=run_command([sys.executable,'-c',parent,child,str(artifact),str(trigger),str(exit_code),str(detached)],
                             log,os.environ,timeout=2 if exit_code=='timeout' else 6)
            hashes=(sha(log),sha(artifact))
            trigger.touch()  # Any escaped writer would now modify both files.
            time.sleep(.3)
            self.assertEqual(code,-1)
            self.assertEqual((sha(log),sha(artifact)),hashes)
            self.assertEqual(artifact.read_text(),'ready')
            self.assertNotIn('late log',log.read_text().splitlines())

    def test_exited_parent_cannot_leave_background_writers(self):
        for exit_code in (0,3):
            for grandchild in (False,True):
                with self.subTest(exit_code=exit_code,grandchild=grandchild):
                    self.check_writer(exit_code,False,grandchild)

    def test_detached_child_and_grandchild_cannot_escape(self):
        for exit_code in (0,3,'timeout'):
            for grandchild in (False,True):
                with self.subTest(exit_code=exit_code,grandchild=grandchild):
                    self.check_writer(exit_code,True,grandchild)

    def test_timeout_kills_descendant_writer_before_return(self):
        self.check_writer('timeout',False,False)


if __name__=='__main__': unittest.main()
