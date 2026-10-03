#!/usr/bin/env python3
"""CLI for building, installing, and checking My Matt Workflow."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# Managed runtime trees are verified by exact file inventory; bytecode caches
# written next to workflow_lib would drift that inventory on every invocation.
sys.dont_write_bytecode = True

from workflow_lib.installer import (
    InstallError,
    install_release,
    load_install_state,
    remove_verified_release,
)
from workflow_lib.check import CheckError, run_check
from workflow_lib.doctor import diagnose_repository
from workflow_lib.release import build_release, release_matches_source
from workflow_lib.review_snapshot import ReviewSnapshotError, build_review_snapshot
from workflow_lib.artifact_review import (
    ArtifactReviewError,
    build_artifact_review_snapshot,
    finalize_artifact_review_snapshot,
    submit_artifact_review_result,
    verify_artifact_review_snapshot,
)
from workflow_lib.validator import ValidationError, validate_repository
from workflow_lib.rules import EXECUTION_AGENTS, RuleError, inspect_rules, resolve_rules
from workflow_lib.tickets import TicketError
from workflow_lib import topic_service, ticket_implementation, ticket_review, ticket_completion, ticket_resolution, branch_review, migration


ROOT = Path(__file__).resolve().parents[1]
AGENT_STATE_HOMES = {
    "codex": Path(
        os.environ.get("CODEX_HOME", Path.home() / ".codex")
    ).expanduser(),
    "cursor": Path.home() / ".cursor",
    "claude": Path.home() / ".claude",
}


def _agent_skills_home(agent: str) -> Path:
    return AGENT_STATE_HOMES[agent] / "skills"


def _default_branch(repo: Path) -> str:
    result = subprocess.run(
        ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0 and "/" in result.stdout:
        return result.stdout.strip().rsplit("/", 1)[-1]
    return "main"


def _discover_standards_sources(repo: Path, agent: str = "auto") -> list[str]:
    """Return project-rule candidates for setup confirmation, without saving them."""
    if agent == "codex":
        codex_instruction = next(
            (
                path
                for path in ("AGENTS.override.md", "AGENTS.md")
                if (repo / path).is_file()
                and (repo / path).read_text(encoding="utf-8").strip()
            ),
            None,
        )
        candidates = [
            *([codex_instruction] if codex_instruction else []),
            "CONTRIBUTING.md",
            "CODING_STANDARDS.md",
        ]
    else:
        candidates = ["AGENTS.md", "CONTRIBUTING.md", "CODING_STANDARDS.md"]
    discovered = [path for path in candidates if (repo / path).is_file()]
    if agent == "codex":
        rule_dir = None
        pattern = ""
    elif agent == "cursor":
        if (repo / ".cursorrules").is_file():
            discovered.append(".cursorrules")
        rule_dir = repo / ".cursor" / "rules"
        pattern = "*.mdc"
    elif agent == "claude":
        discovered.extend(
            path for path in ("CLAUDE.md", ".claude/CLAUDE.md") if (repo / path).is_file()
        )
        rule_dir = repo / ".claude" / "rules"
        pattern = "*.md"
    else:
        rule_dir = None
        pattern = ""
    if rule_dir is not None and rule_dir.is_dir():
        discovered.extend(
            path.relative_to(repo).as_posix()
            for path in sorted(rule_dir.rglob(pattern))
            if path.is_file()
        )
    return discovered


def command_validate(_: argparse.Namespace) -> None:
    try:
        report = validate_repository(ROOT)
    except ValidationError as exc:
        raise SystemExit(str(exc)) from exc
    print(f"VALID skills={report['skills']}")


def _run_all_up_gate(
    *, check_current_release: bool, root: Path | None = None
) -> dict[str, object]:
    """Run the authoritative source gate and render failures consistently."""
    try:
        return run_check(root or ROOT)
    except CheckError as exc:
        print(json.dumps({"status": "invalid", "error": str(exc)}, ensure_ascii=False))
        raise SystemExit(1) from exc


def command_check(_: argparse.Namespace) -> None:
    """Run the one local all-up gate without depending on Git."""
    report = _run_all_up_gate(check_current_release=False)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


def command_doctor(args: argparse.Namespace) -> None:
    """Report source, current release, and host deployment health independently."""
    homes = (
        {
            f"custom-{index + 1}": Path(value).expanduser()
            for index, value in enumerate(args.agent_home)
        }
        if args.agent_home
        else dict(AGENT_STATE_HOMES)
    )
    print(
        json.dumps(
            diagnose_repository(ROOT, homes),
            ensure_ascii=False,
            sort_keys=True,
        )
    )


def _write_current_release(path: Path, release_id: str) -> None:
    """Atomically replace the current release pointer."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(
                json.dumps({"release_id": release_id}, indent=2) + "\n"
            )
            handle.flush()
            if hasattr(os, "fsync"):
                os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def command_build(args: argparse.Namespace) -> None:
    _build_release(args)


def _build_release(args: argparse.Namespace) -> Path:
    """Build and select a release after the caller has passed its gate."""
    release_id = args.release_id or datetime.now().strftime("%Y%m%d-%H%M%S")
    release = build_release(
        ROOT / "skills",
        ROOT / "releases",
        release_id=release_id,
        upstream_id=args.upstream_id,
        repo_root=ROOT,
        source_gate=lambda snapshot_root: _run_all_up_gate(
            check_current_release=False, root=snapshot_root
        ),
        current_pointer=ROOT / "current.json",
        agent_homes=list(AGENT_STATE_HOMES.values())
        + ([Path(args.agent_home).expanduser()] if getattr(args, "agent_home", None) else []),
    )
    print(release)
    return release


def _current_release() -> Path:
    current = json.loads((ROOT / "current.json").read_text())
    return _release_path(current["release_id"])


def _release_path(release_id: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", release_id):
        raise SystemExit(f"非法 release ID：{release_id}")
    return ROOT / "releases" / release_id


def command_install(args: argparse.Namespace, *, validation_context=None) -> str:
    release = _release_path(args.release) if args.release else _current_release()
    state_home, skills_home, target = _resolve_agent_layout(args)
    outcome = install_release(
        release,
        state_home,
        target=target,
        skills_home=skills_home,
        validation_context=validation_context,
    )
    print(f"{'CURRENT' if outcome == 'current' else 'INSTALLED'} {release.name}")
    return outcome


def command_resolve_rules(args: argparse.Namespace) -> None:
    try:
        rules = resolve_rules(
            Path(args.repo),
            args.agent,
            args.path,
            codex_fallback_filenames=args.codex_fallback,
        )
    except RuleError as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps({"agent": args.agent, "rules": rules}, ensure_ascii=False, indent=2))


def command_inspect_rules(args: argparse.Namespace) -> None:
    try:
        result = inspect_rules(
            Path(args.repo),
            args.agent,
            args.path,
            codex_fallback_filenames=args.codex_fallback,
        )
    except RuleError as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(result, ensure_ascii=False, indent=2))


def command_validate_ticket(args: argparse.Namespace) -> None:
    try:
        repo = topic_service.safe_repo(Path(args.repo))
        topic_service.read_config(repo)
        path = Path(args.path).resolve() if args.path else ticket_implementation.select(repo, args.ticket)[1]
        report = ticket_implementation.validate(repo, path)
    except (TicketError, topic_service.TopicError, OSError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(report, ensure_ascii=False))


def command_work_overview(args: argparse.Namespace) -> None:
    try:
        report = topic_service.overview(Path(args.repo), args.topic)
    except (topic_service.TopicError, OSError) as exc:
        raise SystemExit(str(exc)) from exc
    if args.json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    else:
        for topic in report["topics"]:
            print(f'{topic["topic"]}: {topic["status"]}')


def command_review_snapshot(args: argparse.Namespace) -> None:
    try:
        report = build_review_snapshot(Path(args.repo), args.base)
    except ReviewSnapshotError as exc:
        raise SystemExit(str(exc)) from exc

    exit_code = 0
    if args.expect_content_id:
        if report["content_id"] != args.expect_content_id:
            report["status"] = "stale"
            exit_code = 2
        elif args.require_clean and not report["clean"]:
            report["status"] = "dirty"
            exit_code = 2
        else:
            report["status"] = "match"
    elif args.require_clean:
        raise SystemExit("--require-clean 必须与 --expect-content-id 同时使用")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    if exit_code:
        raise SystemExit(exit_code)


def command_artifact_review_snapshot(args: argparse.Namespace) -> None:
    try:
        report = build_artifact_review_snapshot(
            [Path(path) for path in args.artifact],
            artifact_kind=args.kind,
        )
    except ArtifactReviewError as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


def _read_result_object(path: str, label: str) -> dict[str, object]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"无法读取 {label} result：{path}") from exc
    if not isinstance(value, dict):
        raise SystemExit(f"{label} result 必须是 JSON object")
    return value


def command_artifact_review_submit(args: argparse.Namespace) -> None:
    result = _read_result_object(args.result_file, "artifact review")
    try:
        report = submit_artifact_review_result(
            [Path(path) for path in args.artifact], Path(args.snapshot_dir), result
        )
    except ArtifactReviewError as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    if report["status"] == "stale":
        raise SystemExit(2)


def command_artifact_review_verify(args: argparse.Namespace) -> None:
    try:
        report = verify_artifact_review_snapshot(
            [Path(path) for path in args.artifact], args.expect_content_id
        )
    except ArtifactReviewError as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    if report["status"] == "stale":
        raise SystemExit(2)


def command_artifact_review_finalize(args: argparse.Namespace) -> None:
    try:
        report = finalize_artifact_review_snapshot(
            [Path(path) for path in args.artifact],
            args.expect_content_id,
            Path(args.snapshot_dir),
        )
    except ArtifactReviewError as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    if report["status"] == "stale":
        raise SystemExit(2)


def command_deploy(args: argparse.Namespace) -> None:
    """Install the current content, creating a release only when it changed."""
    from workflow_lib.installer import ReleaseValidationContext
    from workflow_lib.fs_safety import exclusive_lock, FilesystemSafetyError
    from workflow_lib.release_references import REFERENCE_LOCK
    validation_context = ReleaseValidationContext()
    current = _current_release() if (ROOT / "current.json").exists() else None
    reusable = False
    if not args.release_id and current is not None:
        try:
            # A release can be source-equivalent while being corrupt on disk;
            # check integrity before deciding it is safe to reuse.
            with exclusive_lock(current.parent, REFERENCE_LOCK):
                validation_context.verify(current)
                reusable = release_matches_source(
                    current,
                    ROOT / "skills",
                    upstream_id=args.upstream_id,
                    repo_root=ROOT,
                )
        except FilesystemSafetyError as exc:
            raise SystemExit(str(exc)) from exc
        except Exception:
            reusable = False
    selected = current
    if not reusable:
        selected = _build_release(
            argparse.Namespace(release_id=args.release_id, upstream_id=args.upstream_id,
                               agent_home=args.agent_home)
        )
    else:
        _run_all_up_gate(check_current_release=False)
        # The check ran on live input: bind the decision again after it.
        if not release_matches_source(current, ROOT / "skills",
                                      upstream_id=args.upstream_id, repo_root=ROOT):
            raise SystemExit("source 在 deploy check 期间发生变化；请重试")
        print(f"REUSED {current}")
    host_status = command_install(
        argparse.Namespace(release=selected.name, target=args.target, agent_home=args.agent_home),
        validation_context=validation_context)
    print(json.dumps({"source": {"status": "valid"},
                      "release": {"status": "current" if reusable else "built",
                                  "release_id": selected.name},
                      "host": {"status": host_status, "target": args.target}}, sort_keys=True))


def command_migrate(args: argparse.Namespace) -> None:
    try:
        report = migration.migrate(Path(args.repo), args.apply)
    except (TicketError, topic_service.TopicError, OSError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


def command_setup(args: argparse.Namespace) -> None:
    try:
        overrides = {"task_backend": args.task_backend, "agent_directory_mode": args.agent_directory_mode,
                     "default_base_branch": args.base_branch, "test_commands": args.test_command,
                     "standards_sources": args.standards_source, "domain_sources": args.domain_source,
                     "default_execution_agent": args.execution_agent, "assurance_level": args.assurance_level}
        report = topic_service.setup(Path(args.repo), overrides, args.apply,
                                     _discover_standards_sources(Path(args.repo), args.execution_agent or "auto"))
    except (topic_service.TopicError, OSError) as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


def emit_status(args,report):
    if getattr(args,'human',False):
        from workflow_lib.status_text import render
        print(render(report))
    else:print(json.dumps(report,ensure_ascii=False,sort_keys=True))


def command_topic(args: argparse.Namespace) -> None:
    try:
        if args.topic_action == "start":
            report = topic_service.start(Path(args.repo), args.topic, args.level)
        elif args.topic_action == "status":
            report = topic_service.status(Path(args.repo), args.topic)
        elif args.topic_action == "test":
            report = branch_review.test(Path(args.repo), args.topic)
        elif args.topic_action == "review":
            report = branch_review.review(Path(args.repo), args.topic, args.submit, args.reviewer_model, args.reviewer_session_id, initiated_by=args.initiated_by, reason=args.reason)
        elif args.topic_action == "abandon":
            report = topic_service.abandon(Path(args.repo), args.topic, args.reason)
        else:
            report = topic_service.complete(Path(args.repo), args.topic)
    except (TicketError, RuleError, topic_service.TopicError, OSError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    emit_status(args,report)


def command_resolve(args: argparse.Namespace) -> None:
    try:
        if args.refresh:
            from workflow_lib import technical_refresh
            report = technical_refresh.refresh(Path(args.repo), args.topic, args.ticket, args.branch,
                                               reason=args.reason, notes_file=args.notes_file)
        elif args.branch:
            report = branch_review.resolve(Path(args.repo), args.topic, args.accept, args.reason)
        else:
            report = ticket_resolution.resolve(Path(args.repo), args.ticket, args.topic, args.accept, args.reason)
    except (TicketError, topic_service.TopicError, RuleError, OSError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


def command_batch(args):
    from workflow_lib import batches
    try:
        repo=Path(args.repo)
        if args.batch_action == 'plan':
            groups=json.loads(Path(args.groups_file).read_text()) if args.groups_file else None
            report=batches.plan(repo,args.topic,groups,args.reason)
        elif args.batch_action == 'status':report=batches.status(repo,args.topic)
        elif args.batch_action == 'test':report=batches.test(repo,args.topic)
        elif args.batch_action == 'review':report=branch_review.review(repo,args.topic,args.submit,args.reviewer_model,args.reviewer_session_id,batch=True)
        elif args.batch_action == 'reopen':report=batches.reopen(repo,args.topic,args.reason)
        elif args.batch_action == 'refresh':
            from workflow_lib import technical_refresh
            report=technical_refresh.refresh(repo,args.topic,batch=True,reason=args.reason,notes_file=args.notes_file)
        elif args.batch_action == 'repair':report=batches.repair(repo,args.topic,args.notes_file)
        else:report=batches.close(repo,args.topic,args.batch_action=='accept',args.reason)
    except (TicketError,RuleError,topic_service.TopicError,OSError,ValueError) as exc:
        raise SystemExit(str(exc))
    emit_status(args,report)


def command_implement(args: argparse.Namespace) -> None:
    try:
        if args.implement_action == "start":
            report = ticket_implementation.start(Path(args.repo), args.ticket, args.topic, args.agent)
        elif args.implement_action == "review":
            report = ticket_review.review(Path(args.repo), args.ticket, args.topic, args.submit, args.reviewer_model, args.reviewer_session_id, args.reason)
        elif args.implement_action == "test":
            argv = args.argv[1:] if args.argv[:1] == ["--"] else args.argv
            report = ticket_implementation.test(Path(args.repo), args.ticket, args.topic, argv)
        elif args.implement_action == "self-review":
            from workflow_lib import batches
            report = batches.self_review(Path(args.repo),args.ticket,args.topic,args.notes_file,args.findings_file,args.no_findings)
        elif args.implement_action == "finish":
            report = ticket_completion.finish(Path(args.repo), args.ticket, args.topic, args.notes_file)
        else:
            report = ticket_implementation.status(Path(args.repo), args.ticket, args.topic)
    except (TicketError, topic_service.TopicError, RuleError, OSError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    emit_status(args,report)


def _release_ids_referenced_by(agent_homes: set[Path]) -> set[str]:
    referenced = {_current_release().name}
    for agent_home in agent_homes:
        state_path = agent_home / "my-matt-workflow" / "install-state.json"
        try:
            state = load_install_state(state_path)
        except InstallError as exc:
            raise SystemExit(f"拒绝清理：安装状态无效：{state_path}: {exc}") from exc
        if state is None:
            continue
        release_id = state.get("release_id")
        assert isinstance(release_id, str)
        referenced.add(release_id)
    return referenced


def command_prune_releases(args: argparse.Namespace) -> None:
    """Delete only release directories not referenced by a known Agent install."""
    agent_homes = set(AGENT_STATE_HOMES.values()) | {
        Path(path).expanduser() for path in args.agent_home
    }
    referenced = _release_ids_referenced_by(agent_homes)
    candidates = sorted(
        path
        for path in (ROOT / "releases").iterdir()
        if path.is_dir()
        and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", path.name)
        and path.name not in referenced
    )
    report = {
        "referenced_release_ids": sorted(referenced),
        "candidates": [path.name for path in candidates],
        "deleted": [],
    }
    if args.apply:
        for path in candidates:
            try:
                remove_verified_release(ROOT / "releases", path)
            except InstallError as exc:
                raise SystemExit(f"拒绝清理 release {path.name}：{exc}") from exc
            report["deleted"].append(path.name)
    print(json.dumps(report, ensure_ascii=False, indent=2))


def _resolve_agent_layout(
    args: argparse.Namespace,
) -> tuple[Path, Path, str | None]:
    if args.agent_home:
        state_home = Path(args.agent_home).expanduser()
        target = args.target if args.target != "auto" else None
        return state_home, state_home / "skills", target
    if args.target != "auto":
        return (
            AGENT_STATE_HOMES[args.target],
            _agent_skills_home(args.target),
            args.target,
        )
    candidates = [
        name for name in AGENT_STATE_HOMES if _agent_skills_home(name).is_dir()
    ]
    if len(candidates) == 1:
        target = candidates[0]
        return AGENT_STATE_HOMES[target], _agent_skills_home(target), target
    if not candidates:
        raise SystemExit("未检测到 Agent Skill 目录；请指定 --target 或 --agent-home")
    raise SystemExit("检测到多个 Agent Skill 目录；请指定 --target 或 --agent-home")


def _add_profile_arguments(command):
    command.add_argument("--repo", default=".")
    command.add_argument("--task-backend")
    command.add_argument("--assurance-level")
    command.add_argument("--agent-directory-mode", choices=["private", "shared"])
    command.add_argument("--base-branch")
    command.add_argument("--execution-agent", choices=["auto", *sorted(EXECUTION_AGENTS)])
    command.add_argument("--test-command", action="append")
    command.add_argument("--standards-source", action="append")
    command.add_argument("--domain-source", action="append")


class WorkflowParser(argparse.ArgumentParser):
    def error(self, message):
        if 'invalid choice' in message and 'command' in message:
            message = '未知命令：' + message
        super().error(message)


def command_metrics(args):
    from workflow_lib.metrics import summarize
    try:
        topic_service.read_config(topic_service.safe_repo(args.repo))
        report = summarize(Path(args.repo), args.topic)
    except (topic_service.TopicError, OSError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


def command_escape(args):
    from workflow_lib.quality_metrics import record_escape
    try:
        report=record_escape(Path(args.repo),args.topic,args.source,args.view,args.expected_layer,args.description,args.batch,args.ticket)
    except (topic_service.TopicError,OSError,ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(report,ensure_ascii=False,sort_keys=True))


def parser() -> argparse.ArgumentParser:
    result = WorkflowParser()
    sub = result.add_subparsers(dest="command", required=True)

    migrate = sub.add_parser("migrate")
    migrate.add_argument("--repo", default=".")
    migrate.add_argument("--apply", action="store_true")
    migrate.set_defaults(func=command_migrate)

    setup = sub.add_parser("setup")
    _add_profile_arguments(setup)
    setup.add_argument("--apply", action="store_true")
    setup.set_defaults(func=command_setup)

    topic = sub.add_parser("topic")
    topic_actions = topic.add_subparsers(dest="topic_action", required=True)
    for action in ("start", "status", "test", "review", "complete", "abandon"):
        command = topic_actions.add_parser(action)
        command.add_argument("--repo", default=".")
        command.add_argument("--topic", required=action == "start")
        if action == "start":
            command.add_argument("--level", choices=("quick", "standard"), required=True)
        if action == "review":
            command.add_argument("--submit")
            command.add_argument("--reviewer-model")
            command.add_argument("--reviewer-session-id")
            command.add_argument("--reason")
            command.add_argument("--initiated-by", choices=("user","agent"))
        if action == "abandon":
            command.add_argument("--reason", required=True)
        if action == 'status':command.add_argument('--human',action='store_true')
        command.set_defaults(func=command_topic)

    batch = sub.add_parser('batch')
    batch_actions=batch.add_subparsers(dest='batch_action',required=True)
    for action in ('plan','status','test','review','repair','close','accept','reopen','refresh'):
        command=batch_actions.add_parser(action)
        command.add_argument('--repo',default='.')
        command.add_argument('--topic')
        command.add_argument('--reason',required=action=='refresh',default='默认整个 Topic 一个批次')
        command.add_argument('--groups-file')
        command.add_argument('--notes-file',required=action=='refresh')
        command.add_argument('--submit')
        command.add_argument('--reviewer-model')
        command.add_argument('--reviewer-session-id')
        if action == 'status':command.add_argument('--human',action='store_true')
        command.set_defaults(func=command_batch)

    implement = sub.add_parser("implement")
    implement_actions = implement.add_subparsers(dest="implement_action", required=True)
    for action in ("start", "test", "review", "self-review", "finish", "status"):
        command = implement_actions.add_parser(action)
        command.add_argument("--repo", default=".")
        command.add_argument("--topic")
        command.add_argument("--ticket")
        if action == "start":
            command.add_argument("--agent", choices=sorted(EXECUTION_AGENTS))
        if action == "review":
            command.add_argument("--submit")
            command.add_argument("--reviewer-model")
            command.add_argument("--reviewer-session-id")
            command.add_argument("--reason")
            command.add_argument("--initiated-by", choices=("user","agent"))
        if action == "test":
            command.add_argument("argv", nargs=argparse.REMAINDER)
        if action in ("finish", "self-review"):
            command.add_argument("--notes-file")
        if action == 'self-review':
            observation=command.add_mutually_exclusive_group()
            observation.add_argument('--findings-file')
            observation.add_argument('--no-findings',action='store_true')
        if action == 'status':command.add_argument('--human',action='store_true')
        command.set_defaults(func=command_implement)

    resolve = sub.add_parser("resolve")
    resolve.add_argument("--repo", default=".")
    selection = resolve.add_mutually_exclusive_group(required=True)
    selection.add_argument("--ticket")
    selection.add_argument("--branch", action="store_true")
    resolve.add_argument("--topic")
    decision = resolve.add_mutually_exclusive_group(required=True)
    decision.add_argument("--accept", action="store_true")
    decision.add_argument("--reopen", action="store_true")
    decision.add_argument("--refresh", action="store_true")
    resolve.add_argument("--notes-file")
    resolve.add_argument("--reason", required=True)
    resolve.set_defaults(func=command_resolve)

    validate = sub.add_parser("validate")
    validate.set_defaults(func=command_validate)

    check = sub.add_parser("check")
    check.set_defaults(func=command_check)

    doctor = sub.add_parser("doctor")
    doctor.add_argument("--agent-home", action="append", default=[])
    doctor.set_defaults(func=command_doctor)

    build = sub.add_parser("build")
    build.add_argument("--release-id")
    build.add_argument("--upstream-id", default="local-matt-skills")
    build.set_defaults(func=command_build)

    install = sub.add_parser("install")
    install.add_argument("--release")
    install.add_argument(
        "--target", choices=["auto", *AGENT_STATE_HOMES], default="auto"
    )
    install.add_argument("--agent-home")
    install.set_defaults(func=command_install)

    resolve_rules_cmd = sub.add_parser("resolve-rules")
    resolve_rules_cmd.add_argument("--repo", default=".")
    resolve_rules_cmd.add_argument("--agent", choices=sorted(EXECUTION_AGENTS), required=True)
    resolve_rules_cmd.add_argument("--path", action="append", default=[])
    resolve_rules_cmd.add_argument("--codex-fallback", action="append", default=[])
    resolve_rules_cmd.set_defaults(func=command_resolve_rules)

    inspect_rules_cmd = sub.add_parser("inspect-rules")
    inspect_rules_cmd.add_argument("--repo", default=".")
    inspect_rules_cmd.add_argument("--agent", choices=sorted(EXECUTION_AGENTS), required=True)
    inspect_rules_cmd.add_argument("--path", action="append", default=[])
    inspect_rules_cmd.add_argument("--codex-fallback", action="append", default=[])
    inspect_rules_cmd.set_defaults(func=command_inspect_rules)

    validate_ticket = sub.add_parser("validate-ticket")
    validate_ticket.add_argument("path", nargs="?")
    validate_ticket.add_argument("--repo", default=".")
    validate_ticket.add_argument("--ticket")
    validate_ticket.set_defaults(func=command_validate_ticket)

    work_overview_cmd = sub.add_parser("work-overview")
    work_overview_cmd.add_argument("--repo", default=".")
    work_overview_cmd.add_argument("--topic")
    work_overview_cmd.add_argument("--json", action="store_true")
    work_overview_cmd.set_defaults(func=command_work_overview)

    review_snapshot = sub.add_parser("review-snapshot")
    review_snapshot.add_argument("--repo", default=".")
    review_snapshot.add_argument("--base", required=True)
    review_snapshot.add_argument("--expect-content-id")
    review_snapshot.add_argument("--require-clean", action="store_true")
    review_snapshot.set_defaults(func=command_review_snapshot)

    artifact_snapshot = sub.add_parser("artifact-review-snapshot")
    artifact_snapshot.add_argument("--artifact", action="append", required=True)
    artifact_snapshot.add_argument("--kind", choices=("general", "design"), default="general")
    artifact_snapshot.set_defaults(func=command_artifact_review_snapshot)

    artifact_open = sub.add_parser("artifact-review-open")
    artifact_open.add_argument("--artifact", action="append", required=True)
    artifact_open.add_argument("--kind", choices=("general", "design"), default="general")
    artifact_open.set_defaults(func=command_artifact_review_snapshot)

    artifact_submit = sub.add_parser("artifact-review-submit")
    artifact_submit.add_argument("--artifact", action="append", required=True)
    artifact_submit.add_argument("--snapshot-dir", required=True)
    artifact_submit.add_argument("--result-file", required=True)
    artifact_submit.set_defaults(func=command_artifact_review_submit)

    artifact_verify = sub.add_parser("artifact-review-verify")
    artifact_verify.add_argument("--artifact", action="append", required=True)
    artifact_verify.add_argument("--expect-content-id", required=True)
    artifact_verify.set_defaults(func=command_artifact_review_verify)

    artifact_finalize = sub.add_parser("artifact-review-finalize")
    artifact_finalize.add_argument("--artifact", action="append", required=True)
    artifact_finalize.add_argument("--expect-content-id", required=True)
    artifact_finalize.add_argument("--snapshot-dir", required=True)
    artifact_finalize.set_defaults(func=command_artifact_review_finalize)

    deploy = sub.add_parser("deploy")
    deploy.add_argument("--release-id")
    deploy.add_argument("--upstream-id", default="local-matt-skills")
    deploy.add_argument(
        "--target", choices=["auto", *AGENT_STATE_HOMES], default="auto"
    )
    deploy.add_argument("--agent-home")
    deploy.set_defaults(func=command_deploy)

    prune_releases = sub.add_parser("prune-releases")
    prune_releases.add_argument("--agent-home", action="append", default=[])
    prune_releases.add_argument("--apply", action="store_true")
    prune_releases.set_defaults(func=command_prune_releases)

    metrics = sub.add_parser("metrics")
    metrics.add_argument("--repo", default=".")
    metrics.add_argument("--topic")
    metrics.set_defaults(func=command_metrics)
    from workflow_lib.quality_metrics import VIEWS,LAYERS,ESCAPE_SOURCES
    escaped=sub.add_parser('escape')
    escaped.add_argument('--repo',default='.')
    escaped.add_argument('--topic',required=True)
    escaped.add_argument('--batch')
    escaped.add_argument('--ticket')
    escaped.add_argument('--source',choices=ESCAPE_SOURCES,required=True)
    escaped.add_argument('--view',choices=VIEWS,required=True)
    escaped.add_argument('--expected-layer',choices=LAYERS,required=True)
    escaped.add_argument('--description',required=True)
    escaped.set_defaults(func=command_escape)
    return result


def main() -> None:
    args = None
    try:
        args = parser().parse_args()
        args.func(args)
    except SystemExit as exc:
        cause = exc.__cause__
        failed_test = isinstance(cause, CheckError) or (
            cause is not None and str(cause).startswith(('测试失败：', '测试命令无法执行：'))
        )
        if exc.code and not failed_test:
            from workflow_lib.metrics import record_command_error
            record_command_error(sys.argv[1:], args)
        raise


if __name__ == "__main__":
    main()
