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
IMPLEMENTATION_ENTRY_STATUSES = {"ready-for-agent", "revalidated"}
TICKET_STATUS_TRANSITIONS = {
    "ready-for-agent": {"implementing"},
    "implementing": {"complete", "blocked-by-design"},
    "blocked-by-design": {"revising"},
    "revising": {"revalidated"},
    "revalidated": {"implementing"},
    "complete": set(),
}


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
    body = lines[1:end]
    index = 0
    while index < len(body):
        line = body[index]
        if not line.strip() or line.lstrip().startswith("#"):
            index += 1
            continue
        if ":" not in line:
            raise TicketError(f"无效 Ticket 配置行：{line}")
        key, raw = line.split(":", 1)
        key = key.strip()
        if not raw.strip():
            items: list[object] = []
            cursor = index + 1
            while cursor < len(body):
                candidate = body[cursor]
                if not candidate.strip() or candidate.lstrip().startswith("#"):
                    cursor += 1
                    continue
                if candidate[:1].isspace() and candidate.lstrip().startswith("- "):
                    items.append(_value(candidate.lstrip()[2:]))
                    cursor += 1
                    continue
                break
            if items:
                result[key] = items
                index = cursor
                continue
        result[key] = _value(raw)
        index += 1
    return result


def _admission_fields(ticket: dict[str, object], path: Path) -> dict[str, object]:
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
    spec_id = ticket.get("spec_id")
    spec_ref = ticket.get("spec_ref")
    revision = ticket.get("spec_revision")
    if not isinstance(spec_id, str) or not spec_id.strip():
        raise TicketError("ready-for-agent Ticket 必须声明 Spec 血缘：spec_id")
    if not isinstance(spec_ref, str) or not spec_ref.strip():
        raise TicketError("ready-for-agent Ticket 必须声明 Spec 血缘：spec_ref")
    if not (
        (isinstance(revision, int) and revision > 0)
        or (isinstance(revision, str) and revision.isdigit() and int(revision) > 0)
    ):
        raise TicketError("ready-for-agent Ticket 必须声明 Spec 血缘：正整数 spec_revision")
    return {
        "execution_agent": agent,
        "spec_id": spec_id,
        "spec_revision": int(revision),
        "spec_ref": spec_ref,
    }


def validate_ready_ticket(path: Path) -> dict[str, object]:
    ticket = frontmatter(path)
    if ticket.get("status") not in IMPLEMENTATION_ENTRY_STATUSES:
        return {"status": "not-ready", "path": str(path)}
    return {
        "status": "ready",
        "path": str(path),
        **_admission_fields(ticket, path),
    }


def validate_ticket_transition(path: Path, target_status: str) -> dict[str, object]:
    """Validate one explicit implementation Ticket state change without writing it."""
    ticket = frontmatter(path)
    if ticket.get("ticket_kind") != "implementation":
        raise TicketError("只有 implementation Ticket 可使用实施状态迁移")
    current = ticket.get("status")
    if current not in TICKET_STATUS_TRANSITIONS:
        raise TicketError(f"未知 implementation Ticket 状态：{current}")
    if target_status not in TICKET_STATUS_TRANSITIONS[current]:
        raise TicketError(f"非法 Ticket 状态迁移：{current} -> {target_status}")
    if target_status == "implementing" and current in IMPLEMENTATION_ENTRY_STATUSES:
        validate_ready_ticket(path)
    if target_status == "revalidated":
        _admission_fields(ticket, path)
    if target_status == "complete" and _unchecked_acceptance(path):
        raise TicketError("验收标准尚未全部勾选，Ticket 不得进入 complete")
    return {
        "status": "allow",
        "path": str(path),
        "from": current,
        "to": target_status,
    }


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
        if (
            ticket.get("ticket_kind") != "implementation"
            or ticket.get("status") not in IMPLEMENTATION_ENTRY_STATUSES
        ):
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
