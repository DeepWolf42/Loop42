#!/usr/bin/env python3
"""JSON CLI for Loop42's pure worker-dispatch reconciliation contract.

This adapter boundary performs no queue writes, process control, model calls, or
other side effects. Provider/OS/Drive adapters translate their observations to
this schema, then call the canonical worker_dispatch functions.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
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

SCHEMA = "loop42.worker-dispatch-cli.v1"
MAX_INPUT_BYTES = 1024 * 1024


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant: {value}")


def _load_json(raw: bytes) -> dict[str, Any]:
    if not raw or len(raw) > MAX_INPUT_BYTES:
        raise ValueError("input must be between 1 byte and 1 MiB")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("input must be valid UTF-8 JSON") from error
    if not isinstance(value, dict):
        raise ValueError("request must be a JSON object")
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


def _task(value: Any, where: str = "task") -> DispatchTask:
    if not isinstance(value, dict):
        raise ValueError(f"{where} must be an object")
    _expect_keys(
        value,
        required={
            "task_id",
            "attempt_id",
            "source_revision",
            "context_fingerprint",
            "acceptance_criteria",
        },
        where=where,
    )
    criteria = value["acceptance_criteria"]
    if not isinstance(criteria, list):
        raise ValueError(f"{where}.acceptance_criteria must be an array")
    return DispatchTask(
        value["task_id"],
        value["attempt_id"],
        value["source_revision"],
        value["context_fingerprint"],
        tuple(criteria),
    )


def _session(value: Any, index: int) -> WorkerSession:
    where = f"observation.worker_sessions[{index}]"
    if not isinstance(value, dict):
        raise ValueError(f"{where} must be an object")
    _expect_keys(
        value,
        required={"session_id"},
        optional={"task_id", "attempt_id", "progress_seq", "progress_at"},
        where=where,
    )
    return WorkerSession(
        session_id=value["session_id"],
        task_id=value.get("task_id"),
        attempt_id=value.get("attempt_id"),
        progress_seq=value.get("progress_seq"),
        progress_at=(
            _timestamp(value["progress_at"], f"{where}.progress_at")
            if value.get("progress_at") is not None
            else None
        ),
    )


def _observation(value: Any) -> HostObservation | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("observation must be an object or null")
    _expect_keys(
        value,
        required={"observed_at", "session_id", "reachable"},
        optional={"worker_sessions", "safety_stop"},
        where="observation",
    )
    sessions = value.get("worker_sessions", [])
    if not isinstance(sessions, list):
        raise ValueError("observation.worker_sessions must be an array")
    return HostObservation(
        observed_at=_timestamp(value["observed_at"], "observation.observed_at"),
        session_id=value["session_id"],
        reachable=value["reachable"],
        worker_sessions=tuple(_session(item, i) for i, item in enumerate(sessions)),
        safety_stop=value.get("safety_stop", False),
    )


def _artifact(value: Any, index: int) -> AttemptArtifact:
    where = f"artifacts[{index}]"
    if not isinstance(value, dict):
        raise ValueError(f"{where} must be an object")
    _expect_keys(
        value,
        required={
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
    try:
        kind = ArtifactKind(value["kind"])
    except (TypeError, ValueError) as error:
        raise ValueError(f"{where}.kind is invalid") from error
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


def _artifacts(value: Any) -> tuple[AttemptArtifact, ...]:
    if not isinstance(value, list):
        raise ValueError("artifacts must be an array")
    return tuple(_artifact(item, i) for i, item in enumerate(value))


def _permit(value: Any) -> DispatchPermit:
    if not isinstance(value, dict):
        raise ValueError("permit must be an object")
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


def _state(value: ReconciledState) -> dict[str, Any]:
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


def _permit_json(value: DispatchPermit | None) -> dict[str, str] | None:
    if value is None:
        return None
    return {
        "task_id": value.task_id,
        "attempt_id": value.attempt_id,
        "source_revision": value.source_revision,
        "context_fingerprint": value.context_fingerprint,
        "basis_fingerprint": value.basis_fingerprint,
    }


def _common(request: dict[str, Any]) -> tuple[
    datetime,
    HostObservation | None,
    tuple[AttemptArtifact, ...],
    int,
    int | None,
]:
    now = _timestamp(request["now"], "now")
    observation = _observation(request["observation"])
    artifacts = _artifacts(request["artifacts"])
    freshness = request.get("freshness_seconds", 300)
    stall = request.get("stall_seconds")
    if not isinstance(freshness, int) or isinstance(freshness, bool):
        raise ValueError("freshness_seconds must be an integer")
    if stall is not None and (not isinstance(stall, int) or isinstance(stall, bool)):
        raise ValueError("stall_seconds must be an integer or null")
    return now, observation, artifacts, freshness, stall


def run_request(request: dict[str, Any]) -> dict[str, Any]:
    if request.get("schema") != SCHEMA:
        raise ValueError(f"schema must be {SCHEMA}")
    operation = request.get("operation")
    common_required = {"schema", "operation", "now", "observation", "artifacts"}
    common_optional = {"freshness_seconds", "stall_seconds"}

    if operation == "reconcile":
        _expect_keys(
            request,
            required=common_required | {"expected"},
            optional=common_optional,
            where="request",
        )
        now, observation, artifacts, freshness, stall = _common(request)
        expected = None if request["expected"] is None else _task(request["expected"], "expected")
        state = reconcile_worker(
            now=now,
            observation=observation,
            artifacts=artifacts,
            expected=expected,
            freshness_seconds=freshness,
            stall_seconds=stall,
        )
        return {"schema": SCHEMA, "operation": operation, "state": _state(state)}

    if operation == "issue-permit":
        _expect_keys(
            request,
            required=common_required | {"task"},
            optional=common_optional,
            where="request",
        )
        now, observation, artifacts, freshness, stall = _common(request)
        task = _task(request["task"])
        permit = issue_dispatch_permit(
            task=task,
            now=now,
            observation=observation,
            artifacts=artifacts,
            freshness_seconds=freshness,
            stall_seconds=stall,
        )
        return {"schema": SCHEMA, "operation": operation, "permit": _permit_json(permit)}

    if operation == "validate-permit":
        _expect_keys(
            request,
            required=common_required | {"task", "permit"},
            optional=common_optional,
            where="request",
        )
        now, observation, artifacts, freshness, stall = _common(request)
        task = _task(request["task"])
        valid = validate_dispatch_permit(
            _permit(request["permit"]),
            task=task,
            now=now,
            observation=observation,
            artifacts=artifacts,
            freshness_seconds=freshness,
            stall_seconds=stall,
        )
        return {"schema": SCHEMA, "operation": operation, "valid": valid}

    raise ValueError("operation must be reconcile, issue-permit, or validate-permit")


def _read_input(path: str) -> bytes:
    if path == "-":
        return sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    with Path(path).open("rb") as stream:
        return stream.read(MAX_INPUT_BYTES + 1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        default="-",
        help="request JSON path, or - for stdin (default)",
    )
    args = parser.parse_args()
    try:
        request = _load_json(_read_input(args.input))
        response = run_request(request)
        print(json.dumps(response, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except (OSError, TypeError, ValueError) as error:
        print(f"worker dispatch: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
