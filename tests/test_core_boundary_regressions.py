from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import sys
import time

from tools.harness.action_policy import ActionEffect, PolicyDecision, PolicyRule
from tools.harness.change_set import ChangeSet, CreateChange, ModifyChange, normalize_changeset, sha256_text
from tools.harness.changeset_executor import apply_changeset, issue_changeset_permit
from tools.harness.worker_provider import WorkerResult, WorkerStatus
from tools.harness.verification_registry import VerificationRegistry, VerificationSpec, run_verifications

ALLOW = (PolicyRule('managed', PolicyDecision.ALLOW, priority=100,
                    target_prefix='repo:', effect=ActionEffect.REVERSIBLE_WRITE),)


class CoreBoundaryRegressions(unittest.TestCase):
    @unittest.skipUnless(sys.platform == 'win32', 'Windows short-path alias')
    def test_short_path_alias_cannot_modify_git_metadata(self):
        import ctypes
        from ctypes import wintypes
        short_path = ctypes.WinDLL('kernel32', use_last_error=True).GetShortPathNameW
        short_path.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
        short_path.restype = wintypes.DWORD
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            metadata = root / '.git'
            metadata.mkdir()
            config = metadata / 'config'
            config.write_bytes(b'old')
            buffer = ctypes.create_unicode_buffer(32768)
            length = short_path(str(metadata), buffer, len(buffer))
            self.assertGreater(length, 0)
            self.assertLess(length, len(buffer))
            alias = Path(buffer.value).name
            if alias.casefold() == '.git':
                self.skipTest('8.3 name generation disabled on this volume')
            relative = alias + '/config'
            changes = normalize_changeset(ChangeSet((
                ModifyChange(relative, sha256_text('old'), 'old', 'new'),
            )), {relative: 'old'})
            with self.assertRaisesRegex(ValueError, 'Git metadata'):
                permit = issue_changeset_permit(root, changes, interactive=False, rules=ALLOW)
                apply_changeset(root, changes, permit, interactive=False, rules=ALLOW)
            self.assertEqual(config.read_bytes(), b'old')

    def test_successful_parent_does_not_leave_verification_descendants(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            child = "import time; from pathlib import Path; time.sleep(0.5); Path('late-write').touch()"
            parent = f"import subprocess,sys; subprocess.Popen([sys.executable, '-c', {child!r}])"
            registry = VerificationRegistry((VerificationSpec('parent', (sys.executable, '-c', parent)),))
            result = run_verifications(root, ('parent',), registry)[0]
            self.assertTrue(result.passed)
            time.sleep(0.7)
            self.assertFalse((root / 'late-write').exists())

    def test_junction_component_is_refused_before_a_write(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / 'linked').mkdir()
            changes = normalize_changeset(ChangeSet((CreateChange('linked/new.txt', 'x'),)), {})
            with mock.patch.object(Path, 'is_junction', lambda path: path.name == 'linked'):
                with self.assertRaisesRegex(ValueError, 'junction'):
                    issue_changeset_permit(root, changes, interactive=False, rules=ALLOW)
            self.assertFalse((root / 'linked' / 'new.txt').exists())

    def test_timeout_quiesces_descendant_verification_processes(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            child = "import time; from pathlib import Path; time.sleep(1.5); Path('late-write').touch()"
            parent = f"import subprocess,sys,time; subprocess.Popen([sys.executable, '-c', {child!r}]); time.sleep(10)"
            registry = VerificationRegistry((VerificationSpec('timeout', (sys.executable, '-c', parent), timeout_seconds=1),))
            result = run_verifications(root, ('timeout',), registry)[0]
            self.assertTrue(result.timed_out)
            time.sleep(1)
            self.assertFalse((root / 'late-write').exists())

    def test_backup_cleanup_failure_does_not_destroy_committed_files(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            for name in ('a.txt', 'b.txt'):
                (root / name).write_bytes(b'old')
            changes = normalize_changeset(ChangeSet(tuple(
                ModifyChange(name, sha256_text('old'), 'old', 'new')
                for name in ('a.txt', 'b.txt'))), {'a.txt': 'old', 'b.txt': 'old'})
            permit = issue_changeset_permit(root, changes, interactive=False, rules=ALLOW)
            unlink = Path.unlink
            cleaned = []
            def fail_second_backup(path, *args, **kwargs):
                if path.name.startswith('.loop42-backup-') and path.exists() and path.stat().st_size:
                    cleaned.append(path)
                    if len(cleaned) == 2:
                        raise PermissionError('cleanup refused')
                return unlink(path, *args, **kwargs)
            with mock.patch.object(Path, 'unlink', fail_second_backup):
                with self.assertRaisesRegex(PermissionError, 'cleanup refused'):
                    apply_changeset(root, changes, permit, interactive=False, rules=ALLOW)
            self.assertEqual((root / 'a.txt').read_bytes(), b'new')
            self.assertEqual((root / 'b.txt').read_bytes(), b'new')

    def test_output_limit_stops_producer_before_following_side_effect(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            registry = VerificationRegistry((VerificationSpec('verbose', (sys.executable, '-c',
                "import os; from pathlib import Path; os.write(1, b'x' * 1048576); Path('continued').touch()")),))
            result = run_verifications(root, ('verbose',), registry, output_limit=16)[0]
            self.assertFalse(result.passed)
            self.assertTrue(result.output_truncated)
            self.assertLessEqual(len(result.output), 16)
            self.assertFalse((root / 'continued').exists())





    def test_permit_cannot_be_replayed_in_another_workspace(self):
        changes = normalize_changeset(ChangeSet((CreateChange('new.txt', 'x'),)), {})
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            permit = issue_changeset_permit(Path(first), changes, interactive=False, rules=ALLOW)
            with self.assertRaises(ValueError):
                apply_changeset(Path(second), changes, permit, interactive=False, rules=ALLOW)
            self.assertFalse((Path(second) / 'new.txt').exists())

    def test_normalized_payload_cannot_reuse_a_fingerprint_after_tampering(self):
        original = normalize_changeset(ChangeSet((CreateChange('new.txt', 'safe'),)), {})
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            permit = issue_changeset_permit(root, original, interactive=False, rules=ALLOW)
            forged_file = replace(original.files[0], after_text='tampered', after_sha256=sha256_text('tampered'))
            forged = replace(original, files=(forged_file,))
            with self.assertRaises(ValueError):
                apply_changeset(root, forged, permit, interactive=False, rules=ALLOW)
            self.assertFalse((root / 'new.txt').exists())

    def test_valid_proposal_is_still_only_a_proposal_and_executor_can_apply_it(self):
        proposal = ChangeSet((CreateChange('valid.txt', 'safe\n'),))
        changes = normalize_changeset(proposal, {})
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            permit = issue_changeset_permit(root, changes, interactive=False, rules=ALLOW)
            result = apply_changeset(root, changes, permit, interactive=False, rules=ALLOW)
            self.assertEqual((root / 'valid.txt').read_bytes(), b'safe\n')
            self.assertEqual(result.changeset_fingerprint, changes.fingerprint)
