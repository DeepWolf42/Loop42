import unittest

from tools.harness.provider_routing import (
    IncrementalCostTier,
    ProviderAvailability,
    ProviderCandidate,
    ProviderProfile,
    RouteRequest,
    select_provider,
)


def profile(
    key,
    *,
    roles=("execution",),
    caps=("propose_changes", "request_verification"),
    cost=IncrementalCostTier.ZERO_OR_INCLUDED,
    rank=100,
    estimate=0,
):
    return ProviderProfile(
        key=key,
        provider=key.split(":")[0],
        model=key,
        roles=roles,
        capabilities=caps,
        cost_tier=cost,
        preference_rank=rank,
        estimated_max_cost_microunits=estimate,
    )


class ProviderRoutingTests(unittest.TestCase):
    def test_zero_or_included_worker_wins_when_sufficient(self):
        local = ProviderCandidate(profile("local:model", rank=50), ProviderAvailability.AVAILABLE)
        paid = ProviderCandidate(
            profile(
                "paid:model",
                cost=IncrementalCostTier.LOW_METERED,
                rank=0,
                estimate=10,
            ),
            ProviderAvailability.AVAILABLE,
        )
        decision = select_provider(
            RouteRequest("execution", ("propose_changes",)),
            (paid, local),
        )
        self.assertEqual(decision.selected.key, "local:model")

    def test_cheaper_worker_is_skipped_when_role_or_capability_is_insufficient(self):
        cheap = ProviderCandidate(
            profile("local:fast", roles=("execution",), caps=("propose_changes",)),
            ProviderAvailability.AVAILABLE,
        )
        recovery = ProviderCandidate(
            profile(
                "paid:deep",
                roles=("recovery",),
                cost=IncrementalCostTier.STANDARD_METERED,
                estimate=50,
            ),
            ProviderAvailability.AVAILABLE,
        )
        decision = select_provider(
            RouteRequest(
                "recovery",
                ("propose_changes", "request_verification"),
            ),
            (cheap, recovery),
        )
        self.assertEqual(decision.selected.key, "paid:deep")
        self.assertIn(("local:fast", "role_not_supported"), decision.rejected)

    def test_unknown_or_unavailable_provider_is_never_selected(self):
        unknown = ProviderCandidate(profile("a:model"), ProviderAvailability.UNKNOWN)
        down = ProviderCandidate(profile("b:model"), ProviderAvailability.UNAVAILABLE)
        decision = select_provider(
            RouteRequest("execution", ("propose_changes",)),
            (unknown, down),
        )
        self.assertIsNone(decision.selected)

    def test_budget_filters_unknown_or_expensive_metered_cost(self):
        unknown_cost = ProviderCandidate(
            profile(
                "a:model",
                cost=IncrementalCostTier.LOW_METERED,
                estimate=None,
            ),
            ProviderAvailability.AVAILABLE,
        )
        expensive = ProviderCandidate(
            profile(
                "b:model",
                cost=IncrementalCostTier.LOW_METERED,
                estimate=101,
            ),
            ProviderAvailability.AVAILABLE,
        )
        okay = ProviderCandidate(
            profile(
                "c:model",
                cost=IncrementalCostTier.LOW_METERED,
                estimate=100,
            ),
            ProviderAvailability.AVAILABLE,
        )
        decision = select_provider(
            RouteRequest(
                "execution",
                ("propose_changes",),
                max_estimated_cost_microunits=100,
            ),
            (unknown_cost, expensive, okay),
        )
        self.assertEqual(decision.selected.key, "c:model")
        self.assertIn(("a:model", "cost_estimate_unknown"), decision.rejected)
        self.assertIn(("b:model", "estimated_cost_exceeds_limit"), decision.rejected)

    def test_preference_rank_breaks_ties_inside_same_cost_tier(self):
        a = ProviderCandidate(profile("a:model", rank=20), ProviderAvailability.AVAILABLE)
        b = ProviderCandidate(profile("b:model", rank=10), ProviderAvailability.AVAILABLE)
        decision = select_provider(
            RouteRequest("execution", ("propose_changes",)),
            (a, b),
        )
        self.assertEqual(decision.selected.key, "b:model")

    def test_exclusion_makes_retry_routing_visible(self):
        first = ProviderCandidate(profile("local:first", rank=0), ProviderAvailability.AVAILABLE)
        second = ProviderCandidate(profile("local:second", rank=1), ProviderAvailability.AVAILABLE)
        decision = select_provider(
            RouteRequest(
                "execution",
                ("propose_changes",),
                excluded_profile_keys=("local:first",),
            ),
            (first, second),
        )
        self.assertEqual(decision.selected.key, "local:second")
        self.assertIn(("local:first", "excluded_for_this_attempt"), decision.rejected)


if __name__ == "__main__":
    unittest.main()
