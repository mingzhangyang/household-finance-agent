"""Every command exit must settle descendant writers before hashing."""
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from collect_evidence import run_command, sha


@unittest.skipUnless(os.name == 'posix', 'POSIX process-group cleanup')
class EvidenceCommands(unittest.TestCase):
    def test_exit_codes_and_launch_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            log=Path(temp)/'command.log'
            self.assertEqual(run_command([sys.executable,'-c','print("done")'],log,os.environ),0)
            self.assertIn('done',log.read_text())
            self.assertEqual(run_command([sys.executable,'-c','raise SystemExit(3)'],log,os.environ),3)
            self.assertEqual(run_command(['/nonexistent/evidence-command'],log,os.environ),-1)

    def test_timeout_kills_descendant_writer_before_return(self):
        with tempfile.TemporaryDirectory() as temp:
            out=Path(temp); log=out/'command.log'; artifact=out/'artifact'
            child='''import pathlib, signal, sys, time
signal.signal(signal.SIGTERM, signal.SIG_IGN)
p=pathlib.Path(sys.argv[1]); p.write_text('ready')
print('child ready', flush=True)
time.sleep(1.5)
p.write_text('late write')
print('late log', flush=True)
'''
            parent='''import subprocess, sys, time
subprocess.Popen([sys.executable, '-c', sys.argv[1], sys.argv[2]])
time.sleep(30)
'''
            code=run_command([sys.executable,'-c',parent,child,str(artifact)],log,os.environ,timeout=.5)
            self.assertEqual(code,-1)
            self.assertEqual(artifact.read_text(),'ready')
            hashes=(sha(log),sha(artifact))
            time.sleep(1.6)
            self.assertEqual((sha(log),sha(artifact)),hashes)
            self.assertNotIn('late log',log.read_text().splitlines())
    def test_exited_parent_cannot_leave_background_writers(self):
        for exit_code in (0, 3):
            for grandchild in (False, True):
                with self.subTest(exit_code=exit_code, grandchild=grandchild), tempfile.TemporaryDirectory() as temp:
                    out=Path(temp); log=out/'command.log'; artifact=out/'artifact'
                    child='''import pathlib, signal, sys, time
signal.signal(signal.SIGTERM, signal.SIG_IGN)
p=pathlib.Path(sys.argv[1]); p.write_text('ready')
print('child ready', flush=True)
time.sleep(1)
p.write_text('late write')
print('late log', flush=True)
'''
                    parent='''import pathlib, subprocess, sys, time
subprocess.Popen([sys.executable, '-c', sys.argv[1], sys.argv[2]])
while not pathlib.Path(sys.argv[2]).exists(): time.sleep(.005)
raise SystemExit(int(sys.argv[3]))
'''
                    if grandchild:
                        # The intermediate process exits before the top-level
                        # parent, leaving a grandchild in the same group.
                        child='import subprocess, sys; subprocess.Popen([sys.executable, "-c", '+repr(child)+', sys.argv[1]])'
                    code=run_command([sys.executable,'-c',parent,child,str(artifact),str(exit_code)],log,os.environ,timeout=5)
                    hashes=(sha(log),sha(artifact))
                    time.sleep(1.1)
                    self.assertEqual(code,-1, 'leftover descendants must fail even a zero exit')
                    self.assertEqual((sha(log),sha(artifact)),hashes)
                    self.assertEqual(artifact.read_text(),'ready')
                    self.assertIn('background descendants',log.read_text())
                    self.assertNotIn('late log',log.read_text().splitlines())


if __name__=='__main__': unittest.main()
