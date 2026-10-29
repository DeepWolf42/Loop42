"""Isolated detached Git worktree leases for autonomous Loop42 workers.

The model never calls this module. A consumer/runtime creates one exact detached
worktree at an already-existing commit, hands that workspace to bounded workers,
and later removes only that exact lease. No fetch, pull, checkout of a branch,
commit, push, merge or network operation is performed here.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import re
import subprocess
import tempfile

_SHA_RE = re.compile(r"[0-9a-f]{7,64}")
_FULL_SHA_RE = re.compile(r"[0-9a-f]{40,64}")
_MAX_OUTPUT = 1024 * 1024
_PREFIX = ".loop42-worktree-"


@dataclass(frozen=True)
class GitWorkspaceLease:
    repo_root: Path
    root: Path
    source_revision: str
    lease_fingerprint: str


def _dir(value: Path, name: str) -> Path:
    path = Path(value)
    if path.is_symlink() or not path.exists() or not path.is_dir():
        raise ValueError(f"{name} must be an existing non-symlink directory")
    return path.resolve()


def _run(argv: list[str], *, cwd: Path, timeout: int = 60) -> str:
    try:
        result = subprocess.run(
            argv,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=False,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise ValueError("git command timed out") from error
    raw = result.stdout[: _MAX_OUTPUT + 1]
    if len(raw) > _MAX_OUTPUT:
        raise ValueError("git output exceeds 1 MiB limit")
    text = raw.decode("utf-8", errors="replace")
    if result.returncode != 0:
        raise ValueError(f"git command failed ({result.returncode}): {text.strip()}")
    return text


def _repo_root(value: Path) -> Path:
    root = _dir(value, "repo_root")
    discovered = _run(["git", "rev-parse", "--show-toplevel"], cwd=root).strip()
    try:
        discovered_path = Path(discovered).resolve()
    except (OSError, RuntimeError) as error:
        raise ValueError("invalid Git repository root") from error
    if discovered_path != root:
        raise ValueError("repo_root must be the Git top-level directory")
    return root


def _resolve_commit(repo_root: Path, source_revision: str) -> str:
    if not isinstance(source_revision, str) or not _SHA_RE.fullmatch(source_revision):
        raise ValueError("source_revision must be a lowercase hexadecimal Git revision")
    resolved = _run(
        ["git", "rev-parse", "--verify", f"{source_revision}^{{commit}}"],
        cwd=repo_root,
    ).strip()
    if not _FULL_SHA_RE.fullmatch(resolved) or not resolved.startswith(source_revision):
        raise ValueError("source_revision did not resolve to the requested commit")
    return resolved


def create_detached_worktree(
    repo_root: Path,
    source_revision: str,
    *,
    parent: Path,
) -> GitWorkspaceLease:
    """Create one detached worktree at an exact existing commit.

    The parent must already exist and is never created implicitly. The generated
    worktree path is owned by this lease and uses a fixed Loop42 prefix.
    """
    repo = _repo_root(repo_root)
    parent_root = _dir(parent, "parent")
    if parent_root == repo or repo in parent_root.parents:
        raise ValueError("worktree parent must be outside repo_root")
    commit = _resolve_commit(repo, source_revision)

    raw = Path(tempfile.mkdtemp(prefix=_PREFIX, dir=parent_root))
    raw.rmdir()  # git worktree add requires the target path to be absent
    try:
        _run(["git", "worktree", "add", "--detach", str(raw), commit], cwd=repo, timeout=120)
        workspace = _dir(raw, "worktree")
        observed = _run(["git", "rev-parse", "HEAD"], cwd=workspace).strip()
        if observed != commit:
            raise ValueError("created worktree HEAD does not match requested commit")
        common = Path(os.path.commonpath([str(parent_root), str(workspace)]))
        if common != parent_root or workspace.parent != parent_root or not workspace.name.startswith(_PREFIX):
            raise ValueError("created worktree escaped its lease parent")
        fingerprint = hashlib.sha256(
            f"loop42.git-worktree.v1\n{repo}\n{workspace}\n{commit}".encode("utf-8")
        ).hexdigest()
        return GitWorkspaceLease(repo, workspace, commit, fingerprint)
    except BaseException:
        # If Git partially registered the path, ask Git to remove only this generated target.
        try:
            _run(["git", "worktree", "remove", "--force", str(raw)], cwd=repo, timeout=60)
        except Exception:
            pass
        if raw.exists() and raw.is_dir() and not raw.is_symlink():
            try:
                raw.rmdir()
            except OSError:
                pass
        raise


def validate_worktree_lease(lease: GitWorkspaceLease) -> None:
    if not isinstance(lease, GitWorkspaceLease):
        raise TypeError("lease must be GitWorkspaceLease")
    repo = _repo_root(lease.repo_root)
    workspace = _dir(lease.root, "worktree")
    if workspace.parent != lease.root.parent.resolve() or not workspace.name.startswith(_PREFIX):
        raise ValueError("worktree lease path is invalid")
    observed = _run(["git", "rev-parse", "HEAD"], cwd=workspace).strip()
    if observed != lease.source_revision:
        raise ValueError("worktree lease HEAD changed")
    expected = hashlib.sha256(
        f"loop42.git-worktree.v1\n{repo}\n{workspace}\n{lease.source_revision}".encode("utf-8")
    ).hexdigest()
    if expected != lease.lease_fingerprint:
        raise ValueError("worktree lease fingerprint mismatch")


def remove_worktree(lease: GitWorkspaceLease) -> None:
    """Remove only the exact generated worktree represented by a valid lease."""
    validate_worktree_lease(lease)
    repo = lease.repo_root.resolve()
    workspace = lease.root.resolve()
    if workspace == repo or repo in workspace.parents:
        raise ValueError("refusing to remove a worktree path inside repository root")
    _run(["git", "worktree", "remove", "--force", str(workspace)], cwd=repo, timeout=120)
    if workspace.exists():
        raise ValueError("git reported worktree removal but path still exists")
