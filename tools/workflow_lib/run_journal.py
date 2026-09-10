"""Resolved implementation context and recoverable local run journals."""

from __future__ import annotations

import glob as globlib
import hashlib
import json
import os
import re
import secrets
import shlex
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .profile import ProfileError, effective_profile, parse_profile
from .rules import EXECUTION_AGENTS, RuleError, resolve_rules
from .lifecycle import (
    LifecycleError,
    coordinate_lifecycle_update,
    project_ticket,
    recover_lifecycle_transactions,
    ticket_lock,
)
from .tickets import (
    TicketError,
    acceptance_items,
    eligible_local_tickets,
    frontmatter,
    review_probes,
    ticket_scope_state,
    ticket_definition_receipt,
    validate_spec_lineage,
)
from .write_gates import resolve_write_gate
from .fs_safety import (
    FilesystemSafetyError,
    quarantine_and_remove,
    register_owned_directory,
    verify_owned_directory,
)


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
REVIEW_METHOD = "my-code-review"
REVIEW_STATUSES = frozenset({"pass", "findings", "inconclusive", "blocked-by-design"})
REVIEW_SEVERITIES = frozenset({"P0", "P1", "P2"})
REVIEW_PROVENANCE_KINDS = frozenset({"self", "independent_session"})
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def _source_receipt(
    repo: Path, path: Path, label: str, *, kind: str = "source"
) -> dict[str, object]:
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
        "kind": kind,
        "path": str(resolved),
        "repo_path": relative.as_posix(),
        "sha256": hashlib.sha256(content).hexdigest(),
        "size": len(content),
    }


def _profile_sources(
    repo: Path, profile_path: Path, profile: dict[str, object], rule_map: list[dict[str, object]]
) -> list[dict[str, object]]:
    receipts = [_source_receipt(repo, profile_path, "Profile", kind="profile")]
    seen = {profile_path.resolve()}
    inputs: list[tuple[str, object]] = [
        ("rule", entry.get("source")) for entry in rule_map
    ]
    inputs.extend(
        (kind, raw)
        for kind, field in (
            ("standard", "standards_sources"),
            ("domain", "domain_sources"),
        )
        for raw in profile.get(field, [])
    )
    for kind, raw in inputs:
        if not isinstance(raw, str) or not raw.strip():
            raise RunJournalError(f"{kind} source 必须是非空仓库相对路径")
        source = Path(raw)
        if not source.is_absolute():
            source = repo / source
        resolved = source.resolve()
        if resolved in seen:
            continue
        receipts.append(_source_receipt(repo, resolved, f"{kind} source", kind=kind))
        seen.add(resolved)
    return receipts


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


def _ticket_boundary_manifest(ticket_path: Path) -> dict[str, object]:
    """Freeze the current Ticket's acceptance contract and direct consumers."""
    records, _ = ticket_scope_state(ticket_path.parent)
    current = frontmatter(ticket_path)
    ticket_id = current.get("id")
    if not isinstance(ticket_id, str) or ticket_id not in records:
        raise RunJournalError("Ticket boundary 缺少当前 Ticket")
    successors: list[dict[str, object]] = []
    for identifier, (path, metadata) in sorted(records.items()):
        blocked_by = metadata.get("blocked_by")
        if isinstance(blocked_by, list) and ticket_id in blocked_by:
            successors.append({
                "id": identifier,
                "definition": ticket_definition_receipt(path),
                "acceptance": acceptance_items(path),
                "blocked_by": sorted(blocked_by),
            })
    probes = review_probes(current, ticket_path)
    if successors:
        probes = sorted([*probes, "downstream-owner"])
    return {
        "current": {
            "id": ticket_id,
            "definition": ticket_definition_receipt(ticket_path),
            "acceptance": acceptance_items(ticket_path),
        },
        "successors": successors,
        "required_probes": probes,
    }


def _verify_ticket_boundary(context: dict[str, object], expected: object) -> dict[str, object]:
    ticket = context.get("ticket")
    if not isinstance(ticket, dict):
        raise RunJournalError("run journal 缺少 Ticket 上下文")
    path = Path(str(ticket.get("path", ""))).resolve()
    try:
        actual = _ticket_boundary_manifest(path)
    except TicketError as exc:
        raise RunJournalError(str(exc)) from exc
    if actual != expected:
        raise RunJournalError("review Ticket boundary 已变化")
    return actual


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
        profile_path = repo / ".agent" / "matt-workflow.md"
        raw_profile, _ = parse_profile(profile_path.read_text(encoding="utf-8"))
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
    try:
        lineage = validate_spec_lineage(ticket_path, ticket)
    except TicketError as exc:
        raise RunJournalError(str(exc)) from exc
    if lineage is None:
        raise RunJournalError("本地 Ticket 缺少可验证的 Spec lineage")

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
    try:
        boundary = _ticket_boundary_manifest(ticket_path)
    except TicketError as exc:
        raise RunJournalError(str(exc)) from exc
    ticket_context: dict[str, object] = {
        "id": ticket_id,
        "path": str(ticket_path),
        "status": ticket["status"],
        "execution_agent": effective_agent,
        "definition": ticket_definition_receipt(ticket_path),
        "declared_scope": ticket.get("rule_scope", []),
        "review_boundary": boundary,
    }
    if requested_agent is not None:
        ticket_context["requested_execution_agent"] = requested_agent
    spec_path = Path(str(lineage["path"]))
    context: dict[str, object] = {
        "schema_version": 1,
        "repo": str(repo),
        "topic": topic,
        "ticket": ticket_context,
        "spec": {
            "id": ticket["spec_id"],
            "revision": int(ticket["spec_revision"]),
            "ref": ticket["spec_ref"],
            "content": _source_receipt(repo, spec_path, "Spec", kind="spec"),
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
        "review_commands": profile["review_commands"],
        "standards_sources": profile["standards_sources"],
        "domain_sources": profile["domain_sources"],
        "rule_map": rule_map,
        "source_receipts": _profile_sources(repo, profile_path, profile, rule_map),
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


def _journal_path(
    repo: Path, context: dict[str, object], *, attempt_id: str | None = None
) -> Path:
    ticket = context["ticket"]
    spec = context["spec"]
    assert isinstance(ticket, dict) and isinstance(spec, dict)
    stem = f"run-{ticket['id']}-spec-r{spec['revision']}"
    if attempt_id is not None:
        stem += f"-attempt-{attempt_id}"
    return (
        repo.resolve()
        / ".agent"
        / "work"
        / str(context["topic"])
        / "runs"
        / f"{stem}.json"
    )


def _json_text(value: dict[str, object]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def _active_attempt(ticket_path: Path, ticket: dict[str, object]) -> tuple[Path, dict[str, object]] | None:
    claimed_by = ticket.get("claimed_by")
    identifier = ticket.get("id")
    revision = ticket.get("spec_revision")
    if not isinstance(claimed_by, str) or not claimed_by:
        return None
    runs = ticket_path.parent.parent / "runs"
    pattern = f"run-{identifier}-spec-r{revision}*.json"
    matches: list[tuple[Path, dict[str, object]]] = []
    for path in sorted(runs.glob(pattern)) if runs.is_dir() else []:
        journal = _load_journal(path)
        if journal.get("attempt_id") == claimed_by and journal.get("submission") is None:
            matches.append((path, journal))
    if len(matches) > 1:
        raise RunJournalError("同一 Ticket claim 对应多个活动 journal")
    return matches[0] if matches else None


def start_run(
    repo: Path,
    ticket_path: Path,
    base: str,
    paths: list[str] | None = None,
    execution_agent: str | None = None,
    parallel: bool = False,
    fail_after_claim_writes: int | None = None,
) -> tuple[Path, dict[str, object]]:
    repo = repo.resolve()
    ticket_path, topic = _ticket_location(repo, ticket_path)
    try:
        with ticket_lock(repo, topic, str(frontmatter(ticket_path).get("id", ""))):
            recover_lifecycle_transactions(
                repo, topic=topic, ticket_id=str(frontmatter(ticket_path).get("id", ""))
            )
            ticket_metadata = frontmatter(ticket_path)
            active = _active_attempt(ticket_path, ticket_metadata)
            if active is not None:
                existing_agent = active[1].get("context", {}).get("ticket", {}).get("execution_agent")
                if execution_agent is not None and existing_agent != execution_agent:
                    raise RunJournalError(
                        "run journal 已固定由 "
                        f"{existing_agent} 执行，当前 Agent 是 {execution_agent}"
                    )
                return active
            eligible = {
                candidate.path.resolve()
                for candidate in eligible_local_tickets(ticket_path.parent)
            }
            if ticket_path not in eligible:
                raise RunJournalError(
                    "run-start Ticket 尚未解除阻塞、已被认领或没有未完成验收"
                )
            context = build_run_context(
                repo, ticket_path, base, paths,
                execution_agent=execution_agent, parallel=parallel,
            )
            ticket = context["ticket"]
            assert isinstance(ticket, dict)
            attempt_id = secrets.token_hex(16)
            legacy_path = _journal_path(repo, context)
            path = (
                legacy_path if not legacy_path.exists()
                else _journal_path(repo, context, attempt_id=attempt_id)
            )
            now = datetime.now(timezone.utc).isoformat()
            journal: dict[str, object] = {
                "schema_version": 2,
                "run_id": ticket["id"],
                "attempt_id": attempt_id,
                "implementation_session_id": secrets.token_hex(16),
                "phase": "admitted",
                "context": context,
                "receipts": {"test": None, "review": None, "code": None},
                "evidence": [],
                "blocker": None,
                "events": [{"phase": "admitted", "at": now}],
            }
            before_ticket = ticket_path.read_text(encoding="utf-8")
            after_ticket = project_ticket(
                before_ticket, status="implementing", claimed_by=attempt_id
            )
            coordinate_lifecycle_update(
                repo,
                topic=topic,
                ticket_id=str(ticket["id"]),
                attempt_id=attempt_id,
                operation="claim",
                updates=[
                    (ticket_path, before_ticket, after_ticket),
                    (path, "", _json_text(journal)),
                ],
                fail_after_writes=fail_after_claim_writes,
            )
            return path, journal
    except (LifecycleError, TicketError) as exc:
        raise RunJournalError(str(exc)) from exc


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
        "review_commands": context.get("review_commands", []),
        "source_receipts": {
            "ticket_definition": ticket.get("definition"),
            "spec": spec.get("content"),
            "stable_sources": context.get("source_receipts", []),
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
    """Reject a submission when any stable work-unit source changed."""
    context = journal.get("context")
    if not isinstance(context, dict):
        raise RunJournalError("run journal context 无效")
    repo = Path(str(context.get("repo", ""))).resolve()
    ticket = context.get("ticket")
    receipt = ticket.get("definition") if isinstance(ticket, dict) else None
    if not isinstance(receipt, dict) or not isinstance(receipt.get("path"), str):
        raise RunJournalError("run journal 缺少固定 Ticket definition receipt")
    current_definition = ticket_definition_receipt(Path(receipt["path"]))
    if current_definition.get("sha256") != receipt.get("sha256"):
        raise RunJournalError("Ticket definition 内容已变化；当前 work unit 已失效")

    spec = context.get("spec")
    spec_receipt = spec.get("content") if isinstance(spec, dict) else None
    stable = context.get("source_receipts")
    receipts = [spec_receipt, *(stable if isinstance(stable, list) else [])]
    for source in receipts:
        if not isinstance(source, dict) or not isinstance(source.get("path"), str):
            raise RunJournalError("run journal 缺少固定 source receipt")
        kind = str(source.get("kind", "source"))
        current = _source_receipt(repo, Path(source["path"]), kind, kind=kind)
        if current.get("sha256") != source.get("sha256") or current.get("size") != source.get("size"):
            raise RunJournalError(f"{kind} 内容已变化；当前 work unit 已失效")


def _scope_files(repo: Path, paths: list[object]) -> list[Path]:
    files: set[Path] = set()
    for raw in paths:
        if not isinstance(raw, str) or not raw:
            raise RunJournalError("code scope 必须是非空仓库相对路径")
        relative = Path(raw)
        if relative.is_absolute() or ".." in relative.parts:
            raise RunJournalError("code scope 越出仓库")
        candidates = (
            list(repo.glob(raw)) if globlib.has_magic(raw) else [repo / relative]
        )
        matched = False
        for candidate in candidates:
            resolved = candidate.resolve()
            try:
                resolved.relative_to(repo)
            except ValueError as exc:
                raise RunJournalError("code scope 越出仓库") from exc
            if resolved.is_file() and not resolved.is_symlink():
                files.add(resolved)
                matched = True
            elif resolved.is_dir() and not resolved.is_symlink():
                files.update(
                    path
                    for path in resolved.rglob("*")
                    if path.is_file() and not path.is_symlink()
                )
                matched = True
        if not matched:
            raise RunJournalError(f"code scope 不存在：{raw}")
    return sorted(files)


def build_code_receipt(path: Path) -> dict[str, object]:
    """Hash the current declared code scope for test/review binding."""
    journal = _load_journal(path)
    context = journal.get("context")
    ticket = context.get("ticket") if isinstance(context, dict) else None
    if not isinstance(context, dict) or not isinstance(ticket, dict):
        raise RunJournalError("run journal context 无效")
    repo = Path(str(context.get("repo", ""))).resolve()
    scope = ticket.get("declared_scope")
    if not isinstance(scope, list) or not scope:
        raise RunJournalError("Ticket 缺少 code scope")
    sources = [
        _source_receipt(repo, source, "code source", kind="code-source")
        for source in _scope_files(repo, scope)
    ]
    encoded = json.dumps(sources, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {
        "kind": "code",
        "content_id": hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
        "sources": sources,
    }


def _evidence_directory(path: Path) -> Path:
    return path.parent / f"{path.stem}.evidence"


def _persist_evidence(path: Path, record: dict[str, object]) -> dict[str, str]:
    encoded = json.dumps(
        record, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    evidence_id = hashlib.sha256(encoded).hexdigest()
    destination = _evidence_directory(path) / f"{evidence_id}.json"
    if destination.exists():
        if destination.read_bytes() != encoded + b"\n":
            raise RunJournalError("evidence id 冲突")
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.parent / f".{evidence_id}.{secrets.token_hex(8)}.tmp"
        try:
            temporary.write_bytes(encoded + b"\n")
            with temporary.open("rb") as handle:
                os.fsync(handle.fileno())
            os.replace(temporary, destination)
        finally:
            if temporary.exists():
                temporary.unlink()
    receipt = {"kind": str(record["kind"]), "evidence_id": evidence_id}
    journal = _load_journal(path)
    context = journal.get("context")
    topic = context.get("topic") if isinstance(context, dict) else None
    ticket_id = journal.get("run_id")
    if not isinstance(context, dict) or not isinstance(topic, str) or not isinstance(ticket_id, str):
        raise RunJournalError("run journal evidence context 无效")
    repo = Path(str(context.get("repo", ""))).resolve()
    try:
        with ticket_lock(repo, topic, ticket_id):
            journal = _load_journal(path)
            registered = journal.get("evidence")
            if not isinstance(registered, list):
                raise RunJournalError("run journal evidence registry 无效")
            if receipt not in registered:
                registered.append(receipt)
                _write_json_atomic(path, journal)
    except LifecycleError as exc:
        raise RunJournalError(str(exc)) from exc
    return receipt


def run_test_evidence(path: Path, argv: list[str]) -> dict[str, str]:
    """Execute one declared test command and persist its runtime evidence."""
    if not argv or any(not isinstance(value, str) or not value for value in argv):
        raise RunJournalError("test evidence command 必须是非空 argv")
    journal = _load_journal(path)
    context = journal.get("context")
    if not isinstance(context, dict):
        raise RunJournalError("run journal context 无效")
    allowed = context.get("test_commands")
    if not isinstance(allowed, list) or argv not in [
        shlex.split(command)
        for command in allowed
        if isinstance(command, str) and command.strip()
    ]:
        raise RunJournalError("test evidence command 未在 work unit 中声明")
    repo = Path(str(context.get("repo", ""))).resolve()
    code = build_code_receipt(path)
    completed = subprocess.run(argv, cwd=repo, capture_output=True, check=False)
    record: dict[str, object] = {
        "kind": "test",
        "status": "pass" if completed.returncode == 0 else "fail",
        "code_content_id": code["content_id"],
        "argv": argv,
        "exit_code": completed.returncode,
        "stdout_sha256": hashlib.sha256(completed.stdout).hexdigest(),
        "stderr_sha256": hashlib.sha256(completed.stderr).hexdigest(),
    }
    return _persist_evidence(path, record)


def open_review_evidence(path: Path) -> dict[str, object]:
    """Create an owned immutable snapshot for an external code reviewer."""
    journal = _load_journal(path)
    context = journal.get("context")
    if not isinstance(context, dict):
        raise RunJournalError("run journal context 无效")
    repo = Path(str(context.get("repo", ""))).resolve()
    base_sha = context.get("base_sha")
    ticket = context.get("ticket")
    implementation_session_id = journal.get("implementation_session_id")
    if not isinstance(base_sha, str) or not base_sha:
        raise RunJournalError("run journal 缺少固定 review baseline")
    if not isinstance(ticket, dict) or not isinstance(implementation_session_id, str):
        raise RunJournalError("run journal 缺少 review session 上下文")
    boundary = ticket.get("review_boundary")
    _verify_ticket_boundary(context, boundary)
    code = build_code_receipt(path)
    review_id = secrets.token_hex(16)
    snapshot_root = _evidence_directory(path) / "review-snapshots"
    snapshot_root.mkdir(parents=True, exist_ok=True)
    snapshot_dir = Path(
        tempfile.mkdtemp(prefix=f"review-{review_id}-", dir=snapshot_root)
    )
    frozen: list[dict[str, object]] = []
    review_inputs: list[dict[str, object]] = []
    try:
        for index, source in enumerate(code["sources"]):
            if not isinstance(source, dict):
                raise RunJournalError("code snapshot source 无效")
            source_path = Path(str(source.get("path", "")))
            target = snapshot_dir / f"current-{index:04d}-{source_path.name}"
            shutil.copy2(source_path, target)
            baseline = subprocess.run(
                ["git", "show", f"{base_sha}:{source['repo_path']}"],
                cwd=repo,
                capture_output=True,
                check=False,
            )
            baseline_path: str | None = None
            baseline_sha256: str | None = None
            baseline_size: int | None = None
            if baseline.returncode == 0:
                baseline_target = snapshot_dir / f"baseline-{index:04d}-{source_path.name}"
                baseline_target.write_bytes(baseline.stdout)
                baseline_path = str(baseline_target)
                baseline_sha256 = hashlib.sha256(baseline.stdout).hexdigest()
                baseline_size = len(baseline.stdout)
            frozen.append({
                "repo_path": source["repo_path"],
                "snapshot_path": str(target),
                "sha256": source["sha256"],
                "size": source["size"],
                "baseline_snapshot_path": baseline_path,
                "baseline_sha256": baseline_sha256,
                "baseline_size": baseline_size,
            })
        raw_inputs: list[dict[str, object]] = []
        spec = context.get("spec")
        if isinstance(spec, dict) and isinstance(spec.get("content"), dict):
            raw_inputs.append(spec["content"])
        sources = context.get("source_receipts")
        if isinstance(sources, list):
            raw_inputs.extend(item for item in sources if isinstance(item, dict))
        seen_inputs: set[str] = set()
        for index, source in enumerate(raw_inputs):
            source_path = Path(str(source.get("path", ""))).resolve()
            repo_path = source.get("repo_path")
            if not isinstance(repo_path, str) or str(source_path) in seen_inputs:
                continue
            seen_inputs.add(str(source_path))
            target = snapshot_dir / f"input-{index:04d}-{source_path.name}"
            shutil.copy2(source_path, target)
            content = target.read_bytes()
            review_inputs.append({
                "kind": str(source.get("kind", "source")),
                "repo_path": repo_path,
                "snapshot_path": str(target),
                "sha256": hashlib.sha256(content).hexdigest(),
                "size": len(content),
            })
        unit = {
            "kind": "code-review-snapshot",
            "method": REVIEW_METHOD,
            "review_id": review_id,
            "journal": str(path.resolve()),
            "base_sha": base_sha,
            "review_scope": "change-only",
            "code_content_id": code["content_id"],
            "artifacts": frozen,
            "review_inputs": review_inputs,
            "ticket_boundary": boundary,
            "implementation_session_id": implementation_session_id,
        }
        marker = snapshot_dir / ".review-unit.json"
        marker.write_text(
            json.dumps(unit, ensure_ascii=False, sort_keys=True) + "\n"
        )
        for file in snapshot_dir.iterdir():
            file.chmod(0o400)
        snapshot_dir.chmod(0o500)
        register_owned_directory(
            snapshot_root, snapshot_dir, purpose="run-review-snapshot"
        )
    except Exception:
        if snapshot_dir.exists():
            snapshot_dir.chmod(0o700)
            shutil.rmtree(snapshot_dir)
        raise
    return {
        "status": "ready",
        "method": REVIEW_METHOD,
        "review_id": review_id,
        "base_sha": base_sha,
        "review_scope": "change-only",
        "snapshot_dir": str(snapshot_dir),
        "code_content_id": code["content_id"],
        "artifacts": frozen,
        "review_inputs": review_inputs,
        "ticket_boundary": boundary,
        "implementation_session_id": implementation_session_id,
    }


def _owned_review_unit(
    path: Path, snapshot_dir: Path
) -> tuple[dict[str, object], dict[str, object], Path, Path, dict[str, object], dict[str, object]]:
    journal = _load_journal(path)
    context = journal.get("context")
    if not isinstance(context, dict):
        raise RunJournalError("run journal context 无效")
    repo = Path(str(context.get("repo", ""))).resolve()
    expected_root = (_evidence_directory(path) / "review-snapshots").resolve()
    snapshot_dir = snapshot_dir.resolve()
    if snapshot_dir.parent != expected_root:
        raise RunJournalError("review snapshot 不属于当前 run")
    try:
        verify_owned_directory(
            expected_root, snapshot_dir, purpose="run-review-snapshot"
        )
        unit = json.loads(
            (snapshot_dir / ".review-unit.json").read_text()
        )
    except (OSError, json.JSONDecodeError, FilesystemSafetyError) as exc:
        raise RunJournalError("review snapshot 无法验证") from exc
    if (
        not isinstance(unit, dict)
        or set(unit) != {
            "kind", "method", "review_id", "journal", "base_sha", "review_scope",
            "code_content_id", "artifacts", "review_inputs", "ticket_boundary", "implementation_session_id"
        }
        or unit.get("kind") != "code-review-snapshot"
        or unit.get("method") != REVIEW_METHOD
        or unit.get("journal") != str(path.resolve())
        or unit.get("base_sha") != context.get("base_sha")
        or unit.get("review_scope") != "change-only"
        or not isinstance(unit.get("artifacts"), list)
        or not isinstance(unit.get("review_inputs"), list)
        or not isinstance(unit.get("implementation_session_id"), str)
    ):
        raise RunJournalError("review snapshot schema 无效")
    _verify_ticket_boundary(context, unit.get("ticket_boundary"))
    code = build_code_receipt(path)
    if unit.get("code_content_id") != code["content_id"]:
        raise RunJournalError("review snapshot 与当前代码不匹配")
    return journal, context, repo, expected_root, unit, code


def _release_review_snapshot(expected_root: Path, snapshot_dir: Path) -> None:
    try:
        snapshot_dir.chmod(0o700)
        quarantine_and_remove(
            expected_root, snapshot_dir, purpose="run-review-snapshot"
        )
    except FilesystemSafetyError as exc:
        raise RunJournalError("review snapshot 无法安全释放") from exc


def _validate_evidence_refs(
    path: Path, context: dict[str, object], unit: dict[str, object], refs: object
) -> None:
    if not isinstance(refs, list) or not refs or not all(
        isinstance(ref, str) and ref for ref in refs
    ):
        raise RunJournalError("review coverage 必须包含证据引用")
    artifacts = unit.get("artifacts")
    spec = context.get("spec")
    known_paths = {
        str(artifact.get("repo_path")) for artifact in artifacts
        if isinstance(artifact, dict)
    } if isinstance(artifacts, list) else set()
    spec_ref = str(spec.get("ref")) if isinstance(spec, dict) else ""
    for ref in refs:
        if ref.startswith("snapshot:") and ref.removeprefix("snapshot:") in known_paths:
            continue
        if ref == f"spec:{spec_ref}":
            continue
        if ref.startswith("test:"):
            _load_evidence(path, {"kind": "test", "evidence_id": ref.removeprefix("test:")}, "test")
            continue
        raise RunJournalError("review coverage 证据引用不属于当前 work unit")


def _validate_self_review_coverage(
    path: Path, context: dict[str, object], unit: dict[str, object], coverage: object
) -> None:
    if not isinstance(coverage, dict) or set(coverage) != {"acceptance", "probes"}:
        raise RunJournalError("self review coverage schema 无效")
    boundary = unit.get("ticket_boundary")
    if not isinstance(boundary, dict):
        raise RunJournalError("review Ticket boundary 无效")
    current = boundary.get("current")
    expected_acceptance = {
        item.get("id") for item in current.get("acceptance", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    } if isinstance(current, dict) else set()
    acceptance = coverage.get("acceptance")
    if not isinstance(acceptance, list):
        raise RunJournalError("self review acceptance coverage 无效")
    seen_acceptance: set[str] = set()
    for item in acceptance:
        if not isinstance(item, dict) or set(item) != {"acceptance_id", "evidence_refs"}:
            raise RunJournalError("self review acceptance 条目无效")
        identifier = item.get("acceptance_id")
        if not isinstance(identifier, str) or identifier in seen_acceptance:
            raise RunJournalError("self review acceptance_id 重复或无效")
        seen_acceptance.add(identifier)
        _validate_evidence_refs(path, context, unit, item.get("evidence_refs"))
    if seen_acceptance != expected_acceptance:
        raise RunJournalError("self review 未完整覆盖当前 Ticket 验收")
    expected_probes = set(boundary.get("required_probes", []))
    probes = coverage.get("probes")
    if not isinstance(probes, list):
        raise RunJournalError("self review probe coverage 无效")
    seen_probes: set[str] = set()
    for item in probes:
        if not isinstance(item, dict) or set(item) != {"probe", "summary", "evidence_refs"}:
            raise RunJournalError("self review probe 条目无效")
        probe = item.get("probe")
        if not isinstance(probe, str) or probe in seen_probes or not isinstance(item.get("summary"), str) or not item["summary"].strip():
            raise RunJournalError("self review probe 重复或无效")
        seen_probes.add(probe)
        _validate_evidence_refs(path, context, unit, item.get("evidence_refs"))
    if seen_probes != expected_probes:
        raise RunJournalError("self review 未完整覆盖必需风险探针")


def _validate_review_result(
    path: Path, result: dict[str, object], unit: dict[str, object], code: dict[str, object],
    context: dict[str, object],
) -> tuple[str, set[str]]:
    if set(result) != {
        "review_id", "status", "code_content_id", "reviewer_provenance", "findings",
        "follow_ons", "design_gap", "self_review_coverage",
    }:
        raise RunJournalError("review result 字段无效")
    status = result.get("status")
    findings = result.get("findings")
    follow_ons = result.get("follow_ons")
    provenance = result.get("reviewer_provenance")
    if (
        status not in REVIEW_STATUSES
        or result.get("review_id") != unit.get("review_id")
        or result.get("code_content_id") != code.get("content_id")
        or not isinstance(findings, list)
        or not isinstance(follow_ons, list)
        or not isinstance(provenance, dict)
        or set(provenance) != {"kind", "session_id"}
        or provenance.get("kind") not in REVIEW_PROVENANCE_KINDS
        or not isinstance(provenance.get("session_id"), str)
        or not _SAFE_ID.fullmatch(str(provenance.get("session_id")))
    ):
        raise RunJournalError("review result 与当前 review snapshot 不匹配")
    if provenance["kind"] == "self":
        if provenance["session_id"] != unit.get("implementation_session_id"):
            raise RunJournalError("self review 必须使用当前 implementation session")
        _validate_self_review_coverage(path, context, unit, result.get("self_review_coverage"))
    elif provenance["session_id"] == unit.get("implementation_session_id") or result.get("self_review_coverage") is not None:
        raise RunJournalError("independent session provenance 或 coverage 无效")
    boundary = unit.get("ticket_boundary")
    current = boundary.get("current") if isinstance(boundary, dict) else None
    acceptance_ids = {
        item.get("id") for item in current.get("acceptance", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    } if isinstance(current, dict) else set()
    successors = {
        item.get("id"): {
            entry.get("id") for entry in item.get("acceptance", [])
            if isinstance(entry, dict) and isinstance(entry.get("id"), str)
        }
        for item in boundary.get("successors", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    } if isinstance(boundary, dict) else {}
    for item in follow_ons:
        if not isinstance(item, dict) or set(item) != {
            "id", "root_cause", "owner_ticket_id", "acceptance_ids", "summary", "baseline_reachable"
        }:
            raise RunJournalError("review follow-on schema 无效")
        owner = item.get("owner_ticket_id")
        refs = item.get("acceptance_ids")
        if (
            not all(isinstance(item.get(field), str) and str(item[field]).strip() for field in ("id", "root_cause", "summary"))
            or owner not in successors
            or not isinstance(refs, list) or not refs or not all(isinstance(ref, str) for ref in refs)
            or not set(refs).issubset(successors[owner])
            or item.get("baseline_reachable") not in {True, False}
        ):
            raise RunJournalError("review follow-on 不属于当前 Ticket 的直接下游")
    design_gap = result.get("design_gap")
    if status == "blocked-by-design":
        if findings or follow_ons or not isinstance(design_gap, dict) or set(design_gap) != {"root_cause", "summary", "evidence_refs"}:
            raise RunJournalError("design gap review result 无效")
        if not all(isinstance(design_gap.get(field), str) and str(design_gap[field]).strip() for field in ("root_cause", "summary")):
            raise RunJournalError("design gap 缺少根因或摘要")
        _validate_evidence_refs(path, context, unit, design_gap.get("evidence_refs"))
        return str(status), {str(design_gap["root_cause"])}
    if design_gap is not None:
        raise RunJournalError("仅 blocked-by-design review 可包含 design_gap")
    if status == "pass":
        if findings:
            raise RunJournalError("pass review 不得包含 findings")
        return str(status), set()
    if not findings:
        raise RunJournalError(f"{status} review 必须包含结构化条目")
    roots: set[str] = set()
    for item in findings:
        if not isinstance(item, dict) or set(item) != {
            "id", "root_cause", "severity", "summary", "baseline_reachable", "acceptance_ids"
        }:
            raise RunJournalError("review finding schema 无效")
        if not all(
            isinstance(item.get(field), str) and str(item[field]).strip()
            for field in ("id", "root_cause", "summary")
        ):
            raise RunJournalError("review finding 缺少 id、root_cause 或 summary")
        item_acceptance = item.get("acceptance_ids")
        if not isinstance(item_acceptance, list) or not item_acceptance or not all(isinstance(value, str) for value in item_acceptance) or not set(item_acceptance).issubset(acceptance_ids):
            raise RunJournalError("review finding 必须引用当前 Ticket 验收")
        if status == "findings":
            if item.get("severity") not in REVIEW_SEVERITIES:
                raise RunJournalError("review finding severity 无效")
            if item.get("baseline_reachable") is not True:
                raise RunJournalError(
                    "review finding 必须能从固定基线到当前快照证明；否则标记 inconclusive"
                )
        elif item.get("severity") is not None or item.get("baseline_reachable") not in {None, False}:
            raise RunJournalError("inconclusive 条目不得伪造 severity 或基线可达性")
        roots.add(str(item["root_cause"]))
    return str(status), roots


def _verify_review_snapshot_bytes(unit: dict[str, object], snapshot_dir: Path) -> None:
    for artifact in unit["artifacts"]:
        expected = {
            "repo_path", "snapshot_path", "sha256", "size",
            "baseline_snapshot_path", "baseline_sha256", "baseline_size",
        }
        if not isinstance(artifact, dict) or set(artifact) != expected:
            raise RunJournalError("review snapshot inventory 无效")
        for prefix in ("", "baseline_"):
            raw_path = artifact[f"{prefix}snapshot_path"]
            digest = artifact[f"{prefix}sha256"]
            size = artifact[f"{prefix}size"]
            if raw_path is None and digest is None and size is None:
                continue
            frozen = Path(str(raw_path))
            if frozen.parent.resolve() != snapshot_dir or not frozen.is_file():
                raise RunJournalError("review snapshot 文件路径无效")
            content = frozen.read_bytes()
            if len(content) != size or hashlib.sha256(content).hexdigest() != digest:
                raise RunJournalError("review snapshot bytes 已漂移")
    inputs = unit.get("review_inputs")
    if not isinstance(inputs, list):
        raise RunJournalError("review input inventory 无效")
    for item in inputs:
        expected = {"kind", "repo_path", "snapshot_path", "sha256", "size"}
        if not isinstance(item, dict) or set(item) != expected:
            raise RunJournalError("review input inventory 无效")
        frozen = Path(str(item.get("snapshot_path", "")))
        if frozen.parent.resolve() != snapshot_dir or not frozen.is_file():
            raise RunJournalError("review input 文件路径无效")
        content = frozen.read_bytes()
        if len(content) != item.get("size") or hashlib.sha256(content).hexdigest() != item.get("sha256"):
            raise RunJournalError("review input bytes 已漂移")


def _previous_review_roots(path: Path) -> set[str]:
    journal = _load_journal(path)
    evidence = journal.get("evidence")
    if not isinstance(evidence, list):
        return set()
    for receipt in reversed(evidence):
        try:
            record = _load_evidence(path, receipt, "review")
        except RunJournalError:
            continue
        if record.get("status") != "findings":
            continue
        roots = record.get("root_causes")
        return set(roots) if isinstance(roots, list) else set()
    return set()


def _return_review_to_implementation(
    path: Path, receipt: dict[str, str], roots: set[str], *, repeated: bool
) -> None:
    journal = _load_journal(path)
    if journal.get("phase") not in {"reviewing", "committing"}:
        raise RunJournalError("带 finding 的 review 只能从 review 阶段返回实施")
    journal["phase"] = "implementing"
    events = journal.get("events")
    if not isinstance(events, list):
        raise RunJournalError("run journal events 无效")
    events.append({
        "phase": "implementing",
        "review_attempt": receipt,
        "root_causes": sorted(roots),
        "repeated_root_cause": repeated,
        "at": datetime.now(timezone.utc).isoformat(),
    })
    _write_json_atomic(path, journal)


def submit_review_result(
    path: Path,
    snapshot_dir: Path,
    result: dict[str, object],
    *,
    execution: str = "host-method",
    argv: list[str] | None = None,
    completed: subprocess.CompletedProcess[bytes] | None = None,
) -> dict[str, object]:
    """Persist every terminal review outcome and release its owned snapshot."""
    journal, context, repo, expected_root, unit, code = _owned_review_unit(
        path, snapshot_dir
    )
    snapshot_dir = snapshot_dir.resolve()
    try:
        if journal.get("phase") not in {"reviewing", "committing"}:
            raise RunJournalError("review result 只能在 review 阶段提交")
        status, roots = _validate_review_result(path, result, unit, code, context)
        _verify_review_snapshot_bytes(unit, snapshot_dir)
        current_code = build_code_receipt(path)
        if current_code["content_id"] != code["content_id"]:
            raise RunJournalError("review result 与当前 review snapshot 不匹配")
        previous_roots = _previous_review_roots(path)
        result_path = _evidence_directory(path) / "review-results" / f"{unit['review_id']}.json"
        if result_path.exists() or result_path.is_symlink():
            raise RunJournalError("review result 目标已存在")
        _write_json_atomic(result_path, result)
        result_receipt = _source_receipt(
            repo, result_path, "review result", kind="review-result"
        )
        record: dict[str, object] = {
            "kind": "review",
            "method": REVIEW_METHOD,
            "status": status,
            "execution": execution,
            "code_content_id": code["content_id"],
            "review_id": unit["review_id"],
            "snapshot_content_id": unit["code_content_id"],
            "snapshot": unit,
            "result": result_receipt,
            "root_causes": sorted(roots),
            "reviewer_provenance": result["reviewer_provenance"],
        }
        if execution == "declared-command":
            if completed is None or argv is None:
                raise RunJournalError("declared-command review 缺少进程证据")
            record.update({
                "argv": argv,
                "exit_code": completed.returncode,
                "stdout_sha256": hashlib.sha256(completed.stdout).hexdigest(),
                "stderr_sha256": hashlib.sha256(completed.stderr).hexdigest(),
            })
        elif execution != "host-method":
            raise RunJournalError("未知 review execution")
        receipt = _persist_evidence(path, record)
        repeated = bool(roots & previous_roots)
        if status == "findings":
            _return_review_to_implementation(path, receipt, roots, repeated=repeated)
        elif status == "blocked-by-design":
            record_run(
                path,
                "blocked-by-design",
                blocker=f"review design gap: {sorted(roots)[0]}",
            )
        next_action = {
            "pass": "submit-completed",
            "findings": "blocked-by-design" if repeated else "fix-findings",
            "inconclusive": "blocked-by-evidence",
            "blocked-by-design": "blocked-by-design",
        }[status]
        return {
            "status": status,
            "next_action": next_action,
            "evidence_receipt": receipt,
            "review_receipt": receipt if status == "pass" else None,
            "repeated_root_causes": sorted(roots & previous_roots),
        }
    finally:
        _release_review_snapshot(expected_root, snapshot_dir)


def record_review_evidence(
    path: Path, snapshot_dir: Path, argv: list[str], *, reviewer_session_id: str | None = None,
) -> dict[str, object]:
    """Run a declared reviewer and persist its pass, findings or inconclusive result."""
    if not argv or any(not isinstance(value, str) or not value for value in argv):
        raise RunJournalError("review evidence command 必须是非空 argv")
    journal, context, repo, expected_root, unit, code = _owned_review_unit(
        path, snapshot_dir
    )
    allowed = context.get("review_commands")
    if not isinstance(allowed, list) or argv not in [
        shlex.split(command)
        for command in allowed
        if isinstance(command, str) and command.strip()
    ]:
        raise RunJournalError("review evidence command 未在 work unit 中声明")
    if reviewer_session_id is not None and (
        not _SAFE_ID.fullmatch(reviewer_session_id)
        or reviewer_session_id == unit.get("implementation_session_id")
    ):
        raise RunJournalError("independent reviewer session id 无效")
    environment = os.environ.copy()
    environment.update({
        "MY_MATT_REVIEW_ID": str(unit["review_id"]),
        "MY_MATT_REVIEW_SNAPSHOT": str(snapshot_dir),
        "MY_MATT_CODE_CONTENT_ID": str(code["content_id"]),
        "MY_MATT_REVIEW_METHOD": REVIEW_METHOD,
        "MY_MATT_TICKET_BOUNDARY": json.dumps(unit["ticket_boundary"], ensure_ascii=False),
        "MY_MATT_IMPLEMENTATION_SESSION_ID": str(unit["implementation_session_id"]),
        "MY_MATT_SPEC_REF": str(context["spec"]["ref"]),
    })
    if reviewer_session_id is not None:
        environment["MY_MATT_REVIEWER_SESSION_ID"] = reviewer_session_id
    completed = subprocess.run(
        argv, cwd=snapshot_dir if reviewer_session_id is not None else repo,
        env=environment, capture_output=True, check=False,
    )
    try:
        result = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        _release_review_snapshot(expected_root, snapshot_dir.resolve())
        raise RunJournalError("review command 未输出有效 JSON") from exc
    if not isinstance(result, dict) or completed.returncode != 0:
        _release_review_snapshot(expected_root, snapshot_dir.resolve())
        raise RunJournalError("review command 结果或退出状态无效")
    return submit_review_result(
        path,
        snapshot_dir,
        result,
        execution="declared-command",
        argv=argv,
        completed=completed,
    )


def _load_evidence(path: Path, receipt: object, kind: str) -> dict[str, object]:
    if (
        not isinstance(receipt, dict)
        or set(receipt) != {"kind", "evidence_id"}
        or receipt.get("kind") != kind
        or not isinstance(receipt.get("evidence_id"), str)
        or not re.fullmatch(r"[0-9a-f]{64}", str(receipt["evidence_id"]))
    ):
        raise RunJournalError(
            f"completed outcome 必须引用 runtime 生成的 {kind}_receipt"
        )
    evidence_id = str(receipt["evidence_id"])
    journal = _load_journal(path)
    registered = journal.get("evidence")
    if not isinstance(registered, list) or receipt not in registered:
        raise RunJournalError(f"{kind} evidence 未由 runtime 登记")
    evidence_path = _evidence_directory(path) / f"{evidence_id}.json"
    try:
        raw = evidence_path.read_bytes()
        record = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise RunJournalError(f"{kind} evidence record 无法读取") from exc
    canonical = json.dumps(
        record, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    if raw != canonical + b"\n" or hashlib.sha256(canonical).hexdigest() != evidence_id:
        raise RunJournalError(f"{kind} evidence record 已漂移")
    return record


def _validate_completion_receipts(
    path: Path, test: object, review: object, code: object
) -> None:
    if not isinstance(code, dict) or code.get("kind") != "code":
        raise RunJournalError("completed outcome 必须包含结构化 code_receipt")
    current = build_code_receipt(path)
    if code != current:
        raise RunJournalError("code receipt 与当前声明范围不匹配")
    content_id = current["content_id"]
    test_evidence = _load_evidence(path, test, "test")
    if not (
        test_evidence.get("status") == "pass"
        and test_evidence.get("exit_code") == 0
        and test_evidence.get("code_content_id") == content_id
        and isinstance(test_evidence.get("argv"), list)
        and all(isinstance(value, str) and value for value in test_evidence["argv"])
        and all(
            isinstance(test_evidence.get(field), str)
            and re.fullmatch(r"[0-9a-f]{64}", str(test_evidence[field]))
            for field in ("stdout_sha256", "stderr_sha256")
        )
    ):
        raise RunJournalError("completed outcome 必须包含与当前代码绑定的结构化 test_receipt")
    review_evidence = _load_evidence(path, review, "review")
    if not (
        review_evidence.get("status") == "pass"
        and review_evidence.get("method") == REVIEW_METHOD
        and review_evidence.get("execution") in {"host-method", "declared-command"}
        and review_evidence.get("code_content_id") == content_id
        and isinstance(review_evidence.get("review_id"), str)
        and bool(str(review_evidence.get("review_id")).strip())
        and isinstance(review_evidence.get("snapshot_content_id"), str)
        and isinstance(review_evidence.get("result"), dict)
    ):
        raise RunJournalError("completed outcome 必须包含与当前代码绑定的结构化 review_receipt")
    journal = _load_journal(path)
    context = journal.get("context")
    result_receipt = review_evidence["result"]
    if not isinstance(context, dict) or not isinstance(result_receipt, dict):
        raise RunJournalError("review evidence context 无效")
    if review_evidence.get("execution") == "declared-command":
        allowed = context.get("review_commands")
        if (
            review_evidence.get("exit_code") != 0
            or not isinstance(review_evidence.get("argv"), list)
            or not isinstance(allowed, list)
            or review_evidence["argv"] not in [
                shlex.split(command)
                for command in allowed
                if isinstance(command, str) and command.strip()
            ]
            or not all(
                isinstance(review_evidence.get(field), str)
                and re.fullmatch(r"[0-9a-f]{64}", str(review_evidence[field]))
                for field in ("stdout_sha256", "stderr_sha256")
            )
        ):
            raise RunJournalError("review evidence command 未由当前 work unit 声明或执行失败")
    repo = Path(str(context.get("repo", ""))).resolve()
    current_result = _source_receipt(
        repo,
        Path(str(result_receipt.get("path", ""))),
        "review result",
        kind="review-result",
    )
    if current_result != result_receipt:
        raise RunJournalError("review result 内容已变化")
    try:
        result = json.loads(Path(str(result_receipt["path"])).read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise RunJournalError("review result 无法重验") from exc
    unit = review_evidence.get("snapshot")
    if not isinstance(unit, dict):
        raise RunJournalError("review evidence snapshot 无效")
    try:
        _verify_ticket_boundary(context, unit.get("ticket_boundary"))
        status, _ = _validate_review_result(path, result, unit, current, context)
    except RunJournalError as exc:
        raise RunJournalError("review result 与 evidence 不匹配") from exc
    if (
        status != "pass"
        or result.get("review_id") != review_evidence.get("review_id")
        or result.get("code_content_id") != content_id
    ):
        raise RunJournalError("review result 与 evidence 不匹配")
    if current["content_id"] != review_evidence["snapshot_content_id"]:
        raise RunJournalError("review snapshot 内容已变化")


def submit_run_outcome(
    path: Path,
    result: dict[str, object],
    *,
    fail_after_writes: int | None = None,
) -> dict[str, object]:
    """Validate and persist the semantic outcome returned by my-implement."""
    expected_fields = {"outcome", "test_receipt", "review_receipt", "code_receipt", "blocker"}
    if set(result) != expected_fields:
        raise RunJournalError("implementation result 字段无效")
    outcome = result.get("outcome")
    if outcome not in IMPLEMENTATION_OUTCOMES:
        raise RunJournalError(f"未知 implementation outcome：{outcome}")
    initial = _load_journal(path)
    context = initial.get("context")
    ticket_context = context.get("ticket") if isinstance(context, dict) else None
    if not isinstance(context, dict) or not isinstance(ticket_context, dict):
        raise RunJournalError("run journal context 无效")
    repo = Path(str(context.get("repo", ""))).resolve()
    ticket_path = Path(str(ticket_context.get("path", ""))).resolve()
    ticket_path, topic = _ticket_location(repo, ticket_path)
    attempt_id = initial.get("attempt_id")
    ticket_id = initial.get("run_id")
    if not isinstance(attempt_id, str) or not _SAFE_ID.fullmatch(attempt_id):
        raise RunJournalError("run journal attempt_id 无效")
    if not isinstance(ticket_id, str) or not _SAFE_ID.fullmatch(ticket_id):
        raise RunJournalError("run journal run_id 无效")

    try:
        with ticket_lock(repo, topic, ticket_id):
            recover_lifecycle_transactions(repo, topic=topic, ticket_id=ticket_id)
            journal = _load_journal(path)
            if journal.get("submission") is not None:
                raise RunJournalError("run journal 已提交 outcome")
            verify_run_sources(journal)

            test_receipt = result.get("test_receipt")
            review_receipt = result.get("review_receipt")
            code_receipt = result.get("code_receipt")
            blocker = result.get("blocker")
            current_phase = journal.get("phase")
            terminal_phase = "complete" if outcome == "completed" else outcome
            if outcome == "completed" and current_phase != "committing":
                raise RunJournalError("completed outcome 只能从 committing phase 提交")
            if current_phase not in RUN_PHASE_TRANSITIONS or terminal_phase not in RUN_PHASE_TRANSITIONS[current_phase]:
                raise RunJournalError(
                    f"非法 run outcome phase 迁移：{current_phase} -> {terminal_phase}"
                )
            if outcome == "completed":
                _validate_completion_receipts(path, test_receipt, review_receipt, code_receipt)
                if blocker not in {None, ""}:
                    raise RunJournalError("completed outcome 不得包含 blocker")
            elif not isinstance(blocker, str) or not blocker.strip():
                raise RunJournalError(f"{outcome} 必须包含 blocker")

            metadata = frontmatter(ticket_path)
            if metadata.get("status") != "implementing" or metadata.get("claimed_by") != attempt_id:
                raise RunJournalError("Ticket mutable projection 与当前 attempt 不匹配")
            now = datetime.now(timezone.utc).isoformat()
            submission = {
                "outcome": outcome,
                "test_receipt": test_receipt,
                "review_receipt": review_receipt,
                "code_receipt": code_receipt,
                "blocker": blocker,
                "at": now,
            }
            updated = json.loads(json.dumps(journal))
            updated["submission"] = submission
            updated["phase"] = terminal_phase
            receipts = updated.get("receipts")
            if not isinstance(receipts, dict):
                raise RunJournalError("run journal receipts 无效")
            receipts.update(
                {"test": test_receipt, "review": review_receipt, "code": code_receipt}
            )
            updated["blocker"] = blocker
            events = updated.get("events")
            if not isinstance(events, list):
                raise RunJournalError("run journal events 无效")
            events.append({"phase": terminal_phase, "outcome": outcome, "at": now})

            before_ticket = ticket_path.read_text(encoding="utf-8")
            ticket_status = {
                "completed": "complete",
                "blocked-by-design": "blocked-by-design",
                "blocked-by-evidence": "ready-for-agent",
            }[str(outcome)]
            after_ticket = project_ticket(
                before_ticket,
                status=ticket_status,
                claimed_by="",
                complete_acceptance=outcome == "completed",
            )
            coordinate_lifecycle_update(
                repo,
                topic=topic,
                ticket_id=ticket_id,
                attempt_id=attempt_id,
                operation="submit",
                updates=[
                    (ticket_path, before_ticket, after_ticket),
                    (path, _json_text(journal), _json_text(updated)),
                ],
                fail_after_writes=fail_after_writes,
            )
            return {
                "status": "accepted",
                "outcome": outcome,
                "next_action": "complete" if outcome == "completed" else "pause",
                "run": updated,
            }
    except LifecycleError as exc:
        raise RunJournalError(str(exc)) from exc


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
        context = build_run_context(
            repo,
            ticket_path,
            base,
            paths,
            execution_agent=execution_agent,
            parallel=parallel,
        )
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
    initial = _load_journal(path)
    context = initial.get("context")
    if not isinstance(context, dict):
        raise RunJournalError("run journal context 无效")
    repo = Path(str(context.get("repo", ""))).resolve()
    topic = context.get("topic")
    ticket_id = initial.get("run_id")
    if not isinstance(topic, str) or not isinstance(ticket_id, str):
        raise RunJournalError("run journal topic 或 run_id 无效")
    try:
        with ticket_lock(repo, topic, ticket_id):
            recover_lifecycle_transactions(repo, topic=topic, ticket_id=ticket_id)
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
    except LifecycleError as exc:
        raise RunJournalError(str(exc)) from exc
