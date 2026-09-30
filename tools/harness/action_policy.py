"""Small fail-closed action policy for Loop42 harness consumers.

This module classifies whether a proposed tool/action may proceed automatically,
must be confirmed by the operator, or must be denied. It never executes actions.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ActionEffect(str, Enum):
    READ_ONLY = "read_only"
    REVERSIBLE_WRITE = "reversible_write"
    PROTECTED = "protected"


class PolicyDecision(str, Enum):
    ALLOW = "allow"
    ASK_USER = "ask_user"
    DENY = "deny"


_DECISION_RANK = {
    PolicyDecision.DENY: 3,
    PolicyDecision.ASK_USER: 2,
    PolicyDecision.ALLOW: 1,
}


@dataclass(frozen=True)
class ActionRequest:
    action: str
    target: str
    effect: ActionEffect

    def __post_init__(self) -> None:
        if not isinstance(self.action, str) or not self.action.strip():
            raise ValueError("action must be non-empty text")
        if not isinstance(self.target, str) or not self.target.strip():
            raise ValueError("target must be non-empty text")
        if not isinstance(self.effect, ActionEffect):
            raise TypeError("effect must be ActionEffect")


@dataclass(frozen=True)
class PolicyRule:
    name: str
    decision: PolicyDecision
    priority: int = 0
    action: str | None = None
    target_prefix: str | None = None
    effect: ActionEffect | None = None
    interactive: bool | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("rule name must be non-empty text")
        if not isinstance(self.decision, PolicyDecision):
            raise TypeError("decision must be PolicyDecision")
        if isinstance(self.priority, bool) or not isinstance(self.priority, int):
            raise TypeError("priority must be an integer")
        if not 0 <= self.priority <= 999:
            raise ValueError("priority must be between 0 and 999")
        if self.action is not None and (
            not isinstance(self.action, str) or not self.action.strip()
        ):
            raise ValueError("rule action must be non-empty text")
        if self.target_prefix is not None and (
            not isinstance(self.target_prefix, str) or not self.target_prefix
        ):
            raise ValueError("target_prefix must be non-empty text")
        if self.effect is not None and not isinstance(self.effect, ActionEffect):
            raise TypeError("rule effect must be ActionEffect")
        if self.interactive is not None and type(self.interactive) is not bool:
            raise TypeError("interactive must be bool or None")


@dataclass(frozen=True)
class PolicyResult:
    decision: PolicyDecision
    reason: str
    rule_name: str | None


def _matches(rule: PolicyRule, request: ActionRequest, interactive: bool) -> bool:
    if rule.action is not None and rule.action != request.action:
        return False
    if rule.target_prefix is not None and not request.target.startswith(rule.target_prefix):
        return False
    if rule.effect is not None and rule.effect is not request.effect:
        return False
    if rule.interactive is not None and rule.interactive is not interactive:
        return False
    return True


def _default(request: ActionRequest) -> PolicyDecision:
    if request.effect is ActionEffect.READ_ONLY:
        return PolicyDecision.ALLOW
    return PolicyDecision.ASK_USER


def evaluate_action_policy(
    request: ActionRequest,
    *,
    interactive: bool,
    rules: tuple[PolicyRule, ...] = (),
) -> PolicyResult:
    """Evaluate one action without granting execution authority.

    Highest priority wins. Equal-priority conflicts fail closed in the order
    DENY > ASK_USER > ALLOW. Protected actions can never be auto-allowed by a
    normal rule: an ALLOW result is downgraded to ASK_USER. In non-interactive
    mode every ASK_USER result becomes DENY.
    """
    if not isinstance(request, ActionRequest):
        raise TypeError("request must be ActionRequest")
    if type(interactive) is not bool:
        raise TypeError("interactive must be bool")
    if not isinstance(rules, tuple) or any(not isinstance(r, PolicyRule) for r in rules):
        raise TypeError("rules must be a tuple of PolicyRule")

    matched = [rule for rule in rules if _matches(rule, request, interactive)]
    if matched:
        matched.sort(
            key=lambda rule: (-rule.priority, -_DECISION_RANK[rule.decision], rule.name)
        )
        winner = matched[0]
        decision = winner.decision
        reason = "matched_rule"
        rule_name = winner.name
    else:
        decision = _default(request)
        reason = "default_effect_policy"
        rule_name = None

    if request.effect is ActionEffect.PROTECTED and decision is PolicyDecision.ALLOW:
        decision = PolicyDecision.ASK_USER
        reason = "protected_action_requires_operator"
    if not interactive and decision is PolicyDecision.ASK_USER:
        decision = PolicyDecision.DENY
        reason = "headless_confirmation_denied"

    return PolicyResult(decision=decision, reason=reason, rule_name=rule_name)
