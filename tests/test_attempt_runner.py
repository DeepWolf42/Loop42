import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.harness.action_policy import ActionEffect, PolicyDecision, PolicyRule
from tools.harness.attempt_runner import AttemptStatus, run_autonomous_attempt
from tools.harness.change_set import ChangeSet, ModifyChange, sha256_text
from tools.harness.git_workspace import remove_worktree
from tools.harness.verification_registry import VerificationRegistry, VerificationSpec
from tools.harness.worker_provider import WorkerRequest, WorkerResult, WorkerStatus


ALLOW = (
    PolicyRule(
        "allow-test-workspace-writes",
        PolicyDecision.ALLOW,
        priority=100,
        effect=ActionEffect.REVERSIBLE_WRITE,
    ),
)


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        shell=False,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stdout.decode("utf-8", errors="replace"))
    return result.stdout.decode().strip()


def make_repo(root: Path) -> tuple[Path, str]:
    repo = root / "repo"
    repo.mkdir()
    git(repo, "init")
    git(repo, "config", "user.email", "loop42@example.invalid")
    git(repo, "config", "user.name", "Loop42 Tests")
    (repo / "x.py").write_text("x = 1\n", encoding="utf-8")
    git(repo, "add", "x.py")
    git(repo, "commit", "-m", "initial")
    return repo, git(repo, "rev-parse", "HEAD")


class FakeProvider:
    def __init__(self, mode="proposal"):
        self.mode = mode
        self.seen = None

    def run(self, request):
        self.seen = request
        common = dict(
            provider="fake",
            model="fake-1",
            task_id=request.task_id,
            attempt_id=request.attempt_id,
            source_revision=request.source_revision,
            context_fingerprint=request.context_fingerprint,
        )
        if self.mode == "blocked":
            return WorkerResult(
                status=WorkerStatus.BLOCKED,
                rationale_summary="not enough context",
                **common,
            )
        if self.mode == "bad_identity":
            common["attempt_id"] = "wrong-attempt"
            return WorkerResult(
                status=WorkerStatus.BLOCKED,
                rationale_summary="wrong",
                **common,
            )
        verification = () if self.mode == "unverified" else ("unit:file",)
        return WorkerResult(
            status=WorkerStatus.PROPOSAL,
            rationale_summary="change x",
            changeset=ChangeSet(
                (
                    ModifyChange(
                        "x.py",
                        sha256_text("x = 1\n"),
                        "x = 1",
                        "x = 2",
                    ),
                ),
                requested_verification=verification,
            ),
            **common,
        )


class AttemptRunnerTests(unittest.TestCase):
    def request(self, revision: str):
        return WorkerRequest(
            task_id="task-1",
            attempt_id="attempt-1",
            source_revision=revision[:12],
            context_fingerprint="a" * 64,
            task="Change x from 1 to 2.",
            context="x.py contains x = 1",
            allowed_capabilities=("propose_changes", "request_verification"),
        )

    def registry(self, *, passing=True):
        code = (
            "from pathlib import Path; assert Path('x.py').read_text() == 'x = 2\\n'"
            if passing
            else "raise SystemExit(7)"
        )
        return VerificationRegistry(
            (
                VerificationSpec(
                    "unit:file",
                    (sys.executable, "-c", code),
                ),
            )
        )

    def test_verified_attempt_changes_only_isolated_worktree(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo, revision = make_repo(root)
            parent = root / "workspaces"
            parent.mkdir()
            provider = FakeProvider()
            result = run_autonomous_attempt(
                repo,
                parent,
                self.request(revision),
                provider,
                self.registry(),
                rules=ALLOW,
            )
            try:
                self.assertEqual(result.status, AttemptStatus.VERIFIED)
                self.assertEqual((result.workspace.root / "x.py").read_text(), "x = 2\n")
                self.assertEqual((repo / "x.py").read_text(), "x = 1\n")
                self.assertEqual(provider.seen.source_revision, revision)
                self.assertTrue(result.verifications[0].passed)
            finally:
                remove_worktree(result.workspace)

    def test_blocked_provider_keeps_workspace_unchanged(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo, revision = make_repo(root)
            parent = root / "workspaces"
            parent.mkdir()
            result = run_autonomous_attempt(
                repo,
                parent,
                self.request(revision),
                FakeProvider("blocked"),
                self.registry(),
                rules=ALLOW,
            )
            try:
                self.assertEqual(result.status, AttemptStatus.BLOCKED)
                self.assertEqual((result.workspace.root / "x.py").read_text(), "x = 1\n")
            finally:
                remove_worktree(result.workspace)

    def test_identity_mismatch_is_provider_failure(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo, revision = make_repo(root)
            parent = root / "workspaces"
            parent.mkdir()
            result = run_autonomous_attempt(
                repo,
                parent,
                self.request(revision),
                FakeProvider("bad_identity"),
                self.registry(),
                rules=ALLOW,
            )
            try:
                self.assertEqual(result.status, AttemptStatus.PROVIDER_FAILED)
                self.assertIn("identity", result.reason)
                self.assertEqual((result.workspace.root / "x.py").read_text(), "x = 1\n")
            finally:
                remove_worktree(result.workspace)

    def test_no_verification_never_claims_verified(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo, revision = make_repo(root)
            parent = root / "workspaces"
            parent.mkdir()
            result = run_autonomous_attempt(
                repo,
                parent,
                self.request(revision),
                FakeProvider("unverified"),
                self.registry(),
                rules=ALLOW,
            )
            try:
                self.assertEqual(result.status, AttemptStatus.APPLIED_UNVERIFIED)
                self.assertEqual((result.workspace.root / "x.py").read_text(), "x = 2\n")
            finally:
                remove_worktree(result.workspace)

    def test_failed_verification_preserves_candidate_for_recovery(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo, revision = make_repo(root)
            parent = root / "workspaces"
            parent.mkdir()
            result = run_autonomous_attempt(
                repo,
                parent,
                self.request(revision),
                FakeProvider(),
                self.registry(passing=False),
                rules=ALLOW,
            )
            try:
                self.assertEqual(result.status, AttemptStatus.VERIFICATION_FAILED)
                self.assertEqual((result.workspace.root / "x.py").read_text(), "x = 2\n")
                self.assertEqual((repo / "x.py").read_text(), "x = 1\n")
            finally:
                remove_worktree(result.workspace)


if __name__ == "__main__":
    unittest.main()
