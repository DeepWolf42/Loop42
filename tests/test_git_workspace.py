from pathlib import Path
import subprocess
import tempfile
import unittest

from tools.harness.git_workspace import (
    create_detached_worktree,
    remove_worktree,
    validate_worktree_lease,
)


def git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=cwd, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, check=True,
    )
    return result.stdout.strip()


class GitWorkspaceTests(unittest.TestCase):
    def make_repo(self, base: Path) -> tuple[Path, str]:
        repo = base / "repo"
        repo.mkdir()
        git(repo, "init", "-q")
        (repo / "file.txt").write_text("base\n", encoding="utf-8")
        git(repo, "add", "file.txt")
        git(repo, "-c", "user.name=Loop42 Test", "-c", "user.email=loop42@example.invalid", "commit", "-q", "-m", "base")
        return repo, git(repo, "rev-parse", "HEAD")

    def test_create_is_detached_exact_and_isolated(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            repo, head = self.make_repo(base)
            parent = base / "leases"
            parent.mkdir()
            lease = create_detached_worktree(repo, head, parent=parent)
            self.assertTrue(lease.root.name.startswith(".loop42-worktree-"))
            self.assertEqual(lease.source_revision, head)
            self.assertEqual(git(lease.root, "rev-parse", "HEAD"), head)
            self.assertEqual(git(lease.root, "branch", "--show-current"), "")
            (lease.root / "file.txt").write_text("changed\n", encoding="utf-8")
            self.assertEqual((repo / "file.txt").read_text(encoding="utf-8"), "base\n")
            validate_worktree_lease(lease)
            remove_worktree(lease)
            self.assertFalse(lease.root.exists())

    def test_short_exact_revision_resolves_to_full_commit(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            repo, head = self.make_repo(base)
            parent = base / "leases"
            parent.mkdir()
            lease = create_detached_worktree(repo, head[:12], parent=parent)
            self.assertEqual(lease.source_revision, head)
            remove_worktree(lease)

    def test_non_commit_or_non_hex_revision_is_refused(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            repo, _head = self.make_repo(base)
            parent = base / "leases"
            parent.mkdir()
            with self.assertRaises(ValueError):
                create_detached_worktree(repo, "main", parent=parent)
            with self.assertRaises(ValueError):
                create_detached_worktree(repo, "0" * 40, parent=parent)

    def test_repo_root_must_be_top_level_and_parent_preexists(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            repo, head = self.make_repo(base)
            nested = repo / "nested"
            nested.mkdir()
            parent = base / "leases"
            parent.mkdir()
            with self.assertRaisesRegex(ValueError, "top-level"):
                create_detached_worktree(nested, head, parent=parent)
            with self.assertRaises(ValueError):
                create_detached_worktree(repo, head, parent=base / "missing")

    def test_worktree_parent_inside_repo_is_refused(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            repo, head = self.make_repo(base)
            parent = repo / ".leases"
            parent.mkdir()
            with self.assertRaisesRegex(ValueError, "outside repo_root"):
                create_detached_worktree(repo, head, parent=parent)

    def test_changed_head_invalidates_lease(self):
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            repo, head = self.make_repo(base)
            (repo / "next.txt").write_text("next\n", encoding="utf-8")
            git(repo, "add", "next.txt")
            git(repo, "-c", "user.name=Loop42 Test", "-c", "user.email=loop42@example.invalid", "commit", "-q", "-m", "next")
            second = git(repo, "rev-parse", "HEAD")
            parent = base / "leases"
            parent.mkdir()
            lease = create_detached_worktree(repo, head, parent=parent)
            git(lease.root, "checkout", "-q", "--detach", second)
            with self.assertRaisesRegex(ValueError, "HEAD changed"):
                validate_worktree_lease(lease)
            # clean up directly via Git because the deliberately-invalid lease must fail closed
            git(repo, "worktree", "remove", "--force", str(lease.root))


if __name__ == "__main__":
    unittest.main()
