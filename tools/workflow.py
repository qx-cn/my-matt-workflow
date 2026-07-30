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

from workflow_lib.doctor import (
    compare_snapshots,
    discover_unmapped_skills,
    snapshot_mapped_tree,
    snapshot_tree,
    validate_upstream_snapshot,
)
from workflow_lib.installer import install_release
from workflow_lib.profile import (
    apply_personal_ignores,
    get_policy_preset,
    merge_profile,
    parse_profile,
    preset_cli_choices,
    render_profile,
)
from workflow_lib.recommendations import build_recommendation_report
from workflow_lib.release import build_release, release_matches_source, validate_skills
from workflow_lib.sync import build_review_bundle
from workflow_lib.work_artifacts import (
    analyze_work_artifacts,
    apply_work_artifact_migration,
)


ROOT = Path(__file__).resolve().parents[1]
OFFICIAL_UPSTREAM = "https://github.com/mattpocock/skills.git"
AGENT_HOMES = {
    "codex": Path.home() / ".codex",
    "cursor": Path.home() / ".cursor",
    "claude": Path.home() / ".claude",
}

ADAPTATION_MAP = {
    "ask-matt": ["my-ask-matt"],
    "grill-me": ["my-grill-me"],
    "grill-with-docs": ["my-grill-with-docs"],
    "to-spec": ["my-to-spec"],
    "to-tickets": ["my-to-tickets"],
    "implement": ["my-implement"],
    "tdd": ["my-tdd", "my-implement"],
    "code-review": ["my-code-review", "my-implement"],
    "diagnosing-bugs": ["my-diagnosing-bugs"],
    "handoff": ["my-handoff"],
    "prototype": ["my-prototype"],
    "wayfinder": ["my-wayfinder"],
    "triage": ["my-triage"],
    "research": ["my-research"],
    "domain-modeling": ["my-domain-modeling", "my-grill-with-docs"],
    "codebase-design": ["my-codebase-design", "my-improve-codebase-architecture"],
    "improve-codebase-architecture": ["my-improve-codebase-architecture"],
    "teach": ["my-teach"],
    "writing-great-skills": ["my-writing-great-skills"],
    "resolving-merge-conflicts": ["my-resolving-merge-conflicts"],
    "to-questionnaire": ["my-to-questionnaire"],
    "wizard": ["my-wizard"],
    "edit-article": ["my-edit-article"],
}

UPSTREAM_PATHS = {
    "ask-matt": "engineering/ask-matt",
    "grill-me": "productivity/grill-me",
    "grill-with-docs": "engineering/grill-with-docs",
    "to-spec": "engineering/to-spec",
    "to-tickets": "engineering/to-tickets",
    "implement": "engineering/implement",
    "tdd": "engineering/tdd",
    "code-review": "engineering/code-review",
    "diagnosing-bugs": "engineering/diagnosing-bugs",
    "handoff": "productivity/handoff",
    "prototype": "engineering/prototype",
    "wayfinder": "engineering/wayfinder",
    "triage": "engineering/triage",
    "research": "engineering/research",
    "domain-modeling": "engineering/domain-modeling",
    "codebase-design": "engineering/codebase-design",
    "improve-codebase-architecture": "engineering/improve-codebase-architecture",
    "teach": "productivity/teach",
    "writing-great-skills": "productivity/writing-great-skills",
    "resolving-merge-conflicts": "engineering/resolving-merge-conflicts",
    "to-questionnaire": "in-progress/to-questionnaire",
    "wizard": "in-progress/wizard",
    "edit-article": "personal/edit-article",
}


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


def command_setup(args: argparse.Namespace) -> None:
    repo = Path(args.repo).resolve()
    profile_path = repo / ".agent" / "matt-workflow.md"
    has_existing_profile = profile_path.exists()
    if args.confirm_candidate_link_repair and not args.migrate_work_artifacts:
        raise SystemExit("候选链接修复需要同时指定 --migrate-work-artifacts")
    if args.migrate_work_artifacts and not args.apply:
        raise SystemExit("迁移工作产物需要 --apply 作为明确确认")
    if args.migrate_work_artifacts and not has_existing_profile:
        raise SystemExit("仅已配置项目可以迁移工作产物")
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
            "test_commands": args.test_command,
            "standards_sources": args.standards_source,
            "domain_sources": args.domain_source,
    }
    preset = get_policy_preset(args.preset) if args.preset else {}
    explicit = {key: value for key, value in overrides.items() if value is not None}
    config = merge_profile(defaults | existing, preset | explicit)
    rendered = render_profile(config, notes)
    print(rendered)
    if has_existing_profile:
        print(json.dumps(analyze_work_artifacts(repo), ensure_ascii=False, indent=2))
    if not args.apply:
        return
    agent_dir = repo / ".agent"
    agent_dir.mkdir(exist_ok=True)
    (agent_dir / "matt-workflow.md").write_text(rendered)
    added, conflicts = apply_personal_ignores(repo)
    print(json.dumps({"added": added, "conflicts": conflicts}, ensure_ascii=False))
    if args.migrate_work_artifacts:
        apply_work_artifact_migration(
            repo,
            confirmed_candidate_link_repairs={
                tuple(candidate)
                for candidate in args.confirm_candidate_link_repair
            },
        )
        print("MIGRATED work artifacts")


def command_validate(_: argparse.Namespace) -> None:
    skills = validate_skills(ROOT / "skills", repo_root=ROOT)
    print(f"VALID skills={len(skills)}")


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
    agent_home = _resolve_agent_home(args)
    target = (
        args.target
        if args.target != "auto"
        else next(
            (
                name
                for name, known_home in AGENT_HOMES.items()
                if known_home.resolve() == agent_home.resolve()
            ),
            None,
        )
    )
    install_release(release, agent_home, target=target)
    print(f"INSTALLED {release.name}")


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
    agent_homes = set(AGENT_HOMES.values()) | {
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


def command_refresh_project(args: argparse.Namespace) -> None:
    """Apply a confirmed refresh without making the caller repeat setup flags."""
    args.refresh = True
    args.apply = True
    command_setup(args)


def command_work_layout(args: argparse.Namespace) -> None:
    """Print a read-only work-artifact migration plan."""
    print(json.dumps(analyze_work_artifacts(Path(args.repo)), ensure_ascii=False, indent=2))


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


def _upstream_skills_from_manifest(raw: dict) -> dict[str, dict[str, str]]:
    """Extract the skill→file hash map from bare or wrapped upstream manifests."""
    if not raw:
        return {}
    skills = raw.get("skills")
    if isinstance(skills, dict) and isinstance(raw.get("source"), dict):
        if not all(isinstance(files, dict) for files in skills.values()):
            raise SystemExit("upstream/manifest.json skills 必须是文件哈希映射")
        return skills
    if "source" in raw or "skills" in raw:
        raise SystemExit("upstream/manifest.json 包装格式无效：需要 source 与 skills")
    if not all(isinstance(files, dict) for files in raw.values()):
        raise SystemExit("upstream/manifest.json 必须是 Skill 文件哈希映射")
    return raw


def _load_upstream_skills_snapshot(path: Path) -> dict[str, dict[str, str]]:
    return _upstream_skills_from_manifest(_load_json(path))


def _write_upstream_manifest(
    path: Path,
    skills: dict[str, dict[str, str]],
    *,
    source: dict | None = None,
) -> None:
    """Write wrapped upstream manifest, preserving an existing source pin."""
    existing = _load_json(path)
    pinned = source
    if pinned is None and isinstance(existing.get("source"), dict):
        pinned = existing["source"]
    if pinned is None:
        pinned = {"repo": OFFICIAL_UPSTREAM, "commit": ""}
    path.write_text(
        json.dumps({"source": pinned, "skills": skills}, ensure_ascii=False, indent=2)
        + "\n"
    )


def _load_list(path: Path) -> list[str]:
    if not path.exists():
        return []
    value = json.loads(path.read_text())
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise SystemExit(f"无效的上游未映射 Skill 基线：{path}")
    return value


def _resolve_agent_home(args: argparse.Namespace) -> Path:
    if args.agent_home:
        return Path(args.agent_home).expanduser()
    if args.target != "auto":
        return AGENT_HOMES[args.target]
    candidates = [home for home in AGENT_HOMES.values() if (home / "skills").is_dir()]
    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise SystemExit("未检测到 Agent Skill 目录；请指定 --target 或 --agent-home")
    raise SystemExit("检测到多个 Agent Skill 目录；请指定 --target 或 --agent-home")


def _with_upstream(source: str, operation):
    source_path = Path(source).expanduser()
    if source_path.exists():
        return operation(source_path)
    if not re.match(r"(?:https?|git)://", source):
        raise SystemExit(f"上游路径不存在：{source}")
    with tempfile.TemporaryDirectory(prefix="my-matt-upstream-") as directory:
        checkout = Path(directory) / "skills"
        result = subprocess.run(["git", "clone", "--depth", "1", source, str(checkout)])
        if result.returncode:
            raise SystemExit("无法下载上游 Skills")
        return operation(checkout)


def _adapted_snapshot(upstream: Path) -> dict:
    return snapshot_mapped_tree(upstream, UPSTREAM_PATHS)


def command_doctor(args: argparse.Namespace) -> None:
    previous = _load_upstream_skills_snapshot(ROOT / "upstream" / "manifest.json")
    known_unmapped = set(_load_list(ROOT / "upstream" / "unmapped.json"))
    def check(upstream: Path) -> None:
        current = _adapted_snapshot(upstream)
        validate_upstream_snapshot(current, set(ADAPTATION_MAP), allow_missing=True)
        result = {"changes": build_review_bundle(compare_snapshots(previous, current), ADAPTATION_MAP)}
        unmapped = discover_unmapped_skills(upstream, UPSTREAM_PATHS)
        additions = sorted(set(unmapped) - known_unmapped)
        if additions:
            result["unmapped_upstream_skills"] = additions
        if args.recommend:
            result["recommendations"] = build_recommendation_report(unmapped)
        if result["changes"] or additions:
            print(json.dumps(result, ensure_ascii=False, indent=2))
            raise SystemExit(2)
        if args.recommend:
            print(json.dumps(result, ensure_ascii=False, indent=2))
    _with_upstream(args.upstream, check)


def command_sync(args: argparse.Namespace) -> None:
    previous = _load_upstream_skills_snapshot(ROOT / "upstream" / "manifest.json")
    def review(upstream: Path) -> dict:
        current = _adapted_snapshot(upstream)
        validate_upstream_snapshot(current, set(ADAPTATION_MAP), allow_missing=True)
        return {
            "changes": build_review_bundle(
                compare_snapshots(previous, current), ADAPTATION_MAP
            ),
            "recommendations": build_recommendation_report(
                discover_unmapped_skills(upstream, UPSTREAM_PATHS)
            ),
        }

    bundle = _with_upstream(args.upstream, review)
    review_path = ROOT / "upstream" / "review.json"
    review_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n")
    print(review_path)


def command_recommend(args: argparse.Namespace) -> None:
    """Print a review-only recommendation report for unadopted upstream Skills."""
    def inspect(upstream: Path) -> None:
        report = build_recommendation_report(
            discover_unmapped_skills(upstream, UPSTREAM_PATHS)
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))

    _with_upstream(args.upstream, inspect)


def command_snapshot(args: argparse.Namespace) -> None:
    snapshot, unmapped = _with_upstream(
        args.upstream,
        lambda upstream: (
            _adapted_snapshot(upstream),
            discover_unmapped_skills(upstream, UPSTREAM_PATHS),
        ),
    )
    validate_upstream_snapshot(
        snapshot,
        set(ADAPTATION_MAP),
        allow_missing=args.allow_deletions,
    )
    _write_upstream_manifest(ROOT / "upstream" / "manifest.json", snapshot)
    (ROOT / "upstream" / "unmapped.json").write_text(
        json.dumps(unmapped, ensure_ascii=False, indent=2) + "\n"
    )
    print(f"SNAPSHOT skills={len(snapshot)}")


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
    setup.add_argument("--test-command", action="append")
    setup.add_argument("--standards-source", action="append")
    setup.add_argument("--domain-source", action="append")
    setup.add_argument("--apply", action="store_true")
    setup.add_argument("--refresh", action="store_true")
    setup.add_argument("--migrate-work-artifacts", action="store_true")
    setup.add_argument(
        "--confirm-candidate-link-repair",
        action="append",
        nargs=2,
        metavar=("SOURCE", "LINK"),
        default=[],
    )
    setup.set_defaults(func=command_setup)

    validate = sub.add_parser("validate")
    validate.set_defaults(func=command_validate)

    build = sub.add_parser("build")
    build.add_argument("--release-id")
    build.add_argument("--upstream-id", default="local-matt-skills")
    build.set_defaults(func=command_build)

    install = sub.add_parser("install")
    install.add_argument("--release")
    install.add_argument("--target", choices=["auto", *AGENT_HOMES], default="auto")
    install.add_argument("--agent-home")
    install.set_defaults(func=command_install)

    deploy = sub.add_parser("deploy")
    deploy.add_argument("--release-id")
    deploy.add_argument("--upstream-id", default="local-matt-skills")
    deploy.add_argument("--target", choices=["auto", *AGENT_HOMES], default="auto")
    deploy.add_argument("--agent-home")
    deploy.set_defaults(func=command_deploy)

    prune_releases = sub.add_parser("prune-releases")
    prune_releases.add_argument("--agent-home", action="append", default=[])
    prune_releases.add_argument("--apply", action="store_true")
    prune_releases.set_defaults(func=command_prune_releases)

    refresh_project = sub.add_parser("refresh-project")
    refresh_project.add_argument("--repo", default=".")
    refresh_project.add_argument(
        "--preset",
        choices=preset_cli_choices(),
        metavar="PRESET",
        help=(
            "策略预设："
            "strict-control|light-control|review|semi-auto|full-auto"
            "（兼容别名 supervised|unattended）"
        ),
    )
    refresh_project.add_argument(
        "--composition-policy", choices=["manual", "automatic"]
    )
    refresh_project.add_argument(
        "--work-scope-policy",
        choices=["single-ticket", "ready-frontier", "approved-plan"],
    )
    refresh_project.add_argument("--decision-policy", choices=["ask", "autonomous", "halt"])
    refresh_project.add_argument("--task-backend", choices=["local", "external", "project-docs", "none"])
    refresh_project.add_argument("--base-branch")
    refresh_project.add_argument("--branch-policy", choices=["confirm", "allow", "deny"])
    refresh_project.add_argument("--commit-policy", choices=["confirm", "allow", "deny"])
    refresh_project.add_argument("--external-write-policy", choices=["confirm", "allow", "deny"])
    refresh_project.add_argument("--docs-writeback", choices=["confirm", "allow", "deny"])
    refresh_project.add_argument("--humanizer-policy", choices=["confirm", "allow", "deny"])
    refresh_project.add_argument("--test-command", action="append")
    refresh_project.add_argument("--standards-source", action="append")
    refresh_project.add_argument("--domain-source", action="append")
    refresh_project.add_argument("--migrate-work-artifacts", action="store_true")
    refresh_project.add_argument(
        "--confirm-candidate-link-repair",
        action="append",
        nargs=2,
        metavar=("SOURCE", "LINK"),
        default=[],
    )
    refresh_project.set_defaults(func=command_refresh_project)

    work_layout = sub.add_parser("work-layout")
    work_layout.add_argument("--repo", default=".")
    work_layout.set_defaults(func=command_work_layout)

    doctor = sub.add_parser("doctor")
    doctor.add_argument("--upstream", default=OFFICIAL_UPSTREAM)
    doctor.add_argument("--recommend", action="store_true")
    doctor.set_defaults(func=command_doctor)

    sync = sub.add_parser("sync")
    sync.add_argument("--upstream", default=OFFICIAL_UPSTREAM)
    sync.set_defaults(func=command_sync)

    recommend = sub.add_parser("recommend")
    recommend.add_argument("--upstream", default=OFFICIAL_UPSTREAM)
    recommend.set_defaults(func=command_recommend)

    snapshot = sub.add_parser("snapshot")
    snapshot.add_argument("--upstream", default=OFFICIAL_UPSTREAM)
    snapshot.add_argument("--allow-deletions", action="store_true")
    snapshot.set_defaults(func=command_snapshot)

    return result


def main() -> None:
    args = parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
