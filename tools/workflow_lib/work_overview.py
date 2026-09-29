"""Read-only projection of local Specs, Tickets, and implementation sessions."""

from __future__ import annotations

import json
from pathlib import Path

from .profile import ProfileError, effective_profile, parse_profile
from .implementation_service import next_implementation_action
from .run_journal import IMPLEMENTATION_OUTCOMES, RunJournalError, verify_run_sources
from .tickets import TicketError, eligible_ticket_candidate, frontmatter, ticket_scope_state


class WorkOverviewError(ValueError):
    """The requested overview cannot be read safely."""


def _relative(repo: Path, path: Path) -> str:
    return path.relative_to(repo).as_posix()


def _files(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(path for path in directory.glob("*.md") if path.is_file() and not path.is_symlink())


def _specs(repo: Path, topic_dir: Path) -> tuple[list[dict[str, object]], list[str]]:
    by_id: dict[str, list[dict[str, object]]] = {}
    problems: list[str] = []
    specs_dir = topic_dir / "specs"
    if specs_dir.is_symlink():
        return [], [f"{_relative(repo, specs_dir)}: Spec 目录不能是符号链接"]
    if specs_dir.is_dir():
        problems.extend(
            f"{_relative(repo, path)}: Spec 不能是符号链接"
            for path in sorted(specs_dir.glob("*.md")) if path.is_symlink()
        )
    for path in _files(specs_dir):
        try:
            metadata = frontmatter(path)
            identifier = metadata.get("spec_id")
            revision = metadata.get("revision")
            if not isinstance(identifier, str) or not identifier:
                raise ValueError("spec_id 缺失")
            if not str(revision).isdigit() or int(str(revision)) < 1:
                raise ValueError("revision 无效")
            by_id.setdefault(identifier, []).append({
                "spec_id": identifier,
                "revision": int(str(revision)),
                "status": metadata.get("status"),
                "path": _relative(repo, path),
            })
        except (OSError, TicketError, ValueError) as exc:
            problems.append(f"{_relative(repo, path)}: {exc}")

    current: list[dict[str, object]] = []
    for identifier, versions in sorted(by_id.items()):
        candidates = [item for item in versions if item["status"] == "current"]
        if not candidates:
            candidates = versions
        revision = max(int(item["revision"]) for item in candidates)
        latest = [item for item in candidates if item["revision"] == revision]
        if len(latest) != 1:
            problems.append(f"Spec {identifier} 的 revision {revision} 不唯一")
            continue
        current.append({**latest[0], "is_current": latest[0]["status"] == "current"})
    return current, problems


def _tickets(repo: Path, topic_dir: Path) -> tuple[list[dict[str, object]], list[dict[str, str]], list[str]]:
    tickets_dir = topic_dir / "tickets"
    if tickets_dir.is_symlink():
        return [], [], [f"{_relative(repo, tickets_dir)}: Ticket 目录不能是符号链接"]
    if not tickets_dir.is_dir():
        return [], [], []
    problems: list[str] = []
    records: dict[str, tuple[Path, dict[str, object]]] = {}
    ambiguous: set[str] = set()
    for path in sorted(tickets_dir.glob("*.md")):
        if path.is_symlink() or not path.is_file():
            problems.append(f"{_relative(repo, path)}: Ticket 不是普通文件")
            continue
        try:
            metadata = frontmatter(path)
            identifier = metadata.get("id")
            if not isinstance(identifier, str) or not identifier:
                raise TicketError("Ticket 缺少有效 id")
            if identifier in ambiguous:
                problems.append(f"{_relative(repo, path)}: Ticket id {identifier} 重复")
                continue
            if identifier in records:
                earlier, _ = records.pop(identifier)
                ambiguous.add(identifier)
                problems.append(
                    f"Ticket id {identifier} 重复：{_relative(repo, earlier)}, {_relative(repo, path)}"
                )
                continue
            records[identifier] = (path, metadata)
        except (OSError, TicketError) as exc:
            problems.append(f"{_relative(repo, path)}: {exc}")

    if not problems:
        try:
            ticket_scope_state(tickets_dir)
        except (OSError, TicketError) as exc:
            problems.append(f"{_relative(repo, tickets_dir)}: {exc}")
    eligible = []
    for identifier, (path, _) in records.items():
        try:
            candidate = eligible_ticket_candidate(identifier, records)
            if candidate is not None:
                eligible.append(candidate)
        except (OSError, TicketError) as exc:
            problems.append(f"{_relative(repo, path)}: {exc}")
    eligible.sort(key=lambda candidate: (candidate.sequence, candidate.identifier))
    eligible_ids = {candidate.identifier for candidate in eligible}
    items: list[dict[str, object]] = []
    for identifier, (path, metadata) in sorted(records.items()):
        blockers = metadata.get("blocked_by")
        if isinstance(blockers, list) and all(isinstance(blocker, str) and blocker for blocker in blockers):
            unresolved = [
                blocker for blocker in blockers
                if blocker not in records or records[blocker][1].get("status") != "complete"
            ]
        else:
            unresolved = None
            problems.append(f"{_relative(repo, path)}: Ticket blocked_by 无效")
        items.append({
            "id": identifier,
            "title": metadata.get("title"),
            "status": metadata.get("status"),
            "path": _relative(repo, path),
            "spec_ref": metadata.get("spec_ref"),
            "blocked_by": unresolved,
            "eligible": identifier in eligible_ids,
            "claimed_by": metadata.get("claimed_by") or None,
        })
    frontier = [
        {"id": candidate.identifier, "path": _relative(repo, candidate.path)}
        for candidate in eligible
    ]
    return items, frontier, problems


def _sessions(repo: Path, topic_dir: Path) -> tuple[list[dict[str, object]], list[str]]:
    runs_dir = topic_dir / "runs"
    if runs_dir.is_symlink():
        return [], [f"{_relative(repo, runs_dir)}: runs 目录不能是符号链接"]
    if not runs_dir.is_dir():
        return [], []
    sessions: list[dict[str, object]] = []
    problems: list[str] = []
    for path in sorted(runs_dir.glob("run-*.json")):
        if path.is_symlink() or not path.is_file():
            problems.append(f"{_relative(repo, path)}: run journal 不是普通文件")
            continue
        try:
            journal = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(journal, dict):
                raise ValueError("run journal 根对象无效")
            phase = journal.get("phase")
            if not isinstance(phase, str):
                raise ValueError("run journal phase 无效")
            submission = journal.get("submission")
            if submission is not None and (
                not isinstance(submission, dict)
                or not isinstance(submission.get("outcome"), str)
                or submission["outcome"] not in IMPLEMENTATION_OUTCOMES
            ):
                raise ValueError("run journal submission 无效")
            if isinstance(submission, dict):
                expected_phase = "complete" if submission["outcome"] == "completed" else submission["outcome"]
                if phase != expected_phase:
                    raise ValueError("run journal submission 与 phase 不一致")
            action = next_implementation_action(journal, error_type=RunJournalError)
            context = journal.get("context")
            if not isinstance(context, dict):
                raise ValueError("run journal context 无效")
            context_repo = context.get("repo")
            if (
                not isinstance(context_repo, str)
                or Path(context_repo).resolve() != repo
                or context.get("topic") != topic_dir.name
            ):
                raise ValueError("run journal 不属于请求的仓库和 topic")
            ticket = context.get("ticket")
            identifier = ticket.get("id") if isinstance(ticket, dict) else None
            if not isinstance(identifier, str):
                raise ValueError("run journal 的 Ticket id 无效")
            attempt_id = journal.get("attempt_id")
            if not isinstance(attempt_id, str) or not attempt_id:
                raise ValueError("run journal 的 attempt_id 无效")
            active = submission is None
            source_state = "not-checked"
            if active:
                try:
                    verify_run_sources(journal)
                    source_state = "match"
                except (OSError, ValueError) as exc:
                    source_state = "stale"
                    problems.append(f"{_relative(repo, path)}: {exc}")
            receipts = journal.get("receipts")
            sessions.append({
                "ticket_id": identifier,
                "path": _relative(repo, path),
                "attempt_id": attempt_id,
                "active": active,
                "phase": action["phase"],
                "next_action": action["next_action"],
                "source_state": source_state,
                "receipt_present": {
                    kind: bool(receipts.get(kind)) for kind in ("test", "review", "code")
                } if isinstance(receipts, dict) else None,
                "submission_outcome": submission["outcome"] if isinstance(submission, dict) else None,
                "evidence_count": len(journal["evidence"])
                if isinstance(journal.get("evidence"), list) else None,
            })
        except (OSError, ValueError, RunJournalError) as exc:
            problems.append(f"{_relative(repo, path)}: {exc}")
    return sessions, problems


def _topic(repo: Path, topic_dir: Path) -> dict[str, object]:
    specs, spec_problems = _specs(repo, topic_dir)
    tickets, frontier, ticket_problems = _tickets(repo, topic_dir)
    sessions, session_problems = _sessions(repo, topic_dir)
    problems = [*spec_problems, *ticket_problems, *session_problems]
    active = [session for session in sessions if session["active"]]
    ticket_by_id = {str(item["id"]): item for item in tickets}
    active_claims: dict[tuple[str, object], list[str]] = {}
    for session in active:
        claim = (str(session["ticket_id"]), session["attempt_id"])
        active_claims.setdefault(claim, []).append(str(session["path"]))
        ticket = ticket_by_id.get(str(session["ticket_id"]))
        if ticket is None or ticket["status"] != "implementing" or ticket["claimed_by"] != session["attempt_id"]:
            problems.append(f"{session['path']}: 活动 journal 与 Ticket claim 不一致")
    for (ticket_id, attempt_id), paths in active_claims.items():
        if len(paths) > 1:
            problems.append(
                f"Ticket {ticket_id} 的同一 claim {attempt_id} 对应多个活动 journal：{', '.join(paths)}"
            )
    for ticket in tickets:
        if ticket["status"] == "implementing" and not any(
            session["ticket_id"] == ticket["id"]
            and session["attempt_id"] == ticket["claimed_by"] for session in active
        ):
            problems.append(f"{ticket['path']}: implementing Ticket 没有匹配的活动 journal")

    matched = [
        session for session in active
        if (ticket := ticket_by_id.get(str(session["ticket_id"]))) is not None
        and ticket["status"] == "implementing"
        and ticket["claimed_by"] == session["attempt_id"]
        and session["source_state"] == "match"
    ]
    if len(matched) == 1 and not any(
        len(paths) > 1 for claim, paths in active_claims.items()
        if claim == (str(matched[0]["ticket_id"]), matched[0]["attempt_id"])
    ):
        next_action = {
            "kind": "implementation-next-action",
            "journal": matched[0]["path"],
            "action": matched[0]["next_action"],
        }
    elif problems:
        next_action = {"kind": "inspect-inconsistent-state"}
    elif len(active) > 1:
        next_action = {"kind": "choose-active-session", "journals": [item["path"] for item in active]}
    elif active:
        next_action = {
            "kind": "implementation-next-action",
            "journal": active[0]["path"],
            "action": active[0]["next_action"],
        }
    elif frontier:
        next_action = {"kind": "start-ticket", "ticket": frontier[0]}
    else:
        next_action = {"kind": "no-eligible-ticket" if tickets else "no-ticket"}
    return {
        "topic": topic_dir.name,
        "specs": specs,
        "tickets": tickets,
        "frontier": frontier,
        "sessions": sessions,
        "next_action": next_action,
        "problems": problems,
    }


def work_overview(repo: Path, *, topic: str | None = None) -> dict[str, object]:
    """Summarize local work without changing any project state."""
    repo = repo.resolve()
    profile_path = repo / ".agent" / "matt-workflow.md"
    try:
        profile, _ = parse_profile(profile_path.read_text(encoding="utf-8"))
        effective = effective_profile(profile)
    except (OSError, ProfileError) as exc:
        raise WorkOverviewError(f"无法读取项目 profile：{exc}") from exc
    backend = effective["task_backend"]
    if backend != "local":
        return {
            "status": "unsupported-backend",
            "repo": str(repo),
            "task_backend": backend,
            "topics": [],
        }
    work = repo / ".agent" / "work"
    if topic is not None and (not topic or topic in {".", ".."} or Path(topic).name != topic):
        raise WorkOverviewError("topic 必须是 .agent/work 下的单层目录名")
    if work.is_symlink():
        raise WorkOverviewError(".agent/work 不能是符号链接")
    if not work.is_dir():
        return {"status": "no-work", "repo": str(repo), "task_backend": backend, "topics": []}
    directories = [work / topic] if topic is not None else sorted(work.iterdir())
    if topic is not None and directories[0].is_symlink():
        raise WorkOverviewError(f"topic 不能是符号链接：{topic}")
    if topic is not None and not directories[0].is_dir():
        raise WorkOverviewError(f"topic 不存在：{topic}")
    problems = [
        f"{_relative(repo, path)}: topic 不能是符号链接"
        for path in directories if path.is_symlink()
    ]
    topics = [
        _topic(repo, path) for path in directories
        if path.is_dir() and not path.is_symlink()
    ]
    return {
        "status": "needs-attention" if problems or any(item["problems"] for item in topics) else "ok",
        "repo": str(repo),
        "task_backend": backend,
        "work_scope_policy": effective["work_scope_policy"],
        "problems": problems,
        "topics": topics,
    }


def format_work_overview(report: dict[str, object]) -> str:
    """Render the same projection for a person without hiding uncertain state."""
    lines = [f"仓库：{report['repo']}", f"状态：{report['status']}"]
    if report["status"] == "unsupported-backend":
        lines.append(f"当前只支持 local 工作产物；项目后端：{report['task_backend']}")
        return "\n".join(lines)
    topics = report["topics"]
    assert isinstance(topics, list)
    for problem in report.get("problems", []):
        lines.append(f"问题：{problem}")
    if not topics:
        lines.append("没有本地工作主题。")
    for item in topics:
        lines.append(f"\n主题：{item['topic']}")
        specs = item["specs"]
        lines.append("  Spec：" + (
            "; ".join(
                f"{spec['spec_id']} r{spec['revision']} [{spec['status'] or '无状态'}] ({spec['path']})"
                for spec in specs
            )
            if specs else "无"
        ))
        tickets = item["tickets"]
        frontier = item["frontier"]
        lines.append(f"  Ticket：{len(tickets)} 张；可开始：" + (
            ", ".join(str(ticket["id"]) for ticket in frontier) if frontier else "无"
        ))
        completed_count = sum(ticket["status"] == "complete" for ticket in tickets)
        if completed_count:
            lines.append(f"  已完成 Ticket：{completed_count} 张；详情见 --json")
        for ticket in (ticket for ticket in tickets if ticket["status"] != "complete"):
            blockers = ticket["blocked_by"]
            suffix = "；阻塞状态未知" if blockers is None else (f"；等待 {', '.join(blockers)}" if blockers else "")
            lines.append(f"    {ticket['id']}: {ticket['status']}{suffix} ({ticket['path']})")
        sessions = item["sessions"]
        for session in (session for session in sessions if session["active"]):
            present = session["receipt_present"]
            receipts = ", ".join(
                kind for kind in ("test", "review", "code") if isinstance(present, dict) and present.get(kind)
            ) or "无"
            lines.append(
                f"  实施会话：{session['ticket_id']} / {session['phase']} / "
                f"下一动作 {session['next_action']} / 来源 {session['source_state']} / "
                f"已有收据 {receipts} ({session['path']})"
            )
        historical_count = sum(not session["active"] for session in sessions)
        if historical_count:
            lines.append(f"  历史实施会话：{historical_count} 条；详情见 --json")
        action = item["next_action"]
        if action["kind"] == "implementation-next-action":
            detail = f"{action['action']} ({action['journal']})"
        elif action["kind"] == "start-ticket":
            detail = f"可手动开始 Ticket {action['ticket']['id']} ({action['ticket']['path']})"
        elif action["kind"] == "inspect-inconsistent-state":
            detail = "先检查下列状态问题"
        elif action["kind"] == "choose-active-session":
            detail = "选择一个活动实施会话；不能推断唯一下一动作"
        else:
            detail = "没有可开始的 Ticket" if action["kind"] == "no-eligible-ticket" else "没有 Ticket"
        lines.append(f"  下一步：{detail}")
        for problem in item["problems"]:
            lines.append(f"  问题：{problem}")
    return "\n".join(lines)
