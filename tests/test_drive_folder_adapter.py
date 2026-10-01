import hashlib
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
    PROPOSAL_SCHEMA,
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

    def write_host(
        self,
        *,
        session_id="host-1",
        safety=False,
        workers=None,
        unidentified_worker_count=0,
    ):
        self.write_json(
            self.root / LOGS / HOST_STATE_FILE,
            {
                "schema": HOST_SCHEMA,
                "observed_at": NOW.isoformat(),
                "session_id": session_id,
                "reachable": True,
                "safety_stop": safety,
                "unidentified_worker_count": unidentified_worker_count,
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

    def test_unidentified_worker_process_blocks_dispatch(self):
        self.write_host(unidentified_worker_count=1)
        snapshot = scan_root(self.root)
        self.assertEqual(snapshot.unidentified_worker_count, 1)
        self.assertIn("unidentified_worker_session", snapshot.dispatch_blockers)

        task, _, _ = load_task_manifest(self.task_path)
        permit, reasons = issue_provider_permit(snapshot, task, now=NOW)
        self.assertIsNone(permit)
        self.assertIn("unidentified_worker_session", reasons)

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

    def test_unverified_proposal_blocks_dispatch_until_terminal_verification(self):
        task, _, _ = load_task_manifest(self.task_path)
        content_name = "review-cora__a1.proposal.md"
        content = b"unverified model proposal\n"
        (self.root / RESULTS / content_name).write_bytes(content)
        self.write_json(
            self.root / RESULTS / "review-cora__a1.proposal.json",
            {
                "schema": PROPOSAL_SCHEMA,
                "task_id": task.task_id,
                "attempt_id": task.attempt_id,
                "source_revision": task.source_revision,
                "context_fingerprint": task.context_fingerprint,
                "observed_at": NOW.isoformat(),
                "worker_session_id": "worker-1",
                "prompt_contract_sha256": "d" * 64,
                "model_id": "local-test",
                "content_file": content_name,
                "content_sha256": hashlib.sha256(content).hexdigest(),
            },
        )

        snapshot = scan_root(self.root)
        self.assertEqual(len(snapshot.proposals), 1)
        self.assertIn(
            "unverified_proposal_requires_verification",
            snapshot.dispatch_blockers,
        )
        self.assertNotIn((RESULTS, content_name), snapshot.legacy_files)

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
        verified = scan_root(self.root)
        self.assertNotIn(
            "unverified_proposal_requires_verification",
            verified.dispatch_blockers,
        )

    def test_proposal_content_hash_mismatch_fails_closed(self):
        task, _, _ = load_task_manifest(self.task_path)
        content_name = "review-cora__a1.proposal.md"
        (self.root / RESULTS / content_name).write_text(
            "actual content\n",
            encoding="utf-8",
        )
        self.write_json(
            self.root / RESULTS / "review-cora__a1.proposal.json",
            {
                "schema": PROPOSAL_SCHEMA,
                "task_id": task.task_id,
                "attempt_id": task.attempt_id,
                "source_revision": task.source_revision,
                "context_fingerprint": task.context_fingerprint,
                "observed_at": NOW.isoformat(),
                "worker_session_id": "worker-1",
                "prompt_contract_sha256": "d" * 64,
                "model_id": "local-test",
                "content_file": content_name,
                "content_sha256": "e" * 64,
            },
        )
        snapshot = scan_root(self.root)
        self.assertIn("provider_evidence_invalid", snapshot.dispatch_blockers)
        self.assertTrue(
            any("proposal content fingerprint mismatch" in item for item in snapshot.errors)
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

    def test_windows_worker_contract_has_no_execution_or_result_authority(self):
        module = (
            Path(__file__).resolve().parents[1]
            / "tools"
            / "harness"
            / "windows_worker_contract.psm1"
        ).read_text(encoding="utf-8")
        self.assertIn("loop42.windows-worker-session.v1", module)
        self.assertIn("loop42.drive-proposal.v1", module)
        self.assertIn("Write-Loop42ProposalManifest", module)
        self.assertIn("worker session already exists; reconcile it before starting another", module)
        self.assertIn("active worker session does not match proposal task identity", module)
        self.assertIn("worker session belongs to a different process", module)
        self.assertNotIn("WorkerSessionId", module)
        self.assertNotIn("loop42.drive-artifact.v1", module)
        self.assertNotIn("receipt_fingerprint", module)
        self.assertNotIn("Start-Process", module)
        self.assertNotIn("Invoke-RestMethod", module)
        self.assertNotIn("ollama", module.lower())

    def test_windows_host_writer_is_evidence_only(self):
        script = (
            Path(__file__).resolve().parents[1]
            / "tools"
            / "harness"
            / "windows_drive_host_state.ps1"
        ).read_text(encoding="utf-8")
        self.assertIn("loop42.drive-host-state.v1", script)
        self.assertIn("unidentified_worker_count", script)
        self.assertIn("[System.IO.File]::Replace", script)
        self.assertNotIn("Start-Process", script)
        self.assertNotIn("Invoke-RestMethod", script)
        self.assertNotIn("ollama", script.lower())

    def test_no_model_identity_roundtrip(self):
        scenario_path = (
            Path(__file__).resolve().parents[1]
            / "tests"
            / "frozen_scenarios"
            / "drive_identity_roundtrip_without_model_v1.json"
        )
        scenario = json.loads(scenario_path.read_text(encoding="utf-8"))
        expected = {item["step"]: item["expected"] for item in scenario["sequence"]}

        task, _, _ = load_task_manifest(self.task_path)
        initial = scan_root(self.root)
        permit, reasons = issue_provider_permit(initial, task, now=NOW)
        self.assertIsNotNone(permit)
        self.assertEqual(reasons, ())
        self.assertTrue(expected["fresh_idle_host"]["permit"])

        queued_path = enqueue_with_permit(self.root, self.task_path, permit, now=NOW)
        self.assertTrue(queued_path.exists())
        self.assertTrue(expected["atomic_queue_write"]["queued"])
        self.assertFalse(expected["atomic_queue_write"]["cloud_sync_confirmed"])

        self.write_host(
            workers=[{
                "session_id": "worker-1",
                "task_id": task.task_id,
                "attempt_id": task.attempt_id,
                "progress_seq": 1,
                "progress_at": NOW.isoformat(),
            }]
        )
        running = reconcile_modern(scan_root(self.root), task, now=NOW)
        self.assertEqual(
            running["state"]["lifecycle"],
            expected["identified_worker_session"]["lifecycle"],
        )
        self.assertEqual(
            running["state"]["can_dispatch"],
            expected["identified_worker_session"]["can_dispatch"],
        )

        proposal_content_name = "review-cora__a1.proposal.md"
        proposal_content = b"bounded unverified proposal\n"
        (self.root / RESULTS / proposal_content_name).write_bytes(proposal_content)
        self.write_json(
            self.root / RESULTS / "review-cora__a1.proposal.json",
            {
                "schema": PROPOSAL_SCHEMA,
                "task_id": task.task_id,
                "attempt_id": task.attempt_id,
                "source_revision": task.source_revision,
                "context_fingerprint": task.context_fingerprint,
                "observed_at": NOW.isoformat(),
                "worker_session_id": "worker-1",
                "prompt_contract_sha256": "d" * 64,
                "model_id": "local-test",
                "content_file": proposal_content_name,
                "content_sha256": hashlib.sha256(proposal_content).hexdigest(),
            },
        )
        proposal_snapshot = scan_root(self.root)
        self.assertIn(
            expected["identity_bound_unverified_proposal"]["dispatch_blocker"],
            proposal_snapshot.dispatch_blockers,
        )

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
        busy_success = reconcile_modern(scan_root(self.root), task, now=NOW)
        self.assertEqual(
            busy_success["state"]["lifecycle"],
            expected["receipt_bound_result_worker_still_busy"]["lifecycle"],
        )
        self.assertEqual(
            busy_success["state"]["can_dispatch"],
            expected["receipt_bound_result_worker_still_busy"]["can_dispatch"],
        )

        self.write_host()
        released = reconcile_modern(scan_root(self.root), task, now=NOW)
        self.assertEqual(
            released["state"]["lifecycle"],
            expected["worker_releases_attempt"]["lifecycle"],
        )
        self.assertEqual(
            released["state"]["can_dispatch"],
            expected["worker_releases_attempt"]["can_dispatch"],
        )

        next_path = Path(self.temp.name) / "next-a2.task.json"
        self.write_task(next_path, attempt="a2")
        next_task, _, _ = load_task_manifest(next_path)
        next_permit, next_reasons = issue_provider_permit(
            scan_root(self.root),
            next_task,
            now=NOW,
        )
        self.assertIsNotNone(next_permit)
        self.assertEqual(next_reasons, ())
        self.assertTrue(expected["next_attempt"]["permit"])

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
