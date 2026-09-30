from datetime import datetime, timedelta, timezone
import unittest

from tools.harness.worker_dispatch import (
    ArtifactKind,
    AttemptArtifact,
    DispatchPermit,
    DispatchTask,
    EvidenceFreshness,
    HostAvailability,
    HostObservation,
    NotificationKind,
    TaskLifecycle,
    WorkerHealth,
    WorkerSession,
    issue_dispatch_permit,
    notification_for,
    reconcile_worker,
    validate_dispatch_permit,
)

NOW = datetime(2026, 9, 29, 20, 0, tzinfo=timezone.utc)
REV = "a" * 40
CTX = "b" * 64
RECEIPT = "c" * 64


def task(attempt="a1", rev=REV, ctx=CTX):
    return DispatchTask(
        "review-cora",
        attempt,
        rev,
        ctx,
        ("return bounded review",),
    )


def artifact(
    kind,
    attempt="a1",
    *,
    rev=REV,
    ctx=CTX,
    minutes=0,
    complete=True,
    valid=True,
    receipt=None,
):
    terminal = kind in {ArtifactKind.RESULT, ArtifactKind.ERROR}
    return AttemptArtifact(
        kind=kind,
        task_id="review-cora",
        attempt_id=attempt,
        source_revision=rev,
        context_fingerprint=ctx,
        observed_at=NOW - timedelta(minutes=minutes),
        complete=complete,
        valid=valid,
        success=(kind is ArtifactKind.RESULT) if terminal else None,
        receipt_fingerprint=receipt,
    )


def host(*sessions, minutes=0, reachable=True, safety=False):
    return HostObservation(
        observed_at=NOW - timedelta(minutes=minutes),
        session_id="host-session",
        reachable=reachable,
        worker_sessions=tuple(sessions),
        safety_stop=safety,
    )


class WorkerDispatchTests(unittest.TestCase):
    def test_idle_fresh_host_separates_stopped_worker_from_failure(self):
        state = reconcile_worker(now=NOW, observation=host(), artifacts=[])
        self.assertEqual(state.host, HostAvailability.AVAILABLE)
        self.assertEqual(state.worker, WorkerHealth.STOPPED)
        self.assertEqual(state.lifecycle, TaskLifecycle.IDLE)
        self.assertTrue(state.can_dispatch)

    def test_queued_attempt_is_not_called_running_without_current_worker_evidence(self):
        state = reconcile_worker(
            now=NOW,
            observation=host(),
            artifacts=[artifact(ArtifactKind.QUEUED)],
            expected=task(),
        )
        self.assertEqual(state.lifecycle, TaskLifecycle.QUEUED)
        self.assertFalse(state.can_dispatch)

    def test_fresh_matching_worker_session_proves_running(self):
        session = WorkerSession(
            "worker-1",
            "review-cora",
            "a1",
            4,
            NOW - timedelta(seconds=10),
        )
        state = reconcile_worker(
            now=NOW,
            observation=host(session),
            artifacts=[artifact(ArtifactKind.STARTED)],
            expected=task(),
        )
        self.assertEqual(state.worker, WorkerHealth.HEALTHY)
        self.assertEqual(state.lifecycle, TaskLifecycle.RUNNING)

    def test_host_off_is_unreachable_not_failed_or_running(self):
        state = reconcile_worker(
            now=NOW,
            observation=host(reachable=False),
            artifacts=[artifact(ArtifactKind.STARTED)],
            expected=task(),
        )
        self.assertEqual(state.host, HostAvailability.UNREACHABLE)
        self.assertEqual(state.worker, WorkerHealth.UNKNOWN)
        self.assertEqual(state.lifecycle, TaskLifecycle.UNKNOWN)

    def test_sync_delay_stale_heartbeat_cannot_prove_running(self):
        session = WorkerSession(
            "worker-1",
            "review-cora",
            "a1",
            9,
            NOW - timedelta(minutes=20),
        )
        state = reconcile_worker(
            now=NOW,
            observation=host(session, minutes=20),
            artifacts=[artifact(ArtifactKind.PROGRESS, minutes=20)],
            expected=task(),
            freshness_seconds=300,
        )
        self.assertEqual(state.freshness, EvidenceFreshness.STALE)
        self.assertEqual(state.lifecycle, TaskLifecycle.UNKNOWN)
        self.assertNotEqual(state.worker, WorkerHealth.FAILED)

    def test_fresh_host_without_worker_is_stopped(self):
        state = reconcile_worker(
            now=NOW,
            observation=host(),
            artifacts=[artifact(ArtifactKind.STARTED)],
            expected=task(),
        )
        self.assertEqual(state.worker, WorkerHealth.STOPPED)
        self.assertEqual(state.lifecycle, TaskLifecycle.UNKNOWN)

    def test_stalled_requires_fresh_host_and_declared_progress_deadline(self):
        session = WorkerSession(
            "worker-1",
            "review-cora",
            "a1",
            2,
            NOW - timedelta(minutes=11),
        )
        no_rule = reconcile_worker(
            now=NOW,
            observation=host(session),
            artifacts=[],
            expected=task(),
        )
        with_rule = reconcile_worker(
            now=NOW,
            observation=host(session),
            artifacts=[],
            expected=task(),
            stall_seconds=600,
        )
        self.assertEqual(no_rule.lifecycle, TaskLifecycle.RUNNING)
        self.assertEqual(with_rule.worker, WorkerHealth.STALLED)
        self.assertEqual(with_rule.lifecycle, TaskLifecycle.UNKNOWN)

    def test_explicit_valid_error_is_failure_not_silence(self):
        state = reconcile_worker(
            now=NOW,
            observation=host(WorkerSession("worker-1")),
            artifacts=[artifact(ArtifactKind.ERROR)],
            expected=task(),
        )
        self.assertEqual(state.lifecycle, TaskLifecycle.FAILED)
        self.assertEqual(state.worker, WorkerHealth.FAILED)
        self.assertFalse(state.can_dispatch)

    def test_matching_complete_result_requires_exact_identity_and_surfaces_receipt(self):
        state = reconcile_worker(
            now=NOW,
            observation=host(),
            artifacts=[artifact(ArtifactKind.RESULT, receipt=RECEIPT)],
            expected=task(),
        )
        self.assertEqual(state.lifecycle, TaskLifecycle.SUCCEEDED)
        self.assertEqual(state.result_receipt, RECEIPT)
        self.assertTrue(state.can_dispatch)

    def test_late_success_from_prior_attempt_blocks_blind_retry(self):
        state = reconcile_worker(
            now=NOW,
            observation=host(),
            artifacts=[
                artifact(
                    ArtifactKind.RESULT,
                    attempt="a0",
                    receipt=RECEIPT,
                )
            ],
            expected=task("a1"),
        )
        self.assertEqual(state.late_results, (("review-cora", "a0"),))
        self.assertFalse(state.can_dispatch)
        self.assertIn("late_result_requires_reconciliation", state.reasons)

    def test_duplicate_workers_are_conflict(self):
        first = WorkerSession("worker-1", "review-cora", "a1")
        second = WorkerSession("worker-2", "review-cora", "a1")
        state = reconcile_worker(
            now=NOW,
            observation=host(first, second),
            artifacts=[],
            expected=task(),
        )
        self.assertEqual(state.worker, WorkerHealth.CONFLICT)
        self.assertEqual(state.lifecycle, TaskLifecycle.CONFLICT)
        self.assertFalse(state.can_dispatch)

    def test_same_attempt_with_stale_revision_is_conflict(self):
        stale = artifact(
            ArtifactKind.RESULT,
            rev="d" * 40,
            receipt=RECEIPT,
        )
        state = reconcile_worker(
            now=NOW,
            observation=host(),
            artifacts=[stale],
            expected=task(),
        )
        self.assertEqual(state.lifecycle, TaskLifecycle.CONFLICT)
        self.assertIn("attempt_identity_mismatch", state.reasons)

    def test_partial_result_never_completes_attempt(self):
        partial = artifact(
            ArtifactKind.RESULT,
            complete=False,
            receipt=RECEIPT,
        )
        state = reconcile_worker(
            now=NOW,
            observation=host(),
            artifacts=[partial],
            expected=task(),
        )
        self.assertEqual(state.lifecycle, TaskLifecycle.UNKNOWN)
        self.assertFalse(state.can_dispatch)
        self.assertIn("partial_or_invalid_terminal_artifact", state.reasons)

    def test_safety_stop_is_latched_dispatch_block(self):
        state = reconcile_worker(
            now=NOW,
            observation=host(safety=True),
            artifacts=[],
            expected=task(),
        )
        self.assertEqual(state.lifecycle, TaskLifecycle.BLOCKED)
        self.assertFalse(state.can_dispatch)
        self.assertIn("safety_stop_latched", state.reasons)

    def test_future_timestamp_is_clock_skew_not_freshness(self):
        observation = HostObservation(
            observed_at=NOW + timedelta(minutes=1),
            session_id="future-host",
            reachable=True,
            worker_sessions=(
                WorkerSession("worker-1", "review-cora", "a1"),
            ),
        )
        state = reconcile_worker(
            now=NOW,
            observation=observation,
            artifacts=[],
            expected=task(),
        )
        self.assertEqual(state.freshness, EvidenceFreshness.UNKNOWN)
        self.assertEqual(state.host, HostAvailability.UNKNOWN)
        self.assertEqual(state.lifecycle, TaskLifecycle.UNKNOWN)
        self.assertIn("host_clock_skew", state.reasons)

    def test_conflicting_terminal_artifacts_fail_closed(self):
        success = artifact(ArtifactKind.RESULT, receipt=RECEIPT)
        failure = artifact(ArtifactKind.ERROR)
        state = reconcile_worker(
            now=NOW,
            observation=host(),
            artifacts=[success, failure],
            expected=task(),
        )
        self.assertEqual(state.lifecycle, TaskLifecycle.CONFLICT)
        self.assertFalse(state.can_dispatch)

    def test_offline_period_does_not_create_notification_noise(self):
        first = reconcile_worker(
            now=NOW,
            observation=host(reachable=False),
            artifacts=[],
            expected=task(),
        )
        second = reconcile_worker(
            now=NOW + timedelta(minutes=1),
            observation=host(reachable=False),
            artifacts=[],
            expected=task(),
        )
        self.assertIsNone(notification_for(None, first))
        self.assertIsNone(notification_for(first, second))

    def test_new_result_notifies_once(self):
        before = reconcile_worker(
            now=NOW,
            observation=host(),
            artifacts=[artifact(ArtifactKind.QUEUED)],
            expected=task(),
        )
        after = reconcile_worker(
            now=NOW,
            observation=host(),
            artifacts=[artifact(ArtifactKind.RESULT, receipt=RECEIPT)],
            expected=task(),
        )
        self.assertEqual(notification_for(before, after), NotificationKind.RESULT)
        self.assertIsNone(notification_for(after, after))

    def test_new_conflict_requests_decision_once(self):
        before = reconcile_worker(
            now=NOW,
            observation=host(),
            artifacts=[],
            expected=task(),
        )
        conflict = reconcile_worker(
            now=NOW,
            observation=host(
                WorkerSession("worker-1", "review-cora", "a1"),
                WorkerSession("worker-2", "review-cora", "a1"),
            ),
            artifacts=[],
            expected=task(),
        )
        self.assertEqual(
            notification_for(before, conflict),
            NotificationKind.DECISION_REQUIRED,
        )
        self.assertIsNone(notification_for(conflict, conflict))

    def test_dispatch_permit_requires_fresh_available_host(self):
        self.assertIsNone(
            issue_dispatch_permit(
                task=task(),
                now=NOW,
                observation=None,
                artifacts=[],
            )
        )
        self.assertIsNone(
            issue_dispatch_permit(
                task=task(),
                now=NOW,
                observation=host(minutes=20),
                artifacts=[],
                freshness_seconds=300,
            )
        )
        permit = issue_dispatch_permit(
            task=task(),
            now=NOW,
            observation=host(),
            artifacts=[],
        )
        self.assertIsInstance(permit, DispatchPermit)

    def test_dispatch_permit_revalidates_same_basis_immediately_before_write(self):
        observation = host()
        permit = issue_dispatch_permit(
            task=task(),
            now=NOW,
            observation=observation,
            artifacts=[],
        )
        self.assertIsNotNone(permit)
        self.assertTrue(
            validate_dispatch_permit(
                permit,
                task=task(),
                now=NOW + timedelta(seconds=30),
                observation=observation,
                artifacts=[],
            )
        )

    def test_dispatch_permit_fails_when_queue_changes_during_pause(self):
        observation = host()
        permit = issue_dispatch_permit(
            task=task(),
            now=NOW,
            observation=observation,
            artifacts=[],
        )
        self.assertIsNotNone(permit)
        other = AttemptArtifact(
            kind=ArtifactKind.QUEUED,
            task_id="another-task",
            attempt_id="a9",
            source_revision=REV,
            context_fingerprint=CTX,
            observed_at=NOW + timedelta(seconds=1),
        )
        self.assertFalse(
            validate_dispatch_permit(
                permit,
                task=task(),
                now=NOW + timedelta(seconds=2),
                observation=observation,
                artifacts=[other],
            )
        )

    def test_dispatch_permit_fails_when_safety_or_host_session_changes(self):
        observation = host()
        permit = issue_dispatch_permit(
            task=task(),
            now=NOW,
            observation=observation,
            artifacts=[],
        )
        self.assertIsNotNone(permit)
        safety = HostObservation(
            observed_at=NOW + timedelta(seconds=1),
            session_id=observation.session_id,
            reachable=True,
            safety_stop=True,
        )
        self.assertFalse(
            validate_dispatch_permit(
                permit,
                task=task(),
                now=NOW + timedelta(seconds=2),
                observation=safety,
                artifacts=[],
            )
        )
        restarted = HostObservation(
            observed_at=NOW + timedelta(seconds=1),
            session_id="host-restarted",
            reachable=True,
        )
        self.assertFalse(
            validate_dispatch_permit(
                permit,
                task=task(),
                now=NOW + timedelta(seconds=2),
                observation=restarted,
                artifacts=[],
            )
        )

    def test_dispatch_permit_expires_when_observation_becomes_stale(self):
        observation = host()
        permit = issue_dispatch_permit(
            task=task(),
            now=NOW,
            observation=observation,
            artifacts=[],
            freshness_seconds=300,
        )
        self.assertIsNotNone(permit)
        self.assertFalse(
            validate_dispatch_permit(
                permit,
                task=task(),
                now=NOW + timedelta(seconds=301),
                observation=observation,
                artifacts=[],
                freshness_seconds=300,
            )
        )

    def test_dispatch_permit_rejects_attempt_reuse_and_changed_task_basis(self):
        observation = host()
        original = task()
        permit = issue_dispatch_permit(
            task=original,
            now=NOW,
            observation=observation,
            artifacts=[],
        )
        self.assertIsNotNone(permit)
        self.assertIsNone(
            issue_dispatch_permit(
                task=original,
                now=NOW,
                observation=observation,
                artifacts=[artifact(ArtifactKind.RESULT, receipt=RECEIPT)],
            )
        )
        changed = DispatchTask(
            original.task_id,
            original.attempt_id,
            original.source_revision,
            original.context_fingerprint,
            ("different acceptance criterion",),
        )
        self.assertFalse(
            validate_dispatch_permit(
                permit,
                task=changed,
                now=NOW,
                observation=observation,
                artifacts=[],
            )
        )


if __name__ == "__main__":
    unittest.main()
