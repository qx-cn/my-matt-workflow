#!/usr/bin/env python3
"""CLI for building, installing, and checking My Matt Workflow."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from workflow_lib.installer import install_release
from workflow_lib.check import CheckError, run_check
from workflow_lib.evals import EvalError, run_scenario, validate_evals, validate_scenario_evidence
from workflow_lib.profile import (
    apply_personal_ignores,
    get_policy_preset,
    merge_profile,
    parse_profile,
    preset_cli_choices,
    render_profile,
)
from workflow_lib.release import build_release, release_matches_source
from workflow_lib.smoke_registry import (
    SmokeRegistryError,
    load_smoke_registry,
    resolve_smoke_scenarios,
)
from workflow_lib.validator import ValidationError, validate_repository
from workflow_lib.rules import EXECUTION_AGENTS, RuleError, resolve_rules
from workflow_lib.tickets import TicketError, validate_ready_ticket


ROOT = Path(__file__).resolve().parents[1]
AGENT_STATE_HOMES = {
    "codex": Path(
        os.environ.get("CODEX_HOME", Path.home() / ".codex")
    ).expanduser(),
    "cursor": Path.home() / ".cursor",
    "claude": Path.home() / ".claude",
}


def _agent_skills_home(agent: str) -> Path:
    if agent == "codex":
        return Path.home() / ".agents" / "skills"
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
    candidates = [
        "AGENTS.override.md",
        "AGENTS.md",
        "CONTRIBUTING.md",
        "CODING_STANDARDS.md",
    ]
    discovered = [path for path in candidates if (repo / path).is_file()]
    if agent == "codex":
        rule_dir = repo / ".agent" / "rules"
        pattern = "*"
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


def _installed_agent(agent_home: str | None) -> str | None:
    if not agent_home:
        return None
    state_path = Path(agent_home).expanduser() / "my-matt-workflow" / "install-state.json"
    if not state_path.is_file():
        return None
    try:
        value = json.loads(state_path.read_text()).get("installed_agent")
    except json.JSONDecodeError:
        return None
    return value if value in EXECUTION_AGENTS else None


def command_setup(args: argparse.Namespace) -> None:
    repo = Path(args.repo).resolve()
    profile_path = repo / ".agent" / "matt-workflow.md"
    has_existing_profile = profile_path.exists()
    existing: dict = {}
    notes = "# 项目工作流说明\n\n仓库规则始终优先。"
    if has_existing_profile:
        existing, notes = parse_profile(profile_path.read_text())
        if args.apply and not args.refresh:
            raise SystemExit("配置已存在；请使用 --refresh 明确刷新")

    defaults = {
        "schema_version": 1,
        "task_backend": "local",
        "default_base_branch": _default_branch(repo),
        "branch_policy": "confirm",
        "commit_policy": "confirm",
        "external_write_policy": "confirm",
        "docs_writeback": "confirm",
        "humanizer_policy": "deny",
        "composition_policy": "manual",
        "work_scope_policy": "single-ticket",
        "decision_policy": "ask",
        "default_execution_agent": _installed_agent(args.agent_home) or "auto",
        "test_commands": [],
        "standards_sources": [],
        "domain_sources": [],
    }
    overrides = {
            "task_backend": args.task_backend,
            "default_base_branch": args.base_branch,
            "branch_policy": args.branch_policy,
            "commit_policy": args.commit_policy,
            "external_write_policy": args.external_write_policy,
            "docs_writeback": args.docs_writeback,
            "humanizer_policy": getattr(args, "humanizer_policy", None),
            "composition_policy": args.composition_policy,
            "work_scope_policy": args.work_scope_policy,
            "decision_policy": args.decision_policy,
            "default_execution_agent": args.execution_agent,
            "test_commands": args.test_command,
            "standards_sources": args.standards_source,
            "domain_sources": args.domain_source,
    }
    preset = get_policy_preset(args.preset) if args.preset else {}
    explicit = {key: value for key, value in overrides.items() if value is not None}
    config = merge_profile(defaults | existing, preset | explicit)
    effective_agent = config["default_execution_agent"]
    print(
        json.dumps(
            {
                "default_execution_agent": effective_agent,
                "detected_standards_sources": _discover_standards_sources(
                    repo, effective_agent
                ),
            },
            ensure_ascii=False,
        )
    )
    rendered = render_profile(config, notes)
    print(rendered)
    if not args.apply:
        return
    agent_dir = repo / ".agent"
    agent_dir.mkdir(exist_ok=True)
    (agent_dir / "matt-workflow.md").write_text(rendered)
    added, conflicts = apply_personal_ignores(repo)
    print(json.dumps({"added": added, "conflicts": conflicts}, ensure_ascii=False))


def command_validate(_: argparse.Namespace) -> None:
    try:
        report = validate_repository(ROOT)
    except ValidationError as exc:
        raise SystemExit(str(exc)) from exc
    print(f"VALID skills={report['skills']}")


def command_validate_evals(args: argparse.Namespace) -> None:
    """Print strict deterministic scenario validation as machine-readable JSON."""
    try:
        report = validate_evals(ROOT, allow_missing=args.allow_missing)
    except EvalError as exc:
        print(json.dumps({"status": "invalid", "error": str(exc)}, ensure_ascii=False))
        raise SystemExit(1) from exc
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


def command_smoke(args: argparse.Namespace) -> None:
    """Validate evidence for scenarios selected through the checked-in registry."""
    try:
        scenarios = resolve_smoke_scenarios(ROOT, args.skills)
        if not scenarios:
            print(
                json.dumps(
                    {
                        "status": "valid",
                        "skills": [],
                        "registered_skills": sorted(load_smoke_registry(ROOT)),
                        "scenarios": [],
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
            return
        for scenario in scenarios:
            validate_scenario_evidence(ROOT, scenario)
            run_scenario(ROOT, scenario)
    except (EvalError, SmokeRegistryError) as exc:
        print(json.dumps({"status": "invalid", "error": str(exc)}, ensure_ascii=False))
        raise SystemExit(1) from exc
    print(
        json.dumps(
            {
                "status": "valid",
                "skills": sorted(set(args.skills)),
                "scenarios": [scenario.identifier for scenario in scenarios],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


def _run_all_up_gate(*, check_current_release: bool) -> dict[str, object]:
    """Run the authoritative source gate and render failures consistently."""
    try:
        return run_check(ROOT, check_current_release=check_current_release)
    except CheckError as exc:
        print(json.dumps({"status": "invalid", "error": str(exc)}, ensure_ascii=False))
        raise SystemExit(1) from exc


def command_check(_: argparse.Namespace) -> None:
    """Run the one local all-up gate without depending on Git."""
    report = _run_all_up_gate(check_current_release=True)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


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
    release_id = args.release_id or datetime.now().strftime("%Y%m%d-%H%M%S")
    release = build_release(
        ROOT / "skills",
        ROOT / "releases",
        release_id=release_id,
        upstream_id=args.upstream_id,
        repo_root=ROOT,
    )
    _write_current_release(ROOT / "current.json", release_id)
    print(release)


def _current_release() -> Path:
    current = json.loads((ROOT / "current.json").read_text())
    return _release_path(current["release_id"])


def _release_path(release_id: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", release_id):
        raise SystemExit(f"非法 release ID：{release_id}")
    return ROOT / "releases" / release_id


def command_install(args: argparse.Namespace) -> None:
    release = _release_path(args.release) if args.release else _current_release()
    state_home, skills_home, target = _resolve_agent_layout(args)
    install_release(
        release,
        state_home,
        target=target,
        skills_home=skills_home,
    )
    print(f"INSTALLED {release.name}")


def command_resolve_rules(args: argparse.Namespace) -> None:
    try:
        rules = resolve_rules(Path(args.repo), args.agent, args.path)
    except RuleError as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps({"agent": args.agent, "rules": rules}, ensure_ascii=False, indent=2))


def command_validate_ticket(args: argparse.Namespace) -> None:
    try:
        report = validate_ready_ticket(Path(args.path))
    except TicketError as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(report, ensure_ascii=False))


def command_deploy(args: argparse.Namespace) -> None:
    """Install the current content, creating a release only when it changed."""
    command_validate(args)
    current = _current_release() if (ROOT / "current.json").exists() else None
    if args.release_id or current is None or not release_matches_source(
        current,
        ROOT / "skills",
        upstream_id=args.upstream_id,
        repo_root=ROOT,
    ):
        command_build(
            argparse.Namespace(
                release_id=args.release_id,
                upstream_id=args.upstream_id,
            )
        )
    else:
        print(f"REUSED {current}")
    command_install(argparse.Namespace(release=None, target=args.target, agent_home=args.agent_home))


def _release_ids_referenced_by(agent_homes: set[Path]) -> set[str]:
    referenced = {_current_release().name}
    for agent_home in agent_homes:
        state_path = agent_home / "my-matt-workflow" / "install-state.json"
        if not state_path.exists():
            continue
        try:
            state = json.loads(state_path.read_text())
        except json.JSONDecodeError as exc:
            raise SystemExit(f"拒绝清理：安装状态无法读取：{state_path}") from exc
        release_id = state.get("release_id")
        if not isinstance(release_id, str) or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", release_id
        ):
            raise SystemExit(f"拒绝清理：安装状态 release_id 无效：{state_path}")
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
            shutil.rmtree(path)
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


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    sub = result.add_subparsers(dest="command", required=True)

    setup = sub.add_parser("setup")
    setup.add_argument("--repo", default=".")
    setup.add_argument(
        "--preset",
        choices=preset_cli_choices(),
        metavar="PRESET",
        help=(
            "策略预设："
            "strict-control|light-control|review|semi-auto|full-auto"
            "（兼容别名 supervised|unattended）"
        ),
    )
    setup.add_argument(
        "--task-backend",
        choices=["local", "external", "project-docs", "none"],
    )
    setup.add_argument("--base-branch")
    setup.add_argument("--branch-policy", choices=["confirm", "allow", "deny"])
    setup.add_argument("--commit-policy", choices=["confirm", "allow", "deny"])
    setup.add_argument("--external-write-policy", choices=["confirm", "allow", "deny"])
    setup.add_argument("--docs-writeback", choices=["confirm", "allow", "deny"])
    setup.add_argument("--humanizer-policy", choices=["confirm", "allow", "deny"])
    setup.add_argument("--composition-policy", choices=["manual", "automatic"])
    setup.add_argument(
        "--work-scope-policy",
        choices=["single-ticket", "ready-frontier", "approved-plan"],
    )
    setup.add_argument("--decision-policy", choices=["ask", "autonomous", "halt"])
    setup.add_argument("--execution-agent", choices=["auto", *sorted(EXECUTION_AGENTS)])
    setup.add_argument("--agent-home")
    setup.add_argument("--test-command", action="append")
    setup.add_argument("--standards-source", action="append")
    setup.add_argument("--domain-source", action="append")
    setup.add_argument("--apply", action="store_true")
    setup.add_argument("--refresh", action="store_true")
    setup.set_defaults(func=command_setup)

    validate = sub.add_parser("validate")
    validate.set_defaults(func=command_validate)

    validate_evals = sub.add_parser("validate-evals")
    validate_evals.add_argument("--allow-missing", action="store_true")
    validate_evals.set_defaults(func=command_validate_evals)

    smoke = sub.add_parser("smoke")
    smoke.add_argument("--skills", nargs="*", default=[])
    smoke.set_defaults(func=command_smoke)

    check = sub.add_parser("check")
    check.set_defaults(func=command_check)

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
    resolve_rules_cmd.set_defaults(func=command_resolve_rules)

    validate_ticket = sub.add_parser("validate-ticket")
    validate_ticket.add_argument("path")
    validate_ticket.set_defaults(func=command_validate_ticket)

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

    return result


def main() -> None:
    args = parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
