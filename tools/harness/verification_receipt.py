"""Content-addressed verification receipts for Loop42 work results.

A receipt binds one independently checked subject to the exact dispatch basis and
acceptance criteria. The fingerprint detects content changes; it is not a digital
signature and does not prove verifier identity by itself.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
import re

from tools.harness.worker_dispatch import (
    ArtifactKind,
    AttemptArtifact,
    DispatchTask,
)

SCHEMA = "loop42.verification-receipt.v1"
_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}")
_SHA_RE = re.compile(r"[0-9a-f]{7,64}")
_FP_RE = re.compile(r"[0-9a-f]{64}")


class CriterionStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    UNKNOWN = "unknown"


def _aware_utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")
    return value.astimezone(timezone.utc)


def _bounded_text(name: str, value: str, limit: int = 1000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{name} must be bounded non-empty text")
    return value


@dataclass(frozen=True)
class EvidenceRef:
    source: str
    fingerprint: str

    def __post_init__(self) -> None:
        _bounded_text("source", self.source, 512)
        if not isinstance(self.fingerprint, str) or not _FP_RE.fullmatch(self.fingerprint):
            raise ValueError("evidence fingerprint must be a SHA-256 hex digest")


@dataclass(frozen=True)
class CriterionVerification:
    criterion: str
    status: CriterionStatus
    evidence: tuple[EvidenceRef, ...] = ()

    def __post_init__(self) -> None:
        _bounded_text("criterion", self.criterion)
        if not isinstance(self.status, CriterionStatus):
            raise TypeError("status must be CriterionStatus")
        evidence = tuple(self.evidence)
        if any(not isinstance(item, EvidenceRef) for item in evidence):
            raise TypeError("evidence must contain EvidenceRef values")
        keys = tuple((item.source, item.fingerprint) for item in evidence)
        if len(set(keys)) != len(keys):
            raise ValueError("duplicate evidence references are not allowed")
        if self.status is CriterionStatus.PASS and not evidence:
            raise ValueError("PASS criteria require at least one evidence reference")
        object.__setattr__(self, "evidence", evidence)


@dataclass(frozen=True)
class VerificationReceipt:
    task_id: str
    attempt_id: str
    source_revision: str
    context_fingerprint: str
    subject_fingerprint: str
    verifier_id: str
    verifier_revision: str
    verified_at: datetime
    criteria: tuple[CriterionVerification, ...]

    def __post_init__(self) -> None:
        for name, value in (
            ("task_id", self.task_id),
            ("attempt_id", self.attempt_id),
            ("verifier_id", self.verifier_id),
        ):
            if not isinstance(value, str) or not _ID_RE.fullmatch(value):
                raise ValueError(f"invalid {name}")
        if not isinstance(self.source_revision, str) or not _SHA_RE.fullmatch(
            self.source_revision
        ):
            raise ValueError("source_revision must be a lowercase Git revision")
        if not isinstance(self.verifier_revision, str) or not _ID_RE.fullmatch(
            self.verifier_revision
        ):
            raise ValueError("invalid verifier_revision")
        for name, value in (
            ("context_fingerprint", self.context_fingerprint),
            ("subject_fingerprint", self.subject_fingerprint),
        ):
            if not isinstance(value, str) or not _FP_RE.fullmatch(value):
                raise ValueError(f"{name} must be a SHA-256 hex digest")
        _aware_utc(self.verified_at)
        criteria = tuple(self.criteria)
        if not criteria or any(not isinstance(item, CriterionVerification) for item in criteria):
            raise ValueError("criteria must contain CriterionVerification values")
        names = tuple(item.criterion for item in criteria)
        if len(set(names)) != len(names):
            raise ValueError("duplicate acceptance criteria are not allowed")
        object.__setattr__(self, "criteria", criteria)


@dataclass(frozen=True)
class ReceiptValidation:
    valid: bool
    reasons: tuple[str, ...]
    fingerprint: str


def receipt_payload(receipt: VerificationReceipt) -> dict:
    if not isinstance(receipt, VerificationReceipt):
        raise TypeError("receipt must be VerificationReceipt")
    return {
        "schema": SCHEMA,
        "task_id": receipt.task_id,
        "attempt_id": receipt.attempt_id,
        "source_revision": receipt.source_revision,
        "context_fingerprint": receipt.context_fingerprint,
        "subject_fingerprint": receipt.subject_fingerprint,
        "verifier_id": receipt.verifier_id,
        "verifier_revision": receipt.verifier_revision,
        "verified_at": _aware_utc(receipt.verified_at).isoformat(),
        "criteria": [
            {
                "criterion": item.criterion,
                "status": item.status.value,
                "evidence": [
                    {"source": evidence.source, "fingerprint": evidence.fingerprint}
                    for evidence in item.evidence
                ],
            }
            for item in receipt.criteria
        ],
    }


def receipt_fingerprint(receipt: VerificationReceipt) -> str:
    encoded = json.dumps(
        receipt_payload(receipt),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_receipt(
    receipt: VerificationReceipt,
    task: DispatchTask,
    *,
    subject_fingerprint: str | None = None,
) -> ReceiptValidation:
    """Validate a receipt against one exact dispatch task.

    This validates identity, acceptance coverage and pass evidence. It does not
    authenticate the verifier and it does not grant execution/write authority.
    """
    if not isinstance(receipt, VerificationReceipt):
        raise TypeError("receipt must be VerificationReceipt")
    if not isinstance(task, DispatchTask):
        raise TypeError("task must be DispatchTask")
    if subject_fingerprint is not None and (
        not isinstance(subject_fingerprint, str) or not _FP_RE.fullmatch(subject_fingerprint)
    ):
        raise ValueError("subject_fingerprint must be a SHA-256 hex digest")

    reasons: list[str] = []
    if (
        receipt.task_id != task.task_id
        or receipt.attempt_id != task.attempt_id
        or receipt.source_revision != task.source_revision
        or receipt.context_fingerprint != task.context_fingerprint
    ):
        reasons.append("task_identity_mismatch")

    receipt_criteria = tuple(item.criterion for item in receipt.criteria)
    if receipt_criteria != task.acceptance_criteria:
        reasons.append("acceptance_criteria_mismatch")

    if any(item.status is not CriterionStatus.PASS for item in receipt.criteria):
        reasons.append("acceptance_not_fully_passed")

    if any(
        item.status is CriterionStatus.PASS and not item.evidence
        for item in receipt.criteria
    ):
        reasons.append("pass_evidence_missing")

    if subject_fingerprint is not None and receipt.subject_fingerprint != subject_fingerprint:
        reasons.append("subject_fingerprint_mismatch")

    return ReceiptValidation(
        valid=not reasons,
        reasons=tuple(reasons),
        fingerprint=receipt_fingerprint(receipt),
    )


def result_artifact_from_receipt(
    receipt: VerificationReceipt,
    task: DispatchTask,
    *,
    observed_at: datetime,
    subject_fingerprint: str | None = None,
) -> AttemptArtifact:
    """Create a successful terminal artifact only from a receipt valid for task."""
    validation = validate_receipt(
        receipt,
        task,
        subject_fingerprint=subject_fingerprint,
    )
    if not validation.valid:
        joined = ",".join(validation.reasons)
        raise ValueError(f"verification receipt is not valid for task: {joined}")
    return AttemptArtifact(
        kind=ArtifactKind.RESULT,
        task_id=task.task_id,
        attempt_id=task.attempt_id,
        source_revision=task.source_revision,
        context_fingerprint=task.context_fingerprint,
        observed_at=observed_at,
        complete=True,
        valid=True,
        success=True,
        receipt_fingerprint=validation.fingerprint,
    )
