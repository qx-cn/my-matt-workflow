"""Mechanical admission checks for local implementation tickets."""

from __future__ import annotations

import json
from pathlib import Path

from .rules import EXECUTION_AGENTS


class TicketError(ValueError):
    """Raised when a ticket cannot enter implementation."""


def _value(raw: str) -> object:
    value = raw.strip()
    if value.startswith("[") and value.endswith("]"):
        return json.loads(value.replace("'", '"'))
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
