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
from .rules import EXECUTION_AGENTS, RuleError, resolve_rules
from .tickets import TicketError, eligible_local_tickets, frontmatter, validate_ready_ticket
from .write_gates import resolve_write_gate


class RunJournalError(ValueError):
    """Raised when an implementation context or journal is invalid."""


RUN_PHASE_TRANSITIONS = {
    "admitted": {"testing", "implementing", "blocked-by-design", "blocked-by-evidence"},
    "testing": {"implementing", "blocked-by-design", "blocked-by-evidence"},
    "implementing": {"testing", "reviewing", "blocked-by-design", "blocked-by-evidence"},
    "blocked-by-design": {"revising"},
    "blocked-by-evidence": {"testing", "implementing", "reviewing"},
    "revising": {"testing", "implementing", "blocked-by-design"},
    "reviewing": {"implementing", "committing", "blocked-by-design", "blocked-by-evidence"},
    "committing": {"complete", "blocked-by-design"},
    "complete": set(),
}
IMPLEMENTATION_OUTCOMES = frozenset(
    {"completed", "blocked-by-design", "blocked-by-evidence"}
)
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def _source_receipt(repo: Path, path: Path, label: str) -> dict[str, object]:
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(repo)
    except ValueError as exc:
        raise RunJournalError(f"{label} 必须位于当前仓库") from exc
    try:
        content = resolved.read_bytes()
    except OSError as exc:
        raise RunJournalError(f"无法读取 {label}：{resolved}") from exc
    return {
        "path": str(resolved),
        "repo_path": relative.as_posix(),
        "sha256": hashlib.sha256(content).hexdigest(),
        "size": len(content),
    }


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


def _resolve_execution_agent(requested: object, current: str | None) -> tuple[str, str | None]:
    if current is not None and current not in EXECUTION_AGENTS:
        raise RunJournalError(f"未知当前执行 Agent：{current}")
    if requested == "auto":
        if current is None:
            raise RunJournalError("execution_agent: auto 需要传入当前执行 Agent")
        return current, "auto"
    if requested not in EXECUTION_AGENTS:
        raise RunJournalError(f"未知 execution_agent：{requested}")
    if current is not None and current != requested:
        raise RunJournalError(
            f"Ticket 指定由 {requested} 执行，当前 Agent 是 {current}"
        )
    assert isinstance(requested, str)
    return requested, None


def build_run_context(
    repo: Path,
    ticket_path: Path,
    base: str,
    paths: list[str] | None = None,
    execution_agent: str | None = None,
    parallel: bool = False,
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
    effective_agent, requested_agent = _resolve_execution_agent(
        ticket["execution_agent"], execution_agent
    )
    try:
        rule_paths = paths or ticket.get("rule_scope", [])
        rule_map = resolve_rules(repo, effective_agent, rule_paths)
    except RuleError as exc:
        raise RunJournalError(str(exc)) from exc
    ticket_context: dict[str, object] = {
        "id": ticket_id,
        "path": str(ticket_path),
        "status": ticket["status"],
        "execution_agent": effective_agent,
        "content": _source_receipt(repo, ticket_path, "Ticket"),
        "declared_scope": ticket.get("rule_scope", []),
    }
    if requested_agent is not None:
        ticket_context["requested_execution_agent"] = requested_agent
    spec_path = Path(str(ticket["spec_ref"]))
    if not spec_path.is_absolute():
        spec_path = repo / spec_path
    context: dict[str, object] = {
        "schema_version": 1,
        "repo": str(repo),
        "topic": topic,
        "ticket": ticket_context,
        "spec": {
            "id": ticket["spec_id"],
            "revision": int(ticket["spec_revision"]),
            "ref": ticket["spec_ref"],
            "content": _source_receipt(repo, spec_path, "Spec"),
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
    if parallel:
        context["parallel_mode"] = True
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


def _journal_path(repo: Path, context: dict[str, object]) -> Path:
    ticket = context["ticket"]
    spec = context["spec"]
    assert isinstance(ticket, dict) and isinstance(spec, dict)
    return (
        repo.resolve()
        / ".agent"
        / "work"
        / str(context["topic"])
        / "runs"
        / f"run-{ticket['id']}-spec-r{spec['revision']}.json"
    )


def start_run(
    repo: Path,
    ticket_path: Path,
    base: str,
    paths: list[str] | None = None,
    execution_agent: str | None = None,
    parallel: bool = False,
) -> tuple[Path, dict[str, object]]:
    try:
        admission = validate_ready_ticket(ticket_path)
    except TicketError as exc:
        raise RunJournalError(str(exc)) from exc
    if admission["status"] != "ready":
        raise RunJournalError("run-start 只接受 ready-for-agent 或 revalidated Ticket")
    context = build_run_context(
        repo, ticket_path, base, paths,
        execution_agent=execution_agent, parallel=parallel,
    )
    ticket = context["ticket"]
    assert isinstance(ticket, dict)
    spec = context["spec"]
    assert isinstance(spec, dict)
    path = _journal_path(repo, context)
    if path.exists():
        existing = _load_journal(path)
        existing_agent = existing.get("context", {}).get("ticket", {}).get("execution_agent")
        if execution_agent is not None and existing_agent != execution_agent:
            raise RunJournalError(
                "run journal 已固定由 "
                f"{existing_agent} 执行，当前 Agent 是 {execution_agent}"
            )
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


def implementation_work_unit(
    journal_path: Path, journal: dict[str, object]
) -> dict[str, object]:
    """Project the runtime journal into the semantic unit consumed by a Skill."""
    context = journal.get("context")
    if not isinstance(context, dict):
        raise RunJournalError("run journal context 无效")
    ticket = context.get("ticket")
    spec = context.get("spec")
    if not isinstance(ticket, dict) or not isinstance(spec, dict):
        raise RunJournalError("run journal 缺少 Ticket 或 Spec 上下文")
    return {
        "kind": "implementation",
        "run_id": journal.get("run_id"),
        "context_id": context.get("context_id"),
        "journal": str(journal_path),
        "execution_mode": "parallel" if context.get("parallel_mode") is True else "serial",
        "ticket": ticket,
        "spec": spec,
        "base_sha": context.get("base_sha"),
        "rule_map": context.get("rule_map", []),
        "test_commands": context.get("test_commands", []),
        "source_receipts": {
            "ticket": ticket.get("content"),
            "spec": spec.get("content"),
        },
        "allowed_scope": {
            "paths": ticket.get("declared_scope", []),
            "work_scope_policy": (
                context.get("policies", {}).get("work_scope_policy")
                if isinstance(context.get("policies"), dict)
                else None
            ),
            "write_gates": context.get("write_gates", {}),
        },
        "expected_outcomes": [
            "completed",
            "blocked-by-design",
            "blocked-by-evidence",
        ],
    }


def _load_journal(path: Path) -> dict[str, object]:
    try:
        journal = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RunJournalError(f"无法读取 run journal：{path}") from exc
    if not isinstance(journal, dict):
        raise RunJournalError(f"run journal 无效：{path}")
    return journal


def verify_run_sources(journal: dict[str, object]) -> None:
    """Reject a submission when its fixed Ticket or Spec bytes changed."""
    context = journal.get("context")
    if not isinstance(context, dict):
        raise RunJournalError("run journal context 无效")
    repo = Path(str(context.get("repo", ""))).resolve()
    for label, key in (("Ticket", "ticket"), ("Spec", "spec")):
        value = context.get(key)
        receipt = value.get("content") if isinstance(value, dict) else None
        if not isinstance(receipt, dict) or not isinstance(receipt.get("path"), str):
            raise RunJournalError(f"run journal 缺少固定 {label} receipt")
        current = _source_receipt(repo, Path(receipt["path"]), label)
        if current.get("sha256") != receipt.get("sha256"):
            raise RunJournalError(f"{label} 内容已变化；当前 work unit 已失效")


def submit_run_outcome(path: Path, result: dict[str, object]) -> dict[str, object]:
    """Validate and persist the semantic outcome returned by my-implement."""
    expected_fields = {"outcome", "test_receipt", "review_receipt", "blocker"}
    if set(result) != expected_fields:
        raise RunJournalError("implementation result 字段无效")
    outcome = result.get("outcome")
    if outcome not in IMPLEMENTATION_OUTCOMES:
        raise RunJournalError(f"未知 implementation outcome：{outcome}")
    journal = _load_journal(path)
    if journal.get("submission") is not None:
        raise RunJournalError("run journal 已提交 outcome")
    verify_run_sources(journal)

    test_receipt = result.get("test_receipt")
    review_receipt = result.get("review_receipt")
    blocker = result.get("blocker")
    if outcome == "completed":
        if not isinstance(test_receipt, str) or not test_receipt.strip():
            raise RunJournalError("completed outcome 必须包含 test_receipt")
        if not isinstance(review_receipt, str) or not review_receipt.strip():
            raise RunJournalError("completed outcome 必须包含 review_receipt")
        if blocker not in {None, ""}:
            raise RunJournalError("completed outcome 不得包含 blocker")
    else:
        if not isinstance(blocker, str) or not blocker.strip():
            raise RunJournalError(f"{outcome} 必须包含 blocker")

    now = datetime.now(timezone.utc).isoformat()
    submission = {
        "outcome": outcome,
        "test_receipt": test_receipt,
        "review_receipt": review_receipt,
        "blocker": blocker,
        "at": now,
    }
    journal["submission"] = submission
    journal["phase"] = "complete" if outcome == "completed" else outcome
    receipts = journal.get("receipts")
    if not isinstance(receipts, dict):
        raise RunJournalError("run journal receipts 无效")
    receipts["test"] = test_receipt
    receipts["review"] = review_receipt
    journal["blocker"] = blocker
    events = journal.get("events")
    if not isinstance(events, list):
        raise RunJournalError("run journal events 无效")
    events.append({"phase": journal["phase"], "outcome": outcome, "at": now})
    _write_json_atomic(path, journal)
    return {
        "status": "accepted",
        "outcome": outcome,
        "next_action": "complete" if outcome == "completed" else "pause",
        "run": journal,
    }


def _concrete_scope(ticket: dict[str, object]) -> tuple[str, ...]:
    raw = ticket.get("rule_scope")
    if not isinstance(raw, list) or not raw or not all(isinstance(item, str) for item in raw):
        raise RunJournalError("并行 Ticket 必须声明非空 rule_scope")
    result: list[str] = []
    for item in raw:
        normalized = Path(item).as_posix().strip("/")
        if not normalized or any(character in normalized for character in "*?[]{}"):
            raise RunJournalError("并行只接受可证明不重叠的具体 rule_scope 路径")
        result.append(normalized)
    return tuple(sorted(set(result)))


def _assert_disjoint_scopes(scopes: list[tuple[str, ...]]) -> None:
    for left_index, left in enumerate(scopes):
        for right in scopes[left_index + 1 :]:
            for first in left:
                for second in right:
                    if first == second or first.startswith(second + "/") or second.startswith(first + "/"):
                        raise RunJournalError(
                            f"并行 Ticket 写入范围重叠：{first} <> {second}"
                        )


def open_implementation_session(
    repo: Path,
    ticket_paths: list[Path],
    base: str,
    *,
    paths: list[str] | None = None,
    execution_agent: str | None = None,
    parallel: bool = False,
) -> dict[str, object]:
    """Open one serial unit or a conservatively isolated parallel dispatch."""
    if not ticket_paths:
        raise RunJournalError("implementation-open 至少需要一张 Ticket")
    if parallel and len(ticket_paths) < 2:
        raise RunJournalError("并行 implementation session 至少需要两张 Ticket")
    if parallel and paths:
        raise RunJournalError("并行 implementation session 的规则路径由各 Ticket rule_scope 决定")
    if not parallel and len(ticket_paths) != 1:
        raise RunJournalError("串行 implementation session 每次只接受一张 Ticket")
    resolved_paths = [path.resolve() for path in ticket_paths]
    if len(resolved_paths) != len(set(resolved_paths)):
        raise RunJournalError("implementation session 不接受重复 Ticket")
    try:
        metadata = [frontmatter(path) for path in resolved_paths]
    except TicketError as exc:
        raise RunJournalError(str(exc)) from exc
    identifiers = [ticket.get("id") for ticket in metadata]
    if len(identifiers) != len(set(identifiers)):
        raise RunJournalError("implementation session 的 Ticket id 必须唯一")
    if parallel:
        topics = {_ticket_location(repo.resolve(), path)[1] for path in resolved_paths}
        if len(topics) != 1:
            raise RunJournalError("并行 Ticket 必须属于同一 topic")
        _assert_disjoint_scopes([_concrete_scope(ticket) for ticket in metadata])

    try:
        eligible = {
            candidate.path.resolve()
            for directory in {path.parent for path in resolved_paths}
            for candidate in eligible_local_tickets(directory)
        }
    except TicketError as exc:
        raise RunJournalError(str(exc)) from exc
    ineligible = [path for path in resolved_paths if path not in eligible]
    if ineligible:
        raise RunJournalError(
            "implementation-open Ticket 尚未解除阻塞、已被认领或没有未完成验收："
            + ", ".join(str(path) for path in ineligible)
        )

    preflight: list[tuple[Path, dict[str, object]]] = []
    for ticket_path in resolved_paths:
        try:
            admission = validate_ready_ticket(ticket_path)
        except TicketError as exc:
            raise RunJournalError(str(exc)) from exc
        if admission["status"] != "ready":
            raise RunJournalError("implementation-open 只接受 ready-for-agent 或 revalidated Ticket")
        context = build_run_context(
            repo,
            ticket_path,
            base,
            paths,
            execution_agent=execution_agent,
            parallel=parallel,
        )
        existing_path = _journal_path(repo, context)
        if existing_path.exists():
            existing = _load_journal(existing_path)
            if existing.get("context", {}).get("context_id") != context["context_id"]:
                raise RunJournalError(f"run journal 已存在且上下文不同：{existing_path}")
            if existing.get("submission") is not None:
                raise RunJournalError(f"implementation lane 已提交：{existing_path}")
        preflight.append((ticket_path, context))

    lanes: list[dict[str, object]] = []
    for ticket_path, _ in preflight:
        journal_path, journal = start_run(
            repo,
            ticket_path,
            base,
            paths,
            execution_agent=execution_agent,
            parallel=parallel,
        )
        unit = implementation_work_unit(journal_path, journal)
        lanes.append(
            {
                "lane_id": unit["run_id"],
                "work_unit": unit,
            }
        )
    digest = hashlib.sha256(
        "\0".join(sorted(
            str(lane["work_unit"]["context_id"])
            for lane in lanes
        )).encode("utf-8")
    ).hexdigest()
    return {
        "status": "ready",
        "session_id": digest,
        "execution_mode": "parallel" if parallel else "serial",
        "lanes": lanes,
    }


def close_implementation_session(paths: list[Path]) -> dict[str, object]:
    """Aggregate submitted lanes without pretending integration already happened."""
    if not paths:
        raise RunJournalError("implementation-close 至少需要一个 journal")
    resolved_paths = [path.resolve() for path in paths]
    if len(resolved_paths) != len(set(resolved_paths)):
        raise RunJournalError("implementation-close 不接受重复 journal")
    lanes: list[dict[str, object]] = []
    base_shas: set[object] = set()
    topics: set[object] = set()
    modes: set[bool] = set()
    context_ids: list[str] = []
    for path in resolved_paths:
        journal = _load_journal(path)
        verify_run_sources(journal)
        context = journal.get("context")
        submission = journal.get("submission")
        if not isinstance(context, dict) or not isinstance(submission, dict):
            raise RunJournalError(f"implementation lane 尚未提交：{path}")
        context_id = context.get("context_id")
        if not isinstance(context_id, str):
            raise RunJournalError(f"implementation lane 缺少 context_id：{path}")
        context_ids.append(context_id)
        base_shas.add(context.get("base_sha"))
        topics.add(context.get("topic"))
        modes.add(context.get("parallel_mode") is True)
        if submission.get("outcome") not in IMPLEMENTATION_OUTCOMES:
            raise RunJournalError(f"implementation lane outcome 无效：{path}")
        lanes.append(
            {
                "run_id": journal.get("run_id"),
                "journal": str(path),
                "outcome": submission.get("outcome"),
            }
        )
    if len(base_shas) != 1:
        raise RunJournalError("implementation lanes 的 base_sha 不一致")
    if len(resolved_paths) > 1 and (modes != {True} or len(topics) != 1):
        raise RunJournalError("多个 journal 不属于同一并行 implementation session")
    session_id = hashlib.sha256("\0".join(sorted(context_ids)).encode("utf-8")).hexdigest()
    completed = all(lane["outcome"] == "completed" for lane in lanes)
    return {
        "status": "ready-for-integration" if completed else "paused",
        "session_id": session_id,
        "next_action": "integrate" if completed else "resolve-blocked-lanes",
        "lanes": lanes,
    }


def record_run(
    path: Path,
    phase: str,
    *,
    test_receipt: str | None = None,
    review_receipt: str | None = None,
    blocker: str | None = None,
) -> dict[str, object]:
    """Record one validated phase transition and optional evidence receipts."""
    journal = _load_journal(path)
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
