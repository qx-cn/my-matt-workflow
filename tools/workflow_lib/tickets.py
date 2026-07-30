"""Parse and select local workflow tickets without relying on Skill prose."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


IMPLEMENTATION = "implementation"
WAYFINDER_DECISION = "wayfinder-decision"
TICKET_KINDS = frozenset({IMPLEMENTATION, WAYFINDER_DECISION})
COMPLETE_STATUS = "complete"
READY_FOR_AGENT = "ready-for-agent"
_CHECKBOX = re.compile(r"^\s*[-*]\s+\[([ xX])\]\s+", re.MULTILINE)
_HEADING = re.compile(r"^#\s+(.+?)\s*$", re.MULTILINE)
_SEQUENCE = re.compile(r"^(?:tickets?-)?(\d+)(?:[-_.]|$)")


class TicketError(ValueError):
    """Base class for invalid local ticket data."""


class TicketParseError(TicketError):
    """Raised when a local ticket frontmatter document is malformed."""


class TicketGraphError(TicketError):
    """Raised when blockers cannot form a closed acyclic ticket graph."""


class TicketSelectionError(TicketError):
    """Raised when a requested ticket cannot be selected for implementation."""


@dataclass(frozen=True)
class Ticket:
    """One local ticket and the normalized fields used by workflow selection."""

    path: Path
    identifier: str
    title: str
    ticket_kind: str | None
    status: str | None
    blocked_by: tuple[str, ...]
    claimed_by: str | None
    tags: tuple[str, ...]
    sequence: int | None
    unchecked_acceptance: int
    checked_acceptance: int

    @property
    def is_wayfinder(self) -> bool:
        return self.ticket_kind == WAYFINDER_DECISION or any(
            tag.startswith("wayfinder:") for tag in self.tags
        )


@dataclass(frozen=True)
class TicketEligibility:
    """Eligibility verdict with stable machine-readable rejection reasons."""

    ticket: Ticket
    reasons: tuple[str, ...]

    @property
    def eligible(self) -> bool:
        return not self.reasons


@dataclass(frozen=True)
class TicketGraph:
    """Validated blocker graph and its unambiguous reference resolver."""

    tickets: tuple[Ticket, ...]
    blockers: dict[Ticket, tuple[Ticket, ...]]
    references: dict[str, tuple[Ticket, ...]]

    def resolve(self, reference: str) -> Ticket:
        normalized = _normalize_reference(reference)
        matches = self.references.get(normalized, ())
        if not matches:
            raise TicketGraphError(f"orphan ticket reference: {reference}")
        if len(matches) != 1:
            names = ", ".join(sorted(ticket.identifier for ticket in matches))
            raise TicketGraphError(
                f"ambiguous ticket reference: {reference} ({names})"
            )
        return matches[0]


def _normalize_reference(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TicketParseError("ticket reference must be a non-empty string")
    normalized = os.path.normpath(value.strip()).replace("\\", "/")
    return normalized.removeprefix("./")


def _parse_scalar(value: str, *, field: str) -> str | int | None:
    value = value.strip()
    if not value or value in {"null", "~"}:
        return None
    if value.startswith(("'", '"')) and value.endswith(value[0]):
        return value[1:-1]
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if value.startswith(("[", "{")):
        raise TicketParseError(f"{field} must not use an inline mapping")
    return value


def _parse_inline_list(value: str, *, field: str) -> list[str]:
    if not (value.startswith("[") and value.endswith("]")):
        raise TicketParseError(f"{field} must be a YAML list")
    contents = value[1:-1].strip()
    if not contents:
        return []
    values = []
    for item in contents.split(","):
        parsed = _parse_scalar(item, field=field)
        if not isinstance(parsed, str) or not parsed:
            raise TicketParseError(f"{field} entries must be non-empty strings")
        values.append(parsed)
    return values


def _parse_frontmatter(text: str) -> tuple[dict[str, object], str]:
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise TicketParseError("ticket must begin with YAML frontmatter")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise TicketParseError("ticket frontmatter has no closing delimiter") from exc

    data: dict[str, object] = {}
    index = 1
    while index < end:
        line = lines[index]
        index += 1
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith((" ", "\t")) or ":" not in line:
            raise TicketParseError(f"invalid frontmatter line: {line}")
        key, raw = line.split(":", 1)
        key = key.strip()
        raw = raw.strip()
        if not key or key in data:
            raise TicketParseError(f"invalid or duplicate frontmatter key: {key!r}")
        if raw.startswith("["):
            data[key] = _parse_inline_list(raw, field=key)
            continue
        if raw:
            data[key] = _parse_scalar(raw, field=key)
            continue

        values: list[str] = []
        while index < end and lines[index].startswith("  - "):
            item = _parse_scalar(lines[index][4:], field=key)
            if not isinstance(item, str) or not item:
                raise TicketParseError(
                    f"{key} entries must be non-empty strings"
                )
            values.append(item)
            index += 1
        data[key] = values if values else None
    return data, "\n".join(lines[end + 1 :])


def _required_string(data: dict[str, object], key: str, fallback: str) -> str:
    value = data.get(key, fallback)
    if not isinstance(value, str) or not value.strip():
        raise TicketParseError(f"{key} must be a non-empty string")
    return value.strip()


def _string_or_none(data: dict[str, object], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise TicketParseError(f"{key} must be a string")
    return value.strip() or None


def _string_list(
    data: dict[str, object], key: str, *, required: bool = False
) -> tuple[str, ...]:
    if key not in data:
        if required:
            raise TicketParseError(f"{key} must be a YAML list")
        return ()
    value = data[key]
    if value is None:
        raise TicketParseError(f"{key} must be a YAML list")
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise TicketParseError(f"{key} must be a YAML list of non-empty strings")
    return tuple(item.strip() for item in value)


def _sequence(data: dict[str, object], path: Path) -> int | None:
    value = data.get("sequence")
    if value is None:
        match = _SEQUENCE.match(path.stem)
        return int(match.group(1)) if match else None
    if not isinstance(value, int) or value < 0:
        raise TicketParseError("sequence must be a non-negative integer")
    return value


def parse_ticket(text: str, *, path: Path) -> Ticket:
    """Parse the local ticket frontmatter subset and acceptance checkboxes."""

    data, body = _parse_frontmatter(text)
    heading = _HEADING.search(body)
    title = _required_string(data, "title", heading.group(1) if heading else path.stem)
    ticket_kind = _string_or_none(data, "ticket_kind")
    if ticket_kind is not None and ticket_kind not in TICKET_KINDS:
        allowed = ", ".join(sorted(TICKET_KINDS))
        raise TicketParseError(f"ticket_kind must be one of: {allowed}")

    statuses = [mark.lower() for mark in _CHECKBOX.findall(body)]
    return Ticket(
        path=path,
        identifier=_required_string(data, "id", path.stem),
        title=title,
        ticket_kind=ticket_kind,
        status=_string_or_none(data, "status"),
        blocked_by=_string_list(data, "blocked_by", required=True),
        claimed_by=_string_or_none(data, "claimed_by"),
        tags=_string_list(data, "tags"),
        sequence=_sequence(data, path),
        unchecked_acceptance=statuses.count(" "),
        checked_acceptance=statuses.count("x"),
    )


def load_tickets(paths: Iterable[Path]) -> tuple[Ticket, ...]:
    """Load tickets in path order so results are repeatable across filesystems."""

    return tuple(
        parse_ticket(path.read_text(encoding="utf-8"), path=path)
        for path in sorted(paths, key=lambda item: item.as_posix())
    )


def _reference_index(tickets: Iterable[Ticket]) -> dict[str, tuple[Ticket, ...]]:
    index: dict[str, set[Ticket]] = {}
    for ticket in tickets:
        references = {
            ticket.identifier,
            ticket.title,
            ticket.path.as_posix(),
            ticket.path.name,
        }
        for reference in references:
            index.setdefault(_normalize_reference(reference), set()).add(ticket)
    return {
        reference: tuple(sorted(items, key=lambda ticket: ticket.identifier))
        for reference, items in index.items()
    }


def _find_cycle(blockers: dict[Ticket, tuple[Ticket, ...]]) -> list[Ticket] | None:
    visiting: set[Ticket] = set()
    visited: set[Ticket] = set()
    trail: list[Ticket] = []

    def visit(ticket: Ticket) -> list[Ticket] | None:
        if ticket in visiting:
            start = trail.index(ticket)
            return trail[start:] + [ticket]
        if ticket in visited:
            return None
        visiting.add(ticket)
        trail.append(ticket)
        for blocker in blockers[ticket]:
            cycle = visit(blocker)
            if cycle:
                return cycle
        trail.pop()
        visiting.remove(ticket)
        visited.add(ticket)
        return None

    for ticket in sorted(blockers, key=lambda item: item.identifier):
        cycle = visit(ticket)
        if cycle:
            return cycle
    return None


def build_ticket_graph(tickets: Iterable[Ticket]) -> TicketGraph:
    """Validate references and cycles, returning a resolver for a ticket set."""

    ordered = tuple(sorted(tickets, key=lambda ticket: ticket.path.as_posix()))
    identifiers = [ticket.identifier for ticket in ordered]
    if len(identifiers) != len(set(identifiers)):
        raise TicketGraphError("ticket identifiers must be unique")

    references = _reference_index(ordered)
    blockers: dict[Ticket, tuple[Ticket, ...]] = {}
    for ticket in ordered:
        resolved: list[Ticket] = []
        for reference in ticket.blocked_by:
            matches = references.get(_normalize_reference(reference), ())
            if not matches:
                raise TicketGraphError(
                    f"{ticket.identifier}: orphan ticket reference: {reference}"
                )
            if len(matches) != 1:
                names = ", ".join(item.identifier for item in matches)
                raise TicketGraphError(
                    f"{ticket.identifier}: ambiguous ticket reference: "
                    f"{reference} ({names})"
                )
            resolved.append(matches[0])
        blockers[ticket] = tuple(resolved)

    cycle = _find_cycle(blockers)
    if cycle:
        rendered = " -> ".join(ticket.identifier for ticket in cycle)
        raise TicketGraphError(f"ticket blocker cycle: {rendered}")
    return TicketGraph(ordered, blockers, references)


def ticket_eligibility(ticket: Ticket, graph: TicketGraph) -> TicketEligibility:
    """Evaluate every implementation gate for one ticket."""

    reasons: list[str] = []
    if ticket.ticket_kind is None:
        reasons.append("ticket_kind is missing or ambiguous")
    elif ticket.ticket_kind != IMPLEMENTATION:
        reasons.append("ticket_kind is not implementation")
    if ticket.is_wayfinder:
        reasons.append("wayfinder tickets cannot be implemented")
    if ticket.status != READY_FOR_AGENT:
        reasons.append("status is not ready-for-agent")
    if ticket.claimed_by is not None:
        reasons.append("ticket is already claimed")
    incomplete = [
        blocker.identifier
        for blocker in graph.blockers[ticket]
        if blocker.status != COMPLETE_STATUS
    ]
    if incomplete:
        reasons.append("blockers are incomplete: " + ", ".join(incomplete))
    if ticket.unchecked_acceptance == 0:
        reasons.append("no unchecked acceptance checkbox")
    return TicketEligibility(ticket, tuple(reasons))


def completion_problems(ticket: Ticket) -> tuple[str, ...]:
    """Return the gates that prevent closing a completed implementation ticket."""

    problems: list[str] = []
    if ticket.ticket_kind != IMPLEMENTATION or ticket.is_wayfinder:
        problems.append("only implementation tickets can pass implementation completion")
    if ticket.checked_acceptance + ticket.unchecked_acceptance == 0:
        problems.append("ticket has no acceptance checkboxes")
    if ticket.unchecked_acceptance:
        problems.append("acceptance checkboxes remain unchecked")
    return tuple(problems)


def _ticket_sort_key(ticket: Ticket) -> tuple[int, str]:
    return (
        ticket.sequence if ticket.sequence is not None else 2**63 - 1,
        ticket.identifier,
    )


def implementation_candidates(tickets: Iterable[Ticket]) -> tuple[Ticket, ...]:
    """Return every currently eligible unclaimed implementation ticket."""

    graph = build_ticket_graph(tickets)
    return tuple(
        sorted(
            (
                ticket
                for ticket in graph.tickets
                if ticket_eligibility(ticket, graph).eligible
            ),
            key=_ticket_sort_key,
        )
    )


def select_implementation_ticket(
    tickets: Iterable[Ticket], selected: str | None = None
) -> Ticket:
    """Select one eligible ticket, preserving invalid explicit selections."""

    graph = build_ticket_graph(tickets)
    if selected is not None:
        try:
            ticket = graph.resolve(selected)
        except TicketGraphError as exc:
            raise TicketSelectionError(str(exc)) from exc
        verdict = ticket_eligibility(ticket, graph)
        if not verdict.eligible:
            raise TicketSelectionError(
                f"{ticket.identifier} is not implementation-eligible: "
                + "; ".join(verdict.reasons)
            )
        return ticket

    candidates = sorted(
        (
            ticket
            for ticket in graph.tickets
            if ticket_eligibility(ticket, graph).eligible
        ),
        key=_ticket_sort_key,
    )
    if not candidates:
        raise TicketSelectionError("no implementation-eligible tickets")
    return candidates[0]
