"""Resolved implementation context and recoverable local run journals."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .profile import ProfileError, effective_profile, parse_profile
from .rules import RuleError, resolve_rules
from .tickets import TicketError, frontmatter, validate_ready_ticket
from .write_gates import resolve_write_gate


class RunJournalError(ValueError):
    """Raised when an implementation context or journal is invalid."""


RUN_PHASE_TRANSITIONS = {
    "admitted": {"testing", "implementing", "blocked-by-design"},
    "testing": {"implementing", "blocked-by-design"},
    "implementing": {"testing", "reviewing", "blocked-by-design"},
    "blocked-by-design": {"revising"},
    "revising": {"testing", "implementing", "blocked-by-design"},
    "reviewing": {"implementing", "committing", "blocked-by-design"},
    "committing": {"complete", "blocked-by-design"},
    "complete": set(),
}
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def _git_sha(repo: Path, value: str) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", f"{value}^{{commit}}"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise RunJournalError(f"无法解析 Git 固定点 {value!r}")
    return result.stdout.strip()


def _ticket_location(repo: Path, ticket_path: Path) -> tuple[Path, str]:
    resolved = ticket_path.resolve()
    try:
        relative = resolved.relative_to(repo)
    except ValueError as exc:
        raise RunJournalError("Ticket 必须位于当前仓库") from exc
    parts = relative.parts
    if len(parts) < 5 or parts[:2] != (".agent", "work") or parts[3] != "tickets":
        raise RunJournalError("本地 Ticket 必须位于 .agent/work/<topic>/tickets/")
    return resolved, parts[2]


def build_run_context(
    repo: Path, ticket_path: Path, base: str, paths: list[str] | None = None
) -> dict[str, object]:
    """Resolve profile, lineage and write gates once without mutating the repo."""
    repo = repo.resolve()
    ticket_path, topic = _ticket_location(repo, ticket_path)
    try:
        raw_profile, _ = parse_profile(
            (repo / ".agent" / "matt-workflow.md").read_text(encoding="utf-8")
        )
        profile = effective_profile(raw_profile)
        ticket = frontmatter(ticket_path)
    except (OSError, ProfileError, TicketError) as exc:
        raise RunJournalError(str(exc)) from exc

    ticket_id = ticket.get("id")
    if not isinstance(ticket_id, str) or not _SAFE_ID.fullmatch(ticket_id):
        raise RunJournalError("Ticket id 缺失或不能用于 run journal")
    required = ("spec_id", "spec_revision", "spec_ref", "execution_agent", "status")
    missing = [field for field in required if ticket.get(field) in {None, ""}]
    if missing:
        raise RunJournalError(f"Ticket 缺少运行上下文字段：{', '.join(missing)}")

    gates = {
        kind: resolve_write_gate(profile, kind=kind).__dict__
        for kind in ("branch", "commit", "external", "docs")
    }
    try:
        rule_map = resolve_rules(repo, str(ticket["execution_agent"]), paths or [])
    except RuleError as exc:
        raise RunJournalError(str(exc)) from exc
    context: dict[str, object] = {
        "schema_version": 1,
        "repo": str(repo),
        "topic": topic,
        "ticket": {
            "id": ticket_id,
            "path": str(ticket_path),
            "status": ticket["status"],
            "execution_agent": ticket["execution_agent"],
        },
        "spec": {
            "id": ticket["spec_id"],
            "revision": int(ticket["spec_revision"]),
            "ref": ticket["spec_ref"],
        },
        "base_sha": _git_sha(repo, base),
        "policies": {
            key: profile[key]
            for key in (
                "composition_policy",
                "work_scope_policy",
                "decision_policy",
                "humanizer_policy",
            )
        },
        "write_gates": gates,
        "test_commands": profile["test_commands"],
        "standards_sources": profile["standards_sources"],
        "domain_sources": profile["domain_sources"],
        "rule_map": rule_map,
    }
    canonical = json.dumps(context, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    context["context_id"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return context


def _write_json_atomic(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
        ) as handle:
            temporary = Path(handle.name)
            json.dump(value, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def start_run(
    repo: Path, ticket_path: Path, base: str, paths: list[str] | None = None
) -> tuple[Path, dict[str, object]]:
    try:
        admission = validate_ready_ticket(ticket_path)
    except TicketError as exc:
        raise RunJournalError(str(exc)) from exc
    if admission["status"] != "ready":
        raise RunJournalError("run-start 只接受 ready-for-agent 或 revalidated Ticket")
    context = build_run_context(repo, ticket_path, base, paths)
    ticket = context["ticket"]
    assert isinstance(ticket, dict)
    spec = context["spec"]
    assert isinstance(spec, dict)
    path = (
        repo.resolve()
        / ".agent"
        / "work"
        / str(context["topic"])
        / "runs"
        / f"run-{ticket['id']}-spec-r{spec['revision']}.json"
    )
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing.get("context", {}).get("context_id") != context["context_id"]:
            raise RunJournalError(f"run journal 已存在且上下文不同：{path}")
        return path, existing
    now = datetime.now(timezone.utc).isoformat()
    journal: dict[str, object] = {
        "schema_version": 1,
        "run_id": ticket["id"],
        "phase": "admitted",
        "context": context,
        "receipts": {"test": None, "review": None},
        "blocker": None,
        "events": [{"phase": "admitted", "at": now}],
    }
    _write_json_atomic(path, journal)
    return path, journal


def record_run(
    path: Path,
    phase: str,
    *,
    test_receipt: str | None = None,
    review_receipt: str | None = None,
    blocker: str | None = None,
) -> dict[str, object]:
    """Record one validated phase transition and optional evidence receipts."""
    try:
        journal = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RunJournalError(f"无法读取 run journal：{path}") from exc
    current = journal.get("phase")
    if current not in RUN_PHASE_TRANSITIONS or phase not in RUN_PHASE_TRANSITIONS[current]:
        raise RunJournalError(f"非法 run phase 迁移：{current} -> {phase}")
    if phase == "blocked-by-design" and not blocker:
        raise RunJournalError("进入 blocked-by-design 必须记录 blocker")
    receipts = journal.get("receipts")
    if not isinstance(receipts, dict):
        raise RunJournalError("run journal receipts 无效")
    if test_receipt is not None:
        receipts["test"] = test_receipt
    if review_receipt is not None:
        receipts["review"] = review_receipt
    journal["phase"] = phase
    journal["blocker"] = blocker if phase == "blocked-by-design" else None
    events = journal.get("events")
    if not isinstance(events, list):
        raise RunJournalError("run journal events 无效")
    event: dict[str, object] = {
        "phase": phase,
        "at": datetime.now(timezone.utc).isoformat(),
    }
    if blocker:
        event["blocker"] = blocker
    if test_receipt is not None:
        event["test_receipt"] = test_receipt
    if review_receipt is not None:
        event["review_receipt"] = review_receipt
    events.append(event)
    _write_json_atomic(path, journal)
    return journal
