"""Deterministic mapping from decision class and profile policy to one action."""

from __future__ import annotations

from dataclasses import dataclass


DECISION_CLASSES = {"routine", "consequential", "user-exclusive"}


@dataclass(frozen=True)
class DecisionGate:
    status: str
    decision_class: str
    policy: str
    reason: str


def resolve_decision_gate(
    profile: dict[str, object], *, decision_class: str
) -> DecisionGate:
    """Resolve a classified decision without making the decision itself."""
    if decision_class not in DECISION_CLASSES:
        raise ValueError(f"未知决策类型：{decision_class}")
    policy = profile.get("decision_policy")
    if policy not in {"ask", "autonomous", "halt"}:
        raise ValueError(f"decision_policy 无效：{policy!r}")

    if decision_class == "routine":
        return DecisionGate("allow", decision_class, str(policy), "routine-detail")
    if decision_class == "user-exclusive":
        status = "pause" if policy == "halt" else "confirm"
        return DecisionGate(status, decision_class, str(policy), "user-exclusive")
    if policy == "ask":
        return DecisionGate("confirm", decision_class, str(policy), "policy-ask")
    if policy == "halt":
        return DecisionGate("pause", decision_class, str(policy), "policy-halt")
    return DecisionGate("allow", decision_class, str(policy), "policy-autonomous")
