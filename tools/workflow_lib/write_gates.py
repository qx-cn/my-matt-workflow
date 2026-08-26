"""Deterministic gates for the four profile-controlled write classes."""

from __future__ import annotations

from dataclasses import dataclass


_POLICY_BY_KIND = {
    "branch": "branch_policy",
    "commit": "commit_policy",
    "external": "external_write_policy",
    "docs": "docs_writeback",
}


@dataclass(frozen=True)
class WriteGate:
    status: str
    policy: str
    reason: str


def resolve_write_gate(
    profile: dict[str, object], *, kind: str, approved_scope: bool = False
) -> WriteGate:
    """Resolve one write without performing it.

    External writes need an already-approved target/scope even when the profile
    permits automatic external writes.  Fixed destructive prohibitions are not
    represented here and remain unconditional safety rules.
    """
    if kind not in _POLICY_BY_KIND:
        raise ValueError(f"未知写操作类型：{kind}")
    field = _POLICY_BY_KIND[kind]
    policy = profile.get(field)
    if policy not in {"allow", "confirm", "deny"}:
        raise ValueError(f"{field} 无效：{policy!r}")
    if policy == "deny":
        return WriteGate("deny", field, "policy-deny")
    if kind == "external" and policy == "allow" and not approved_scope:
        return WriteGate("pause", field, "new-external-authorization")
    if policy == "confirm":
        return WriteGate("confirm", field, "policy-confirm")
    return WriteGate("allow", field, "policy-allow")
