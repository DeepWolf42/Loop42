"""Pure, fail-closed ChangeSet normalization for model-proposed code changes.

This module never reads or writes the filesystem. Callers provide the exact
current text snapshot for every relevant path. Loop42 validates proposal shape,
base identity and ambiguity, then produces a deterministic normalized change
record plus unified diff. Execution and authority remain consumer concerns.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import difflib
import hashlib
import re
from typing import Mapping, Tuple


_PATH_PART_RE = re.compile(r"[^/\\]+")
_VERIFICATION_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}")
_MAX_PATH = 512
_MAX_TEXT = 2 * 1024 * 1024
_MAX_CHANGES = 64
_MAX_VERIFICATIONS = 32


class ChangeOperation(str, Enum):
    MODIFY = "modify"
    CREATE = "create"
    DELETE = "delete"


def sha256_text(value: str) -> str:
    if not isinstance(value, str):
        raise TypeError("value must be text")
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _validate_path(path: str) -> str:
    if not isinstance(path, str) or not path or len(path) > _MAX_PATH:
        raise ValueError("path must be bounded non-empty text")
    if path.startswith(("/", "\\")) or "\\" in path:
        raise ValueError("path must be repository-relative POSIX text")
    parts = path.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise ValueError("path must not contain empty, dot, or parent segments")
    if any(not _PATH_PART_RE.fullmatch(part) for part in parts):
        raise ValueError("invalid path segment")
    return path


def _bounded_text(value: str, name: str, *, allow_empty: bool = True) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be text")
    if not allow_empty and not value:
        raise ValueError(f"{name} must be non-empty")
    if len(value.encode("utf-8")) > _MAX_TEXT:
        raise ValueError(f"{name} exceeds 2 MiB limit")
    return value


def _validate_sha256(value: str, name: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    return value


@dataclass(frozen=True)
class ModifyChange:
    path: str
    base_sha256: str
    search: str
    replace: str
    expected_matches: int = 1

    def __post_init__(self) -> None:
        _validate_path(self.path)
        _validate_sha256(self.base_sha256, "base_sha256")
        _bounded_text(self.search, "search", allow_empty=False)
        _bounded_text(self.replace, "replace")
        if self.expected_matches != 1:
            raise ValueError("ChangeSet v1 requires expected_matches=1")


@dataclass(frozen=True)
class CreateChange:
    path: str
    content: str

    def __post_init__(self) -> None:
        _validate_path(self.path)
        _bounded_text(self.content, "content")


@dataclass(frozen=True)
class DeleteChange:
    path: str
    base_sha256: str

    def __post_init__(self) -> None:
        _validate_path(self.path)
        _validate_sha256(self.base_sha256, "base_sha256")


Change = ModifyChange | CreateChange | DeleteChange


@dataclass(frozen=True)
class ChangeSet:
    changes: Tuple[Change, ...]
    requested_verification: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        changes = tuple(self.changes)
        if not changes or len(changes) > _MAX_CHANGES:
            raise ValueError("changes must contain between 1 and 64 entries")
        if any(not isinstance(item, (ModifyChange, CreateChange, DeleteChange)) for item in changes):
            raise TypeError("changes contains an unsupported change type")
        paths = [item.path for item in changes]
        if len(set(paths)) != len(paths):
            raise ValueError("a ChangeSet may contain at most one operation per path")
        verifications = tuple(self.requested_verification)
        if len(verifications) > _MAX_VERIFICATIONS:
            raise ValueError("too many requested verification identifiers")
        if any(
            not isinstance(item, str) or not _VERIFICATION_RE.fullmatch(item)
            for item in verifications
        ):
            raise ValueError("requested_verification must contain bounded identifiers, not commands")
        if len(set(verifications)) != len(verifications):
            raise ValueError("duplicate requested verification identifiers")
        object.__setattr__(self, "changes", changes)
        object.__setattr__(self, "requested_verification", verifications)


CHANGESET_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "schema": {"const": "loop42.changeset.v1"},
        "changes": {
            "type": "array",
            "minItems": 1,
            "maxItems": _MAX_CHANGES,
            "items": {
                "oneOf": [
                    {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "operation": {"const": "modify"},
                            "path": {"type": "string", "minLength": 1, "maxLength": _MAX_PATH},
                            "base_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                            "search": {"type": "string", "minLength": 1},
                            "replace": {"type": "string"},
                            "expected_matches": {"const": 1},
                        },
                        "required": [
                            "operation", "path", "base_sha256", "search",
                            "replace", "expected_matches"
                        ],
                    },
                    {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "operation": {"const": "create"},
                            "path": {"type": "string", "minLength": 1, "maxLength": _MAX_PATH},
                            "content": {"type": "string"},
                        },
                        "required": ["operation", "path", "content"],
                    },
                    {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "operation": {"const": "delete"},
                            "path": {"type": "string", "minLength": 1, "maxLength": _MAX_PATH},
                            "base_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                        },
                        "required": ["operation", "path", "base_sha256"],
                    },
                ]
            },
        },
        "requested_verification": {
            "type": "array",
            "maxItems": _MAX_VERIFICATIONS,
            "items": {"type": "string", "minLength": 1, "maxLength": 128},
        },
    },
    "required": ["schema", "changes", "requested_verification"],
}


def changeset_schema_fingerprint() -> str:
    import json

    rendered = json.dumps(CHANGESET_SCHEMA, sort_keys=True, separators=(",", ":"))
    return sha256_text(rendered)


def _exact_keys(value: object, required: set[str], name: str) -> dict:
    if not isinstance(value, dict) or set(value) != required:
        raise ValueError(f"{name} has unexpected or missing fields")
    return value


def parse_changeset(value: object) -> ChangeSet:
    """Parse one strict provider-facing `loop42.changeset.v1` object."""
    root = _exact_keys(value, {"schema", "changes", "requested_verification"}, "changeset")
    if root["schema"] != "loop42.changeset.v1":
        raise ValueError("unsupported changeset schema")
    raw_changes = root["changes"]
    if not isinstance(raw_changes, list):
        raise ValueError("changes must be an array")
    parsed: list[Change] = []
    for raw in raw_changes:
        if not isinstance(raw, dict):
            raise ValueError("change entry must be an object")
        operation = raw.get("operation")
        if operation == ChangeOperation.MODIFY.value:
            item = _exact_keys(
                raw,
                {"operation", "path", "base_sha256", "search", "replace", "expected_matches"},
                "modify change",
            )
            parsed.append(
                ModifyChange(
                    path=item["path"],
                    base_sha256=item["base_sha256"],
                    search=item["search"],
                    replace=item["replace"],
                    expected_matches=item["expected_matches"],
                )
            )
        elif operation == ChangeOperation.CREATE.value:
            item = _exact_keys(raw, {"operation", "path", "content"}, "create change")
            parsed.append(CreateChange(path=item["path"], content=item["content"]))
        elif operation == ChangeOperation.DELETE.value:
            item = _exact_keys(raw, {"operation", "path", "base_sha256"}, "delete change")
            parsed.append(DeleteChange(path=item["path"], base_sha256=item["base_sha256"]))
        else:
            raise ValueError("unsupported change operation")

    verification = root["requested_verification"]
    if not isinstance(verification, list):
        raise ValueError("requested_verification must be an array")
    return ChangeSet(tuple(parsed), tuple(verification))


@dataclass(frozen=True)
class NormalizedFileChange:
    operation: ChangeOperation
    path: str
    before_sha256: str | None
    after_sha256: str | None
    before_text: str | None
    after_text: str | None


@dataclass(frozen=True)
class NormalizedChangeSet:
    files: Tuple[NormalizedFileChange, ...]
    requested_verification: Tuple[str, ...]
    unified_diff: str
    fingerprint: str


def _file_diff(path: str, before: str | None, after: str | None) -> str:
    before_lines = [] if before is None else before.splitlines(keepends=True)
    after_lines = [] if after is None else after.splitlines(keepends=True)
    from_name = "/dev/null" if before is None else f"a/{path}"
    to_name = "/dev/null" if after is None else f"b/{path}"
    return "".join(
        difflib.unified_diff(
            before_lines,
            after_lines,
            fromfile=from_name,
            tofile=to_name,
            lineterm="\n",
        )
    )


def normalize_changeset(changeset: ChangeSet, current_files: Mapping[str, str]) -> NormalizedChangeSet:
    """Validate a proposal against an exact caller-supplied source snapshot.

    `current_files` is authoritative only for this call. A consumer must still
    re-read and revalidate state immediately before any real side effect.
    """
    if not isinstance(changeset, ChangeSet):
        raise TypeError("changeset must be ChangeSet")
    if not isinstance(current_files, Mapping):
        raise TypeError("current_files must be a mapping")

    normalized: list[NormalizedFileChange] = []
    diffs: list[str] = []

    for change in changeset.changes:
        path = change.path
        present = path in current_files
        before = current_files.get(path)
        if before is not None and not isinstance(before, str):
            raise TypeError("current_files values must be text")

        if isinstance(change, ModifyChange):
            if not present or before is None:
                raise ValueError(f"modify target does not exist: {path}")
            if sha256_text(before) != change.base_sha256:
                raise ValueError(f"modify base hash mismatch: {path}")
            matches = before.count(change.search)
            if matches != 1:
                raise ValueError(f"modify search must match exactly once: {path}")
            after = before.replace(change.search, change.replace, 1)
            if after == before:
                raise ValueError(f"modify would make no change: {path}")
            operation = ChangeOperation.MODIFY
        elif isinstance(change, CreateChange):
            if present:
                raise ValueError(f"create target already exists: {path}")
            before = None
            after = change.content
            operation = ChangeOperation.CREATE
        else:
            if not present or before is None:
                raise ValueError(f"delete target does not exist: {path}")
            if sha256_text(before) != change.base_sha256:
                raise ValueError(f"delete base hash mismatch: {path}")
            after = None
            operation = ChangeOperation.DELETE

        item = NormalizedFileChange(
            operation=operation,
            path=path,
            before_sha256=None if before is None else sha256_text(before),
            after_sha256=None if after is None else sha256_text(after),
            before_text=before,
            after_text=after,
        )
        normalized.append(item)
        diffs.append(_file_diff(path, before, after))

    diff = "".join(diffs)
    fingerprint_source = "\n".join(
        [
            "loop42.changeset.v1",
            *[
                "|".join(
                    [
                        item.operation.value,
                        item.path,
                        item.before_sha256 or "-",
                        item.after_sha256 or "-",
                    ]
                )
                for item in normalized
            ],
            *[f"verify:{item}" for item in changeset.requested_verification],
            f"diff:{sha256_text(diff)}",
        ]
    )
    return NormalizedChangeSet(
        files=tuple(normalized),
        requested_verification=changeset.requested_verification,
        unified_diff=diff,
        fingerprint=sha256_text(fingerprint_source),
    )
