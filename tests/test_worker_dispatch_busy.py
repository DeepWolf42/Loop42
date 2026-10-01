"""A visible busy session must block dispatch even before queue sync arrives."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
import unittest

from tools.harness.worker_dispatch import (
    ArtifactKind, AttemptArtifact, DispatchTask, HostObservation, TaskLifecycle,
    WorkerSession, issue_dispatch_permit, reconcile_worker, validate_dispatch_permit,
)

NOW = datetime(2026, 9, 30, 19, 0, tzinfo=timezone.utc)
TASK = DispatchTask("next-review", "attempt-2", "a" * 40, "b" * 64, ("bounded review",))


def observation(session):
    return HostObservation(NOW, "host-1", True, (session,))


class BusyWorkerDispatchTests(unittest.TestCase):
    def test_busy_session_blocks_permit_without_queue_artifacts(self):
        for task_id, attempt_id, progress_at in (
            ("existing-review", "attempt-1", NOW),
            (TASK.task_id, TASK.attempt_id, NOW),
            ("existing-review", "attempt-1", NOW - timedelta(minutes=20)),
        ):
            with self.subTest(task_id=task_id, progress_at=progress_at):
                host = observation(WorkerSession("worker-1", task_id, attempt_id, 1, progress_at))
                self.assertIsNone(issue_dispatch_permit(
                    task=TASK, now=NOW, observation=host, artifacts=[], stall_seconds=600,
                ))

    def test_busy_session_blocks_reconcile_without_expected_task(self):
        host = observation(WorkerSession("worker-1", "existing-review", "attempt-1"))
        state = reconcile_worker(now=NOW, observation=host, artifacts=[])
        self.assertFalse(state.can_dispatch)

    def test_result_does_not_free_a_still_busy_worker(self):
        result = AttemptArtifact(
            ArtifactKind.RESULT, TASK.task_id, TASK.attempt_id,
            TASK.source_revision, TASK.context_fingerprint, NOW,
            success=True, receipt_fingerprint="c" * 64,
        )
        host = observation(WorkerSession("worker-1", TASK.task_id, TASK.attempt_id))
        state = reconcile_worker(now=NOW, observation=host, artifacts=[result], expected=TASK)
        self.assertEqual(state.lifecycle, TaskLifecycle.SUCCEEDED)
        self.assertFalse(state.can_dispatch)

    def test_idle_worker_permit_is_invalid_after_worker_becomes_busy(self):
        idle = observation(WorkerSession("worker-1"))
        permit = issue_dispatch_permit(task=TASK, now=NOW, observation=idle, artifacts=[])
        self.assertIsNotNone(permit)
        self.assertTrue(validate_dispatch_permit(
            permit, task=TASK, now=NOW, observation=idle, artifacts=[],
        ))
        busy = observation(WorkerSession("worker-1", "existing-review", "attempt-1"))
        self.assertFalse(validate_dispatch_permit(
            permit, task=TASK, now=NOW, observation=busy, artifacts=[],
        ))
        self.assertIsNone(issue_dispatch_permit(
            task=TASK, now=NOW, observation=busy, artifacts=[],
        ))

    def test_cli_does_not_issue_permit_for_busy_worker_without_queue_artifacts(self):
        request = {
            "schema": "loop42.worker-dispatch-cli.v1", "operation": "issue-permit",
            "now": NOW.isoformat(), "artifacts": [],
            "observation": {
                "observed_at": NOW.isoformat(), "session_id": "host-1", "reachable": True,
                "worker_sessions": [{"session_id": "worker-1", "task_id": "existing-review", "attempt_id": "attempt-1"}],
            },
            "task": {
                "task_id": TASK.task_id, "attempt_id": TASK.attempt_id,
                "source_revision": TASK.source_revision, "context_fingerprint": TASK.context_fingerprint,
                "acceptance_criteria": list(TASK.acceptance_criteria),
            },
        }
        result = subprocess.run(
            [sys.executable, "-m", "tools.harness.worker_dispatch_cli"],
            input=json.dumps(request), text=True, capture_output=True,
            cwd=Path(__file__).resolve().parents[1], timeout=10, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIsNone(json.loads(result.stdout)["permit"])
