import unittest
from datetime import datetime, timedelta, timezone

from tools.harness.side_effect_reconcile import (
    SideEffectIntent,
    SideEffectObservation,
    SideEffectState,
    reconcile_side_effect,
)


class SideEffectReconcileTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 1, 5, 0, tzinfo=timezone.utc)
        self.intent = SideEffectIntent(
            action_id="merge-pr-27",
            action="merge_pull_request",
            target="github:DeepWolf42/Loop42:pr:27",
            state_scope="github.pr.merge-state.v1",
            before_fingerprint="a" * 64,
            desired_fingerprint="b" * 64,
        )

    def obs(self, fingerprint="a" * 64, **kwargs):
        values = dict(
            observed_at=self.now,
            target=self.intent.target,
            state_scope=self.intent.state_scope,
            state_fingerprint=fingerprint,
        )
        values.update(kwargs)
        return SideEffectObservation(**values)

    def test_lost_response_after_success_is_applied_and_never_reconsidered(self):
        result = reconcile_side_effect(
            self.intent, now=self.now, observation=self.obs("b" * 64)
        )
        self.assertEqual(result.state, SideEffectState.APPLIED)
        self.assertFalse(result.may_reconsider)

    def test_unchanged_pre_action_state_is_not_applied_but_requires_fresh_decision(self):
        result = reconcile_side_effect(
            self.intent, now=self.now,
            observation=self.obs("a" * 64, quiescent_action_id=self.intent.action_id),
        )
        self.assertEqual(result.state, SideEffectState.NOT_APPLIED)
        self.assertTrue(result.may_reconsider)

    def test_diverged_state_is_conflict(self):
        result = reconcile_side_effect(
            self.intent, now=self.now, observation=self.obs("c" * 64)
        )
        self.assertEqual(result.state, SideEffectState.CONFLICT)
        self.assertFalse(result.may_reconsider)

    def test_unchanged_target_during_inflight_request_does_not_prove_not_applied(self):
        # A read can overtake the original write after the caller loses its reply.
        # Freshness and exact target identity cannot prove the request has ended.
        result = reconcile_side_effect(
            self.intent, now=self.now, observation=self.obs()
        )
        self.assertEqual(result.state, SideEffectState.UNKNOWN)
        self.assertFalse(result.may_reconsider)

    def test_quiescence_of_another_attempt_cannot_enable_reconsideration(self):
        result = reconcile_side_effect(
            self.intent, now=self.now,
            observation=self.obs(quiescent_action_id="other-attempt"),
        )
        self.assertEqual(result.state, SideEffectState.UNKNOWN)
        self.assertFalse(result.may_reconsider)

    def test_late_write_after_unknown_is_observed_without_replay(self):
        first = reconcile_side_effect(self.intent, now=self.now, observation=self.obs())
        self.assertFalse(first.may_reconsider)
        # Provider completes the original request after the first observation.
        later = reconcile_side_effect(
            self.intent, now=self.now + timedelta(seconds=1),
            observation=self.obs("b" * 64, observed_at=self.now + timedelta(seconds=1)),
        )
        self.assertEqual(later.state, SideEffectState.APPLIED)
        self.assertFalse(later.may_reconsider)

    def test_quiescence_does_not_override_stale_or_incomplete_observations(self):
        for changes in (dict(complete=False), dict(valid=False),
                        dict(observed_at=self.now - timedelta(seconds=301))):
            result = reconcile_side_effect(
                self.intent, now=self.now,
                observation=self.obs(quiescent_action_id=self.intent.action_id, **changes),
            )
            self.assertEqual(result.state, SideEffectState.UNKNOWN)
            self.assertFalse(result.may_reconsider)

    def test_quiescence_identity_is_validated(self):
        for value in (True, 1, "", "invalid id", "x" * 129):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.obs(quiescent_action_id=value)

    def test_missing_stale_future_and_invalid_evidence_are_unknown(self):
        self.assertEqual(
            reconcile_side_effect(self.intent, now=self.now, observation=None).state,
            SideEffectState.UNKNOWN,
        )
        stale = self.obs(observed_at=self.now - timedelta(seconds=301))
        future = self.obs(observed_at=self.now + timedelta(seconds=1))
        invalid = self.obs(valid=False)
        incomplete = self.obs(complete=False)
        for observation in (stale, future, invalid, incomplete):
            with self.subTest(observation=observation):
                result = reconcile_side_effect(
                    self.intent, now=self.now, observation=observation
                )
                self.assertEqual(result.state, SideEffectState.UNKNOWN)
                self.assertFalse(result.may_reconsider)

    def test_wrong_target_or_projection_scope_fails_closed_as_conflict(self):
        wrong_target = self.obs(target="github:DeepWolf42/Loop42:pr:28")
        wrong_scope = self.obs(state_scope="github.pr.other-state.v1")
        for observation in (wrong_target, wrong_scope):
            with self.subTest(observation=observation):
                result = reconcile_side_effect(
                    self.intent, now=self.now, observation=observation
                )
                self.assertEqual(result.state, SideEffectState.CONFLICT)
                self.assertFalse(result.may_reconsider)

    def test_ambiguous_intent_and_bad_inputs_are_rejected(self):
        with self.assertRaises(ValueError):
            SideEffectIntent(
                action_id="x",
                action="write",
                target="repo:file",
                state_scope="repo.file.v1",
                before_fingerprint="a" * 64,
                desired_fingerprint="a" * 64,
            )
        with self.assertRaises(ValueError):
            SideEffectObservation(
                observed_at=self.now.replace(tzinfo=None),
                target=self.intent.target,
                state_scope=self.intent.state_scope,
                state_fingerprint="a" * 64,
            )
        with self.assertRaises(TypeError):
            reconcile_side_effect(
                self.intent,
                now=self.now,
                observation=self.obs(),
                freshness_seconds=True,
            )


if __name__ == "__main__":
    unittest.main()
