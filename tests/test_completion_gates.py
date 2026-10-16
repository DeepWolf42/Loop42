import json
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from tools.checks.completion_gates import load_contract, verify


class CompletionGatesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)

        def git(*args):
            r = subprocess.run(["git", *args], cwd=self.repo, capture_output=True, text=True, check=True)
            return r.stdout.strip()

        git("init", "-q")
        git("config", "user.email", "test@example.invalid")
        git("config", "user.name", "test")
        (self.repo / "test_case.py").write_text(
            'import sys\nassert "--bad-selector" not in sys.argv\nprint("CHECK_OK")\n', encoding="utf-8"
        )
        git("add", "test_case.py")
        git("commit", "-qm", "fixture")
        self.rev = git("rev-parse", "HEAD")
        self.gate = {
            "id": "selector",
            "criterion": "Simulated CORA-like suffix counterexample is rejected",
            "argv": [sys.executable, "test_case.py"],
            "expect_line": "CHECK_OK",
            "timeout_seconds": 5,
        }
        self.contract = {"schema": "loop42.completion-gates.v1", "gates": [self.gate]}

    def test_valid_gate_passes_on_exact_revision(self):
        report = verify(self.contract, self.repo, expected_revision=self.rev, run=True)
        self.assertTrue(report["complete"])
        self.assertEqual(report["gates"][0]["status"], "PASS")
        self.assertEqual(len(report["gate_definition_sha256"]), 64)

    def test_claimed_success_cannot_override_failing_gate(self):
        self.gate["argv"] = [sys.executable, "test_case.py", "--bad-selector"]
        report = verify(self.contract, self.repo, expected_revision=self.rev, run=True)
        self.assertFalse(report["complete"])
        self.assertEqual(report["gates"][0]["status"], "FAIL")

    def test_missed_expectation_fails_despite_zero_exit(self):
        self.gate["expect_line"] = "MISSING_ASSERTION"
        self.assertFalse(verify(self.contract, self.repo, expected_revision=self.rev, run=True)["complete"])

    def test_parse_only_never_counts_as_success(self):
        report = verify(self.contract, self.repo, expected_revision=self.rev, run=False)
        self.assertFalse(report["complete"])
        self.assertEqual(report["gates"][0]["status"], "NOT_RUN")

    def test_wrong_sha_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "stale source revision"):
            verify(self.contract, self.repo, expected_revision="a" * 40, run=True)

    def test_changed_tracked_content_fails_closed(self):
        (self.repo / "test_case.py").write_text('print("CHECK_OK")\n')
        with self.assertRaisesRegex(ValueError, "dirty"):
            verify(self.contract, self.repo, expected_revision=self.rev, run=True)

    def test_gate_that_modifies_tracked_source_cannot_certify_itself(self):
        self.gate["argv"] = [sys.executable, "-c", "from pathlib import Path; Path('test_case.py').write_text('changed'); print('CHECK_OK')"]
        report = verify(self.contract, self.repo, expected_revision=self.rev, run=True)
        self.assertFalse(report["complete"])
        self.assertEqual(report["gates"][0]["status"], "FAIL_SOURCE_CHANGED")

    def test_every_gate_must_pass(self):
        self.contract["gates"].append({**self.gate, "id": "secondary", "expect_line": "NOT_PRINTED"})
        report = verify(self.contract, self.repo, expected_revision=self.rev, run=True)
        self.assertFalse(report["complete"])
        self.assertEqual([g["status"] for g in report["gates"]], ["PASS", "FAIL"])

    def test_malformed_or_duplicate_gates_rejected(self):
        self.contract["gates"].append(dict(self.gate))
        p = self.repo / "contract.json"
        p.write_text(json.dumps(self.contract))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            load_contract(p)
        p.write_text('{"schema":"a","schema":"a"}')
        with self.assertRaisesRegex(ValueError, "duplicate JSON"):
            load_contract(p)

    def test_actual_loop42_worker_identity_regression_is_detected(self):
        """A fresh committed semantic mutation must fail the real worker suite."""
        baseline = Path(__file__).resolve().parents[1]
        for rel in (
            "tools/__init__.py",
            "tools/harness/__init__.py",
            "tools/harness/worker_dispatch.py",
            "tests/test_worker_dispatch.py",
        ):
            target = self.repo / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(baseline / rel, target)

        def git(*args):
            return subprocess.run(
                ["git", *args], cwd=self.repo, check=True,
                capture_output=True, text=True,
            ).stdout.strip()

        self.gate["argv"] = [
            sys.executable, "-m", "unittest", "discover",
            "-s", "tests", "-p", "test_worker_dispatch.py",
        ]
        self.gate["criterion"] = "Real Loop42 worker identity regression passes"
        self.gate["expect_line"] = "OK"
        self.gate["timeout_seconds"] = 30
        git("add", ".")
        git("commit", "-qm", "snapshot real worker module and tests")
        clean_sha = git("rev-parse", "HEAD")
        baseline_report = verify(self.contract, self.repo, expected_revision=clean_sha, run=True)
        self.assertTrue(baseline_report["complete"], baseline_report)

        # Simulate a real bug: falsely accept a stale source revision.
        worker = self.repo / "tools/harness/worker_dispatch.py"
        original = worker.read_text(encoding="utf-8")
        needle = "and artifact.source_revision == task.source_revision"
        self.assertIn(needle, original)
        worker.write_text(original.replace(needle, "and True", 1), encoding="utf-8")
        git("add", "tools/harness/worker_dispatch.py")
        git("commit", "-qm", "intentionally break revision identity matching")
        bad_sha = git("rev-parse", "HEAD")
        failing_report = verify(self.contract, self.repo, expected_revision=bad_sha, run=True)
        self.assertFalse(failing_report["complete"], failing_report)
        self.assertEqual(failing_report["gates"][0]["status"], "FAIL")


    def test_changed_gate_changes_definition_digest(self):
        r1 = verify(self.contract, self.repo, expected_revision=self.rev, run=True)
        self.gate["criterion"] = "Different acceptance meaning"
        r2 = verify(self.contract, self.repo, expected_revision=self.rev, run=True)
        self.assertNotEqual(r1["gate_definition_sha256"], r2["gate_definition_sha256"])


if __name__ == "__main__":
    unittest.main()
