"""Timeouts must settle descendant writers before artifacts are hashed."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from collect_evidence import run_command, sha


@unittest.skipUnless(sys.platform == 'linux', 'Linux process-group cleanup')
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


if __name__=='__main__': unittest.main()
