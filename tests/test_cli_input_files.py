"""CLI file input must be bounded regular bytes, never an EOF-waiting device."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tools.harness.worker_dispatch_cli import MAX_INPUT_BYTES, _read_input

ROOT = Path(__file__).resolve().parents[1]


class CliInputFileTests(unittest.TestCase):
    def test_regular_file_boundary_and_byte_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "request.json"
            for raw in (b"", b"\x00\xff\x1a\r\n", b'{"source":"\xc3\xa4"}\r\n', b"x" * MAX_INPUT_BYTES):
                path.write_bytes(raw)
                self.assertEqual(_read_input(str(path)), raw)
            path.write_bytes(b"x" * (MAX_INPUT_BYTES + 1))
            with self.assertRaises(ValueError):
                _read_input(str(path))

    def test_open_pipe_rejected_before_read_on_both_platforms(self):
        # Real owned pipe descriptors, injected only at the open boundary.
        # Keeping the writer open makes an unsafe buffered read block.
        script = '''
import os
from pathlib import Path
from unittest.mock import patch
from tools.harness.worker_dispatch_cli import _read_input
r,w=os.pipe()
def descriptor(*a,**k):return os.dup(r)
def handle(*a,**k):return os.fdopen(os.dup(r),'rb')
try:
    with patch.object(Path,'open',side_effect=handle),patch('os.open',side_effect=descriptor):
        try:_read_input('owned-pipe')
        except ValueError:print('REJECTED_NONREGULAR')
        else:raise SystemExit('pipe accepted')
finally:
    os.close(r);os.close(w)
'''
        try:
            result = subprocess.run([sys.executable, "-B", "-c", script], cwd=ROOT,
                                    capture_output=True, timeout=3)
        except subprocess.TimeoutExpired:
            self.fail("CLI file input blocked on an open pipe")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(b"REJECTED_NONREGULAR", result.stdout)

    @unittest.skipUnless(hasattr(os, "mkfifo"), "real named FIFO requires POSIX")
    def test_both_cli_entrypoints_reject_fifo_without_success_output(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "request.json"
            os.mkfifo(path)
            for module in ("worker_dispatch_cli", "verification_receipt_cli"):
                with self.subTest(module=module):
                    try:
                        result = subprocess.run([sys.executable, "-B", "-m", "tools.harness." + module,
                                                 "--input", str(path)], cwd=ROOT,
                                                capture_output=True, timeout=3)
                    except subprocess.TimeoutExpired:
                        self.fail(module + " blocked on FIFO without a writer")
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertEqual(result.stdout, b"")
                    self.assertNotIn(b"Traceback", result.stderr)

    def test_directory_and_missing_file_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            for path in (directory, str(Path(directory) / "missing")):
                with self.subTest(path=path), self.assertRaises((ValueError, OSError)):
                    _read_input(path)

    def test_known_final_symlink_is_rejected_before_opening_any_descriptor(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "request.json"
            target.write_bytes(b"{}")
            with patch.object(Path, "is_symlink", return_value=True), patch("os.open", wraps=os.open) as opened:
                with self.assertRaises(ValueError):
                    _read_input(str(target))
                opened.assert_not_called()

    def test_real_final_symlink_never_becomes_request_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "request.json"
            target.write_bytes(b"{}")
            link = Path(directory) / "link.json"
            try:
                link.symlink_to(target)
            except OSError as error:
                if getattr(error, "winerror", None) == 1314:
                    self.skipTest("Windows symlink creation privilege unavailable")
                raise
            with self.assertRaises(ValueError):
                _read_input(str(link))

    @unittest.skipUnless(os.name == "posix" and hasattr(os, "O_NOFOLLOW"),
                         "atomic final-symlink defense requires POSIX O_NOFOLLOW")
    def test_final_symlink_missed_by_precheck_is_rejected_by_open(self):
        import errno
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "request.json"
            target.write_bytes(b"{}")
            link = Path(directory) / "link.json"
            link.symlink_to(target)
            # Deterministic open-boundary countercase, not a claimed live race.
            with patch.object(Path, "is_symlink", return_value=False):
                with self.assertRaises(OSError) as error:
                    _read_input(str(link))
                self.assertEqual(error.exception.errno, errno.ELOOP)


if __name__ == "__main__":
    unittest.main()
