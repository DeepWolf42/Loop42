import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from tools.harness.action_policy import ActionEffect, PolicyDecision, PolicyRule
from tools.harness.change_set import ChangeSet, CreateChange, DeleteChange, ModifyChange, normalize_changeset, sha256_text
from tools.harness.changeset_executor import apply_changeset, issue_changeset_permit, validate_changeset_permit


ALLOW = (
    PolicyRule(
        "allow-managed-repo-writes",
        PolicyDecision.ALLOW,
        priority=100,
        target_prefix="repo:",
        effect=ActionEffect.REVERSIBLE_WRITE,
    ),
)


class ChangeSetExecutorTests(unittest.TestCase):
    def normalized(self, root: Path):
        old = "old\n"
        mod = "a = 1\n"
        (root / "old.txt").write_text(old, encoding="utf-8")
        (root / "mod.py").write_text(mod, encoding="utf-8")
        proposal = ChangeSet((
            ModifyChange("mod.py", sha256_text(mod), "a = 1", "a = 2"),
            CreateChange("new.txt", "new\n"),
            DeleteChange("old.txt", sha256_text(old)),
        ))
        return normalize_changeset(proposal, {"mod.py": mod, "old.txt": old})

    def test_headless_write_is_denied_without_explicit_policy(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            changes = self.normalized(root)
            with self.assertRaises(PermissionError):
                issue_changeset_permit(root, changes, interactive=False)

    def test_permit_then_apply_modify_create_delete(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            changes = self.normalized(root)
            permit = issue_changeset_permit(root, changes, interactive=False, rules=ALLOW)
            receipt = apply_changeset(root, changes, permit, interactive=False, rules=ALLOW)
            self.assertEqual((root / "mod.py").read_text(), "a = 2\n")
            self.assertEqual((root / "new.txt").read_text(), "new\n")
            self.assertFalse((root / "old.txt").exists())
            self.assertEqual(receipt.changeset_fingerprint, changes.fingerprint)
            self.assertEqual(len(receipt.files), 3)
            self.assertFalse(list(root.glob(".loop42-*")))

    def test_basis_change_after_permit_blocks_write(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            changes = self.normalized(root)
            permit = issue_changeset_permit(root, changes, interactive=False, rules=ALLOW)
            (root / "mod.py").write_text("someone else changed it\n")
            with self.assertRaises(ValueError):
                validate_changeset_permit(root, changes, permit, interactive=False, rules=ALLOW)
            self.assertFalse((root / "new.txt").exists())

    def test_symlink_target_is_refused(self):
        if not hasattr(os, "symlink"):
            self.skipTest("symlink unavailable")
        with tempfile.TemporaryDirectory() as raw, tempfile.TemporaryDirectory() as outside_raw:
            root = Path(raw)
            outside = Path(outside_raw) / "outside.txt"
            outside.write_text("x", encoding="utf-8")
            try:
                os.symlink(outside, root / "link.txt")
            except OSError:
                self.skipTest("symlink creation unavailable")
            proposal = ChangeSet((ModifyChange("link.txt", sha256_text("x"), "x", "y"),))
            changes = normalize_changeset(proposal, {"link.txt": "x"})
            with self.assertRaisesRegex(ValueError, "symlink"):
                issue_changeset_permit(root, changes, interactive=False, rules=ALLOW)
            self.assertEqual(outside.read_text(), "x")

    def test_normal_exception_rolls_back_already_applied_files(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            changes = self.normalized(root)
            permit = issue_changeset_permit(root, changes, interactive=False, rules=ALLOW)
            real_replace = os.replace
            calls = {"n": 0}

            def flaky(src, dst):
                calls["n"] += 1
                # staged writes happen via replace during apply. Fail after at least one target changed.
                if calls["n"] == 3:
                    raise OSError("injected failure")
                return real_replace(src, dst)

            with mock.patch("tools.harness.changeset_executor.os.replace", side_effect=flaky):
                with self.assertRaisesRegex(OSError, "injected failure"):
                    apply_changeset(root, changes, permit, interactive=False, rules=ALLOW)
            self.assertEqual((root / "mod.py").read_text(), "a = 1\n")
            self.assertEqual((root / "old.txt").read_text(), "old\n")
            self.assertFalse((root / "new.txt").exists())


if __name__ == "__main__":
    unittest.main()
