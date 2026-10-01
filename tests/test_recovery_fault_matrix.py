import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest

from tools.harness.side_effect_reconcile import (
    SideEffectIntent,
    SideEffectObservation,
    reconcile_side_effect,
)
from tools.harness.worker_dispatch import (
    ArtifactKind,
    AttemptArtifact,
    DispatchTask,
    HostObservation,
    WorkerSession,
    issue_dispatch_permit,
    reconcile_worker,
    validate_dispatch_permit,
)

ROOT = Path(__file__).resolve().parents[1]
SCENARIO = ROOT / "tests" / "frozen_scenarios" / "recovery_fault_matrix_v1.json"
NOW = datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc)
REV = "a" * 40
CTX = "b" * 64
RECEIPT = "c" * 64


def expected():
    data = json.loads(SCENARIO.read_text(encoding="utf-8"))
    return {item["name"]: item["expected"] for item in data["cases"]}


def task(attempt="a1"):
    return DispatchTask(
        "review-cora",
        attempt,
        REV,
        CTX,
        ("return bounded review",),
    )


def host(*sessions, reachable=True, safety_stop=False):
    return HostObservation(
        observed_at=NOW,
        session_id="host-1",
        reachable=reachable,
        worker_sessions=tuple(sessions),
        safety_stop=safety_stop,
    )


def artifact(kind, attempt="a1", *, complete=True):
    return AttemptArtifact(
        kind=kind,
        task_id="review-cora",
        attempt_id=attempt,
        source_revision=REV,
        context_fingerprint=CTX,
        observed_at=NOW,
        complete=complete,
        valid=True,
        success=True if kind is ArtifactKind.RESULT else None,
        receipt_fingerprint=RECEIPT if kind is ArtifactKind.RESULT else None,
    )


class RecoveryFaultMatrixTests(unittest.TestCase):
    def test_side_effect_interruption_cases(self):
        matrix = expected()
        intent = SideEffectIntent(
            action_id="write-1",
            action="write",
            target="consumer:queue:item",
            state_scope="consumer.queue.item.v1",
            before_fingerprint="d" * 64,
            desired_fingerprint="e" * 64,
        )

        applied = reconcile_side_effect(
            intent,
            now=NOW,
            observation=SideEffectObservation(
                observed_at=NOW,
                target=intent.target,
                state_scope=intent.state_scope,
                state_fingerprint=intent.desired_fingerprint,
            ),
        )
        exp = matrix["lost_response_after_side_effect_applied"]
        self.assertEqual(applied.state.value, exp["side_effect_state"])
        self.assertEqual(applied.may_reconsider, exp["may_reconsider"])

        stale = reconcile_side_effect(
            intent,
            now=NOW,
            observation=SideEffectObservation(
                observed_at=NOW - timedelta(minutes=10),
                target=intent.target,
                state_scope=intent.state_scope,
                state_fingerprint=intent.before_fingerprint,
            ),
            freshness_seconds=300,
        )
        exp = matrix["stale_side_effect_observation"]
        self.assertEqual(stale.state.value, exp["side_effect_state"])
        self.assertEqual(stale.may_reconsider, exp["may_reconsider"])

    def test_partial_and_late_result_cases(self):
        matrix = expected()

        partial = reconcile_worker(
            now=NOW,
            observation=host(),
            artifacts=[artifact(ArtifactKind.RESULT, complete=False)],
            expected=task(),
        )
        exp = matrix["partial_terminal_result"]
        self.assertEqual(partial.lifecycle.value, exp["task_lifecycle"])
        self.assertEqual(partial.can_dispatch, exp["can_dispatch"])

        late = reconcile_worker(
            now=NOW,
            observation=host(),
            artifacts=[artifact(ArtifactKind.RESULT, attempt="a0")],
            expected=task("a1"),
        )
        exp = matrix["late_result_from_prior_attempt"]
        self.assertEqual(late.can_dispatch, exp["can_dispatch"])
        self.assertIn(exp["reason"], late.reasons)

    def test_duplicate_worker_and_offline_history_cases(self):
        matrix = expected()

        duplicate = reconcile_worker(
            now=NOW,
            observation=host(
                WorkerSession("worker-1", "review-cora", "a1"),
                WorkerSession("worker-2", "review-cora", "a1"),
            ),
            artifacts=[],
            expected=task(),
        )
        exp = matrix["duplicate_worker_sessions"]
        self.assertEqual(duplicate.lifecycle.value, exp["task_lifecycle"])
        self.assertEqual(duplicate.can_dispatch, exp["can_dispatch"])

        offline = reconcile_worker(
            now=NOW,
            observation=host(reachable=False),
            artifacts=[artifact(ArtifactKind.STARTED)],
            expected=task(),
        )
        exp = matrix["host_off_after_historic_start"]
        self.assertEqual(offline.host.value, exp["host"])
        self.assertEqual(offline.worker.value, exp["worker"])
        self.assertEqual(offline.lifecycle.value, exp["task_lifecycle"])

    def test_safety_stop_invalidates_previously_issued_permit(self):
        matrix = expected()
        idle = host()
        permit = issue_dispatch_permit(
            task=task(),
            now=NOW,
            observation=idle,
            artifacts=[],
        )
        self.assertIsNotNone(permit)

        stopped = host(safety_stop=True)
        valid = validate_dispatch_permit(
            permit,
            task=task(),
            now=NOW,
            observation=stopped,
            artifacts=[],
        )
        self.assertEqual(valid, matrix["safety_stop_after_permit"]["permit_valid"])

    def test_matrix_names_are_unique_and_fixture_is_explicit(self):
        data = json.loads(SCENARIO.read_text(encoding="utf-8"))
        names = [item["name"] for item in data["cases"]]
        self.assertEqual(len(names), len(set(names)))
        self.assertTrue(data["basis"]["fixture_only"])


if __name__ == "__main__":
    unittest.main()
