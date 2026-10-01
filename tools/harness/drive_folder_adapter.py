#!/usr/bin/env python3
"""Thin filesystem/Google-Drive-sync adapter for Loop42 worker evidence.

The adapter treats a local synced folder as a provider surface. It never starts
or stops a worker/model. Queue writes are allowed only through an already issued
DispatchPermit that is revalidated against a fresh rescan immediately before an
atomic local file write.

Legacy markdown/text jobs remain visible diagnostics only. They are never
silently upgraded to modern task identity and never become retry permission.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from typing import Any

from tools.harness.worker_dispatch import (
    ArtifactKind,
    AttemptArtifact,
    DispatchPermit,
    DispatchTask,
    HostObservation,
    ReconciledState,
    WorkerSession,
    issue_dispatch_permit,
    reconcile_worker,
    validate_dispatch_permit,
)


TASK_SCHEMA = "loop42.drive-task.v1"
HOST_SCHEMA = "loop42.drive-host-state.v1"
ARTIFACT_SCHEMA = "loop42.drive-artifact.v1"
SNAPSHOT_SCHEMA = "loop42.drive-folder-snapshot.v1"
LEGACY_SCHEMA = "loop42.drive-legacy-reconciliation.v1"

INBOX = "00_Inbox"
RESULTS = "10_Results"
LOGS = "90_Logs"
ERRORS = "95_Error"
ARCHIVE = "99_Archive"
HOST_STATE_FILE = "loop42-host-state.json"
REQUIRED_SURFACES = (INBOX, RESULTS, LOGS, ERRORS, ARCHIVE)
MAX_JSON_BYTES = 1024 * 1024


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant: {value}")


def _load_json_file(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    if not raw or len(raw) > MAX_JSON_BYTES:
        raise ValueError(f"{path.name}: JSON must be between 1 byte and 1 MiB")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{path.name}: invalid UTF-8 JSON") from error
    if not isinstance(value, dict):
        raise ValueError(f"{path.name}: root must be a JSON object")
    return value


def _expect_keys(
    value: dict[str, Any],
    *,
    required: set[str],
    optional: set[str] = frozenset(),
    where: str,
) -> None:
    missing = required - set(value)
    extra = set(value) - required - optional
    if missing:
        raise ValueError(f"{where} missing fields: {', '.join(sorted(missing))}")
    if extra:
        raise ValueError(f"{where} unexpected fields: {', '.join(sorted(extra))}")


def _timestamp(value: Any, where: str) -> datetime:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{where} must be an ISO-8601 timestamp")
    rendered = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(rendered)
    except ValueError as error:
        raise ValueError(f"{where} must be an ISO-8601 timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{where} must include a timezone offset")
    return parsed


def _iso(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat()


def _task_payload(task: DispatchTask) -> dict[str, Any]:
    return {
        "task_id": task.task_id,
        "attempt_id": task.attempt_id,
        "source_revision": task.source_revision,
        "context_fingerprint": task.context_fingerprint,
        "acceptance_criteria": list(task.acceptance_criteria),
    }


def _task_manifest(value: dict[str, Any], where: str) -> tuple[DispatchTask, datetime]:
    _expect_keys(
        value,
        required={
            "schema",
            "task_id",
            "attempt_id",
            "source_revision",
            "context_fingerprint",
            "acceptance_criteria",
            "observed_at",
        },
        where=where,
    )
    if value["schema"] != TASK_SCHEMA:
        raise ValueError(f"{where}.schema must be {TASK_SCHEMA}")
    criteria = value["acceptance_criteria"]
    if not isinstance(criteria, list):
        raise ValueError(f"{where}.acceptance_criteria must be an array")
    return (
        DispatchTask(
            value["task_id"],
            value["attempt_id"],
            value["source_revision"],
            value["context_fingerprint"],
            tuple(criteria),
        ),
        _timestamp(value["observed_at"], f"{where}.observed_at"),
    )


def load_task_manifest(path: Path) -> tuple[DispatchTask, datetime, dict[str, Any]]:
    value = _load_json_file(path)
    task, observed_at = _task_manifest(value, path.name)
    return task, observed_at, value


def _session(value: Any, index: int, where: str) -> WorkerSession:
    item_where = f"{where}.worker_sessions[{index}]"
    if not isinstance(value, dict):
        raise ValueError(f"{item_where} must be an object")
    _expect_keys(
        value,
        required={"session_id"},
        optional={"task_id", "attempt_id", "progress_seq", "progress_at"},
        where=item_where,
    )
    return WorkerSession(
        session_id=value["session_id"],
        task_id=value.get("task_id"),
        attempt_id=value.get("attempt_id"),
        progress_seq=value.get("progress_seq"),
        progress_at=(
            _timestamp(value["progress_at"], f"{item_where}.progress_at")
            if value.get("progress_at") is not None
            else None
        ),
    )


def _host_observation(value: dict[str, Any], where: str) -> HostObservation:
    _expect_keys(
        value,
        required={"schema", "observed_at", "session_id", "reachable"},
        optional={"worker_sessions", "safety_stop"},
        where=where,
    )
    if value["schema"] != HOST_SCHEMA:
        raise ValueError(f"{where}.schema must be {HOST_SCHEMA}")
    sessions = value.get("worker_sessions", [])
    if not isinstance(sessions, list):
        raise ValueError(f"{where}.worker_sessions must be an array")
    return HostObservation(
        observed_at=_timestamp(value["observed_at"], f"{where}.observed_at"),
        session_id=value["session_id"],
        reachable=value["reachable"],
        worker_sessions=tuple(
            _session(item, index, where) for index, item in enumerate(sessions)
        ),
        safety_stop=value.get("safety_stop", False),
    )


def _artifact(
    value: dict[str, Any],
    *,
    where: str,
    required_kind: ArtifactKind,
) -> AttemptArtifact:
    _expect_keys(
        value,
        required={
            "schema",
            "kind",
            "task_id",
            "attempt_id",
            "source_revision",
            "context_fingerprint",
            "observed_at",
        },
        optional={"complete", "valid", "success", "receipt_fingerprint"},
        where=where,
    )
    if value["schema"] != ARTIFACT_SCHEMA:
        raise ValueError(f"{where}.schema must be {ARTIFACT_SCHEMA}")
    try:
        kind = ArtifactKind(value["kind"])
    except (TypeError, ValueError) as error:
        raise ValueError(f"{where}.kind is invalid") from error
    if kind is not required_kind:
        raise ValueError(
            f"{where}.kind must be {required_kind.value} on this provider surface"
        )
    if kind is ArtifactKind.RESULT and not value.get("receipt_fingerprint"):
        raise ValueError(f"{where}: RESULT requires receipt_fingerprint")
    return AttemptArtifact(
        kind=kind,
        task_id=value["task_id"],
        attempt_id=value["attempt_id"],
        source_revision=value["source_revision"],
        context_fingerprint=value["context_fingerprint"],
        observed_at=_timestamp(value["observed_at"], f"{where}.observed_at"),
        complete=value.get("complete", True),
        valid=value.get("valid", True),
        success=value.get("success"),
        receipt_fingerprint=value.get("receipt_fingerprint"),
    )


def _observation_json(value: HostObservation | None) -> dict[str, Any] | None:
    if value is None:
        return None
    return {
        "observed_at": _iso(value.observed_at),
        "session_id": value.session_id,
        "reachable": value.reachable,
        "safety_stop": value.safety_stop,
        "worker_sessions": [
            {
                "session_id": item.session_id,
                **({"task_id": item.task_id, "attempt_id": item.attempt_id}
                   if item.task_id is not None else {}),
                **({"progress_seq": item.progress_seq}
                   if item.progress_seq is not None else {}),
                **({"progress_at": _iso(item.progress_at)}
                   if item.progress_at is not None else {}),
            }
            for item in value.worker_sessions
        ],
    }


def _artifact_json(value: AttemptArtifact) -> dict[str, Any]:
    result: dict[str, Any] = {
        "kind": value.kind.value,
        "task_id": value.task_id,
        "attempt_id": value.attempt_id,
        "source_revision": value.source_revision,
        "context_fingerprint": value.context_fingerprint,
        "observed_at": _iso(value.observed_at),
        "complete": value.complete,
        "valid": value.valid,
    }
    if value.success is not None:
        result["success"] = value.success
    if value.receipt_fingerprint is not None:
        result["receipt_fingerprint"] = value.receipt_fingerprint
    return result


@dataclass(frozen=True)
class FolderSnapshot:
    root: Path
    observation: HostObservation | None
    tasks: tuple[DispatchTask, ...]
    artifacts: tuple[AttemptArtifact, ...]
    legacy_files: tuple[tuple[str, str], ...]
    missing_surfaces: tuple[str, ...]
    errors: tuple[str, ...]

    @property
    def dispatch_blockers(self) -> tuple[str, ...]:
        blockers: list[str] = []
        if self.missing_surfaces:
            blockers.append("provider_surface_missing")
        if self.errors:
            blockers.append("provider_evidence_invalid")
        if self.legacy_files:
            blockers.append("legacy_evidence_requires_reconciliation")
        return tuple(blockers)


def _surface_files(root: Path, surface: str) -> list[Path]:
    path = root / surface
    if not path.is_dir():
        return []
    return sorted((item for item in path.iterdir() if item.is_file()), key=lambda p: p.name)


def scan_root(root: Path) -> FolderSnapshot:
    root = root.expanduser()
    if not root.is_dir():
        raise ValueError("Drive root must be an existing directory")

    missing = tuple(surface for surface in REQUIRED_SURFACES if not (root / surface).is_dir())
    errors: list[str] = []
    legacy: list[tuple[str, str]] = []
    tasks: list[DispatchTask] = []
    artifacts: list[AttemptArtifact] = []

    observation = None
    host_path = root / LOGS / HOST_STATE_FILE
    if host_path.is_file():
        try:
            observation = _host_observation(_load_json_file(host_path), HOST_STATE_FILE)
        except (OSError, TypeError, ValueError) as error:
            errors.append(str(error))

    for path in _surface_files(root, INBOX):
        if path.name.endswith(".task.json"):
            try:
                task, observed_at, _ = load_task_manifest(path)
                tasks.append(task)
                artifacts.append(
                    AttemptArtifact(
                        kind=ArtifactKind.QUEUED,
                        task_id=task.task_id,
                        attempt_id=task.attempt_id,
                        source_revision=task.source_revision,
                        context_fingerprint=task.context_fingerprint,
                        observed_at=observed_at,
                    )
                )
            except (OSError, TypeError, ValueError) as error:
                errors.append(str(error))
        elif path.suffix.lower() in {".md", ".txt"}:
            legacy.append((INBOX, path.name))

    surfaces = (
        (RESULTS, ".result.json", ArtifactKind.RESULT),
        (ERRORS, ".error.json", ArtifactKind.ERROR),
        (ARCHIVE, ".archive.json", ArtifactKind.ARCHIVED),
    )
    for surface, suffix, kind in surfaces:
        for path in _surface_files(root, surface):
            if path.name.endswith(suffix):
                try:
                    artifacts.append(
                        _artifact(
                            _load_json_file(path),
                            where=path.name,
                            required_kind=kind,
                        )
                    )
                except (OSError, TypeError, ValueError) as error:
                    errors.append(str(error))
            elif path.suffix.lower() in {".md", ".txt"}:
                legacy.append((surface, path.name))

    return FolderSnapshot(
        root=root,
        observation=observation,
        tasks=tuple(tasks),
        artifacts=tuple(artifacts),
        legacy_files=tuple(sorted(legacy)),
        missing_surfaces=missing,
        errors=tuple(errors),
    )


def snapshot_json(snapshot: FolderSnapshot) -> dict[str, Any]:
    return {
        "schema": SNAPSHOT_SCHEMA,
        "root": str(snapshot.root),
        "observation": _observation_json(snapshot.observation),
        "tasks": [_task_payload(item) for item in snapshot.tasks],
        "artifacts": [_artifact_json(item) for item in snapshot.artifacts],
        "legacy_files": [
            {"surface": surface, "name": name}
            for surface, name in snapshot.legacy_files
        ],
        "missing_surfaces": list(snapshot.missing_surfaces),
        "errors": list(snapshot.errors),
        "dispatch_blockers": list(snapshot.dispatch_blockers),
    }


def _state_json(value: ReconciledState) -> dict[str, Any]:
    return {
        "host": value.host.value,
        "worker": value.worker.value,
        "lifecycle": value.lifecycle.value,
        "freshness": value.freshness.value,
        "can_dispatch": value.can_dispatch,
        "reasons": list(value.reasons),
        "outstanding": [list(item) for item in value.outstanding],
        "late_results": [list(item) for item in value.late_results],
        "result_receipt": value.result_receipt,
    }


def reconcile_modern(
    snapshot: FolderSnapshot,
    task: DispatchTask,
    *,
    now: datetime,
    freshness_seconds: int = 300,
    stall_seconds: int | None = None,
) -> dict[str, Any]:
    state = reconcile_worker(
        now=now,
        observation=snapshot.observation,
        artifacts=snapshot.artifacts,
        expected=task,
        freshness_seconds=freshness_seconds,
        stall_seconds=stall_seconds,
    )
    return {
        "schema": SNAPSHOT_SCHEMA,
        "operation": "reconcile",
        "state": _state_json(state),
        "provider_blockers": list(snapshot.dispatch_blockers),
    }


def legacy_reconcile(snapshot: FolderSnapshot, legacy_name: str) -> dict[str, Any]:
    if not isinstance(legacy_name, str) or not legacy_name.strip():
        raise ValueError("legacy_name must be non-empty")
    stem = Path(legacy_name).stem
    matches = [
        (surface, name)
        for surface, name in snapshot.legacy_files
        if stem in Path(name).stem
    ]
    surfaces = {surface for surface, _ in matches}
    reasons: list[str] = []
    if INBOX in surfaces:
        reasons.append("legacy_task_present")
    if RESULTS in surfaces:
        reasons.append("legacy_result_candidate_present")
    if ERRORS in surfaces:
        reasons.append("legacy_error_candidate_present")
    if ARCHIVE in surfaces:
        reasons.append("legacy_archive_candidate_present")
    if not matches:
        reasons.append("legacy_evidence_absent")
    reasons.extend(
        (
            "structured_identity_missing",
            "terminal_identity_unverifiable",
            "blind_retry_forbidden",
        )
    )
    if surfaces == {INBOX}:
        reasons.append("terminal_evidence_absent")
    return {
        "schema": LEGACY_SCHEMA,
        "legacy_name": legacy_name,
        "state": "unknown",
        "can_retry": False,
        "can_dispatch_replacement": False,
        "requires_operator_reconciliation": True,
        "matches": [
            {"surface": surface, "name": name} for surface, name in matches
        ],
        "reasons": reasons,
    }


def issue_provider_permit(
    snapshot: FolderSnapshot,
    task: DispatchTask,
    *,
    now: datetime,
    freshness_seconds: int = 300,
    stall_seconds: int | None = None,
) -> tuple[DispatchPermit | None, tuple[str, ...]]:
    if snapshot.dispatch_blockers:
        return None, snapshot.dispatch_blockers
    permit = issue_dispatch_permit(
        task=task,
        now=now,
        observation=snapshot.observation,
        artifacts=snapshot.artifacts,
        freshness_seconds=freshness_seconds,
        stall_seconds=stall_seconds,
    )
    if permit is None:
        return None, ("canonical_dispatch_not_permitted",)
    return permit, ()


def _permit_json(value: DispatchPermit | None) -> dict[str, Any] | None:
    if value is None:
        return None
    return {
        "task_id": value.task_id,
        "attempt_id": value.attempt_id,
        "source_revision": value.source_revision,
        "context_fingerprint": value.context_fingerprint,
        "basis_fingerprint": value.basis_fingerprint,
    }


def _permit_from_json(value: dict[str, Any]) -> DispatchPermit:
    _expect_keys(
        value,
        required={
            "task_id",
            "attempt_id",
            "source_revision",
            "context_fingerprint",
            "basis_fingerprint",
        },
        where="permit",
    )
    return DispatchPermit(
        task_id=value["task_id"],
        attempt_id=value["attempt_id"],
        source_revision=value["source_revision"],
        context_fingerprint=value["context_fingerprint"],
        basis_fingerprint=value["basis_fingerprint"],
    )


def enqueue_with_permit(
    root: Path,
    task_manifest_path: Path,
    permit: DispatchPermit,
    *,
    now: datetime,
    freshness_seconds: int = 300,
    stall_seconds: int | None = None,
) -> Path:
    task, _observed_at, manifest = load_task_manifest(task_manifest_path)
    snapshot = scan_root(root)
    if snapshot.dispatch_blockers:
        raise ValueError(
            "provider dispatch blocked: " + ",".join(snapshot.dispatch_blockers)
        )
    if not validate_dispatch_permit(
        permit,
        task=task,
        now=now,
        observation=snapshot.observation,
        artifacts=snapshot.artifacts,
        freshness_seconds=freshness_seconds,
        stall_seconds=stall_seconds,
    ):
        raise ValueError("dispatch permit no longer matches fresh provider evidence")

    target = root / INBOX / f"{task.task_id}__{task.attempt_id}.task.json"
    if target.exists():
        raise ValueError("target queue manifest already exists")

    rendered = (
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")
    temp = target.with_name(f".{target.name}.tmp-{os.getpid()}")
    try:
        with temp.open("xb") as stream:
            stream.write(rendered)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, target)
    finally:
        if temp.exists():
            temp.unlink()

    # Re-read what was written so a local encoding/serialization failure does
    # not masquerade as a queued task. Cloud-sync completion remains provider
    # evidence and is intentionally not inferred here.
    written_task, _written_at, _ = load_task_manifest(target)
    if written_task != task:
        raise ValueError("written queue manifest does not match requested task")
    return target


def _now(value: str | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    return _timestamp(value, "now")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--now")
    parser.add_argument("--freshness-seconds", type=int, default=300)
    parser.add_argument("--stall-seconds", type=int)
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("snapshot")

    legacy = commands.add_parser("legacy-reconcile")
    legacy.add_argument("--name", required=True)

    reconcile = commands.add_parser("reconcile")
    reconcile.add_argument("--task", type=Path, required=True)

    issue = commands.add_parser("issue-permit")
    issue.add_argument("--task", type=Path, required=True)

    validate = commands.add_parser("validate-permit")
    validate.add_argument("--task", type=Path, required=True)
    validate.add_argument("--permit", type=Path, required=True)

    enqueue = commands.add_parser("enqueue")
    enqueue.add_argument("--task", type=Path, required=True)
    enqueue.add_argument("--permit", type=Path, required=True)

    args = parser.parse_args()
    try:
        now = _now(args.now)
        snapshot = scan_root(args.root)

        if args.command == "snapshot":
            output = snapshot_json(snapshot)
        elif args.command == "legacy-reconcile":
            output = legacy_reconcile(snapshot, args.name)
        elif args.command == "reconcile":
            task, _observed_at, _manifest = load_task_manifest(args.task)
            output = reconcile_modern(
                snapshot,
                task,
                now=now,
                freshness_seconds=args.freshness_seconds,
                stall_seconds=args.stall_seconds,
            )
        elif args.command == "issue-permit":
            task, _observed_at, _manifest = load_task_manifest(args.task)
            permit, reasons = issue_provider_permit(
                snapshot,
                task,
                now=now,
                freshness_seconds=args.freshness_seconds,
                stall_seconds=args.stall_seconds,
            )
            output = {
                "schema": SNAPSHOT_SCHEMA,
                "operation": "issue-permit",
                "permit": _permit_json(permit),
                "reasons": list(reasons),
            }
        else:
            task, _observed_at, _manifest = load_task_manifest(args.task)
            permit = _permit_from_json(_load_json_file(args.permit))
            if args.command == "validate-permit":
                valid = (
                    not snapshot.dispatch_blockers
                    and validate_dispatch_permit(
                        permit,
                        task=task,
                        now=now,
                        observation=snapshot.observation,
                        artifacts=snapshot.artifacts,
                        freshness_seconds=args.freshness_seconds,
                        stall_seconds=args.stall_seconds,
                    )
                )
                output = {
                    "schema": SNAPSHOT_SCHEMA,
                    "operation": "validate-permit",
                    "valid": bool(valid),
                    "provider_blockers": list(snapshot.dispatch_blockers),
                }
            elif args.command == "enqueue":
                target = enqueue_with_permit(
                    args.root,
                    args.task,
                    permit,
                    now=now,
                    freshness_seconds=args.freshness_seconds,
                    stall_seconds=args.stall_seconds,
                )
                output = {
                    "schema": SNAPSHOT_SCHEMA,
                    "operation": "enqueue",
                    "queued_path": str(target),
                    "cloud_sync_confirmed": False,
                    "authority": (
                        "local queue write only; caller owns approval and cloud-sync/"
                        "worker execution authority"
                    ),
                }
            else:
                raise ValueError("unsupported command")

        print(json.dumps(output, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except (OSError, TypeError, ValueError) as error:
        print(f"drive folder adapter: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
