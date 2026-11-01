"""Real subprocess checks for optional stdout/stderr separation, not model mocks."""
from pathlib import Path
import sys
import tempfile
import unittest

from tools.harness.verification_registry import VerificationRegistry,VerificationSpec,run_verifications


class VerificationStreamsTests(unittest.TestCase):
    def run_process(self,script,**kwargs):
        registry=VerificationRegistry((VerificationSpec('test:streams',(sys.executable,'-B','-c',script),1),))
        with tempfile.TemporaryDirectory() as directory:
            return run_verifications(Path(directory),('test:streams',),registry,**kwargs)[0]

    def test_separated_stderr_cannot_corrupt_json_stdout(self):
        result=self.run_process('import sys;print("{\\"ok\\":true}");print("private diagnostic",file=sys.stderr)',separate_stderr=True)
        self.assertTrue(result.passed)
        self.assertEqual(result.output.strip(),'{"ok":true}')
        self.assertNotIn('private diagnostic',result.output)

    def test_default_combined_output_remains_compatible(self):
        result=self.run_process('import sys;print("stdout");print("stderr",file=sys.stderr)')
        self.assertTrue(result.passed)
        self.assertIn('stdout',result.output)
        self.assertIn('stderr',result.output)

    def test_stderr_counts_toward_the_shared_limit(self):
        result=self.run_process('import sys;print("{\\"ok\\":true}");sys.stderr.write("x"*4096)',separate_stderr=True,output_limit=64)
        self.assertFalse(result.passed)
        self.assertTrue(result.output_truncated)
        self.assertIsNone(result.exit_code)
        self.assertLessEqual(len(result.output.encode()),64)

    def test_timeout_still_fails_closed_with_two_streams(self):
        result=self.run_process('import time;time.sleep(30)',separate_stderr=True)
        self.assertFalse(result.passed)
        self.assertTrue(result.timed_out)
        self.assertIsNone(result.exit_code)

    def test_invalid_option_is_rejected_before_execution(self):
        with self.assertRaises(TypeError):self.run_process('raise SystemExit(0)',separate_stderr=1)

if __name__=='__main__':unittest.main()
