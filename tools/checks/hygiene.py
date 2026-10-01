#!/usr/bin/env python3
"""Pure evidence-driven hygiene classification for Loop42 consumers.

Adapters collect fresh evidence about repository/Drive/workspace items. This
module classifies that evidence without deleting, moving, renaming, archiving,
or otherwise mutating the target.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from enum import Enum
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any

INPUT_SCHEMA = "loop42.hygiene-input.v1"
REPORT_SCHEMA = "loop42.hygiene-report.v1"
MAX_INPUT_BYTES = 1024 * 1024
_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}")


class HygieneKind(str, Enum):
    BRANCH = "branch"
    FILE = "file"
    DOCUMENT = "document"
    FOLDER = "folder"
    REFERENCE = "reference"
    OTHER = "other"


class HygieneCategory(str, Enum):
    ACTIVE = "active"
    HISTORICAL = "historical"
    SUPERSEDED = "superseded"
    MERGED_BRANCH = "merged_branch"
    DUPLICATE_CANDIDATE = "duplicate_candidate"
    ORPHANED = "orphaned"
    STALE_REFERENCE = "stale_reference"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class HygieneEvidence:
    fresh: bool
    complete: bool
    active: bool | None = None
    historical: bool | None = None
    superseded: bool | None = None
    merged: bool | None = None
    referenced: bool | None = None
    duplicate_candidate: bool | None = None
    stale_reference: bool | None = None

    def __post_init__(self) -> None:
        for name in (
            "fresh",
            "complete",
            "active",
            "historical",
            "superseded",
            "merged",
            "referenced",
            "duplicate_candidate",
            "stale_reference",
        ):
            value = getattr(self, name)
            if value is not None and type(value) is not bool:
                raise TypeError(f"{name} must be bool or None")


@dataclass(frozen=True)
class HygieneItem:
    item_id: str
    kind: HygieneKind
    protected: bool
    evidence: HygieneEvidence

    def __post_init__(self) -> None:
        if not isinstance(self.item_id, str) or not _ID_RE.fullmatch(self.item_id):
            raise ValueError("invalid item_id")
        if not isinstance(self.kind, HygieneKind):
            raise TypeError("kind must be HygieneKind")
        if type(self.protected) is not bool:
            raise TypeError("protected must be boolean")
        if not isinstance(self.evidence, HygieneEvidence):
            raise TypeError("evidence must be HygieneEvidence")
        if self.evidence.merged is True and self.kind is not HygieneKind.BRANCH:
            raise ValueError("merged evidence is only valid for branch items")


@dataclass(frozen=True)
class HygieneAssessment:
    item_id: str
    kind: HygieneKind
    category: HygieneCategory
    reasons: tuple[str, ...]
    cleanup_candidate: bool
    protected: bool
    destructive_action_allowed: bool = False


def classify_hygiene(item: HygieneItem) -> HygieneAssessment:
    """Classify one item from explicit evidence; never infer deletion authority."""
    if not isinstance(item, HygieneItem):
        raise TypeError("item must be HygieneItem")
    ev = item.evidence

    if not ev.fresh:
        category = HygieneCategory.UNKNOWN
        reasons = ("evidence_stale",)
    elif not ev.complete:
        category = HygieneCategory.UNKNOWN
        reasons = ("evidence_incomplete",)
    elif ev.stale_reference is True:
        category = HygieneCategory.STALE_REFERENCE
        reasons = ("reference_disagrees_with_current_truth",)
    elif item.kind is HygieneKind.BRANCH and ev.merged is True:
        category = HygieneCategory.MERGED_BRANCH
        reasons = ("branch_has_verified_merged_change",)
    elif ev.duplicate_candidate is True:
        category = HygieneCategory.DUPLICATE_CANDIDATE
        reasons = ("explicit_duplicate_evidence",)
    elif ev.superseded is True:
        category = HygieneCategory.SUPERSEDED
        reasons = ("newer_authoritative_state_supersedes_item",)
    elif ev.historical is True:
        category = HygieneCategory.HISTORICAL
        reasons = ("intentional_history",)
    elif ev.active is True:
        category = HygieneCategory.ACTIVE
        reasons = ("current_use_confirmed",)
    elif ev.referenced is False:
        category = HygieneCategory.ORPHANED
        reasons = ("fresh_complete_scan_found_no_reference",)
    else:
        category = HygieneCategory.UNKNOWN
        reasons = ("insufficient_evidence",)

    cleanup_candidate = category in {
        HygieneCategory.SUPERSEDED,
        HygieneCategory.MERGED_BRANCH,
        HygieneCategory.DUPLICATE_CANDIDATE,
        HygieneCategory.ORPHANED,
    }
    if item.protected and cleanup_candidate:
        reasons = (*reasons, "protected_retention_guard")

    return HygieneAssessment(
        item_id=item.item_id,
        kind=item.kind,
        category=category,
        reasons=reasons,
        cleanup_candidate=cleanup_candidate,
        protected=item.protected,
        destructive_action_allowed=False,
    )


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant: {value}")


def _load_json(data: bytes) -> dict[str, Any]:
    if len(data) > MAX_INPUT_BYTES:
        raise ValueError("input exceeds 1 MiB")
    try:
        value = json.loads(
            data.decode("utf-8"),
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


def _optional_bool(value: Any, where: str) -> bool | None:
    if value is None:
        return None
    if type(value) is not bool:
        raise ValueError(f"{where} must be boolean or null")
    return value


def _evidence(value: Any, index: int) -> HygieneEvidence:
    where = f"items[{index}].evidence"
    if not isinstance(value, dict):
        raise ValueError(f"{where} must be an object")
    _expect_keys(
        value,
        required={"fresh", "complete"},
        optional={
            "active",
            "historical",
            "superseded",
            "merged",
            "referenced",
            "duplicate_candidate",
            "stale_reference",
        },
        where=where,
    )
    if type(value["fresh"]) is not bool or type(value["complete"]) is not bool:
        raise ValueError(f"{where}.fresh and complete must be boolean")
    return HygieneEvidence(
        fresh=value["fresh"],
        complete=value["complete"],
        active=_optional_bool(value.get("active"), f"{where}.active"),
        historical=_optional_bool(value.get("historical"), f"{where}.historical"),
        superseded=_optional_bool(value.get("superseded"), f"{where}.superseded"),
        merged=_optional_bool(value.get("merged"), f"{where}.merged"),
        referenced=_optional_bool(value.get("referenced"), f"{where}.referenced"),
        duplicate_candidate=_optional_bool(
            value.get("duplicate_candidate"), f"{where}.duplicate_candidate"
        ),
        stale_reference=_optional_bool(
            value.get("stale_reference"), f"{where}.stale_reference"
        ),
    )


def _item(value: Any, index: int) -> HygieneItem:
    where = f"items[{index}]"
    if not isinstance(value, dict):
        raise ValueError(f"{where} must be an object")
    _expect_keys(
        value,
        required={"item_id", "kind", "protected", "evidence"},
        where=where,
    )
    try:
        kind = HygieneKind(value["kind"])
    except (TypeError, ValueError) as error:
        raise ValueError(f"{where}.kind is invalid") from error
    if type(value["protected"]) is not bool:
        raise ValueError(f"{where}.protected must be boolean")
    return HygieneItem(
        item_id=value["item_id"],
        kind=kind,
        protected=value["protected"],
        evidence=_evidence(value["evidence"], index),
    )


def _encoded(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def hygiene_report(request: dict[str, Any]) -> dict[str, Any]:
    _expect_keys(
        request,
        required={"schema", "scope", "items"},
        where="request",
    )
    if request["schema"] != INPUT_SCHEMA:
        raise ValueError(f"schema must be {INPUT_SCHEMA}")
    scope = request["scope"]
    if not isinstance(scope, str) or not _ID_RE.fullmatch(scope):
        raise ValueError("scope must be a bounded identifier")
    values = request["items"]
    if not isinstance(values, list):
        raise ValueError("items must be an array")
    if len(values) > 10000:
        raise ValueError("too many hygiene items")

    items = tuple(_item(value, index) for index, value in enumerate(values))
    ids = [item.item_id for item in items]
    if len(ids) != len(set(ids)):
        raise ValueError("item_id values must be unique")

    assessments = sorted(
        (classify_hygiene(item) for item in items),
        key=lambda item: item.item_id,
    )
    rendered = [
        {
            "item_id": item.item_id,
            "kind": item.kind.value,
            "category": item.category.value,
            "reasons": list(item.reasons),
            "cleanup_candidate": item.cleanup_candidate,
            "protected": item.protected,
            "destructive_action_allowed": item.destructive_action_allowed,
        }
        for item in assessments
    ]
    counts = {
        category.value: sum(item.category is category for item in assessments)
        for category in HygieneCategory
    }
    report: dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "scope": scope,
        "items": rendered,
        "counts": counts,
        "destructive_actions_allowed": False,
        "rule": "hygiene_is_reconciliation_not_deletion",
    }
    report["fingerprint"] = hashlib.sha256(_encoded(report)).hexdigest()
    return report


def _read_input(path: str) -> bytes:
    if path == "-":
        return sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    with Path(path).open("rb") as stream:
        return stream.read(MAX_INPUT_BYTES + 1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="-", help="JSON path, or - for stdin")
    args = parser.parse_args()
    try:
        request = _load_json(_read_input(args.input))
        print(
            json.dumps(
                hygiene_report(request),
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
        )
        return 0
    except (OSError, TypeError, ValueError) as error:
        print(f"loop42 hygiene: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
