"""Bounded verification registry and runner for Loop42 consumers.

Models request verification identifiers. Only consumer-owned registry entries become
processes. Commands execute as argv with shell=False inside an explicit workspace.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Iterable, Tuple

_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}")
_MAX_ARG = 4096
_MAX_SPECS = 128
_DEFAULT_OUTPUT_LIMIT = 1024 * 1024


@dataclass(frozen=True)
class VerificationSpec:
    identifier: str
    argv: Tuple[str, ...]
    timeout_seconds: int = 300

    def __post_init__(self) -> None:
        if not isinstance(self.identifier, str) or not _ID_RE.fullmatch(self.identifier):
            raise ValueError("invalid verification identifier")
        argv = tuple(self.argv)
        if not argv or len(argv) > 64 or any(
            not isinstance(item, str) or not item or len(item) > _MAX_ARG for item in argv
        ):
            raise ValueError("argv must contain bounded non-empty text arguments")
        if isinstance(self.timeout_seconds, bool) or not isinstance(self.timeout_seconds, int):
            raise TypeError("timeout_seconds must be an integer")
        if not 1 <= self.timeout_seconds <= 3600:
            raise ValueError("timeout_seconds must be between 1 and 3600")
        object.__setattr__(self, "argv", argv)


@dataclass(frozen=True)
class VerificationRegistry:
    specs: Tuple[VerificationSpec, ...]

    def __post_init__(self) -> None:
        specs = tuple(self.specs)
        if len(specs) > _MAX_SPECS or any(not isinstance(item, VerificationSpec) for item in specs):
            raise ValueError("verification registry contains invalid specs")
        identifiers = [item.identifier for item in specs]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("duplicate verification identifier")
        object.__setattr__(self, "specs", specs)

    def resolve(self, identifiers: Iterable[str]) -> Tuple[VerificationSpec, ...]:
        requested = tuple(identifiers)
        if len(requested) > 32 or any(
            not isinstance(item, str) or not _ID_RE.fullmatch(item) for item in requested
        ):
            raise ValueError("invalid requested verification identifiers")
        if len(set(requested)) != len(requested):
            raise ValueError("duplicate requested verification identifiers")
        by_id = {item.identifier: item for item in self.specs}
        missing = [item for item in requested if item not in by_id]
        if missing:
            raise ValueError("unknown verification identifier: " + ", ".join(missing))
        return tuple(by_id[item] for item in requested)


@dataclass(frozen=True)
class VerificationResult:
    identifier: str
    argv: Tuple[str, ...]
    exit_code: int | None
    timed_out: bool
    output: str
    output_truncated: bool

    @property
    def passed(self) -> bool:
        return not self.timed_out and self.exit_code == 0


def _workspace_root(value: Path) -> Path:
    root = Path(value)
    if root.is_symlink() or not root.exists() or not root.is_dir():
        raise ValueError("workspace root must be an existing non-symlink directory")
    return root.resolve()


def run_verifications(
    workspace: Path,
    identifiers: Iterable[str],
    registry: VerificationRegistry,
    *,
    stop_on_failure: bool = True,
    output_limit: int = _DEFAULT_OUTPUT_LIMIT,
) -> Tuple[VerificationResult, ...]:
    """Run only pre-registered argv commands; never evaluate a model command string."""
    if not isinstance(registry, VerificationRegistry):
        raise TypeError("registry must be VerificationRegistry")
    if type(stop_on_failure) is not bool:
        raise TypeError("stop_on_failure must be boolean")
    if isinstance(output_limit, bool) or not isinstance(output_limit, int) or not 1 <= output_limit <= 16 * 1024 * 1024:
        raise ValueError("output_limit must be between 1 byte and 16 MiB")
    root = _workspace_root(workspace)
    specs = registry.resolve(identifiers)  # resolve every ID before the first process starts
    results: list[VerificationResult] = []

    for spec in specs:
        with tempfile.TemporaryFile() as capture:
            process = subprocess.Popen(
                list(spec.argv),
                cwd=root,
                stdin=subprocess.DEVNULL,
                stdout=capture,
                stderr=subprocess.STDOUT,
                shell=False,
            )
            timed_out = False
            try:
                exit_code = process.wait(timeout=spec.timeout_seconds)
            except subprocess.TimeoutExpired:
                timed_out = True
                process.kill()
                process.wait()
                exit_code = None
            capture.flush()
            capture.seek(0)
            raw = capture.read(output_limit + 1)
        truncated = len(raw) > output_limit
        raw = raw[:output_limit]
        result = VerificationResult(
            identifier=spec.identifier,
            argv=spec.argv,
            exit_code=exit_code,
            timed_out=timed_out,
            output=raw.decode("utf-8", errors="replace"),
            output_truncated=truncated,
        )
        results.append(result)
        if stop_on_failure and not result.passed:
            break
    return tuple(results)
