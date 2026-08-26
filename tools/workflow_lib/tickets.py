"""Mechanical admission checks for local implementation tickets."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .rules import EXECUTION_AGENTS


class TicketError(ValueError):
    """Raised when a ticket cannot enter implementation."""


_CHECKBOX = re.compile(r"^\s*- \[(?P<state>[ xX])\]\s+.+$", re.MULTILINE)


@dataclass(frozen=True)
class TicketCandidate:
    """A locally stored implementation Ticket eligible for deterministic ordering."""

    identifier: str
    path: Path
    sequence: int


def _value(raw: str) -> object:
    value = raw.strip()
    if value.startswith("[") and value.endswith("]"):
        try:
            return json.loads(value.replace("'", '"'))
        except json.JSONDecodeError:
            contents = value[1:-1].strip()
            if not contents:
                return []
            return [item.strip().strip("\"'") for item in contents.split(",")]
    return value.strip("\"'")


def frontmatter(path: Path) -> dict[str, object]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        raise TicketError("Ticket 缺少 YAML frontmatter")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise TicketError("Ticket frontmatter 未结束") from exc
    result: dict[str, object] = {}
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            raise TicketError(f"无效 Ticket 配置行：{line}")
        key, raw = line.split(":", 1)
        result[key.strip()] = _value(raw)
    return result


def validate_ready_ticket(path: Path) -> dict[str, object]:
    ticket = frontmatter(path)
    if ticket.get("status") != "ready-for-agent":
        return {"status": "not-ready", "path": str(path)}
    agent = ticket.get("execution_agent")
    if agent not in EXECUTION_AGENTS:
        raise TicketError("ready-for-agent Ticket 必须指定 execution_agent")
    for field in ("rule_sources", "rule_scope", "rule_constraints", "rule_conflicts"):
        if not isinstance(ticket.get(field), list):
            raise TicketError(f"ready-for-agent Ticket 必须声明 {field} 列表")
    if not ticket["rule_sources"] or not ticket["rule_scope"] or not ticket["rule_constraints"]:
        raise TicketError("ready-for-agent Ticket 必须具备规则来源、作用范围和派生约束")
    if ticket["rule_conflicts"]:
        raise TicketError("存在未解决 rule_conflicts，Ticket 不得进入实施")
    return {"status": "ready", "path": str(path), "execution_agent": agent}


def _sequence(ticket: dict[str, object], path: Path) -> int:
    value = ticket.get("sequence")
    if isinstance(value, str) and value.isdigit():
        return int(value)
    if isinstance(value, int):
        return value
    raise TicketError(f"Ticket 缺少有效 sequence：{path}")


def _unchecked_acceptance(path: Path) -> bool:
    return any(match["state"] == " " for match in _CHECKBOX.finditer(path.read_text(encoding="utf-8")))


def eligible_local_tickets(tickets_dir: Path, *, allowed_ids: set[str] | None = None) -> list[TicketCandidate]:
    """Return ready local implementation Tickets in stable workflow order.

    This is intentionally read-only: claiming, completing, and committing stay
    in the host workflow, so selecting the next Ticket cannot mutate a project.
    """
    if not tickets_dir.is_dir():
        raise TicketError(f"Ticket 目录不存在：{tickets_dir}")
    records: dict[str, tuple[Path, dict[str, object]]] = {}
    for path in sorted(tickets_dir.glob("*.md")):
        ticket = frontmatter(path)
        identifier = ticket.get("id")
        if not isinstance(identifier, str) or not identifier:
            raise TicketError(f"Ticket 缺少有效 id：{path}")
        if identifier in records:
            raise TicketError(f"Ticket id 重复：{identifier}")
        records[identifier] = (path, ticket)

    candidates: list[TicketCandidate] = []
    for identifier, (path, ticket) in records.items():
        if allowed_ids is not None and identifier not in allowed_ids:
            continue
        if ticket.get("ticket_kind") != "implementation" or ticket.get("status") != "ready-for-agent":
            continue
        if ticket.get("claimed_by") not in {None, ""}:
            continue
        blocked_by = ticket.get("blocked_by")
        if not isinstance(blocked_by, list):
            raise TicketError(f"Ticket blocked_by 必须是列表：{path}")
        missing = [blocker for blocker in blocked_by if blocker not in records]
        if missing:
            raise TicketError(f"Ticket 依赖不存在：{identifier} -> {', '.join(map(str, missing))}")
        if any(records[blocker][1].get("status") != "complete" for blocker in blocked_by):
            continue
        if not _unchecked_acceptance(path):
            continue
        validate_ready_ticket(path)
        candidates.append(TicketCandidate(identifier, path, _sequence(ticket, path)))
    return sorted(candidates, key=lambda candidate: (candidate.sequence, candidate.identifier))


def implementation_ticket_ids(tickets_dir: Path) -> list[str]:
    """Return the immutable local implementation scope in stable id order."""
    if not tickets_dir.is_dir():
        raise TicketError(f"Ticket 目录不存在：{tickets_dir}")
    identifiers: set[str] = set()
    for path in sorted(tickets_dir.glob("*.md")):
        ticket = frontmatter(path)
        if ticket.get("ticket_kind") != "implementation":
            continue
        identifier = ticket.get("id")
        if not isinstance(identifier, str) or not identifier:
            raise TicketError(f"Ticket 缺少有效 id：{path}")
        if identifier in identifiers:
            raise TicketError(f"Ticket id 重复：{identifier}")
        identifiers.add(identifier)
    return sorted(identifiers)
