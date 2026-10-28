#!/usr/bin/env python3
"""Bounded read-only gap/reuse preflight for existing Matrixloop RECONCILE/TARGET."""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

from tools.context.repository_map import repository_map
from tools.checks.gap_reuse_github import collect_open_work

SCHEMA = "loop42.gap-reuse-preflight.v1"
TRIGGERS = frozenset({"architecture", "new_infrastructure", "repeated_failure", "dependency_decision", "scheduled", "routine"})
AREAS = ("open_work", "installed_capabilities", "external_patterns")
STATES = frozenset({"CHECKED_NO_DELTA", "USEFUL_CANDIDATE", "NOT_SEARCHED", "BLOCKED_UNKNOWN"})
MAX_EVIDENCE_BYTES = 64 * 1024
MAX_ITEMS_PER_AREA = 8
MAX_CANDIDATES = 3
_TERMS = re.compile(r"[A-Za-z0-9_.-]{3,}")


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, encoding="utf-8", timeout=20).stdout.strip()


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate JSON key: {key}")
        out[key] = value
    return out


def _reject_constant(value: str) -> None:
    raise ValueError(f"invalid JSON constant: {value}")


def _load_evidence(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    if path.is_symlink() or not path.is_file():
        raise ValueError("evidence must be a regular file")
    if path.stat().st_size > MAX_EVIDENCE_BYTES:
        raise ValueError("evidence exceeds 64 KiB")
    try:
        data = json.loads(path.read_text(encoding="utf-8"),
                          object_pairs_hook=_strict_object, parse_constant=_reject_constant)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid UTF-8 JSON evidence") from exc
    if not isinstance(data, dict) or set(data) - set(AREAS):
        raise ValueError("evidence must be an object with only known area keys")
    return data


def _checked_at(value: str) -> bool:
    if not isinstance(value, str):
        return False
    try:
        ts = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return ts.tzinfo is not None and ts.utcoffset() is not None
    except ValueError:
        return False


def _evidence_area(name: str, raw: Any, head: str) -> tuple[dict[str, Any], list[dict[str, str]]]:
    if raw is None:
        return {"area": name, "status": "NOT_SEARCHED", "basis": "no adapter evidence supplied"}, []
    if not isinstance(raw, dict) or set(raw) - {"status", "source", "checked_at", "revision", "items", "reason"}:
        raise ValueError(f"invalid {name} evidence")
    status = raw.get("status")
    if status not in STATES:
        raise ValueError(f"invalid {name} coverage status")
    if status in {"NOT_SEARCHED", "BLOCKED_UNKNOWN"}:
        if raw.get("items"):
            raise ValueError(f"{name}: unchecked area cannot claim candidates")
        return {"area": name, "status": status,
                "basis": str(raw.get("reason", "adapter did not verify this area"))[:200]}, []
    if not isinstance(raw.get("source"), str) or not raw["source"].strip() or not _checked_at(raw.get("checked_at")):
        raise ValueError(f"{name}: checked coverage requires source and offset-aware checked_at")
    if name != "external_patterns" and raw.get("revision") != head:
        return {"area": name, "status": "BLOCKED_UNKNOWN",
                "basis": "supplied evidence revision differs from current HEAD"}, []
    items = raw.get("items", [])
    if not isinstance(items, list) or len(items) > MAX_ITEMS_PER_AREA:
        raise ValueError(f"{name}: too many or invalid items")
    if status == "CHECKED_NO_DELTA" and items:
        raise ValueError(f"{name}: no-delta coverage cannot contain candidates")
    if status == "USEFUL_CANDIDATE" and not items:
        raise ValueError(f"{name}: candidate status requires items")
    candidates: list[dict[str, str]] = []
    for item in items:
        if not isinstance(item, dict) or set(item) != {"name", "reference", "reason"}:
            raise ValueError(f"{name}: item requires name, reference and reason")
        if not all(isinstance(value, str) and 0 < len(value) <= 300 for value in item.values()):
            raise ValueError(f"{name}: invalid candidate fields")
        candidates.append({"area": name, **item, "evidence": "adapter-supplied; fit not independently verified"})
    return {"area": name, "status": status, "basis": raw["source"][:240],
            "checked_at": raw["checked_at"]}, candidates


def preflight(repo: Path, *, target: str, trigger: str, expected_head: str,
              evidence: dict[str, Any] | None = None,
              github_repository: str | None = None) -> dict[str, Any]:
    if not isinstance(target, str) or not target.strip() or len(target) > 240:
        raise ValueError("target must be 1-240 characters")
    if trigger not in TRIGGERS:
        raise ValueError("unsupported trigger")
    if not isinstance(expected_head, str) or not re.fullmatch(r"[0-9a-f]{40}", expected_head):
        raise ValueError("expected_head must be a full 40-hex commit")
    repo = repo.resolve()
    head = _git(repo, "rev-parse", "HEAD")
    root = Path(_git(repo, "rev-parse", "--show-toplevel")).resolve()
    if root != repo or head != expected_head:
        raise ValueError("repo root or live HEAD differs; reconcile first")
    if evidence is None:
        evidence = {}
    if not isinstance(evidence, dict) or set(evidence) - set(AREAS):
        raise ValueError("unknown evidence areas")

    if trigger == "routine":
        result: dict[str, Any] = {
            "schema": SCHEMA, "head": head, "target": target, "trigger": trigger,
            "status": "SKIPPED", "coverage": [], "candidates": [],
            "next_action": "PROCEED_WITH_NORMAL_MATRIXLOOP", "adoption_authorized": False,
            "limitations": ["Routine work is not blocked by a scout."],
        }
    else:
        if github_repository is not None:
            if "open_work" in evidence:
                raise ValueError("choose supplied open_work evidence or GitHub collection, not both")
            evidence = {**evidence, "open_work": collect_open_work(
                github_repository, target=target, revision=head,
                token=os.environ.get("GITHUB_TOKEN"))}
        result = {"schema": SCHEMA, "head": head, "target": target, "trigger": trigger,
                  "status": "INSPECTED", "coverage": [], "candidates": [], "adoption_authorized": False,
                  "limitations": ["Name/symbol matching is a lead, not proof of implementation or fit.",
                                  "GitHub is queried only when explicitly selected; title leads are not verified reuse.",
                                  "No tool inventory or external pattern research is performed."]}
        mapped = repository_map(repo, query=target, budget_bytes=32768)
        terms = {term.lower() for term in _TERMS.findall(target)
                 if term.lower() not in {"with", "from", "this", "that", "eine", "einen", "und", "the", "for"}}
        matched = []
        for entry in mapped["entries"]:
            names = " ".join([entry["path"], *[str(s.get("name", "")) for s in entry.get("symbols", [])]]).lower()
            if any(term in names for term in terms):
                matched.append({"area": "owned_repository", "name": entry["path"],
                                "reference": f"{head}:{entry['path']}",
                                "reason": "filename/symbol keyword match only; inspect behavior and reuse fit",
                                "evidence": "tracked working-tree symbol map; not verified reuse"})
        status = "USEFUL_CANDIDATE" if matched else ("NOT_SEARCHED" if mapped["truncated"] else "CHECKED_NO_DELTA")
        result["coverage"].append({"area": "owned_repository", "status": status,
                                   "basis": "tracked working-tree path/symbol probe; not full implementation audit",
                                   "fingerprint": mapped["fingerprint"], "truncated": mapped["truncated"]})
        result["candidates"].extend(matched[:MAX_CANDIDATES])
        for name in AREAS:
            coverage, candidates = _evidence_area(name, evidence.get(name), head)
            result["coverage"].append(coverage)
            result["candidates"].extend(candidates)
        priority = {"owned_repository": 0, "open_work": 1, "installed_capabilities": 2, "external_patterns": 3}
        result["candidates"].sort(key=lambda value: (priority[value["area"]], value["name"]))
        result["candidates"] = result["candidates"][:MAX_CANDIDATES]
        if result["candidates"]:
            result["next_action"] = "VERIFY_REUSE_FIT_WITH_SMALLEST_TEST"
        elif any(area["status"] in {"NOT_SEARCHED", "BLOCKED_UNKNOWN"} for area in result["coverage"]):
            result["next_action"] = "RESEARCH_ONLY_HIGHEST_IMPACT_UNKNOWN_IF_NEEDED"
        else:
            result["next_action"] = "NO_USEFUL_DELTA_IN_CHECKED_SCOPE"
    if _git(repo, "rev-parse", "HEAD") != head:
        raise ValueError("live HEAD changed during preflight")
    result["fingerprint"] = hashlib.sha256(
        json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--trigger", choices=sorted(TRIGGERS), required=True)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--evidence", type=Path)
    parser.add_argument("--github-repository", help="opt-in one-page open PR/issue title probe for owner/name")
    args = parser.parse_args(argv)
    try:
        report = preflight(args.repo, target=args.target, trigger=args.trigger,
                           expected_head=args.expected_head, evidence=_load_evidence(args.evidence),
                           github_repository=args.github_repository)
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        print(f"loop42 gap/reuse preflight: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
