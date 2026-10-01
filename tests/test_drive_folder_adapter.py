import json
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from tools.harness.drive_folder_adapter import (
    ARCHIVE,
    ARTIFACT_SCHEMA,
    ERRORS,
    HOST_SCHEMA,
    HOST_STATE_FILE,
    INBOX,
    LEGACY_SCHEMA,
    LOGS,
    RESULTS,
    SNAPSHOT_SCHEMA,
    TASK_SCHEMA,
    enqueue_with_permit,
    issue_provider_permit,
    legacy_reconcile,
    load_task_manifest,
    reconcile_modern,
    scan_root,
)
from tools.harness.worker_dispatch import TaskLifecycle, validate_dispatch_permit

NOW = datetime(2026, 10, 1, 10, 30, tzinfo=timezone.utc)
REV = "a" * 40
CTX = "b" * 64
RECEIPT = "c" * 64


class DriveFolderAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "DeepThought_Away"
        for name in (INBOX, RESULTS, LOGS, ERRORS, ARCHIVE):
            (self.root / name).mkdir(parents=True, exist_ok=True)
        self.task_path = Path(self.temp.name) / "next.task.json"
        self.write_task(self.task_path)
        self.write_host()

    def tearDown(self):
        self.temp.cleanup()

    def write_json(self, path, value):
        path.write_text(
            json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )

    def write_task(self, path, *, attempt="a1"):
        self.write_json(
            path,
            {
                "schema": TASK_SCHEMA,
                "task_id": "review-cora",
                "attempt_id": attempt,
                "source_revision": REV,
                "context_fingerprint": CTX,
                "acceptance_criteria": ["return bounded review"],
                "observed_at": NOW.isoformat(),
            },
        )

    def write_host(self, *, session_id="host-1", safety=False, workers=None):
        self.write_json(
            self.root / LOGS / HOST_STATE_FILE,
            {
                "schema": HOST_SCHEMA,
                "observed_at": NOW.isoformat(),
                "session_id": session_id,
                "reachable": True,
                "safety_stop": safety,
                "worker_sessions": workers or [],
            },
        )

    def test_legacy_job_is_unknown_and_blocks_new_dispatch(self):
        name = "025_legacy_code_review.md"
        (self.root / INBOX / name).write_text("legacy job\n", encoding="utf-8")

        snapshot = scan_root(self.root)
        result = legacy_reconcile(snapshot, name)
        self.assertEqual(result["schema"], LEGACY_SCHEMA)
        self.assertEqual(result["state"], "unknown")
        self.assertFalse(result["can_retry"])
        self.assertFalse(result["can_dispatch_replacement"])
        self.assertTrue(result["requires_operator_reconciliation"])
        self.assertIn("legacy_task_present", result["reasons"])
        self.assertIn("structured_identity_missing", result["reasons"])
        self.assertIn("terminal_evidence_absent", result["reasons"])
        self.assertIn("blind_retry_forbidden", result["reasons"])

        task, _, _ = load_task_manifest(self.task_path)
        permit, reasons = issue_provider_permit(snapshot, task, now=NOW)
        self.assertIsNone(permit)
        self.assertIn("legacy_inbox_requires_reconciliation", reasons)

    def test_historic_legacy_results_do_not_poison_new_dispatch(self):
        (self.root / RESULTS / "2026-09-28_old_review.md").write_text(
            "historic result\n",
            encoding="utf-8",
        )
        (self.root / ARCHIVE / "old_job.md").write_text(
            "historic archive\n",
            encoding="utf-8",
        )
        snapshot = scan_root(self.root)
        self.assertEqual(snapshot.dispatch_blockers, ())
        task, _, _ = load_task_manifest(self.task_path)
        permit, reasons = issue_provider_permit(snapshot, task, now=NOW)
        self.assertIsNotNone(permit)
        self.assertEqual(reasons, ())

    def test_fresh_complete_surfaces_can_issue_and_atomically_enqueue(self):
        snapshot = scan_root(self.root)
        self.assertEqual(snapshot.dispatch_blockers, ())
        task, _, _ = load_task_manifest(self.task_path)

        permit, reasons = issue_provider_permit(snapshot, task, now=NOW)
        self.assertIsNotNone(permit)
        self.assertEqual(reasons, ())

        target = enqueue_with_permit(
            self.root,
            self.task_path,
            permit,
            now=NOW,
        )
        self.assertTrue(target.is_file())
        self.assertTrue(target.name.endswith(".task.json"))

        queued = scan_root(self.root)
        self.assertEqual(len(queued.tasks), 1)
        second, second_reasons = issue_provider_permit(queued, task, now=NOW)
        self.assertIsNone(second)
        self.assertIn("canonical_dispatch_not_permitted", second_reasons)

    def test_host_session_change_invalidates_permit_before_write(self):
        snapshot = scan_root(self.root)
        task, _, _ = load_task_manifest(self.task_path)
        permit, _ = issue_provider_permit(snapshot, task, now=NOW)
        self.assertIsNotNone(permit)

        self.write_host(session_id="host-2")
        changed = scan_root(self.root)
        self.assertFalse(
            validate_dispatch_permit(
                permit,
                task=task,
                now=NOW,
                observation=changed.observation,
                artifacts=changed.artifacts,
            )
        )
        with self.assertRaisesRegex(ValueError, "permit no longer matches"):
            enqueue_with_permit(
                self.root,
                self.task_path,
                permit,
                now=NOW,
            )
        self.assertEqual(list((self.root / INBOX).glob("*.task.json")), [])

    def test_safety_stop_invalidates_permit_before_write(self):
        snapshot = scan_root(self.root)
        task, _, _ = load_task_manifest(self.task_path)
        permit, _ = issue_provider_permit(snapshot, task, now=NOW)
        self.assertIsNotNone(permit)

        self.write_host(safety=True)
        with self.assertRaisesRegex(ValueError, "permit no longer matches"):
            enqueue_with_permit(
                self.root,
                self.task_path,
                permit,
                now=NOW,
            )

    def test_structured_result_with_receipt_reconciles_success(self):
        task, _, _ = load_task_manifest(self.task_path)
        self.write_json(
            self.root / RESULTS / "review-cora__a1.result.json",
            {
                "schema": ARTIFACT_SCHEMA,
                "kind": "result",
                "task_id": task.task_id,
                "attempt_id": task.attempt_id,
                "source_revision": task.source_revision,
                "context_fingerprint": task.context_fingerprint,
                "observed_at": NOW.isoformat(),
                "complete": True,
                "valid": True,
                "success": True,
                "receipt_fingerprint": RECEIPT,
            },
        )
        snapshot = scan_root(self.root)
        output = reconcile_modern(snapshot, task, now=NOW)
        self.assertEqual(output["schema"], SNAPSHOT_SCHEMA)
        self.assertEqual(output["state"]["lifecycle"], TaskLifecycle.SUCCEEDED.value)
        self.assertEqual(output["state"]["result_receipt"], RECEIPT)

    def test_result_without_receipt_is_invalid_provider_evidence(self):
        task, _, _ = load_task_manifest(self.task_path)
        self.write_json(
            self.root / RESULTS / "bad.result.json",
            {
                "schema": ARTIFACT_SCHEMA,
                "kind": "result",
                "task_id": task.task_id,
                "attempt_id": task.attempt_id,
                "source_revision": task.source_revision,
                "context_fingerprint": task.context_fingerprint,
                "observed_at": NOW.isoformat(),
                "success": True,
            },
        )
        snapshot = scan_root(self.root)
        self.assertIn("provider_evidence_invalid", snapshot.dispatch_blockers)
        self.assertTrue(any("receipt_fingerprint" in item for item in snapshot.errors))

    def test_missing_surface_fails_closed_for_dispatch(self):
        (self.root / ERRORS).rmdir()
        snapshot = scan_root(self.root)
        self.assertIn(ERRORS, snapshot.missing_surfaces)
        self.assertIn("provider_surface_missing", snapshot.dispatch_blockers)

        task, _, _ = load_task_manifest(self.task_path)
        permit, reasons = issue_provider_permit(snapshot, task, now=NOW)
        self.assertIsNone(permit)
        self.assertIn("provider_surface_missing", reasons)

    def test_frozen_legacy_scenario_matches_contract(self):
        path = (
            Path(__file__).resolve().parents[1]
            / "tests"
            / "frozen_scenarios"
            / "drive_legacy_attempt_unknown_v1.json"
        )
        data = json.loads(path.read_text(encoding="utf-8"))
        expected = data["expected"]
        self.assertEqual(expected["state"], "unknown")
        self.assertFalse(expected["can_retry"])
        self.assertFalse(expected["can_dispatch_replacement"])
        self.assertTrue(expected["requires_operator_reconciliation"])
        self.assertTrue(expected["must_not_infer_running_from_historic_start"])
        self.assertTrue(expected["must_not_infer_failure_from_missing_terminal"])
        self.assertTrue(expected["must_preserve_legacy_file"])

    def test_duplicate_json_keys_fail_closed(self):
        path = self.root / LOGS / HOST_STATE_FILE
        path.write_text(
            '{"schema":"loop42.drive-host-state.v1","schema":"bad"}',
            encoding="utf-8",
        )
        snapshot = scan_root(self.root)
        self.assertIn("provider_evidence_invalid", snapshot.dispatch_blockers)
        self.assertTrue(any("duplicate JSON key" in item for item in snapshot.errors))


if __name__ == "__main__":
    unittest.main()
