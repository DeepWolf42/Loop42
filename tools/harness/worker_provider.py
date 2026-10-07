"""Provider-neutral worker request/result contract for Loop42.

Adapters may call OpenAI, Anthropic, Gemini, DeepSeek, Ollama or future models,
but the generic Loop42 core depends only on this bounded contract. A provider
result is a proposal, never execution authority.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Protocol, Tuple

from tools.harness.change_set import ChangeSet


_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")
_SHA_RE = re.compile(r"[0-9a-f]{7,64}")
_FP_RE = re.compile(r"[0-9a-f]{64}")
_CAP_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}")


class WorkerStatus(str, Enum):
    PROPOSAL = "proposal"
    BLOCKED = "blocked"
    FAILED = "failed"


@dataclass(frozen=True)
class WorkerRequest:
    task_id: str
    attempt_id: str
    source_revision: str
    context_fingerprint: str
    task: str
    context: str
    allowed_capabilities: Tuple[str, ...]
    requested_role: str = "general"

    def __post_init__(self) -> None:
        for name, value in (("task_id", self.task_id), ("attempt_id", self.attempt_id)):
            if not isinstance(value, str) or not _ID_RE.fullmatch(value):
                raise ValueError(f"invalid {name}")
        if not isinstance(self.source_revision, str) or not _SHA_RE.fullmatch(self.source_revision):
            raise ValueError("source_revision must be a lowercase Git revision")
        if not isinstance(self.context_fingerprint, str) or not _FP_RE.fullmatch(self.context_fingerprint):
            raise ValueError("context_fingerprint must be a SHA-256 digest")
        for name, value, limit in (
            ("task", self.task, 20_000),
            ("context", self.context, 2_000_000),
            ("requested_role", self.requested_role, 128),
        ):
            if not isinstance(value, str) or not value.strip() or len(value) > limit:
                raise ValueError(f"{name} must be bounded non-empty text")
        capabilities = tuple(self.allowed_capabilities)
        if len(capabilities) > 64 or any(
            not isinstance(item, str) or not _CAP_RE.fullmatch(item)
            for item in capabilities
        ):
            raise ValueError("allowed_capabilities contains invalid identifiers")
        if len(set(capabilities)) != len(capabilities):
            raise ValueError("duplicate allowed_capabilities")
        object.__setattr__(self, "allowed_capabilities", capabilities)


@dataclass(frozen=True)
class WorkerUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_microunits: int | None = None

    def __post_init__(self) -> None:
        for name, value in (
            ("input_tokens", self.input_tokens),
            ("output_tokens", self.output_tokens),
            ("cost_microunits", self.cost_microunits),
        ):
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, int) or value < 0
            ):
                raise ValueError(f"{name} must be a non-negative integer or None")


@dataclass(frozen=True)
class WorkerResult:
    status: WorkerStatus
    provider: str
    model: str
    task_id: str
    attempt_id: str
    source_revision: str
    context_fingerprint: str
    rationale_summary: str
    evidence: Tuple[str, ...] = ()
    changeset: ChangeSet | None = None
    usage: WorkerUsage = WorkerUsage()
    raw_response_fingerprint: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, WorkerStatus):
            raise TypeError("status must be WorkerStatus")
        for name, value in (("provider", self.provider), ("model", self.model)):
            if not isinstance(value, str) or not value.strip() or len(value) > 256:
                raise ValueError(f"{name} must be bounded non-empty text")
        for name, value in (("task_id", self.task_id), ("attempt_id", self.attempt_id)):
            if not isinstance(value, str) or not _ID_RE.fullmatch(value):
                raise ValueError(f"invalid {name}")
        if not isinstance(self.source_revision, str) or not _SHA_RE.fullmatch(self.source_revision):
            raise ValueError("source_revision must be a lowercase Git revision")
        if not isinstance(self.context_fingerprint, str) or not _FP_RE.fullmatch(self.context_fingerprint):
            raise ValueError("context_fingerprint must be a SHA-256 digest")
        if not isinstance(self.rationale_summary, str) or len(self.rationale_summary) > 4000:
            raise ValueError("rationale_summary must be bounded text")
        evidence = tuple(self.evidence)
        if len(evidence) > 64 or any(
            not isinstance(item, str) or not item or len(item) > 1000 for item in evidence
        ):
            raise ValueError("evidence contains invalid entries")
        if len(set(evidence)) != len(evidence):
            raise ValueError("duplicate evidence entries")
        object.__setattr__(self, "evidence", evidence)
        if self.status is WorkerStatus.PROPOSAL and self.changeset is None:
            raise ValueError("proposal result requires a ChangeSet")
        if self.status is not WorkerStatus.PROPOSAL and self.changeset is not None:
            raise ValueError("only proposal results may carry a ChangeSet")
        if not isinstance(self.usage, WorkerUsage):
            raise TypeError("usage must be WorkerUsage")
        if self.raw_response_fingerprint is not None and not _FP_RE.fullmatch(
            self.raw_response_fingerprint
        ):
            raise ValueError("raw_response_fingerprint must be SHA-256 or None")


class WorkerProvider(Protocol):
    """Thin provider adapter. It may propose; it never receives execution authority."""

    def run(self, request: WorkerRequest) -> WorkerResult:
        ...
