#!/usr/bin/env python3
"""Project-agnostic, hash-bound context snapshots with guarded checkpoint writeback."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile


LIMIT = 256 * 1024
MANIFEST_SCHEMA = "loop42.context-manifest.v1"
SNAPSHOT_SCHEMA = "loop42.project-snapshot.v1"
REQUIRED_RESULT_FIELDS = {
    "id", "basis", "known", "proven", "open", "discarded", "next", "evidence"
}


def encoded(value):
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def digest(value):
    return hashlib.sha256(value).hexdigest()


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        encoding="utf-8",
        timeout=15,
    ).stdout.strip()


def source_path(repo, name):
    if not isinstance(name, str) or not name or "\\" in name or ":" in name:
        raise ValueError("invalid source path")
    relative = PurePosixPath(name)
    if relative.is_absolute() or ".." in relative.parts or ".git" in relative.parts:
        raise ValueError("source path must stay inside the checkout")
    path = repo.joinpath(*relative.parts)
    if (
        not path.resolve().is_relative_to(repo)
        or any(p.is_symlink() for p in [path, *path.parents] if p != repo)
    ):
        raise ValueError("symlinked sources are not supported")
    if not path.is_file():
        raise ValueError(f"missing source: {name}")
    return path


def read_bytes(path):
    with path.open("rb") as stream:
        data = stream.read(LIMIT + 1)
    if not data or len(data) > LIMIT:
        raise ValueError("empty or oversized source; split the context explicitly")
    return data


def _validate_manifest(value):
    if not isinstance(value, dict) or value.get("schema") != MANIFEST_SCHEMA:
        raise ValueError("invalid Loop42 context manifest")
    roles = value.get("roles")
    if not isinstance(roles, dict) or not roles or "project_state" not in roles:
        raise ValueError("manifest roles must include project_state")
    for role, path in roles.items():
        if not isinstance(role, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", role):
            raise ValueError("invalid manifest role")
        if not isinstance(path, str) or not path:
            raise ValueError(f"invalid path for role: {role}")
    external = value.get("external_sources", [])
    if not isinstance(external, list):
        raise ValueError("external_sources must be a list")
    return roles, external


def snapshot(repo, manifest_name="loop42-context.json"):
    repo = repo.resolve()
    if Path(git(repo, "rev-parse", "--show-toplevel")).resolve() != repo:
        raise ValueError("--repo must be the Git checkout root")

    manifest_path = source_path(repo, manifest_name)
    manifest_raw = read_bytes(manifest_path)
    manifest = json.loads(manifest_raw)
    roles, external_sources = _validate_manifest(manifest)

    documents = []
    for name in dict.fromkeys(roles.values()):
        data = read_bytes(source_path(repo, name))
        documents.append(
            {"path": name, "sha256": digest(data), "text": data.decode("utf-8")}
        )

    head = git(repo, "rev-parse", "HEAD")
    value = {
        "schema": SNAPSHOT_SCHEMA,
        "head": head,
        "manifest_path": manifest_name,
        "manifest_sha256": digest(manifest_raw),
        "roles": roles,
        "documents": documents,
        "external_sources": external_sources,
        "remote_freshness": "UNKNOWN",
        "source_scope": (
            "local working files; HEAD is provenance, not proof files are committed"
        ),
    }
    if len(encoded(value)) > LIMIT:
        raise ValueError("context exceeds 256 KiB; no silent truncation")

    if head != git(repo, "rev-parse", "HEAD"):
        raise ValueError("basis changed while reading; reload")
    if manifest_raw != read_bytes(source_path(repo, manifest_name)):
        raise ValueError("manifest changed while reading; reload")
    for document in documents:
        current = read_bytes(source_path(repo, document["path"]))
        if digest(current) != document["sha256"]:
            raise ValueError("source changed while reading; reload")

    value["fingerprint"] = digest(encoded(value))
    return value


def _validate_result(result):
    if not isinstance(result, dict) or set(result) != REQUIRED_RESULT_FIELDS:
        raise ValueError(
            "result requires exactly id, basis, known, proven, open, "
            "discarded, next, evidence"
        )
    for name, value in result.items():
        if not isinstance(value, str) or not value.strip() or len(value) > 8000:
            raise ValueError(f"invalid result field: {name}")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", result["id"]):
        raise ValueError("id must be a short lowercase checkpoint identifier")
    if not re.fullmatch(r"[0-9a-f]{64}", result["basis"]):
        raise ValueError("invalid basis fingerprint")


def checkpoint(repo, result_path, manifest_name="loop42-context.json"):
    repo = repo.resolve()
    result = json.loads(read_bytes(result_path))
    _validate_result(result)

    common = Path(git(repo, "rev-parse", "--git-common-dir"))
    if not common.is_absolute():
        common = repo / common
    lock = common / "loop42-project-context.lock"

    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    temporary = None
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(str(os.getpid()))

        current = snapshot(repo, manifest_name)
        if result["basis"] != current["fingerprint"]:
            raise ValueError("stale basis: reload and reconcile; do not replay")

        target = source_path(repo, current["roles"]["project_state"])
        original = read_bytes(target)
        text = original.decode("utf-8")
        marker = f'<!-- loop42-checkpoint:{result["id"]} -->'
        if marker in text:
            raise ValueError("duplicate checkpoint id")

        first, separator, rest = text.partition("\n")
        if not first.startswith("# ") or not separator:
            raise ValueError("state document must start with a Markdown title")

        when = datetime.now(timezone.utc).isoformat(timespec="seconds")
        block = [
            marker,
            f'## {result["id"]} — {when}',
            "",
            f'- Basis: `{current["head"]}`; context `{current["fingerprint"]}`.',
            (
                "- Record status: operator/tool-submitted checkpoint; "
                "factual claims require linked evidence."
            ),
        ]
        for name in ["known", "proven", "open", "discarded", "next", "evidence"]:
            value = (
                result[name]
                .replace("\r\n", "\n")
                .replace("\r", "\n")
                .replace("\n", "\n  ")
            )
            block.append(f"- {name.capitalize()}: {value}")

        updated = first + "\n\n" + "\n".join(block) + "\n\n" + rest.lstrip("\n")
        if len(updated.encode("utf-8")) > LIMIT:
            raise ValueError("checkpoint would exceed source size limit")

        projected = {key: value for key, value in current.items() if key != "fingerprint"}
        projected["documents"] = [
            {
                **document,
                "text": updated,
                "sha256": digest(updated.encode("utf-8")),
            }
            if document["path"] == current["roles"]["project_state"]
            else document
            for document in current["documents"]
        ]
        if len(encoded(projected)) > LIMIT:
            raise ValueError("checkpoint would exceed total context size limit")

        with tempfile.NamedTemporaryFile(
            mode="wb", dir=target.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(updated.encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())

        if snapshot(repo, manifest_name)["fingerprint"] != result["basis"]:
            raise ValueError("basis changed before replacement; reload")
        if target.read_bytes() != original:
            raise ValueError("state changed before replacement; reload")

        os.replace(temporary, target)
        temporary = None
        return {
            "updated": current["roles"]["project_state"],
            "id": result["id"],
            "committed": False,
            "pushed": False,
        }
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        lock.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--manifest", default="loop42-context.json")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("read")
    write = commands.add_parser(
        "checkpoint", help="write an already-reviewed result to existing state"
    )
    write.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()

    try:
        if args.command == "read":
            output = snapshot(args.repo, args.manifest)
        else:
            output = checkpoint(args.repo, args.result, args.manifest)
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print(f"loop42 context: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
