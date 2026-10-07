import sys
import tempfile
from pathlib import Path
import unittest

from tools.harness.verification_registry import (
    VerificationRegistry,
    VerificationSpec,
    run_verifications,
)


class VerificationRegistryTests(unittest.TestCase):
    def test_unknown_identifier_fails_before_any_process_starts(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            marker = root / "marker"
            registry = VerificationRegistry((
                VerificationSpec("known", (sys.executable, "-c", f"from pathlib import Path; Path({str(marker)!r}).write_text('ran')")),
            ))
            with self.assertRaisesRegex(ValueError, "unknown verification identifier"):
                run_verifications(root, ("known", "missing"), registry)
            self.assertFalse(marker.exists())

    def test_registered_argv_runs_without_shell_and_captures_result(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            registry = VerificationRegistry((
                VerificationSpec("unit:x", (sys.executable, "-c", "print('ok')")),
            ))
            result = run_verifications(root, ("unit:x",), registry)[0]
            self.assertTrue(result.passed)
            self.assertIn("ok", result.output)

    def test_failure_stops_following_verification(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            marker = root / "later"
            registry = VerificationRegistry((
                VerificationSpec("fail", (sys.executable, "-c", "raise SystemExit(3)")),
                VerificationSpec("later", (sys.executable, "-c", f"from pathlib import Path; Path({str(marker)!r}).write_text('ran')")),
            ))
            results = run_verifications(root, ("fail", "later"), registry)
            self.assertEqual(len(results), 1)
            self.assertFalse(results[0].passed)
            self.assertFalse(marker.exists())

    def test_output_is_bounded(self):
        with tempfile.TemporaryDirectory() as raw:
            registry = VerificationRegistry((
                VerificationSpec("verbose", (sys.executable, "-c", "print('x' * 4096)")),
            ))
            result = run_verifications(Path(raw), ("verbose",), registry, output_limit=128)[0]
            self.assertTrue(result.passed)
            self.assertTrue(result.output_truncated)
            self.assertLessEqual(len(result.output.encode('utf-8')), 128)


if __name__ == "__main__":
    unittest.main()
