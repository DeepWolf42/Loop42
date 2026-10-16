"""Pure provider-routing policy for one visible Loop42 attempt.

Routing selects one provider profile. It never calls a model and never hides
fallback/retry. A later attempt may route again from fresh state.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum
import re
from typing import Tuple


_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}")


class IncrementalCostTier(IntEnum):
    ZERO_OR_INCLUDED = 0
    LOW_METERED = 1
    STANDARD_METERED = 2
    PREMIUM_METERED = 3


class ProviderAvailability(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ProviderProfile:
    key: str
    provider: str
    model: str
    roles: Tuple[str, ...]
    capabilities: Tuple[str, ...]
    cost_tier: IncrementalCostTier
    preference_rank: int = 100
    estimated_max_cost_microunits: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.key, str) or not _ID_RE.fullmatch(self.key):
            raise ValueError("invalid provider profile key")
        for name, value in (("provider", self.provider), ("model", self.model)):
            if not isinstance(value, str) or not value.strip() or len(value) > 256:
                raise ValueError(f"{name} must be bounded non-empty text")
        for name, values in (("roles", self.roles), ("capabilities", self.capabilities)):
            values = tuple(values)
            if not values or len(values) > 64 or any(
                not isinstance(item, str) or not _ID_RE.fullmatch(item) for item in values
            ):
                raise ValueError(f"{name} must contain bounded identifiers")
            if len(set(values)) != len(values):
                raise ValueError(f"duplicate {name}")
            object.__setattr__(self, name, values)
        if not isinstance(self.cost_tier, IncrementalCostTier):
            raise TypeError("cost_tier must be IncrementalCostTier")
        if isinstance(self.preference_rank, bool) or not isinstance(self.preference_rank, int):
            raise TypeError("preference_rank must be an integer")
        if not 0 <= self.preference_rank <= 10000:
            raise ValueError("preference_rank must be between 0 and 10000")
        value = self.estimated_max_cost_microunits
        if value is not None and (
            isinstance(value, bool) or not isinstance(value, int) or value < 0
        ):
            raise ValueError("estimated_max_cost_microunits must be non-negative or None")


@dataclass(frozen=True)
class ProviderCandidate:
    profile: ProviderProfile
    availability: ProviderAvailability
    availability_evidence: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.profile, ProviderProfile):
            raise TypeError("profile must be ProviderProfile")
        if not isinstance(self.availability, ProviderAvailability):
            raise TypeError("availability must be ProviderAvailability")
        if not isinstance(self.availability_evidence, str) or len(self.availability_evidence) > 1000:
            raise ValueError("availability_evidence must be bounded text")


@dataclass(frozen=True)
class RouteRequest:
    role: str
    required_capabilities: Tuple[str, ...]
    max_cost_tier: IncrementalCostTier = IncrementalCostTier.PREMIUM_METERED
    max_estimated_cost_microunits: int | None = None
    excluded_profile_keys: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.role, str) or not _ID_RE.fullmatch(self.role):
            raise ValueError("invalid route role")
        for name, values in (
            ("required_capabilities", self.required_capabilities),
            ("excluded_profile_keys", self.excluded_profile_keys),
        ):
            values = tuple(values)
            if len(values) > 64 or any(
                not isinstance(item, str) or not _ID_RE.fullmatch(item) for item in values
            ):
                raise ValueError(f"{name} contains invalid identifiers")
            if len(set(values)) != len(values):
                raise ValueError(f"duplicate {name}")
            object.__setattr__(self, name, values)
        if not isinstance(self.max_cost_tier, IncrementalCostTier):
            raise TypeError("max_cost_tier must be IncrementalCostTier")
        value = self.max_estimated_cost_microunits
        if value is not None and (
            isinstance(value, bool) or not isinstance(value, int) or value < 0
        ):
            raise ValueError("max_estimated_cost_microunits must be non-negative or None")


@dataclass(frozen=True)
class RouteDecision:
    selected: ProviderProfile | None
    eligible_profile_keys: Tuple[str, ...]
    rejected: Tuple[tuple[str, str], ...]


def select_provider(
    request: RouteRequest,
    candidates: Tuple[ProviderCandidate, ...],
) -> RouteDecision:
    """Choose the lowest sufficient visible provider for one attempt."""
    if not isinstance(request, RouteRequest):
        raise TypeError("request must be RouteRequest")
    if not isinstance(candidates, tuple) or any(
        not isinstance(item, ProviderCandidate) for item in candidates
    ):
        raise TypeError("candidates must be a tuple of ProviderCandidate")
    keys = [item.profile.key for item in candidates]
    if len(set(keys)) != len(keys):
        raise ValueError("duplicate provider profile keys")

    required = set(request.required_capabilities)
    excluded = set(request.excluded_profile_keys)
    eligible: list[ProviderProfile] = []
    rejected: list[tuple[str, str]] = []

    for candidate in candidates:
        profile = candidate.profile
        reason = None
        if profile.key in excluded:
            reason = "excluded_for_this_attempt"
        elif candidate.availability is not ProviderAvailability.AVAILABLE:
            reason = f"availability_{candidate.availability.value}"
        elif request.role not in profile.roles:
            reason = "role_not_supported"
        elif not required.issubset(set(profile.capabilities)):
            reason = "capability_missing"
        elif profile.cost_tier > request.max_cost_tier:
            reason = "cost_tier_exceeds_limit"
        elif request.max_estimated_cost_microunits is not None:
            estimate = profile.estimated_max_cost_microunits
            if estimate is None:
                reason = "cost_estimate_unknown"
            elif estimate > request.max_estimated_cost_microunits:
                reason = "estimated_cost_exceeds_limit"

        if reason is None:
            eligible.append(profile)
        else:
            rejected.append((profile.key, reason))

    eligible.sort(
        key=lambda profile: (
            int(profile.cost_tier),
            profile.preference_rank,
            profile.key,
        )
    )
    selected = eligible[0] if eligible else None
    return RouteDecision(
        selected=selected,
        eligible_profile_keys=tuple(item.key for item in eligible),
        rejected=tuple(rejected),
    )
