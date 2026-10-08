"""One bounded autonomous coding attempt for Loop42.

This composes existing provider-neutral contracts without adding retry, commit,
push, merge or publish authority. The runtime owns the isolated workspace and
all side effects; the model only returns a WorkerResult proposal.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Tuple

from tools.harness.action_policy import PolicyRule
from tools.harness.change_set import ChangeSet, NormalizedChangeSet, normalize_changeset
from tools.harness.changeset_executor import (
    ChangeSetReceipt,
    apply_changeset,
    issue_changeset_permit,
)
from tools.harness.git_workspace import GitWorkspaceLease, create_detached_worktree
from tools.harness.verification_registry import (
    VerificationRegistry,
    VerificationResult,
    run_verifications,
)
from tools.harness.worker_provider import WorkerRequest, WorkerResult, WorkerStatus


class AttemptStatus(str, Enum):
    BLOCKED = "blocked"
    PROVIDER_FAILED = "provider_failed"
    REJECTED = "rejected"
    APPLIED_UNVERIFIED = "applied_unverified"
    VERIFICATION_FAILED = "verification_failed"
    VERIFIED = "verified"


@dataclass(frozen=True)
class AttemptResult:
    status: AttemptStatus
    reason: str
    workspace: GitWorkspaceLease
    request: WorkerRequest
    worker_result: WorkerResult | None = None
    normalized_changeset: NormalizedChangeSet | None = None
    receipt: ChangeSetReceipt | None = None
    verifications: Tuple[VerificationResult, ...] = ()


def _bound_request(request: WorkerRequest, exact_revision: str) -> WorkerRequest:
    return WorkerRequest(
        task_id=request.task_id,
        attempt_id=request.attempt_id,
        source_revision=exact_revision,
        context_fingerprint=request.context_fingerprint,
        task=request.task,
        context=request.context,
        allowed_capabilities=request.allowed_capabilities,
        requested_role=request.requested_role,
    )


def _validate_result_identity(request: WorkerRequest, result: WorkerResult) -> None:
    if not isinstance(result, WorkerResult):
        raise TypeError("provider must return WorkerResult")
    expected = (
        request.task_id,
        request.attempt_id,
        request.source_revision,
        request.context_fingerprint,
    )
    observed = (
        result.task_id,
        result.attempt_id,
        result.source_revision,
        result.context_fingerprint,
    )
    if observed != expected:
        raise ValueError("worker result identity does not match the exact attempt")


def _safe_target(root: Path, relative: str) -> Path:
    current = root
    parts = relative.split("/")
    for part in parts[:-1]:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"symlink path component refused: {relative}")
        if not current.exists() or not current.is_dir():
            raise ValueError(f"parent directory does not exist: {relative}")
    target = current / parts[-1]
    if target.is_symlink():
        raise ValueError(f"symlink target refused: {relative}")
    return target


def _snapshot_proposal_paths(workspace: Path, changeset: ChangeSet) -> dict[str, str]:
    root = Path(workspace)
    if root.is_symlink() or not root.exists() or not root.is_dir():
        raise ValueError("workspace must be an existing non-symlink directory")
    root = root.resolve()
    snapshot: dict[str, str] = {}
    for change in changeset.changes:
        target = _safe_target(root, change.path)
        if not target.exists():
            continue
        if not target.is_file():
            raise ValueError(f"proposal target is not a regular file: {change.path}")
        raw = target.read_bytes()
        try:
            snapshot[change.path] = raw.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValueError(f"proposal target is not UTF-8 text: {change.path}") from error
    return snapshot


def _reason(prefix: str, error: BaseException) -> str:
    text = str(error).strip().replace("\n", " ")
    if len(text) > 1000:
        text = text[:1000]
    return f"{prefix}:{type(error).__name__}:{text}"


def run_autonomous_attempt(
    repo_root: Path,
    workspace_parent: Path,
    request: WorkerRequest,
    provider,
    verification_registry: VerificationRegistry,
    *,
    interactive: bool = False,
    rules: Tuple[PolicyRule, ...] = (),
) -> AttemptResult:
    """Run exactly one visible attempt and retain its isolated workspace.

    The caller owns later cleanup, retry/recovery, commit, push and PR decisions.
    No automatic provider fallback or retry happens inside this function.
    """
    if not isinstance(request, WorkerRequest):
        raise TypeError("request must be WorkerRequest")
    if not isinstance(verification_registry, VerificationRegistry):
        raise TypeError("verification_registry must be VerificationRegistry")
    if type(interactive) is not bool:
        raise TypeError("interactive must be boolean")
    if not isinstance(rules, tuple) or any(not isinstance(item, PolicyRule) for item in rules):
        raise TypeError("rules must be a tuple of PolicyRule")
    if not hasattr(provider, "run") or not callable(provider.run):
        raise TypeError("provider must expose callable run(request)")

    lease = create_detached_worktree(
        Path(repo_root),
        request.source_revision,
        parent=Path(workspace_parent),
    )
    bound = _bound_request(request, lease.source_revision)

    try:
        worker = provider.run(bound)
        _validate_result_identity(bound, worker)
    except Exception as error:
        return AttemptResult(
            AttemptStatus.PROVIDER_FAILED,
            _reason("provider", error),
            lease,
            bound,
        )

    if worker.status is WorkerStatus.BLOCKED:
        return AttemptResult(
            AttemptStatus.BLOCKED,
            worker.rationale_summary or "worker blocked",
            lease,
            bound,
            worker_result=worker,
        )
    if worker.status is WorkerStatus.FAILED:
        return AttemptResult(
            AttemptStatus.PROVIDER_FAILED,
            worker.rationale_summary or "worker failed",
            lease,
            bound,
            worker_result=worker,
        )

    assert worker.changeset is not None
    try:
        snapshot = _snapshot_proposal_paths(lease.root, worker.changeset)
        normalized = normalize_changeset(worker.changeset, snapshot)
        permit = issue_changeset_permit(
            lease.root,
            normalized,
            interactive=interactive,
            rules=rules,
        )
        receipt = apply_changeset(
            lease.root,
            normalized,
            permit,
            interactive=interactive,
            rules=rules,
        )
    except Exception as error:
        return AttemptResult(
            AttemptStatus.REJECTED,
            _reason("changeset", error),
            lease,
            bound,
            worker_result=worker,
        )

    if not normalized.requested_verification:
        return AttemptResult(
            AttemptStatus.APPLIED_UNVERIFIED,
            "changes applied but no verification identifier was requested",
            lease,
            bound,
            worker_result=worker,
            normalized_changeset=normalized,
            receipt=receipt,
        )

    try:
        verifications = run_verifications(
            lease.root,
            normalized.requested_verification,
            verification_registry,
        )
    except Exception as error:
        return AttemptResult(
            AttemptStatus.VERIFICATION_FAILED,
            _reason("verification", error),
            lease,
            bound,
            worker_result=worker,
            normalized_changeset=normalized,
            receipt=receipt,
        )

    if not verifications or any(not item.passed for item in verifications):
        return AttemptResult(
            AttemptStatus.VERIFICATION_FAILED,
            "one or more registered verifications failed",
            lease,
            bound,
            worker_result=worker,
            normalized_changeset=normalized,
            receipt=receipt,
            verifications=verifications,
        )

    return AttemptResult(
        AttemptStatus.VERIFIED,
        "registered verification passed",
        lease,
        bound,
        worker_result=worker,
        normalized_changeset=normalized,
        receipt=receipt,
        verifications=verifications,
    )
