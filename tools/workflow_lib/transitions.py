"""Small, deterministic control surface for implementation Ticket handoff."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .tickets import TicketCandidate, eligible_local_tickets


@dataclass(frozen=True)
class Transition:
    status: str
    reason: str
    next_ticket: TicketCandidate | None = None


def ticket_transition(
    tickets_dir: Path,
    *,
    work_scope_policy: str,
    allowed_ids: set[str] | None = None,
    blocker: str | None = None,
) -> Transition:
    """Choose the post-completion action without performing any write.

    ``allowed_ids`` is the immutable full-auto scope captured when the host
    workflow begins.  It prevents newly created Tickets from expanding an
    approved plan mid-run.
    """
    if blocker:
        return Transition("pause", blocker)
    if work_scope_policy == "single-ticket":
        return Transition("complete", "single-ticket")
    if work_scope_policy not in {"ready-frontier", "approved-plan"}:
        return Transition("pause", f"unsupported-work-scope:{work_scope_policy}")
    candidates = eligible_local_tickets(
        tickets_dir,
        allowed_ids=allowed_ids if work_scope_policy == "approved-plan" else None,
    )
    if not candidates:
        return Transition("complete", "no-eligible-ticket")
    return Transition("continue", "next-eligible-ticket", candidates[0])
