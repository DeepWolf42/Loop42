"""Pure post-interruption reconciliation for bounded side effects.

Provider-specific adapters reduce one target to a stable state fingerprint.
This module only classifies fresh evidence. It never performs or authorizes the
side effect, and it never treats an interrupted response as proof of failure.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import re

_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}")
_FP_RE = re.compile(r"[0-9a-f]{64}")


class SideEffectState(str, Enum):
    APPLIED = "applied"
    NOT_APPLIED = "not_applied"
    CONFLICT = "conflict"
    UNKNOWN = "unknown"


def _aware_utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")
    return value.astimezone(timezone.utc)


def _bounded_text(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip() or len(value) > 1000:
        raise ValueError(f"{name} must be bounded non-empty text")


@dataclass(frozen=True)
class SideEffectIntent:
    """Exact before/desired state projection for one side-effect attempt."""

    action_id: str
    action: str
    target: str
    state_scope: str
    before_fingerprint: str
    desired_fingerprint: str

    def __post_init__(self) -> None:
        if not isinstance(self.action_id, str) or not _ID_RE.fullmatch(self.action_id):
            raise ValueError("invalid action_id")
        _bounded_text("action", self.action)
        _bounded_text("target", self.target)
        if not isinstance(self.state_scope, str) or not _ID_RE.fullmatch(self.state_scope):
            raise ValueError("invalid state_scope")
        for name, value in (
            ("before_fingerprint", self.before_fingerprint),
            ("desired_fingerprint", self.desired_fingerprint),
        ):
            if not isinstance(value, str) or not _FP_RE.fullmatch(value):
                raise ValueError(f"{name} must be a SHA-256 hex digest")
        if self.before_fingerprint == self.desired_fingerprint:
            raise ValueError("before and desired fingerprints must differ")


@dataclass(frozen=True)
class SideEffectObservation:
    """Fresh provider observation using the intent's exact state projection."""

    observed_at: datetime
    target: str
    state_scope: str
    state_fingerprint: str
    complete: bool = True
    valid: bool = True

    def __post_init__(self) -> None:
        _aware_utc(self.observed_at)
        _bounded_text("target", self.target)
        if not isinstance(self.state_scope, str) or not _ID_RE.fullmatch(self.state_scope):
            raise ValueError("invalid state_scope")
        if not isinstance(self.state_fingerprint, str) or not _FP_RE.fullmatch(
            self.state_fingerprint
        ):
            raise ValueError("state_fingerprint must be a SHA-256 hex digest")
        if type(self.complete) is not bool or type(self.valid) is not bool:
            raise TypeError("complete and valid must be boolean")


@dataclass(frozen=True)
class SideEffectReconciliation:
    state: SideEffectState
    reasons: tuple[str, ...]
    may_reconsider: bool


def reconcile_side_effect(
    intent: SideEffectIntent,
    *,
    now: datetime,
    observation: SideEffectObservation | None,
    freshness_seconds: int = 300,
) -> SideEffectReconciliation:
    """Classify fresh post-interruption evidence without replaying an action.

    ``may_reconsider`` means only that fresh evidence still matches the exact
    pre-action state. It is not permission to execute: policy, authorization and
    provider preconditions must be evaluated again before any new side effect.
    """
    if not isinstance(intent, SideEffectIntent):
        raise TypeError("intent must be SideEffectIntent")
    now = _aware_utc(now)
    if not isinstance(freshness_seconds, int) or isinstance(freshness_seconds, bool):
        raise TypeError("freshness_seconds must be an integer")
    if freshness_seconds <= 0:
        raise ValueError("freshness_seconds must be positive")

    if observation is None:
        return SideEffectReconciliation(
            SideEffectState.UNKNOWN, ("observation_missing",), False
        )
    if not isinstance(observation, SideEffectObservation):
        raise TypeError("observation must be SideEffectObservation or None")

    if observation.target != intent.target or observation.state_scope != intent.state_scope:
        return SideEffectReconciliation(
            SideEffectState.CONFLICT, ("observation_identity_mismatch",), False
        )

    age = (now - _aware_utc(observation.observed_at)).total_seconds()
    if age < 0:
        return SideEffectReconciliation(
            SideEffectState.UNKNOWN, ("observation_clock_skew",), False
        )
    if age > freshness_seconds:
        return SideEffectReconciliation(
            SideEffectState.UNKNOWN, ("observation_stale",), False
        )
    if not observation.complete or not observation.valid:
        return SideEffectReconciliation(
            SideEffectState.UNKNOWN, ("observation_incomplete_or_invalid",), False
        )

    if observation.state_fingerprint == intent.desired_fingerprint:
        return SideEffectReconciliation(
            SideEffectState.APPLIED, ("desired_state_observed",), False
        )
    if observation.state_fingerprint == intent.before_fingerprint:
        return SideEffectReconciliation(
            SideEffectState.NOT_APPLIED, ("pre_action_state_observed",), True
        )
    return SideEffectReconciliation(
        SideEffectState.CONFLICT, ("target_state_diverged",), False
    )
