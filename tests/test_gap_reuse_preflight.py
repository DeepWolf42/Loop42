from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

from tools.checks.gap_reuse_preflight import preflight, _load_evidence


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


class GapReusePreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name)
        git(self.repo, "init")
        git(self.repo, "config", "user.email", "loop42@example.invalid")
        git(self.repo, "config", "user.name", "Loop42 Test")
        (self.repo / "checkpoint.py").write_text("def recover_checkpoint():\n    return True\n", encoding="utf-8")
        (self.repo / "README.md").write_text("# Test repository\n", encoding="utf-8")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-m", "fixture")
        self.head = git(self.repo, "rev-parse", "HEAD")

    def tearDown(self):
        self.temp.cleanup()

    def check(self, target="checkpoint recovery", trigger="architecture", evidence=None):
        return preflight(self.repo, target=target, trigger=trigger, expected_head=self.head, evidence=evidence)

    def test_real_local_scan_finds_existing_candidate_and_honest_unknowns(self):
        result = self.check()
        self.assertEqual(result["candidates"][0]["name"], "checkpoint.py")
        self.assertEqual(result["next_action"], "VERIFY_REUSE_FIT_WITH_SMALLEST_TEST")
        self.assertEqual([x["status"] for x in result["coverage"]][1:], ["NOT_SEARCHED"] * 3)
        self.assertFalse(result["adoption_authorized"])

    def test_no_match_does_not_mean_no_external_solution(self):
        result = self.check("unrelated kubernetes")
        self.assertEqual(result["next_action"], "RESEARCH_ONLY_HIGHEST_IMPACT_UNKNOWN_IF_NEEDED")
        self.assertEqual(result["coverage"][-1]["status"], "NOT_SEARCHED")

    def test_open_work_and_tools_precede_external_candidates(self):
        stamp = "2026-10-28T08:20:00+01:00"
        def area(name, revision=None):
            result = {"status":"USEFUL_CANDIDATE", "source":"fixture://" + name, "checked_at":stamp,
                      "items":[{"name":name, "reference":"fixture://" + name, "reason":"reusable pattern"}]}
            if revision is not None:
                result["revision"] = revision
            return result
        result = self.check("unrelated target", evidence={
            "external_patterns":area("framework"),
            "open_work":area("existing_pr", self.head),
            "installed_capabilities":area("built_in_tool", self.head),
        })
        self.assertEqual([x["name"] for x in result["candidates"]], ["existing_pr", "built_in_tool", "framework"])

    def test_stale_open_work_never_counted_as_checked(self):
        result = self.check("unrelated target", evidence={"open_work": {
            "status":"USEFUL_CANDIDATE", "source":"fixture", "checked_at":"2026-10-28T08:20:00Z",
            "revision":"0" * 40, "items":[{"name":"old", "reference":"x", "reason":"old"}]}})
        self.assertEqual(result["coverage"][1]["status"], "BLOCKED_UNKNOWN")
        self.assertFalse(result["candidates"])

    def test_checked_no_delta_needs_evidence_and_cannot_have_candidates(self):
        with self.assertRaisesRegex(ValueError, "requires source"):
            self.check(evidence={"external_patterns": {"status":"CHECKED_NO_DELTA"}})
        with self.assertRaisesRegex(ValueError, "no-delta"):
            self.check(evidence={"external_patterns": {"status":"CHECKED_NO_DELTA", "source":"x", "checked_at":"2026-10-28T08:20:00Z", "items":[{"name":"a", "reference":"x", "reason":"r"}]}})

    def test_stale_head_rejected_and_routine_not_scanned(self):
        with self.assertRaisesRegex(ValueError, "live HEAD differs"):
            preflight(self.repo, target="x", trigger="architecture", expected_head="0" * 40)
        result = self.check(trigger="routine")
        self.assertEqual(result["status"], "SKIPPED")
        self.assertEqual(result["coverage"], [])

    def test_cli_read_only_and_valid_json(self):
        cli = Path(__file__).resolve().parents[1] / "tools/checks/gap_reuse_preflight.py"
        invocation = [sys.executable, "-m", "tools.checks.gap_reuse_preflight",
                      "--repo", str(self.repo), "--target", "checkpoint recovery",
                      "--trigger", "repeated_failure", "--expected-head", self.head]
        run = subprocess.run(invocation, capture_output=True, text=True, cwd=cli.parents[2])
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout)["schema"], "loop42.gap-reuse-preflight.v1")
        self.assertEqual(git(self.repo, "status", "--porcelain"), "")

    def test_evidence_duplicate_keys_rejected(self):
        evidence = self.repo / "evidence.json"
        evidence.write_text('{"open_work":{},"open_work":{}}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            _load_evidence(evidence)


if __name__ == "__main__":
    unittest.main()
