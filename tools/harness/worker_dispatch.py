#!/usr/bin/env python3
"""Pure reconciliation contract for bounded single-worker dispatch.

Provider/OS/queue adapters translate observations into these immutable records.
This module never starts a worker, executes model output, writes a queue, or
grants consumer authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import re
from typing import Iterable, Tuple

_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
_SHA_RE = re.compile(r"[0-9a-f]{7,64}")
_FP_RE = re.compile(r"[0-9a-f]{64}")


class HostAvailability(str, Enum):
    AVAILABLE = "available"
    UNREACHABLE = "unreachable"
    UNKNOWN = "unknown"


class WorkerHealth(str, Enum):
    HEALTHY = "healthy"
    STOPPED = "stopped"
    STALLED = "stalled"
    FAILED = "failed"
    CONFLICT = "conflict"
    UNKNOWN = "unknown"


class TaskLifecycle(str, Enum):
    IDLE = "idle"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CONFLICT = "conflict"
    BLOCKED = "blocked"
    UNKNOWN = "unknown"


class EvidenceFreshness(str, Enum):
    FRESH = "fresh"
    STALE = "stale"
    UNKNOWN = "unknown"


class ArtifactKind(str, Enum):
    QUEUED = "queued"
    STARTED = "started"
    PROGRESS = "progress"
    RESULT = "result"
    ERROR = "error"
    ARCHIVED = "archived"


class NotificationKind(str, Enum):
    RESULT = "result"
    ACTIONABLE_FAILURE = "actionable_failure"
    DECISION_REQUIRED = "decision_required"


def _aware_utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")
    return value.astimezone(timezone.utc)


@dataclass(frozen=True)
class DispatchTask:
    task_id: str
    attempt_id: str
    source_revision: str
    context_fingerprint: str
    acceptance_criteria: Tuple[str, ...]

    def __post_init__(self) -> None:
        for name, value in (("task_id", self.task_id), ("attempt_id", self.attempt_id)):
            if not isinstance(value, str) or not _ID_RE.fullmatch(value):
                raise ValueError(f"invalid {name}")
        if not isinstance(self.source_revision, str) or not _SHA_RE.fullmatch(self.source_revision):
            raise ValueError("source_revision must be a lowercase Git revision")
        if not isinstance(self.context_fingerprint, str) or not _FP_RE.fullmatch(self.context_fingerprint):
            raise ValueError("context_fingerprint must be a SHA-256 hex digest")
        criteria = tuple(self.acceptance_criteria)
        if not criteria or any(
            not isinstance(item, str) or not item.strip() or len(item) > 1000
            for item in criteria
        ):
            raise ValueError("acceptance_criteria must contain bounded non-empty text")
        object.__setattr__(self, "acceptance_criteria", criteria)


@dataclass(frozen=True)
class WorkerSession:
    session_id: str
    task_id: str | None = None
    attempt_id: str | None = None
    progress_seq: int | None = None
    progress_at: datetime | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.session_id, str) or not _ID_RE.fullmatch(self.session_id):
            raise ValueError("invalid worker session_id")
        if (self.task_id is None) != (self.attempt_id is None):
            raise ValueError("task_id and attempt_id must be present together")
        for name, value in (("task_id", self.task_id), ("attempt_id", self.attempt_id)):
            if value is not None and (
                not isinstance(value, str) or not _ID_RE.fullmatch(value)
            ):
                raise ValueError(f"invalid {name}")
        if self.progress_seq is not None and (
            not isinstance(self.progress_seq, int)
            or isinstance(self.progress_seq, bool)
            or self.progress_seq < 0
        ):
            raise ValueError("progress_seq must be a non-negative integer")
        if self.progress_at is not None:
            _aware_utc(self.progress_at)


@dataclass(frozen=True)
class HostObservation:
    observed_at: datetime
    session_id: str
    reachable: bool
    worker_sessions: Tuple[WorkerSession, ...] = ()
    safety_stop: bool = False

    def __post_init__(self) -> None:
        _aware_utc(self.observed_at)
        if not isinstance(self.session_id, str) or not _ID_RE.fullmatch(self.session_id):
            raise ValueError("invalid host session_id")
        if not isinstance(self.reachable, bool) or not isinstance(self.safety_stop, bool):
            raise TypeError("reachable and safety_stop must be boolean")
        sessions = tuple(self.worker_sessions)
        if any(not isinstance(item, WorkerSession) for item in sessions):
            raise TypeError("worker_sessions must contain WorkerSession values")
        object.__setattr__(self, "worker_sessions", sessions)


@dataclass(frozen=True)
class AttemptArtifact:
    kind: ArtifactKind
    task_id: str
    attempt_id: str
    source_revision: str
    context_fingerprint: str
    observed_at: datetime
    complete: bool = True
    valid: bool = True
    success: bool | None = None
    receipt_fingerprint: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ArtifactKind):
            raise TypeError("kind must be ArtifactKind")
        for name, value in (("task_id", self.task_id), ("attempt_id", self.attempt_id)):
            if not isinstance(value, str) or not _ID_RE.fullmatch(value):
                raise ValueError(f"invalid {name}")
        if not isinstance(self.source_revision, str) or not _SHA_RE.fullmatch(self.source_revision):
            raise ValueError("source_revision must be a lowercase Git revision")
        if not isinstance(self.context_fingerprint, str) or not _FP_RE.fullmatch(self.context_fingerprint):
            raise ValueError("context_fingerprint must be a SHA-256 hex digest")
        _aware_utc(self.observed_at)
        if not isinstance(self.complete, bool) or not isinstance(self.valid, bool):
            raise TypeError("complete and valid must be boolean")
        if self.kind in {ArtifactKind.RESULT, ArtifactKind.ERROR}:
            if self.success is None or not isinstance(self.success, bool):
                raise ValueError("terminal artifacts require boolean success")
            if self.kind is ArtifactKind.RESULT and not self.success:
                raise ValueError("RESULT must use success=True; failures use ERROR")
            if self.kind is ArtifactKind.ERROR and self.success:
                raise ValueError("ERROR must use success=False")
        elif self.success is not None:
            raise ValueError("non-terminal artifacts must not set success")
        if self.receipt_fingerprint is not None and not _FP_RE.fullmatch(
            self.receipt_fingerprint
        ):
            raise ValueError("receipt_fingerprint must be a SHA-256 hex digest")


@dataclass(frozen=True)
class ReconciledState:
    host: HostAvailability
    worker: WorkerHealth
    lifecycle: TaskLifecycle
    freshness: EvidenceFreshness
    can_dispatch: bool
    reasons: Tuple[str, ...]
    outstanding: Tuple[Tuple[str, str], ...]
    late_results: Tuple[Tuple[str, str], ...]
    result_receipt: str | None = None


def _age_seconds(now: datetime, then: datetime) -> float:
    return (_aware_utc(now) - _aware_utc(then)).total_seconds()


def _matching(artifact: AttemptArtifact, task: DispatchTask) -> bool:
    return (
        artifact.task_id == task.task_id
        and artifact.attempt_id == task.attempt_id
        and artifact.source_revision == task.source_revision
        and artifact.context_fingerprint == task.context_fingerprint
    )


def _terminal(
    artifacts: Iterable[AttemptArtifact], key: tuple[str, str]
) -> AttemptArtifact | None:
    valid = [
        item
        for item in artifacts
        if (item.task_id, item.attempt_id) == key
        and item.kind in {ArtifactKind.RESULT, ArtifactKind.ERROR}
        and item.complete
        and item.valid
    ]
    if not valid:
        return None
    signatures = {
        (
            item.kind,
            item.source_revision,
            item.context_fingerprint,
            item.receipt_fingerprint,
        )
        for item in valid
    }
    if len(signatures) != 1:
        return None
    return max(valid, key=lambda item: item.observed_at)


def reconcile_worker(
    *,
    now: datetime,
    observation: HostObservation | None,
    artifacts: Iterable[AttemptArtifact],
    expected: DispatchTask | None = None,
    freshness_seconds: int = 300,
    stall_seconds: int | None = None,
) -> ReconciledState:
    """Reconcile queue/worker/result evidence without inferring from silence.

    A stale or absent host observation never proves RUNNING or FAILED. Completion
    only accepts a complete, valid terminal artifact whose task/attempt/revision/
    context exactly match the expected task.
    """
    _aware_utc(now)
    if not isinstance(freshness_seconds, int) or freshness_seconds <= 0:
        raise ValueError("freshness_seconds must be positive")
    if stall_seconds is not None and (
        not isinstance(stall_seconds, int) or stall_seconds <= 0
    ):
        raise ValueError("stall_seconds must be positive when provided")

    artifacts = tuple(artifacts)
    if any(not isinstance(item, AttemptArtifact) for item in artifacts):
        raise TypeError("artifacts must contain AttemptArtifact values")

    reasons: list[str] = []
    fresh_observation = False
    if observation is None:
        freshness = EvidenceFreshness.UNKNOWN
        host = HostAvailability.UNKNOWN
        worker = WorkerHealth.UNKNOWN
        reasons.append("host_observation_missing")
        sessions: tuple[WorkerSession, ...] = ()
    else:
        age = _age_seconds(now, observation.observed_at)
        if age < 0:
            freshness = EvidenceFreshness.UNKNOWN
            host = HostAvailability.UNKNOWN
            worker = WorkerHealth.UNKNOWN
            reasons.append("host_clock_skew")
            sessions = ()
        elif age > freshness_seconds:
            freshness = EvidenceFreshness.STALE
            host = HostAvailability.UNREACHABLE
            worker = WorkerHealth.UNKNOWN
            reasons.append("host_observation_stale")
            sessions = ()
        elif not observation.reachable:
            freshness = EvidenceFreshness.FRESH
            host = HostAvailability.UNREACHABLE
            worker = WorkerHealth.UNKNOWN
            reasons.append("host_unreachable")
            sessions = ()
        else:
            fresh_observation = True
            freshness = EvidenceFreshness.FRESH
            host = HostAvailability.AVAILABLE
            sessions = observation.worker_sessions
            if not sessions:
                worker = WorkerHealth.STOPPED
                reasons.append("worker_absent_on_fresh_host")
            elif len({item.session_id for item in sessions}) != len(sessions) or len(
                sessions
            ) > 1:
                worker = WorkerHealth.CONFLICT
                reasons.append("multiple_worker_sessions")
            else:
                worker = WorkerHealth.HEALTHY

    keys = {(item.task_id, item.attempt_id) for item in artifacts}
    conflicting_terminal: set[tuple[str, str]] = set()
    for key in keys:
        valid_terminal = [
            item
            for item in artifacts
            if (item.task_id, item.attempt_id) == key
            and item.kind in {ArtifactKind.RESULT, ArtifactKind.ERROR}
            and item.complete
            and item.valid
        ]
        signatures = {
            (
                item.kind,
                item.source_revision,
                item.context_fingerprint,
                item.receipt_fingerprint,
            )
            for item in valid_terminal
        }
        if len(signatures) > 1:
            conflicting_terminal.add(key)

    outstanding = []
    for key in sorted(keys):
        if key in conflicting_terminal or _terminal(artifacts, key) is not None:
            continue
        if any(
            item.kind
            in {ArtifactKind.QUEUED, ArtifactKind.STARTED, ArtifactKind.PROGRESS}
            and item.complete
            and item.valid
            for item in artifacts
            if (item.task_id, item.attempt_id) == key
        ):
            outstanding.append(key)

    late_results = []
    if expected is not None:
        for key in sorted(keys):
            if key == (expected.task_id, expected.attempt_id):
                continue
            terminal = _terminal(artifacts, key)
            if (
                terminal
                and terminal.kind is ArtifactKind.RESULT
                and terminal.task_id == expected.task_id
            ):
                late_results.append(key)

    safety_stop = bool(observation and observation.safety_stop)
    if safety_stop:
        reasons.append("safety_stop_latched")

    lifecycle = TaskLifecycle.IDLE if expected is None else TaskLifecycle.UNKNOWN
    receipt = None

    if conflicting_terminal:
        lifecycle = TaskLifecycle.CONFLICT
        worker = WorkerHealth.CONFLICT if fresh_observation else worker
        reasons.append("conflicting_terminal_artifacts")
    elif expected is not None:
        exact = [item for item in artifacts if _matching(item, expected)]
        foreign_same_attempt = [
            item
            for item in artifacts
            if item.task_id == expected.task_id
            and item.attempt_id == expected.attempt_id
            and not _matching(item, expected)
        ]
        if foreign_same_attempt:
            lifecycle = TaskLifecycle.CONFLICT
            reasons.append("attempt_identity_mismatch")
        else:
            terminal = _terminal(exact, (expected.task_id, expected.attempt_id))
            if terminal is not None:
                lifecycle = (
                    TaskLifecycle.SUCCEEDED
                    if terminal.kind is ArtifactKind.RESULT
                    else TaskLifecycle.FAILED
                )
                receipt = terminal.receipt_fingerprint
                if terminal.kind is ArtifactKind.ERROR and fresh_observation:
                    worker = WorkerHealth.FAILED
                reasons.append("validated_terminal_artifact")
            elif any(
                item.kind in {ArtifactKind.RESULT, ArtifactKind.ERROR}
                and (not item.complete or not item.valid)
                for item in exact
            ):
                lifecycle = TaskLifecycle.UNKNOWN
                reasons.append("partial_or_invalid_terminal_artifact")
            elif safety_stop:
                lifecycle = TaskLifecycle.BLOCKED
            elif fresh_observation and worker is WorkerHealth.CONFLICT:
                lifecycle = TaskLifecycle.CONFLICT
            else:
                current_sessions = [
                    item
                    for item in sessions
                    if item.task_id == expected.task_id
                    and item.attempt_id == expected.attempt_id
                ]
                if fresh_observation and len(current_sessions) == 1:
                    session = current_sessions[0]
                    if stall_seconds is not None and session.progress_at is not None:
                        progress_age = _age_seconds(now, session.progress_at)
                        if progress_age >= 0 and progress_age > stall_seconds:
                            worker = WorkerHealth.STALLED
                            lifecycle = TaskLifecycle.UNKNOWN
                            reasons.append("declared_progress_deadline_exceeded")
                        elif progress_age < 0:
                            lifecycle = TaskLifecycle.UNKNOWN
                            reasons.append("progress_clock_skew")
                        else:
                            lifecycle = TaskLifecycle.RUNNING
                    else:
                        lifecycle = TaskLifecycle.RUNNING
                elif any(
                    item.kind is ArtifactKind.QUEUED and item.complete and item.valid
                    for item in exact
                ):
                    lifecycle = TaskLifecycle.QUEUED
                elif any(
                    item.kind in {ArtifactKind.STARTED, ArtifactKind.PROGRESS}
                    and item.complete
                    and item.valid
                    for item in exact
                ):
                    lifecycle = TaskLifecycle.UNKNOWN
                    reasons.append("historic_activity_not_current_progress")

    if late_results:
        reasons.append("late_result_requires_reconciliation")

    can_dispatch = (
        not safety_stop
        and worker is not WorkerHealth.CONFLICT
        and not conflicting_terminal
        and not outstanding
        and not late_results
        and (
            expected is None
            or lifecycle in {TaskLifecycle.SUCCEEDED, TaskLifecycle.FAILED}
        )
    )
    if expected is not None and lifecycle is TaskLifecycle.FAILED:
        can_dispatch = False
        reasons.append("failed_attempt_requires_new_attempt")

    return ReconciledState(
        host=host,
        worker=worker,
        lifecycle=lifecycle,
        freshness=freshness,
        can_dispatch=can_dispatch,
        reasons=tuple(dict.fromkeys(reasons)),
        outstanding=tuple(outstanding),
        late_results=tuple(late_results),
        result_receipt=receipt,
    )


def notification_for(
    previous: ReconciledState | None,
    current: ReconciledState,
) -> NotificationKind | None:
    """Return only meaningful state-transition notifications.

    Ordinary offline/stale observations are intentionally silent. Adapters can
    persist the previous reconciled state and use this helper to avoid repeated
    alerts while a host is powered off or temporarily unreachable.
    """
    if not isinstance(current, ReconciledState):
        raise TypeError("current must be ReconciledState")
    if previous is not None and not isinstance(previous, ReconciledState):
        raise TypeError("previous must be ReconciledState or None")

    if current.lifecycle is TaskLifecycle.SUCCEEDED:
        if (
            previous is None
            or previous.lifecycle is not TaskLifecycle.SUCCEEDED
            or previous.result_receipt != current.result_receipt
        ):
            return NotificationKind.RESULT
        return None

    if current.lifecycle is TaskLifecycle.FAILED:
        if previous is None or previous.lifecycle is not TaskLifecycle.FAILED:
            return NotificationKind.ACTIONABLE_FAILURE
        return None

    needs_decision = (
        current.lifecycle in {TaskLifecycle.CONFLICT, TaskLifecycle.BLOCKED}
        or bool(current.late_results)
    )
    previous_needs_decision = bool(
        previous
        and (
            previous.lifecycle in {TaskLifecycle.CONFLICT, TaskLifecycle.BLOCKED}
            or previous.late_results
        )
    )
    if needs_decision and (
        not previous_needs_decision
        or previous is None
        or previous.reasons != current.reasons
        or previous.late_results != current.late_results
    ):
        return NotificationKind.DECISION_REQUIRED
    return None
