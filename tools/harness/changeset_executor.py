"""Policy-gated filesystem executor for a normalized Loop42 ChangeSet.

The model never calls this module. A consumer first normalizes model output, then
issues a permit from fresh workspace state and policy, and revalidates that permit
immediately before applying the bounded text-file side effects.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import stat
import tempfile
from typing import Iterable, Tuple

from tools.harness.action_policy import (
    ActionEffect,
    ActionRequest,
    PolicyDecision,
    PolicyRule,
    evaluate_action_policy,
)
from tools.harness.change_set import ChangeOperation, NormalizedChangeSet, sha256_text


@dataclass(frozen=True)
class ChangeSetPermit:
    changeset_fingerprint: str
    basis_fingerprint: str
    policy_fingerprint: str


@dataclass(frozen=True)
class AppliedFileReceipt:
    operation: ChangeOperation
    path: str
    before_sha256: str | None
    after_sha256: str | None


@dataclass(frozen=True)
class ChangeSetReceipt:
    changeset_fingerprint: str
    basis_fingerprint: str
    final_fingerprint: str
    files: Tuple[AppliedFileReceipt, ...]


def _root(value: Path) -> Path:
    root = Path(value)
    if root.is_symlink() or not root.exists() or not root.is_dir():
        raise ValueError("workspace root must be an existing non-symlink directory")
    return root.resolve()


def _target(root: Path, relative: str) -> Path:
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


def _read_regular_text(target: Path, relative: str) -> tuple[str, int]:
    if not target.exists() or not target.is_file() or target.is_symlink():
        raise ValueError(f"expected regular file: {relative}")
    raw = target.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(f"non-UTF-8 file refused: {relative}") from error
    return text, stat.S_IMODE(target.stat().st_mode)


def _policy_records(
    changeset: NormalizedChangeSet,
    *,
    interactive: bool,
    rules: Tuple[PolicyRule, ...],
) -> tuple[tuple[str, str, str, str | None], ...]:
    records = []
    for item in changeset.files:
        result = evaluate_action_policy(
            ActionRequest(
                action=f"changeset.{item.operation.value}",
                target=f"repo:{item.path}",
                effect=ActionEffect.REVERSIBLE_WRITE,
            ),
            interactive=interactive,
            rules=rules,
        )
        records.append((item.operation.value, item.path, result.decision.value, result.rule_name))
        if result.decision is not PolicyDecision.ALLOW:
            raise PermissionError(
                f"change blocked by action policy: {item.operation.value} {item.path} -> {result.decision.value}"
            )
    return tuple(records)


def _basis(
    workspace: Path,
    changeset: NormalizedChangeSet,
) -> tuple[str, tuple[tuple[str, str, int | None], ...]]:
    root = _root(workspace)
    states: list[tuple[str, str, int | None]] = []
    for item in changeset.files:
        target = _target(root, item.path)
        if item.before_sha256 is None:
            if target.exists():
                raise ValueError(f"create basis changed; target exists: {item.path}")
            states.append((item.path, "missing", None))
            continue
        text, mode = _read_regular_text(target, item.path)
        digest = sha256_text(text)
        if digest != item.before_sha256:
            raise ValueError(f"workspace basis hash mismatch: {item.path}")
        states.append((item.path, digest, mode))
    payload = "\n".join(
        [changeset.fingerprint, *[f"{path}|{digest}|{mode if mode is not None else '-'}" for path, digest, mode in states]]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest(), tuple(states)


def _policy_fingerprint(records: Iterable[tuple[str, str, str, str | None]]) -> str:
    payload = "\n".join("|".join((op, path, decision, rule or "-")) for op, path, decision, rule in records)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def issue_changeset_permit(
    workspace: Path,
    changeset: NormalizedChangeSet,
    *,
    interactive: bool,
    rules: Tuple[PolicyRule, ...] = (),
) -> ChangeSetPermit:
    if not isinstance(changeset, NormalizedChangeSet):
        raise TypeError("changeset must be NormalizedChangeSet")
    if type(interactive) is not bool:
        raise TypeError("interactive must be boolean")
    if not isinstance(rules, tuple) or any(not isinstance(item, PolicyRule) for item in rules):
        raise TypeError("rules must be a tuple of PolicyRule")
    basis, _ = _basis(workspace, changeset)
    policy = _policy_records(changeset, interactive=interactive, rules=rules)
    return ChangeSetPermit(changeset.fingerprint, basis, _policy_fingerprint(policy))


def validate_changeset_permit(
    workspace: Path,
    changeset: NormalizedChangeSet,
    permit: ChangeSetPermit,
    *,
    interactive: bool,
    rules: Tuple[PolicyRule, ...] = (),
) -> None:
    if not isinstance(permit, ChangeSetPermit):
        raise TypeError("permit must be ChangeSetPermit")
    if permit.changeset_fingerprint != changeset.fingerprint:
        raise ValueError("permit changeset fingerprint mismatch")
    basis, _ = _basis(workspace, changeset)
    policy = _policy_records(changeset, interactive=interactive, rules=rules)
    if basis != permit.basis_fingerprint:
        raise ValueError("changeset permit basis changed")
    if _policy_fingerprint(policy) != permit.policy_fingerprint:
        raise ValueError("changeset permit policy changed")


def _staged_write(target: Path, text: str, mode: int) -> Path:
    fd, raw_path = tempfile.mkstemp(prefix=".loop42-stage-", dir=target.parent)
    staged = Path(raw_path)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(text.encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(staged, mode)
        return staged
    except BaseException:
        staged.unlink(missing_ok=True)
        raise


def _backup_name(target: Path) -> Path:
    fd, raw_path = tempfile.mkstemp(prefix=".loop42-backup-", dir=target.parent)
    os.close(fd)
    backup = Path(raw_path)
    backup.unlink()
    return backup


def _assert_target_basis(target: Path, item) -> tuple[str | None, int | None]:
    if item.before_sha256 is None:
        if target.exists() or target.is_symlink():
            raise ValueError(f"target changed immediately before create: {item.path}")
        return None, None
    text, mode = _read_regular_text(target, item.path)
    if sha256_text(text) != item.before_sha256:
        raise ValueError(f"target changed immediately before write: {item.path}")
    return text, mode


def apply_changeset(
    workspace: Path,
    changeset: NormalizedChangeSet,
    permit: ChangeSetPermit,
    *,
    interactive: bool,
    rules: Tuple[PolicyRule, ...] = (),
) -> ChangeSetReceipt:
    """Apply one normalized ChangeSet after immediate permit revalidation.

    Writes are staged and existing files are renamed to rollback backups before
    replacement/deletion. A normal exception triggers best-effort rollback. A hard
    process/host interruption still requires the generic side-effect reconciler.
    """
    root = _root(workspace)
    validate_changeset_permit(root, changeset, permit, interactive=interactive, rules=rules)

    staged: dict[str, Path] = {}
    backups: dict[str, Path] = {}
    applied: list[str] = []
    try:
        # Stage desired content before the first repository side effect.
        for item in changeset.files:
            target = _target(root, item.path)
            _before_text, mode = _assert_target_basis(target, item)
            if item.after_text is not None:
                staged[item.path] = _staged_write(target, item.after_text, mode if mode is not None else 0o644)

        # Recheck each exact target immediately before its own side effect.
        for item in changeset.files:
            target = _target(root, item.path)
            _assert_target_basis(target, item)
            if item.before_sha256 is not None:
                backup = _backup_name(target)
                os.replace(target, backup)
                backups[item.path] = backup
            if item.after_text is not None:
                os.replace(staged.pop(item.path), target)
            applied.append(item.path)

        # Verify exact desired state before discarding rollback backups.
        final_states = []
        for item in changeset.files:
            target = _target(root, item.path)
            if item.after_sha256 is None:
                if target.exists() or target.is_symlink():
                    raise ValueError(f"delete postcondition failed: {item.path}")
                final_states.append((item.path, "missing"))
            else:
                text, _mode = _read_regular_text(target, item.path)
                digest = sha256_text(text)
                if digest != item.after_sha256:
                    raise ValueError(f"write postcondition failed: {item.path}")
                final_states.append((item.path, digest))

        final_payload = "\n".join([changeset.fingerprint, *[f"{path}|{digest}" for path, digest in final_states]])
        receipt = ChangeSetReceipt(
            changeset_fingerprint=changeset.fingerprint,
            basis_fingerprint=permit.basis_fingerprint,
            final_fingerprint=hashlib.sha256(final_payload.encode("utf-8")).hexdigest(),
            files=tuple(
                AppliedFileReceipt(item.operation, item.path, item.before_sha256, item.after_sha256)
                for item in changeset.files
            ),
        )
        for backup in backups.values():
            backup.unlink(missing_ok=True)
        return receipt
    except BaseException:
        # Roll back process-visible failures. Hard interruption is reconciled later.
        for path in reversed(applied):
            item = next(entry for entry in changeset.files if entry.path == path)
            target = _target(root, path)
            if target.exists() and not target.is_symlink():
                target.unlink()
            backup = backups.get(path)
            if backup is not None and backup.exists():
                os.replace(backup, target)
        for path, backup in backups.items():
            if path not in applied and backup.exists():
                target = _target(root, path)
                if not target.exists():
                    os.replace(backup, target)
        raise
    finally:
        for path in staged.values():
            path.unlink(missing_ok=True)
