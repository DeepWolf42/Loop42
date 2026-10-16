#!/usr/bin/env python3
"""Optional, fail-closed completion checks for trusted repo-local commands.

This is a check runner, not a sandbox or semantic proof of an English criterion.
An operator must inspect the contract and invoked scripts before using --run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

SCHEMA = "loop42.completion-gates.v1"
MAX_BYTES = 65536
MAX_OUTPUT_BYTES = 1048576
SHA = re.compile(r"[0-9a-f]{40}\Z")
ID = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,63}\Z")


def _strict_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    obj: dict[str, object] = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError(f"duplicate JSON key: {key}")
        obj[key] = value
    return obj


def _no_constant(value: str) -> None:
    raise ValueError(f"invalid JSON number: {value}")


def load_contract(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    if len(raw) > MAX_BYTES:
        raise ValueError("contract exceeds 64 KiB")
    try:
        data = json.loads(raw, object_pairs_hook=_strict_pairs, parse_constant=_no_constant)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid JSON contract") from exc
    if not isinstance(data, dict) or set(data) != {"schema", "gates"}:
        raise ValueError("invalid contract fields")
    if data["schema"] != SCHEMA:
        raise ValueError("invalid schema")
    gates = data["gates"]
    if not isinstance(gates, list) or not 1 <= len(gates) <= 20:
        raise ValueError("1 to 20 gates required")
    seen: set[str] = set()
    for gate in gates:
        if not isinstance(gate, dict) or set(gate) != {"id", "criterion", "argv", "expect_line", "timeout_seconds"}:
            raise ValueError("invalid gate fields")
        gate_id = gate["id"]
        if not isinstance(gate_id, str) or not ID.fullmatch(gate_id) or gate_id in seen:
            raise ValueError("duplicate or malformed gate id")
        seen.add(gate_id)
        if not isinstance(gate["criterion"], str) or not gate["criterion"].strip() or len(gate["criterion"]) > 400:
            raise ValueError("invalid criterion")
        argv = gate["argv"]
        if not isinstance(argv, list) or not 1 <= len(argv) <= 32 or any(not isinstance(s, str) or not s or len(s) > 1024 for s in argv):
            raise ValueError("invalid argv")
        if not isinstance(gate["expect_line"], str) or not gate["expect_line"].strip() or len(gate["expect_line"]) > 250 or "\n" in gate["expect_line"] or "\r" in gate["expect_line"]:
            raise ValueError("invalid expect_line")
        t = gate["timeout_seconds"]
        if type(t) is not int or not 1 <= t <= 300:
            raise ValueError("invalid timeout")
    return data


def _git(repo: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args], stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=10, check=False)
    if r.returncode:
        raise ValueError("cannot establish Git revision / cleanliness")
    return r.stdout.strip()


def verify(contract: dict[str, object], repo: Path, *, expected_revision: str, run: bool) -> dict[str, object]:
    if not isinstance(expected_revision, str) or not SHA.fullmatch(expected_revision):
        raise ValueError("invalid expected revision")
    repo = repo.resolve(strict=True)
    if not repo.is_dir():
        raise ValueError("repository path must be a directory")
    root = Path(_git(repo, "rev-parse", "--show-toplevel")).resolve(strict=True)
    if root != repo:
        raise ValueError("repo must be the actual Git root")
    revision = _git(repo, "rev-parse", "HEAD")
    if revision != expected_revision:
        raise ValueError("stale source revision")
    if _git(repo, "status", "--porcelain", "--untracked-files=no"):
        raise ValueError("tracked working tree is dirty")
    digest = hashlib.sha256(json.dumps(contract, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode()).hexdigest()
    results = []
    for gate in contract["gates"]:
        g = {"id": gate["id"], "status": "NOT_RUN", "output_sha256": None}
        if run:
            try:
                # Direct exec, no shell interpolation. Not a security boundary: argv can invoke code.
                with tempfile.TemporaryFile() as output:
                    p = subprocess.run(gate["argv"], cwd=repo, stdin=subprocess.DEVNULL, stdout=output,
                                       stderr=subprocess.STDOUT, timeout=gate["timeout_seconds"], check=False)
                    output.seek(0)
                    raw = output.read(MAX_OUTPUT_BYTES + 1)
                    if len(raw) > MAX_OUTPUT_BYTES:
                        g["status"] = "FAIL_OUTPUT_LIMIT"
                    else:
                        content = raw.decode("utf-8", errors="replace")
                        g["output_sha256"] = hashlib.sha256(raw).hexdigest()
                        if p.returncode == 0 and gate["expect_line"] in content.splitlines():
                            g["status"] = "PASS"
                        else:
                            g["status"] = "FAIL"
                    # A gate may change the worktree or even HEAD while running.
                    if _git(repo, "rev-parse", "HEAD") != expected_revision or _git(repo, "status", "--porcelain", "--untracked-files=no"):
                        g["status"] = "FAIL_SOURCE_CHANGED"
            except (OSError, ValueError, subprocess.TimeoutExpired):
                g["status"] = "FAIL_EXECUTION"
        results.append(g)
    passed = bool(run) and all(r["status"] == "PASS" for r in results)
    return {"schema": "loop42.completion-gates-result.v1", "source_revision": revision,
            "gate_definition_sha256": digest, "complete": passed, "gates": results}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Inspect a completion contract; execute only after reviewing each command")
    p.add_argument("contract", type=Path)
    p.add_argument("--repo", type=Path, default=Path("."))
    p.add_argument("--expected-revision", required=True, help="exact 40-character SHA supplied by trusted task/CI")
    p.add_argument("--run", action="store_true", help="explicitly execute trusted commands")
    args = p.parse_args(argv)
    try:
        contract = load_contract(args.contract)
        if not args.run:
            print(json.dumps({"review_required": True, "source_revision": args.expected_revision,
                              "gates": contract["gates"]}, indent=2))
        report = verify(contract, args.repo, expected_revision=args.expected_revision, run=args.run)
    except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"complete": False, "error": str(exc)}))
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0 if report["complete"] else 1


if __name__ == "__main__":
    sys.exit(main())
