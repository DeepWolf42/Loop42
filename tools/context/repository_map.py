#!/usr/bin/env python3
"""Deterministic, bounded repository navigation map for Loop42 consumers.

The map is read-only. It summarizes tracked files and selected top-level symbols so
an agent can choose what to inspect next without loading an entire repository.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

MAP_SCHEMA = "loop42.repository-map.v1"
MAX_TRACKED_FILES = 20000
MAX_SOURCE_BYTES = 256 * 1024
DEFAULT_BUDGET_BYTES = 16 * 1024
MAX_BUDGET_BYTES = 256 * 1024
_QUERY_RE = re.compile(r"[A-Za-z0-9_.-]+")


def _encoded(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        encoding="utf-8",
        timeout=20,
    ).stdout


def _repo_root(repo: Path) -> Path:
    repo = repo.resolve()
    root = Path(_git(repo, "rev-parse", "--show-toplevel").strip()).resolve()
    if root != repo:
        raise ValueError("--repo must be the Git checkout root")
    return repo


def _tracked_paths(repo: Path) -> tuple[str, ...]:
    raw = _git(repo, "ls-files", "-z")
    paths = tuple(item for item in raw.split("\0") if item)
    if len(paths) > MAX_TRACKED_FILES:
        raise ValueError("repository has too many tracked files for bounded mapping")
    return paths


def _safe_path(repo: Path, name: str) -> Path:
    if not isinstance(name, str) or not name or "\\" in name or ":" in name:
        raise ValueError("invalid tracked path")
    relative = PurePosixPath(name)
    if relative.is_absolute() or ".." in relative.parts or ".git" in relative.parts:
        raise ValueError("tracked path escapes repository")
    path = repo.joinpath(*relative.parts)
    if not path.resolve().is_relative_to(repo):
        raise ValueError("tracked path escapes repository")
    if any(part.is_symlink() for part in [path, *path.parents] if part != repo):
        raise ValueError("symlinked tracked paths are not supported")
    if not path.is_file():
        raise ValueError(f"tracked file is missing: {name}")
    return path


def _read_source(path: Path) -> tuple[bytes | None, str]:
    size = path.stat().st_size
    if size > MAX_SOURCE_BYTES:
        return None, "oversized"
    data = path.read_bytes()
    if b"\0" in data:
        return None, "binary"
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return None, "non_utf8"
    return data, "text"


def _module_name(path: str) -> str | None:
    if not path.endswith(".py"):
        return None
    parts = list(PurePosixPath(path).with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts) if parts else None


def _annotation(value: ast.expr | None) -> str:
    if value is None:
        return ""
    text = ast.unparse(value)
    return text if len(text) <= 80 else text[:77] + "..."


def _function_signature(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    args = node.args
    positional = [*args.posonlyargs, *args.args]
    defaults = [None] * (len(positional) - len(args.defaults)) + list(args.defaults)
    rendered: list[str] = []
    for index, (arg, default) in enumerate(zip(positional, defaults)):
        item = arg.arg
        ann = _annotation(arg.annotation)
        if ann:
            item += f": {ann}"
        if default is not None:
            item += "=..."
        rendered.append(item)
        if args.posonlyargs and index + 1 == len(args.posonlyargs):
            rendered.append("/")
    if args.vararg is not None:
        item = "*" + args.vararg.arg
        ann = _annotation(args.vararg.annotation)
        if ann:
            item += f": {ann}"
        rendered.append(item)
    elif args.kwonlyargs:
        rendered.append("*")
    for arg, default in zip(args.kwonlyargs, args.kw_defaults):
        item = arg.arg
        ann = _annotation(arg.annotation)
        if ann:
            item += f": {ann}"
        if default is not None:
            item += "=..."
        rendered.append(item)
    if args.kwarg is not None:
        item = "**" + args.kwarg.arg
        ann = _annotation(args.kwarg.annotation)
        if ann:
            item += f": {ann}"
        rendered.append(item)
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    result = f"{prefix} {node.name}({', '.join(rendered)})"
    returns = _annotation(node.returns)
    if returns:
        result += f" -> {returns}"
    return result


def _python_summary(text: str) -> tuple[list[dict[str, object]], tuple[str, ...], str]:
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return [], (), "parse_error"

    symbols: list[dict[str, object]] = []
    imports: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.append(
                {
                    "kind": "function",
                    "name": node.name,
                    "line": node.lineno,
                    "signature": _function_signature(node),
                }
            )
        elif isinstance(node, ast.ClassDef):
            bases = ", ".join(ast.unparse(base) for base in node.bases)
            signature = f"class {node.name}" + (f"({bases})" if bases else "")
            symbols.append(
                {
                    "kind": "class",
                    "name": node.name,
                    "line": node.lineno,
                    "signature": signature[:200],
                }
            )
        elif isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return symbols[:80], tuple(sorted(imports)), "parsed"


def _markdown_summary(text: str) -> list[dict[str, object]]:
    result = []
    for number, line in enumerate(text.splitlines(), start=1):
        match = re.match(r"^(#{1,3})\s+(.+?)\s*$", line)
        if match:
            result.append(
                {
                    "kind": "heading",
                    "name": match.group(2)[:160],
                    "line": number,
                    "level": len(match.group(1)),
                }
            )
        if len(result) >= 40:
            break
    return result


def _json_summary(text: str) -> tuple[list[dict[str, object]], str]:
    try:
        value = json.loads(text)
    except (json.JSONDecodeError, RecursionError):
        return [], "parse_error"
    if not isinstance(value, dict):
        return [], "parsed"
    return [
        {"kind": "key", "name": key}
        for key in list(value)[:80]
        if isinstance(key, str)
    ], "parsed"


def _entry(repo: Path, path: str) -> dict[str, object]:
    source = _safe_path(repo, path)
    data, status = _read_source(source)
    entry: dict[str, object] = {
        "path": path,
        "status": status,
        "sha256": _digest(source.read_bytes()) if data is not None else None,
        "symbols": [],
        "imports": [],
    }
    if data is None:
        return entry

    text = data.decode("utf-8")
    if path.endswith(".py"):
        symbols, imports, parse_status = _python_summary(text)
        entry["symbols"] = symbols
        entry["imports"] = list(imports)
        entry["status"] = parse_status
    elif path.lower().endswith((".md", ".markdown")):
        entry["symbols"] = _markdown_summary(text)
    elif path.lower().endswith(".json"):
        symbols, parse_status = _json_summary(text)
        entry["symbols"] = symbols
        entry["status"] = parse_status
    return entry


def _query_terms(query: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(term.lower() for term in _QUERY_RE.findall(query)))


def _score(
    entry: dict[str, object],
    *,
    inbound: int,
    terms: tuple[str, ...],
    targets: frozenset[str],
) -> int:
    path = str(entry["path"])
    lower_path = path.lower()
    score = inbound * 20
    depth = len(PurePosixPath(path).parts)
    score += max(0, 6 - depth)
    if path.endswith(".py"):
        score += 4
    if path in targets:
        score += 100000
    for term in terms:
        if term in lower_path:
            score += 500
        for symbol in entry.get("symbols", []):
            if term in str(symbol.get("name", "")).lower():
                score += 300
    return score


def repository_map(
    repo: Path,
    *,
    query: str = "",
    targets: tuple[str, ...] = (),
    budget_bytes: int = DEFAULT_BUDGET_BYTES,
) -> dict[str, object]:
    repo = _repo_root(repo)
    if (
        not isinstance(budget_bytes, int)
        or isinstance(budget_bytes, bool)
        or budget_bytes < 1024
        or budget_bytes > MAX_BUDGET_BYTES
    ):
        raise ValueError("budget_bytes must be an integer between 1024 and 262144")

    tracked = _tracked_paths(repo)
    tracked_set = frozenset(tracked)
    normalized_targets = tuple(dict.fromkeys(targets))
    unknown = [target for target in normalized_targets if target not in tracked_set]
    if unknown:
        raise ValueError("target is not a tracked file: " + ", ".join(unknown))
    target_set = frozenset(normalized_targets)

    head_before = _git(repo, "rev-parse", "HEAD").strip()
    entries = [_entry(repo, path) for path in tracked]

    module_to_path = {
        module: str(entry["path"])
        for entry in entries
        if (module := _module_name(str(entry["path"]))) is not None
    }
    inbound = {path: 0 for path in tracked}
    for entry in entries:
        for imported in entry.get("imports", []):
            candidate = module_to_path.get(str(imported))
            if candidate is not None and candidate != entry["path"]:
                inbound[candidate] += 1

    terms = _query_terms(query)
    ranked = sorted(
        entries,
        key=lambda item: (
            -_score(
                item,
                inbound=inbound[str(item["path"])],
                terms=terms,
                targets=target_set,
            ),
            str(item["path"]),
        ),
    )

    selected: list[dict[str, object]] = []
    for item in ranked:
        compact = {
            "path": item["path"],
            "status": item["status"],
            "sha256": item["sha256"],
            "inbound_references": inbound[str(item["path"])],
            "symbols": item["symbols"],
        }
        projected = {
            "schema": MAP_SCHEMA,
            "head": head_before,
            "query_terms": terms,
            "targets": normalized_targets,
            "budget_bytes": budget_bytes,
            "candidate_count": len(entries),
            "entries": [*selected, compact],
            "truncated": False,
        }
        if len(_encoded(projected)) > budget_bytes:
            if item["path"] in target_set:
                raise ValueError("budget is too small for requested target summaries")
            continue
        selected.append(compact)

    selected_paths = {str(item["path"]) for item in selected}
    if not target_set.issubset(selected_paths):
        raise ValueError("requested target summary could not fit the budget")

    for item in selected:
        if item["sha256"] is None:
            continue
        current = _safe_path(repo, str(item["path"])).read_bytes()
        if _digest(current) != item["sha256"]:
            raise ValueError("source changed while mapping; reload")
    if _git(repo, "rev-parse", "HEAD").strip() != head_before:
        raise ValueError("HEAD changed while mapping; reload")

    result: dict[str, object] = {
        "schema": MAP_SCHEMA,
        "head": head_before,
        "query_terms": terms,
        "targets": normalized_targets,
        "budget_bytes": budget_bytes,
        "candidate_count": len(entries),
        "entries": selected,
        "truncated": len(selected) < len(entries),
        "source_scope": "tracked working-tree files; HEAD is provenance, not proof bytes are committed",
    }
    result["fingerprint"] = _digest(_encoded(result))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--query", default="")
    parser.add_argument("--target", action="append", default=[])
    parser.add_argument("--budget-bytes", type=int, default=DEFAULT_BUDGET_BYTES)
    args = parser.parse_args()
    try:
        result = repository_map(
            args.repo,
            query=args.query,
            targets=tuple(args.target),
            budget_bytes=args.budget_bytes,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, TypeError, subprocess.SubprocessError) as error:
        print(f"loop42 repository map: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
