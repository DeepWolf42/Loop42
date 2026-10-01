"""Pure evidence-gated retry classification for bounded work attempts.

Backoff is useful only after a retry is proven admissible. This module never
infers retryability from model text, a missing heartbeat, or an interrupted
response. Ambiguous state is reconciled instead of replayed.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from tools.harness.side_effect_reconcile import SideEffectState


class FailureClass(str, Enum):
    TRANSIENT = "transient"
    PERMANENT = "permanent"
    UNKNOWN = "unknown"
    CONFLICT = "conflict"
    SAFETY_STOP = "safety_stop"


class RetryDecision(str, Enum):
    RETRY_AFTER_BACKOFF = "retry_after_backoff"
    DO_NOT_RETRY = "do_not_retry"
    RECONCILE = "reconcile"
    OPERATOR_REQUIRED = "operator_required"


@dataclass(frozen=True)
class RetryAssessment:
    decision: RetryDecision
    delay_seconds: int | None
    reasons: tuple[str, ...]
    attempts_remaining: int


def _positive_int(name: str, value: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be an integer")
    if value <= 0:
        raise ValueError(f"{name} must be positive")


def _backoff_delay(attempt: int, base: int, cap: int) -> int:
    delay = min(base, cap)
    for _ in range(attempt - 1):
        if delay >= cap:
            return cap
        delay = min(cap, delay * 2)
    return delay


def assess_retry(
    *,
    failure: FailureClass,
    attempt: int,
    max_attempts: int,
    fresh_evidence: bool,
    side_effect_possible: bool,
    side_effect_state: SideEffectState | None = None,
    base_delay_seconds: int = 10,
    max_delay_seconds: int = 600,
) -> RetryAssessment:
    """Classify retry eligibility without scheduling or authorizing execution.

    attempt is the number of the attempt that just ended, starting at 1.
    A retry is considered only for an explicitly classified transient failure,
    fresh evidence, remaining budget, and an explicit declaration of whether
    a side effect was possible. A possible side effect requires a freshly
    reconciled NOT_APPLIED state before retry can remain eligible.
    """
    if not isinstance(failure, FailureClass):
        raise TypeError("failure must be FailureClass")
    _positive_int("attempt", attempt)
    _positive_int("max_attempts", max_attempts)
    _positive_int("base_delay_seconds", base_delay_seconds)
    _positive_int("max_delay_seconds", max_delay_seconds)
    if type(fresh_evidence) is not bool:
        raise TypeError("fresh_evidence must be boolean")
    if type(side_effect_possible) is not bool:
        raise TypeError("side_effect_possible must be boolean")
    if side_effect_state is not None and not isinstance(
        side_effect_state, SideEffectState
    ):
        raise TypeError("side_effect_state must be SideEffectState or None")
    if not side_effect_possible and side_effect_state is not None:
        raise ValueError(
            "side_effect_state must be omitted when side_effect_possible is false"
        )

    remaining = max(0, max_attempts - attempt)

    if failure is FailureClass.SAFETY_STOP:
        return RetryAssessment(
            RetryDecision.OPERATOR_REQUIRED,
            None,
            ("safety_stop_requires_operator",),
            remaining,
        )

    if not fresh_evidence:
        return RetryAssessment(
            RetryDecision.RECONCILE,
            None,
            ("retry_evidence_not_fresh",),
            remaining,
        )

    if side_effect_possible and side_effect_state is None:
        return RetryAssessment(
            RetryDecision.RECONCILE,
            None,
            ("side_effect_state_missing",),
            remaining,
        )

    if side_effect_state is SideEffectState.APPLIED:
        return RetryAssessment(
            RetryDecision.DO_NOT_RETRY,
            None,
            ("side_effect_already_applied",),
            remaining,
        )
    if side_effect_state in (SideEffectState.CONFLICT, SideEffectState.UNKNOWN):
        return RetryAssessment(
            RetryDecision.RECONCILE,
            None,
            ("side_effect_state_ambiguous",),
            remaining,
        )

    if failure in (FailureClass.UNKNOWN, FailureClass.CONFLICT):
        return RetryAssessment(
            RetryDecision.RECONCILE,
            None,
            ("failure_requires_reconciliation",),
            remaining,
        )
    if failure is FailureClass.PERMANENT:
        return RetryAssessment(
            RetryDecision.DO_NOT_RETRY,
            None,
            ("permanent_failure",),
            remaining,
        )
    if remaining == 0:
        return RetryAssessment(
            RetryDecision.DO_NOT_RETRY,
            None,
            ("retry_budget_exhausted",),
            0,
        )

    reasons = ["verified_transient_failure", "retry_budget_available"]
    if side_effect_possible:
        reasons.append("side_effect_confirmed_not_applied")
    else:
        reasons.append("no_side_effect_possible")
    return RetryAssessment(
        RetryDecision.RETRY_AFTER_BACKOFF,
        _backoff_delay(attempt, base_delay_seconds, max_delay_seconds),
        tuple(reasons),
        remaining,
    )
