from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping, Sequence

_REVISION_RE = re.compile(r"[0-9a-f]{7,64}")
_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}")
_METRICS = {
    "routing",
    "repetition",
    "validation",
    "evidence_use",
    "answer_contract",
    "overhead",
}


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    return value


def _fields(
    value: Mapping[str, Any],
    required: set[str],
    name: str,
    optional: set[str] | None = None,
) -> None:
    optional = optional or set()
    missing = required - set(value)
    extra = set(value) - required - optional
    if missing:
        raise ValueError(f"{name} missing fields: {sorted(missing)}")
    if extra:
        raise ValueError(f"{name} has unexpected fields: {sorted(extra)}")


def _text(value: Any, name: str, maximum: int = 4000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{name} must be bounded non-empty text")
    return value


def _identifier(value: Any, name: str) -> str:
    value = _text(value, name, 256)
    if not _ID_RE.fullmatch(value):
        raise ValueError(f"{name} has invalid characters")
    return value


def _integer(value: Any, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def _boolean(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be boolean")
    return value


def _canonical(value: Any, name: str) -> str:
    try:
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be canonical JSON data") from exc
    if len(encoded.encode("utf-8")) > 16_384:
        raise ValueError(f"{name} exceeds 16384 UTF-8 bytes")
    return encoded


def _metric(status: str, **details: Any) -> dict[str, Any]:
    return {"status": status, **details}


def _scenario(raw: Mapping[str, Any]) -> dict[str, Any]:
    _fields(
        raw,
        {"schema", "scenario_id", "basis", "requirements"},
        "scenario",
        {"purpose", "fixture", "expected_boundary"},
    )
    if raw["schema"] != "loop42.agent-eval-scenario.v1":
        raise ValueError("unsupported scenario schema")

    basis = _mapping(raw["basis"], "scenario.basis")
    _fields(basis, {"kind", "loop42_revision"}, "scenario.basis")
    if basis["kind"] not in {"simulated_fixture", "captured_fixture"}:
        raise ValueError("unsupported scenario basis kind")
    revision = _text(basis["loop42_revision"], "scenario revision", 64)
    if not _REVISION_RE.fullmatch(revision):
        raise ValueError("scenario revision must be lowercase hex")

    req = _mapping(raw["requirements"], "scenario.requirements")
    _fields(
        req,
        {
            "first_capability",
            "capability_subsequence",
            "repeat_allowance",
            "max_input_validation_failures",
            "require_evidence_citation",
            "required_answer_term_groups",
            "required_metrics",
        },
        "scenario.requirements",
    )

    subsequence = req["capability_subsequence"]
    if not isinstance(subsequence, list) or not subsequence:
        raise ValueError("capability_subsequence must be a non-empty list")
    subsequence = tuple(_identifier(item, "capability") for item in subsequence)

    allowance = _mapping(req["repeat_allowance"], "repeat_allowance")
    allowance = {
        _identifier(key, "repeat capability"): _integer(value, "repeat allowance")
        for key, value in allowance.items()
    }

    groups = req["required_answer_term_groups"]
    if not isinstance(groups, list):
        raise ValueError("required_answer_term_groups must be a list")
    normalized_groups = []
    for group in groups:
        if not isinstance(group, list) or not group:
            raise ValueError("answer term groups must be non-empty lists")
        normalized_groups.append(tuple(_text(term, "answer term", 200) for term in group))

    required_metrics = req["required_metrics"]
    if (
        not isinstance(required_metrics, list)
        or not required_metrics
        or len(set(required_metrics)) != len(required_metrics)
        or any(metric not in _METRICS for metric in required_metrics)
    ):
        raise ValueError("required_metrics is invalid")

    return {
        "scenario_id": _identifier(raw["scenario_id"], "scenario_id"),
        "revision": revision,
        "first_capability": _identifier(req["first_capability"], "first_capability"),
        "subsequence": subsequence,
        "allowance": allowance,
        "max_invalid": _integer(
            req["max_input_validation_failures"], "max_input_validation_failures"
        ),
        "require_evidence": _boolean(
            req["require_evidence_citation"], "require_evidence_citation"
        ),
        "term_groups": tuple(normalized_groups),
        "required_metrics": tuple(required_metrics),
    }


def _transcript(raw: Mapping[str, Any]) -> dict[str, Any]:
    _fields(raw, {"schema", "basis", "capture_capabilities", "events"}, "transcript")
    if raw["schema"] != "loop42.agent-transcript.v1":
        raise ValueError("unsupported transcript schema")

    basis = _mapping(raw["basis"], "transcript.basis")
    _fields(
        basis,
        {"scenario_id", "loop42_revision", "harness_id", "harness_version", "model_id"},
        "transcript.basis",
    )
    revision = _text(basis["loop42_revision"], "transcript revision", 64)
    if not _REVISION_RE.fullmatch(revision):
        raise ValueError("transcript revision must be lowercase hex")
    model_id = basis["model_id"]
    if model_id is not None:
        model_id = _text(model_id, "model_id", 256)

    capture = _mapping(raw["capture_capabilities"], "capture_capabilities")
    _fields(
        capture,
        {"tool_calls", "tool_results", "final_answer", "token_usage"},
        "capture_capabilities",
    )
    capture = {key: _boolean(value, key) for key, value in capture.items()}

    events = raw["events"]
    if not isinstance(events, list) or len(events) > 1000:
        raise ValueError("events must contain at most 1000 items")

    calls = []
    results = []
    answers = []
    usages = []
    call_ids = set()

    for index, raw_event in enumerate(events):
        event = _mapping(raw_event, f"events[{index}]")
        kind = event.get("type")
        if kind == "tool_call":
            if not capture["tool_calls"]:
                raise ValueError("tool_call contradicts capture capabilities")
            _fields(event, {"type", "call_id", "capability", "arguments"}, "tool_call")
            call_id = _identifier(event["call_id"], "call_id")
            if call_id in call_ids:
                raise ValueError("tool call IDs must be unique")
            call_ids.add(call_id)
            arguments = _canonical(event["arguments"], "arguments")
            calls.append(
                {
                    "call_id": call_id,
                    "capability": _identifier(event["capability"], "capability"),
                    "arguments_sha256": hashlib.sha256(arguments.encode()).hexdigest(),
                }
            )
        elif kind == "tool_result":
            if not capture["tool_results"]:
                raise ValueError("tool_result contradicts capture capabilities")
            _fields(
                event,
                {"type", "call_id", "status", "evidence_ids"},
                "tool_result",
                {"error_code"},
            )
            if event["status"] not in {"success", "error", "unavailable"}:
                raise ValueError("unsupported tool result status")
            evidence_ids = event["evidence_ids"]
            if not isinstance(evidence_ids, list):
                raise ValueError("evidence_ids must be a list")
            evidence_ids = tuple(_identifier(item, "evidence_id") for item in evidence_ids)
            if len(set(evidence_ids)) != len(evidence_ids):
                raise ValueError("evidence_ids must be unique")
            error_code = event.get("error_code")
            if error_code is not None:
                error_code = _identifier(error_code, "error_code")
            results.append(
                {
                    "call_id": _identifier(event["call_id"], "call_id"),
                    "status": event["status"],
                    "evidence_ids": evidence_ids,
                    "error_code": error_code,
                }
            )
        elif kind == "final_answer":
            if not capture["final_answer"]:
                raise ValueError("final_answer contradicts capture capabilities")
            _fields(event, {"type", "text"}, "final_answer")
            answers.append(_text(event["text"], "final answer", 50_000))
        elif kind == "usage":
            if not capture["token_usage"]:
                raise ValueError("usage contradicts capture capabilities")
            _fields(
                event,
                {"type", "input_tokens", "output_tokens"},
                "usage",
                {"cached_input_tokens"},
            )
            usages.append(
                {
                    "input_tokens": _integer(event["input_tokens"], "input_tokens"),
                    "output_tokens": _integer(event["output_tokens"], "output_tokens"),
                    "cached_input_tokens": _integer(
                        event.get("cached_input_tokens", 0), "cached_input_tokens"
                    ),
                }
            )
        else:
            raise ValueError(f"unsupported event type at index {index}")

    if capture["final_answer"] and len(answers) != 1:
        raise ValueError("captured transcript requires exactly one final answer")
    if capture["token_usage"] and len(usages) != 1:
        raise ValueError("captured transcript requires exactly one usage event")
    if capture["tool_results"]:
        if any(result["call_id"] not in call_ids for result in results):
            raise ValueError("tool result references an uncaptured call")
        result_ids = [result["call_id"] for result in results]
        if len(result_ids) != len(set(result_ids)):
            raise ValueError("captured tool results must be unique per call")
        missing_results = call_ids - set(result_ids)
        if missing_results:
            raise ValueError(
                f"captured tool calls missing results: {sorted(missing_results)}"
            )

    return {
        "basis": {
            "scenario_id": _identifier(basis["scenario_id"], "scenario_id"),
            "loop42_revision": revision,
            "harness_id": _identifier(basis["harness_id"], "harness_id"),
            "harness_version": _text(basis["harness_version"], "harness_version", 256),
            "model_id": model_id,
        },
        "capture": capture,
        "calls": tuple(calls),
        "results": tuple(results),
        "answer": answers[0] if answers else None,
        "usage": usages[0] if usages else None,
    }


def _subsequence(values: Sequence[str], required: Sequence[str]) -> bool:
    index = 0
    for value in values:
        if index < len(required) and value == required[index]:
            index += 1
    return index == len(required)


def evaluate_agent_transcript(
    transcript: Mapping[str, Any],
    scenario: Mapping[str, Any],
) -> dict[str, Any]:
    """Score one captured agent run; the report never grants execution authority."""

    sc = _scenario(_mapping(scenario, "scenario"))
    tr = _transcript(_mapping(transcript, "transcript"))
    basis_match = (
        tr["basis"]["scenario_id"] == sc["scenario_id"]
        and tr["basis"]["loop42_revision"] == sc["revision"]
    )
    metrics: dict[str, dict[str, Any]] = {}

    if tr["capture"]["tool_calls"]:
        capabilities = [call["capability"] for call in tr["calls"]]
        ok = (
            bool(capabilities)
            and capabilities[0] == sc["first_capability"]
            and _subsequence(capabilities, sc["subsequence"])
        )
        metrics["routing"] = _metric(
            "PASS" if ok else "FAIL",
            first_capability=capabilities[0] if capabilities else None,
            capability_sequence=capabilities,
        )

        signatures: dict[tuple[str, str], int] = {}
        for call in tr["calls"]:
            key = (call["capability"], call["arguments_sha256"])
            signatures[key] = signatures.get(key, 0) + 1
        details = []
        disallowed = 0
        for (capability, digest), count in sorted(signatures.items()):
            extras = max(0, count - 1)
            allowed = sc["allowance"].get(capability, 0)
            excess = max(0, extras - allowed)
            if extras:
                details.append(
                    {
                        "capability": capability,
                        "arguments_sha256": digest,
                        "extra_calls": extras,
                        "allowed_extra_calls": allowed,
                        "excess_extra_calls": excess,
                    }
                )
            disallowed += excess
        metrics["repetition"] = _metric(
            "PASS" if disallowed == 0 else "FAIL",
            disallowed_extra_calls=disallowed,
            repeated_signatures=details,
        )
    else:
        metrics["routing"] = _metric("UNKNOWN", reason="tool_calls_not_captured")
        metrics["repetition"] = _metric("UNKNOWN", reason="tool_calls_not_captured")

    if tr["capture"]["tool_results"]:
        invalid = sum(
            result["error_code"] == "invalid_request" for result in tr["results"]
        )
        metrics["validation"] = _metric(
            "PASS" if invalid <= sc["max_invalid"] else "FAIL",
            input_validation_failures=invalid,
            allowed=sc["max_invalid"],
        )
    else:
        metrics["validation"] = _metric("UNKNOWN", reason="tool_results_not_captured")

    if not sc["require_evidence"]:
        metrics["evidence_use"] = _metric("PASS", required=False)
    elif not tr["capture"]["tool_results"] or not tr["capture"]["final_answer"]:
        metrics["evidence_use"] = _metric(
            "UNKNOWN", reason="evidence_or_final_answer_not_captured"
        )
    else:
        evidence_ids = sorted(
            {
                evidence_id
                for result in tr["results"]
                for evidence_id in result["evidence_ids"]
            }
        )
        cited = [
            evidence_id
            for evidence_id in evidence_ids
            if evidence_id in (tr["answer"] or "")
        ]
        metrics["evidence_use"] = _metric(
            "PASS" if cited else "FAIL",
            produced_evidence_ids=evidence_ids,
            cited_evidence_ids=cited,
        )

    if tr["capture"]["final_answer"]:
        normalized = (tr["answer"] or "").casefold()
        missing = [
            list(group)
            for group in sc["term_groups"]
            if not any(term.casefold() in normalized for term in group)
        ]
        metrics["answer_contract"] = _metric(
            "PASS" if not missing else "FAIL",
            missing_term_groups=missing,
        )
    else:
        metrics["answer_contract"] = _metric(
            "UNKNOWN", reason="final_answer_not_captured"
        )

    if tr["capture"]["token_usage"]:
        usage = tr["usage"]
        metrics["overhead"] = _metric(
            "PASS",
            tool_calls=len(tr["calls"]) if tr["capture"]["tool_calls"] else None,
            input_tokens=usage["input_tokens"],
            cached_input_tokens=usage["cached_input_tokens"],
            output_tokens=usage["output_tokens"],
        )
    else:
        metrics["overhead"] = _metric(
            "UNKNOWN",
            reason="token_usage_not_captured",
            tool_calls=len(tr["calls"]) if tr["capture"]["tool_calls"] else None,
        )

    statuses = [metrics[name]["status"] for name in sc["required_metrics"]]
    if not basis_match or "FAIL" in statuses:
        verdict = "FAIL"
    elif "UNKNOWN" in statuses:
        verdict = "UNKNOWN"
    else:
        verdict = "PASS"

    return {
        "schema": "loop42.agent-eval-report.v1",
        "scenario_id": sc["scenario_id"],
        "basis_match": basis_match,
        "evaluated_basis": tr["basis"],
        "required_metrics": list(sc["required_metrics"]),
        "metrics": metrics,
        "verdict": verdict,
        "authority": "evaluation_evidence_only",
    }
