"""Opt-in, read-only comparison of a proposed supplemental agent lesson.

The input is untrusted externally supplied evidence metadata. A promising
result is a review candidate, not a verification receipt or adoption permit.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping

_SHA = re.compile(r"[0-9a-f]{64}\Z")
_REV = re.compile(r"[0-9a-f]{40}\Z")
_STATES = {"PASS", "FAIL", "UNKNOWN"}


@dataclass(frozen=True)
class TrialDecision:
    status: str  # PROMISING / REJECT / INCONCLUSIVE
    reason: str
    improved: int
    regressed: int
    preserved_holdouts: int


def _object(value: Any, fields: set[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError(f"{label}: expected exact fields {sorted(fields)}")
    return value


def _hex(value: Any, pattern: re.Pattern[str], label: str) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        raise ValueError(f"{label}: invalid identifier")
    return value


def _name(value: Any, label: str) -> str:
    if not isinstance(value, str) or not (1 <= len(value) <= 160) or value != value.strip():
        raise ValueError(f"{label}: invalid name")
    return value


def _run(raw: Any, label: str, source: str, prompt: str, scenario: str) -> Mapping[str, Any]:
    run = _object(raw, {
        "result", "source_revision", "prompt_sha256", "scenario_sha256",
        "verifier_id", "verifier_revision", "harness_id", "model_id", "evidence_sha256",
    }, label)
    if not isinstance(run["result"], str) or run["result"] not in _STATES:
        raise ValueError(f"{label}: invalid result")
    if (run["source_revision"], run["prompt_sha256"], run["scenario_sha256"]) != (source, prompt, scenario):
        raise ValueError(f"{label}: stale/mismatched source, prompt or scenario")
    _hex(run["verifier_revision"], _REV, f"{label}.verifier_revision")
    _hex(run["evidence_sha256"], _SHA, f"{label}.evidence_sha256")
    for key in ("verifier_id", "harness_id", "model_id"):
        _name(run[key], f"{label}.{key}")
    return run


def evaluate_refinement_trial(raw: Any) -> TrialDecision:
    """Classify one paired A/B trial, without executing or persisting anything.

    Hashes and verifier IDs are identity claims, not authentication or evidence
    that a model or verifier was actually run; review source artifacts separately.
    """
    doc = _object(raw, {"schema", "source_revision", "baseline_prompt_sha256",
                        "candidate_prompt_sha256", "lesson", "cases"}, "trial")
    if doc["schema"] != "loop42.refinement-trial.v1":
        raise ValueError("unknown trial schema")
    source = _hex(doc["source_revision"], _REV, "source_revision")
    baseline = _hex(doc["baseline_prompt_sha256"], _SHA, "baseline_prompt_sha256")
    candidate = _hex(doc["candidate_prompt_sha256"], _SHA, "candidate_prompt_sha256")
    if baseline == candidate:
        raise ValueError("no identifiable instruction change")
    if not isinstance(doc["lesson"], str) or not (1 <= len(doc["lesson"].strip()) <= 800):
        raise ValueError("invalid lesson")
    cases = doc["cases"]
    if not isinstance(cases, list) or not (2 <= len(cases) <= 40):
        raise ValueError("trial requires 2-40 paired cases")

    seen: set[str] = set()
    harness: tuple[str, str] | None = None
    improved = regressed = preserved = 0
    target_improved = 0
    unknown = False
    invalid_holdout = False
    for i, value in enumerate(cases):
        item = _object(value, {"scenario_id", "scenario_sha256", "kind", "baseline", "candidate"}, f"case[{i}]")
        scenario_id = _name(item["scenario_id"], f"case[{i}].scenario_id")
        if scenario_id in seen:
            raise ValueError("duplicate scenario ID")
        seen.add(scenario_id)
        scenario_sha = _hex(item["scenario_sha256"], _SHA, f"case[{i}].scenario_sha256")
        if item["kind"] not in ("target", "holdout"):
            raise ValueError("invalid case kind")
        before = _run(item["baseline"], f"case[{i}].baseline", source, baseline, scenario_sha)
        after = _run(item["candidate"], f"case[{i}].candidate", source, candidate, scenario_sha)
        # The *same* verifier must score both arms of a case. Different frozen
        # scenarios can legitimately require different independent verifiers.
        verifier_before = (before["verifier_id"], before["verifier_revision"])
        verifier_after = (after["verifier_id"], after["verifier_revision"])
        if verifier_before != verifier_after:
            raise ValueError("incomparable verifier across trial arms")
        identity_before = (before["harness_id"], before["model_id"])
        identity_after = (after["harness_id"], after["model_id"])
        if identity_before != identity_after or (harness is not None and harness != identity_before):
            raise ValueError("incomparable harness/model across trial")
        harness = identity_before

        a, b = before["result"], after["result"]
        if "UNKNOWN" in (a, b):
            unknown = True
        elif a == "PASS" and b == "FAIL":
            regressed += 1
        elif a == "FAIL" and b == "PASS":
            improved += 1
            if item["kind"] == "target":
                target_improved += 1
        if item["kind"] == "holdout":
            if a == b == "PASS":
                preserved += 1
            else:
                invalid_holdout = True

    if regressed:
        return TrialDecision("REJECT", "paired regression", improved, regressed, preserved)
    if unknown:
        return TrialDecision("INCONCLUSIVE", "missing/unknown result", improved, regressed, preserved)
    if invalid_holdout or not preserved:
        return TrialDecision("INCONCLUSIVE", "holdout not demonstrably preserved", improved, regressed, preserved)
    if not target_improved:
        return TrialDecision("INCONCLUSIVE", "no verified target improvement", improved, regressed, preserved)
    return TrialDecision("PROMISING", "independent artifact review required; not an adoption permit", improved, regressed, preserved)
