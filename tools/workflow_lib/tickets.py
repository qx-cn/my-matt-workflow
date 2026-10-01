"""Mechanical admission checks for local implementation tickets."""

from __future__ import annotations

import json
import hashlib
import re
from pathlib import Path

from .rules import EXECUTION_AGENT_POLICIES


class TicketError(ValueError):
    """Raised when a ticket cannot enter implementation."""


_CHECKBOX = re.compile(r"^\s*- \[(?P<state>[ xX])\]\s+.+$", re.MULTILINE)
_ACCEPTANCE = re.compile(
    r"^\s*- \[(?P<state>[ xX])\]\s+(?P<text>.+)$", re.MULTILINE
)
REVIEW_PROBES = frozenset({"recovery", "unknown-response"})
IMPLEMENTATION_ENTRY_STATUSES = {"ready-for-agent"}
def _value(raw: str) -> object:
    value = raw.strip()
    if value.startswith("[") and value.endswith("]"):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            try:
                return json.loads(value.replace("'", '"'))
            except json.JSONDecodeError:
                pass
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
    if ticket.get("ticket_kind") != "implementation":
        raise TicketError("只有 implementation Ticket 可进入实施")
    if "claimed_by" not in ticket:
        raise TicketError("ready-for-agent Ticket 必须显式声明 claimed_by")
    claimed_by = ticket.get("claimed_by")
    if claimed_by is not None and not isinstance(claimed_by, str):
        raise TicketError(f"Ticket claimed_by 必须是字符串：{path}")
    if claimed_by not in {None, ""}:
        raise TicketError("ready-for-agent Ticket 已被认领")
    blocked_by = ticket.get("blocked_by")
    if not isinstance(blocked_by, list) or not all(
        isinstance(item, str) and item for item in blocked_by
    ):
        raise TicketError("ready-for-agent Ticket 必须声明 blocked_by 字符串列表")
    agent = ticket.get("execution_agent")
    if not isinstance(agent, str) or agent not in EXECUTION_AGENT_POLICIES:
        raise TicketError(
            "ready-for-agent Ticket 的 execution_agent 必须是 auto、codex、cursor 或 claude"
        )
    for field in ("rule_sources", "rule_scope", "rule_constraints", "rule_conflicts", "touchpoints"):
        if field in ticket and (not isinstance(ticket[field], list) or
                                not all(isinstance(x,str) and x.strip() for x in ticket[field])):
            raise TicketError(f"Ticket {field} 必须是字符串列表")
    if ticket.get("rule_conflicts"):
        raise TicketError("存在未解决 rule_conflicts，Ticket 不得进入实施")
    review_probes(ticket, path)
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
    validate_spec_lineage(path, ticket)
    return {
        "execution_agent": agent,
        "spec_id": spec_id,
        "spec_revision": int(revision),
        "spec_ref": spec_ref,
    }


def validate_spec_lineage(
    ticket_path: Path, ticket: dict[str, object] | None = None
) -> dict[str, object] | None:
    """Verify canonical local Ticket metadata against its referenced Spec."""
    ticket_path = ticket_path.resolve()
    parts = ticket_path.parts
    try:
        agent_index = parts.index(".agent")
    except ValueError:
        return None
    suffix = parts[agent_index:]
    if len(suffix) < 5 or suffix[1] != "work" or suffix[3] != "tickets":
        return None
    repo = Path(*parts[:agent_index])
    topic = suffix[2]
    metadata = ticket or frontmatter(ticket_path)
    raw_ref = metadata.get("spec_ref")
    if not isinstance(raw_ref, str) or not raw_ref:
        raise TicketError("Ticket Spec ref 无效")
    ref = Path(raw_ref)
    if ref.is_absolute() or ".." in ref.parts:
        raise TicketError("Ticket Spec ref 必须是仓库相对安全路径")
    spec_path = (repo / ref).resolve()
    expected_root = (repo / ".agent" / "work" / topic / "specs").resolve()
    if (
        spec_path.parent != expected_root
        or not spec_path.is_file()
        or spec_path.is_symlink()
    ):
        raise TicketError("Ticket Spec ref 必须指向同 topic 的 specs 直接子文件")
    spec = frontmatter(spec_path)
    try:
        ticket_revision = int(str(metadata.get("spec_revision")))
        spec_revision = int(str(spec.get("revision")))
    except ValueError as exc:
        raise TicketError("Spec revision 必须是正整数") from exc
    if (
        spec.get("spec_id") != metadata.get("spec_id")
        or spec_revision != ticket_revision
    ):
        raise TicketError("Ticket 的 spec_id/spec_revision 与 Spec frontmatter 不一致")
    return {
        "path": str(spec_path),
        "spec_id": spec["spec_id"],
        "revision": spec_revision,
    }


def _unchecked_acceptance(path):
    return any(match['state'] == ' ' for match in _CHECKBOX.finditer(path.read_text()))


def validate_ready_ticket(
    path: Path, *, dependency_statuses: dict[str, str] | None = None
) -> dict[str, object]:
    ticket = frontmatter(path)
    if ticket.get("status") not in IMPLEMENTATION_ENTRY_STATUSES:
        return {"status": "not-ready", "path": str(path)}
    admission = _admission_fields(ticket, path)
    blocked_by = ticket["blocked_by"]
    assert isinstance(blocked_by, list)
    if blocked_by:
        if dependency_statuses is None:
            raise TicketError("含依赖的 Ticket 必须在完整依赖图中验证")
        missing = [item for item in blocked_by if item not in dependency_statuses]
        if missing:
            raise TicketError(f"Ticket 依赖不存在：{', '.join(missing)}")
        unresolved = [item for item in blocked_by if dependency_statuses[item] != "complete"]
        if unresolved:
            raise TicketError(f"Ticket 依赖尚未完成：{', '.join(unresolved)}")
    if not _unchecked_acceptance(path):
        raise TicketError("ready-for-agent Ticket 必须至少包含一项未完成验收")
    return {
        "status": "ready",
        "path": str(path),
        **admission,
    }


def ticket_definition(path: Path) -> dict[str, object]:
    """Return the stable definition, excluding mutable claim/status/observations."""
    ticket = frontmatter(path)
    mutable_fields = {"status", "claimed_by"}
    metadata = {
        key: value for key, value in ticket.items() if key not in mutable_fields
    }
    text = path.read_text(encoding="utf-8")
    body = text.split("---", 2)[-1]
    stable_body = [
        re.sub(r"^(\s*- \[)[ xX](\])", r"\1 \2", line)
        for line in body.splitlines()
    ]
    return {"metadata": metadata, "body": "\n".join(stable_body).strip()}


def ticket_definition_receipt(path: Path) -> dict[str, object]:
    definition = ticket_definition(path)
    encoded = json.dumps(
        definition, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return {
        "kind": "ticket-definition",
        "path": str(path.resolve()),
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "size": len(encoded),
    }


def acceptance_items(path: Path) -> list[dict[str, str]]:
    """Return stable acceptance identifiers for a Ticket's checkbox criteria."""
    ticket = frontmatter(path)
    identifier = ticket.get("id")
    if not isinstance(identifier, str) or not identifier:
        raise TicketError("Ticket 缺少有效 id")
    return [
        {"id": f"{identifier}#A{index}", "text": match["text"].strip()}
        for index, match in enumerate(_ACCEPTANCE.finditer(path.read_text(encoding="utf-8")), start=1)
    ]


def review_probes(ticket: dict[str, object], path: Path) -> list[str]:
    """Validate the optional, explicitly declared self-review risk probes."""
    declared = ticket.get("review_probes", [])
    if not isinstance(declared, list) or not all(
        isinstance(item, str) and item in REVIEW_PROBES for item in declared
    ):
        raise TicketError(
            f"Ticket review_probes 必须是 {', '.join(sorted(REVIEW_PROBES))} 的去重列表：{path}"
        )
    if len(set(declared)) != len(declared):
        raise TicketError(f"Ticket review_probes 不得重复：{path}")
    return sorted(declared)
