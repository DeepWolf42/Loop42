import unittest
from datetime import datetime, timedelta, timezone

from tools.harness.retry_policy import (
    FailureClass,
    RetryDecision,
    assess_retry,
)
from tools.harness.side_effect_reconcile import (
    SideEffectIntent,
    SideEffectObservation,
    SideEffectState,
    reconcile_side_effect,
)


class RetryPolicyTests(unittest.TestCase):
    def assess(self, **kwargs):
        values = dict(
            failure=FailureClass.TRANSIENT,
            attempt=1,
            max_attempts=4,
            fresh_evidence=True,
            side_effect_possible=False,
        )
        values.update(kwargs)
        return assess_retry(**values)

    def test_transient_failure_uses_bounded_exponential_backoff(self):
        self.assertEqual(self.assess(attempt=1).delay_seconds, 10)
        self.assertEqual(self.assess(attempt=2).delay_seconds, 20)
        self.assertEqual(self.assess(attempt=3).delay_seconds, 40)
        capped = self.assess(
            attempt=3, base_delay_seconds=20, max_delay_seconds=30
        )
        self.assertEqual(capped.delay_seconds, 30)
        self.assertEqual(capped.decision, RetryDecision.RETRY_AFTER_BACKOFF)

    def test_unknown_conflict_or_stale_evidence_requires_reconciliation(self):
        cases = (
            dict(failure=FailureClass.UNKNOWN),
            dict(failure=FailureClass.CONFLICT),
            dict(fresh_evidence=False),
            dict(
                side_effect_possible=True,
                side_effect_state=SideEffectState.UNKNOWN,
            ),
            dict(
                side_effect_possible=True,
                side_effect_state=SideEffectState.CONFLICT,
            ),
        )
        for case in cases:
            with self.subTest(case=case):
                result = self.assess(**case)
                self.assertEqual(result.decision, RetryDecision.RECONCILE)
                self.assertIsNone(result.delay_seconds)

    def test_applied_side_effect_is_never_retried(self):
        result = self.assess(
            side_effect_possible=True,
            side_effect_state=SideEffectState.APPLIED,
        )
        self.assertEqual(result.decision, RetryDecision.DO_NOT_RETRY)
        self.assertIn("side_effect_already_applied", result.reasons)

    def test_not_applied_side_effect_still_needs_other_retry_gates(self):
        retry = self.assess(
            side_effect_possible=True,
            side_effect_state=SideEffectState.NOT_APPLIED,
        )
        self.assertEqual(retry.decision, RetryDecision.RETRY_AFTER_BACKOFF)
        self.assertIn("side_effect_confirmed_not_applied", retry.reasons)

        unknown = self.assess(
            failure=FailureClass.UNKNOWN,
            side_effect_possible=True,
            side_effect_state=SideEffectState.NOT_APPLIED,
        )
        self.assertEqual(unknown.decision, RetryDecision.RECONCILE)

    def test_possible_side_effect_requires_explicit_reconciled_state(self):
        missing = self.assess(side_effect_possible=True)
        self.assertEqual(missing.decision, RetryDecision.RECONCILE)
        self.assertIsNone(missing.delay_seconds)
        self.assertIn("side_effect_state_missing", missing.reasons)

    def test_retry_requires_prior_attempt_proven_quiescent(self):
        now = datetime(2026, 10, 15, 9, 0, tzinfo=timezone.utc)
        intent = SideEffectIntent(
            action_id="attempt-1",
            action="write",
            target="repo:config.txt",
            state_scope="repo.file.v1",
            before_fingerprint="a" * 64,
            desired_fingerprint="b" * 64,
        )

        def observe(**overrides):
            values = dict(
                observed_at=now,
                target=intent.target,
                state_scope=intent.state_scope,
                state_fingerprint=intent.before_fingerprint,
            )
            values.update(overrides)
            return reconcile_side_effect(
                intent,
                now=now,
                observation=SideEffectObservation(**values),
            )

        # The unchanged file can be read before an interrupted write finishes.
        # A caller cannot safely turn that observation into NOT_APPLIED.
        for evidence in (
            {},
            {"quiescent_action_id": "another-attempt"},
            {
                "quiescent_action_id": intent.action_id,
                "observed_at": now - timedelta(seconds=301),
            },
        ):
            with self.subTest(evidence=evidence):
                reconciled = observe(**evidence)
                self.assertEqual(reconciled.state, SideEffectState.UNKNOWN)
                self.assertFalse(reconciled.may_reconsider)
                retry = self.assess(
                    side_effect_possible=True,
                    side_effect_state=reconciled.state,
                )
                self.assertEqual(retry.decision, RetryDecision.RECONCILE)
                self.assertIsNone(retry.delay_seconds)

        # A matching provider-proven quiescence marker is a required
        # prerequisite, not by itself an execution permission.
        confirmed = observe(quiescent_action_id=intent.action_id)
        self.assertEqual(confirmed.state, SideEffectState.NOT_APPLIED)
        self.assertTrue(confirmed.may_reconsider)
        eligible = self.assess(
            side_effect_possible=True,
            side_effect_state=confirmed.state,
        )
        self.assertEqual(eligible.decision, RetryDecision.RETRY_AFTER_BACKOFF)
        self.assertEqual(eligible.delay_seconds, 10)

    def test_safety_stop_requires_operator_and_permanent_failure_stops(self):
        safety = self.assess(failure=FailureClass.SAFETY_STOP)
        self.assertEqual(safety.decision, RetryDecision.OPERATOR_REQUIRED)
        self.assertIsNone(safety.delay_seconds)

        permanent = self.assess(failure=FailureClass.PERMANENT)
        self.assertEqual(permanent.decision, RetryDecision.DO_NOT_RETRY)
        self.assertIsNone(permanent.delay_seconds)

    def test_retry_budget_is_hard_cap(self):
        result = self.assess(attempt=4, max_attempts=4)
        self.assertEqual(result.decision, RetryDecision.DO_NOT_RETRY)
        self.assertEqual(result.attempts_remaining, 0)
        self.assertIn("retry_budget_exhausted", result.reasons)

    def test_invalid_inputs_fail_closed(self):
        with self.assertRaises(TypeError):
            self.assess(failure="transient")
        with self.assertRaises(TypeError):
            self.assess(fresh_evidence=1)
        with self.assertRaises(ValueError):
            self.assess(attempt=0)
        with self.assertRaises(ValueError):
            self.assess(max_attempts=0)
        with self.assertRaises(TypeError):
            self.assess(side_effect_possible=1)
        with self.assertRaises(TypeError):
            self.assess(
                side_effect_possible=True,
                side_effect_state="not_applied",
            )
        with self.assertRaises(ValueError):
            self.assess(side_effect_state=SideEffectState.NOT_APPLIED)


if __name__ == "__main__":
    unittest.main()
