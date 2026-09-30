import unittest

from tools.harness.action_policy import (
    ActionEffect,
    ActionRequest,
    PolicyDecision,
    PolicyRule,
    evaluate_action_policy,
)


class ActionPolicyTests(unittest.TestCase):
    def req(self, effect=ActionEffect.READ_ONLY, action="inspect", target="repo"):
        return ActionRequest(action=action, target=target, effect=effect)

    def test_read_only_defaults_to_allow(self):
        result = evaluate_action_policy(self.req(), interactive=False)
        self.assertEqual(result.decision, PolicyDecision.ALLOW)

    def test_write_defaults_to_confirmation_interactive_and_deny_headless(self):
        request = self.req(ActionEffect.REVERSIBLE_WRITE, "edit", "branch:file")
        self.assertEqual(
            evaluate_action_policy(request, interactive=True).decision,
            PolicyDecision.ASK_USER,
        )
        self.assertEqual(
            evaluate_action_policy(request, interactive=False).decision,
            PolicyDecision.DENY,
        )

    def test_specific_rule_can_allow_reversible_write(self):
        request = self.req(ActionEffect.REVERSIBLE_WRITE, "checkpoint", "draft:x")
        rule = PolicyRule(
            "allow-draft-checkpoint",
            PolicyDecision.ALLOW,
            priority=100,
            action="checkpoint",
            target_prefix="draft:",
        )
        result = evaluate_action_policy(request, interactive=False, rules=(rule,))
        self.assertEqual(result.decision, PolicyDecision.ALLOW)
        self.assertEqual(result.rule_name, rule.name)

    def test_protected_action_cannot_be_auto_allowed(self):
        request = self.req(ActionEffect.PROTECTED, "publish", "release:v1")
        rule = PolicyRule(
            "overbroad-allow",
            PolicyDecision.ALLOW,
            priority=999,
            action="publish",
        )
        interactive = evaluate_action_policy(request, interactive=True, rules=(rule,))
        headless = evaluate_action_policy(request, interactive=False, rules=(rule,))
        self.assertEqual(interactive.decision, PolicyDecision.ASK_USER)
        self.assertEqual(interactive.reason, "protected_action_requires_operator")
        self.assertEqual(headless.decision, PolicyDecision.DENY)

    def test_higher_priority_wins_and_equal_priority_fails_closed(self):
        request = self.req(ActionEffect.REVERSIBLE_WRITE, "write", "repo:file")
        allow = PolicyRule("allow", PolicyDecision.ALLOW, priority=10, action="write")
        ask = PolicyRule("ask", PolicyDecision.ASK_USER, priority=20, action="write")
        self.assertEqual(
            evaluate_action_policy(request, interactive=True, rules=(allow, ask)).decision,
            PolicyDecision.ASK_USER,
        )
        deny = PolicyRule("deny", PolicyDecision.DENY, priority=20, action="write")
        self.assertEqual(
            evaluate_action_policy(request, interactive=True, rules=(ask, deny)).decision,
            PolicyDecision.DENY,
        )

    def test_rule_filters_action_target_effect_and_mode(self):
        request = self.req(ActionEffect.REVERSIBLE_WRITE, "edit", "repo:docs/x")
        rules = (
            PolicyRule("wrong-action", PolicyDecision.DENY, priority=999, action="delete"),
            PolicyRule("wrong-target", PolicyDecision.DENY, priority=999, target_prefix="other:"),
            PolicyRule("wrong-effect", PolicyDecision.DENY, priority=999, effect=ActionEffect.READ_ONLY),
            PolicyRule("headless-only", PolicyDecision.DENY, priority=999, interactive=False),
            PolicyRule("match", PolicyDecision.ALLOW, priority=1, action="edit"),
        )
        result = evaluate_action_policy(request, interactive=True, rules=rules)
        self.assertEqual(result.decision, PolicyDecision.ALLOW)
        self.assertEqual(result.rule_name, "match")

    def test_invalid_policy_input_fails_closed_at_construction(self):
        with self.assertRaises(ValueError):
            ActionRequest("", "repo", ActionEffect.READ_ONLY)
        with self.assertRaises(ValueError):
            PolicyRule("x", PolicyDecision.ALLOW, priority=1000)
        with self.assertRaises(TypeError):
            evaluate_action_policy(self.req(), interactive="yes")  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
