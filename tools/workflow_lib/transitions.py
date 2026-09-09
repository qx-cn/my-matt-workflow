"""Small, deterministic control surface for implementation Ticket handoff."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

from .tickets import (
    TicketCandidate,
    TicketError,
    eligible_local_tickets,
    ticket_scope_state,
    ticket_definition_receipt,
)


@dataclass(frozen=True)
class Transition:
    status: str
    reason: str
    next_ticket: TicketCandidate | None = None


def create_approved_scope(tickets_dir: Path, allowed_ids: set[str]) -> dict[str, object]:
    """Create the immutable plan scope that a trusted host can persist at approval."""
    if not allowed_ids:
        raise TicketError("批准范围不能为空")
    records, scope = ticket_scope_state(tickets_dir, allowed_ids=allowed_ids)
    definitions = {
        identifier: ticket_definition_receipt(records[identifier][0])["sha256"]
        for identifier in sorted(scope)
    }
    payload: dict[str, object] = {
        "schema_version": 1,
        "kind": "approved-ticket-scope",
        "tickets_dir": str(tickets_dir.resolve()),
        "allowed_ids": sorted(scope),
        "definitions": definitions,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    payload["scope_id"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return payload


def _validated_scope(tickets_dir: Path, scope: object) -> set[str]:
    if not isinstance(scope, dict) or set(scope) != {
        "schema_version", "kind", "tickets_dir", "allowed_ids", "definitions", "scope_id"
    }:
        raise TicketError("approved scope artifact 字段无效")
    if scope.get("schema_version") != 1 or scope.get("kind") != "approved-ticket-scope":
        raise TicketError("approved scope artifact 版本或类型无效")
    raw_ids = scope.get("allowed_ids")
    if not isinstance(raw_ids, list) or not raw_ids or not all(isinstance(item, str) for item in raw_ids):
        raise TicketError("approved scope artifact 缺少 allowed_ids")
    if str(tickets_dir.resolve()) != scope.get("tickets_dir"):
        raise TicketError("approved scope artifact 的 Ticket 目录不匹配")
    expected = create_approved_scope(tickets_dir, set(raw_ids))
    if expected != scope:
        raise TicketError("approved scope artifact 已损坏或 Ticket definition 已漂移")
    return set(raw_ids)


def ticket_transition(
    tickets_dir: Path,
    *,
    work_scope_policy: str,
    allowed_ids: set[str] | None = None,
    approved_scope: dict[str, object] | None = None,
    blocker: str | None = None,
) -> Transition:
    """Choose the post-completion action without performing any write.

    ``allowed_ids`` is the immutable full-auto scope captured when the host
    workflow begins.  It prevents newly created Tickets from expanding an
    approved plan mid-run.
    """
    if blocker:
        return Transition("blocked", blocker)
    if work_scope_policy == "single-ticket":
        return Transition("complete", "single-ticket")
    if work_scope_policy not in {"ready-frontier", "approved-plan"}:
        return Transition("invalid", f"unsupported-work-scope:{work_scope_policy}")
    if work_scope_policy == "approved-plan" and approved_scope is None:
        return Transition("invalid", "approved-scope-missing")
    try:
        approved_ids = (
            _validated_scope(tickets_dir, approved_scope)
            if work_scope_policy == "approved-plan"
            else None
        )
        if work_scope_policy == "approved-plan" and allowed_ids is not None:
            return Transition("invalid", "legacy-allowed-ids-are-not-an-approved-scope")
        records, scope = ticket_scope_state(tickets_dir, allowed_ids=approved_ids)
        candidates = eligible_local_tickets(tickets_dir, allowed_ids=approved_ids)
    except TicketError as exc:
        return Transition("invalid", str(exc))
    if not candidates:
        if scope and all(records[identifier][1].get("status") == "complete" for identifier in scope):
            return Transition("complete", "approved-scope-complete")
        return Transition("blocked", "no-eligible-ticket")
    return Transition("continue", "next-eligible-ticket", candidates[0])
