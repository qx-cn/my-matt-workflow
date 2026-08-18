"""Project profile parsing and safe personal-directory ignores."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from .rules import EXECUTION_AGENTS


class ProfileError(ValueError):
    """Raised when a project profile is unsupported or invalid."""


SUPPORTED_SCHEMA_VERSION = 1
TASK_BACKENDS = {"local", "external", "project-docs", "none"}
POLICIES = {"confirm", "allow", "deny"}
COMPOSITION_POLICIES = {"manual", "automatic"}
WORK_SCOPE_POLICIES = {"single-ticket", "ready-frontier", "approved-plan"}
DECISION_POLICIES = {"ask", "autonomous", "halt"}

PROFILE_FIELD_ORDER = (
    "schema_version",
    "task_backend",
    "default_base_branch",
    "branch_policy",
    "commit_policy",
    "external_write_policy",
    "docs_writeback",
    "humanizer_policy",
    "composition_policy",
    "work_scope_policy",
    "decision_policy",
    "default_execution_agent",
    "test_commands",
    "standards_sources",
    "domain_sources",
)

BASE_DEFAULTS: dict[str, Any] = {
    "schema_version": 1,
    "task_backend": "local",
    "default_base_branch": "main",
    "default_execution_agent": "auto",
    "test_commands": [],
    "standards_sources": [],
    "domain_sources": [],
}

POLICY_PRESETS: dict[str, dict[str, str]] = {
    "strict-control": {
        "composition_policy": "manual",
        "work_scope_policy": "single-ticket",
        "decision_policy": "ask",
        "branch_policy": "confirm",
        "commit_policy": "confirm",
        "external_write_policy": "confirm",
        "docs_writeback": "confirm",
        "humanizer_policy": "deny",
    },
    "light-control": {
        "composition_policy": "automatic",
        "work_scope_policy": "single-ticket",
        "decision_policy": "ask",
        "branch_policy": "confirm",
        "commit_policy": "confirm",
        "external_write_policy": "confirm",
        "docs_writeback": "confirm",
        "humanizer_policy": "confirm",
    },
    "review": {
        "composition_policy": "automatic",
        "work_scope_policy": "single-ticket",
        "decision_policy": "ask",
        "branch_policy": "confirm",
        "commit_policy": "allow",
        "external_write_policy": "confirm",
        "docs_writeback": "confirm",
        "humanizer_policy": "confirm",
    },
    "semi-auto": {
        "composition_policy": "automatic",
        "work_scope_policy": "ready-frontier",
        "decision_policy": "ask",
        "branch_policy": "confirm",
        "commit_policy": "allow",
        "external_write_policy": "confirm",
        "docs_writeback": "confirm",
        "humanizer_policy": "confirm",
    },
    "full-auto": {
        "composition_policy": "automatic",
        "work_scope_policy": "approved-plan",
        "decision_policy": "autonomous",
        "branch_policy": "allow",
        "commit_policy": "allow",
        "external_write_policy": "allow",
        "docs_writeback": "allow",
        "humanizer_policy": "allow",
    },
}

POLICY_PRESET_ALIASES = {
    "supervised": "strict-control",
    "unattended": "full-auto",
}

POLICY_PRESET_LABELS = {
    "strict-control": "严格控制，默认",
    "light-control": "轻轻控制",
    "review": "我做审核",
    "semi-auto": "半自动化",
    "full-auto": "全自动化",
}

POLICY_VALUE_MEANINGS: dict[str, dict[str, str]] = {
    "task_backend": {
        "local": "本地 `.agent/work/` 产物",
        "external": "外部 Tracker",
        "project-docs": "项目文档后端",
        "none": "不使用任务后端",
    },
    "branch_policy": {
        "confirm": "分支写操作前确认",
        "allow": "允许自动分支写操作",
        "deny": "禁止分支写操作",
    },
    "commit_policy": {
        "confirm": "提交前确认",
        "allow": "验证通过后可自动提交",
        "deny": "禁止提交",
    },
    "external_write_policy": {
        "confirm": "对外写（push/PR 等）前确认",
        "allow": "允许自动对外写",
        "deny": "禁止对外写",
    },
    "docs_writeback": {
        "confirm": "写回团队文档前确认",
        "allow": "允许自动写回文档",
        "deny": "禁止写回文档",
    },
    "humanizer_policy": {
        "deny": "不主动调用 my-humanizer",
        "confirm": "调用 my-humanizer 并先确认再落笔",
        "allow": "叙述段可自动 my-humanizer 落笔；契约段仍冻结",
    },
    "composition_policy": {
        "manual": "提示用户手动启动依赖 Skill",
        "automatic": "可在流程内自动加载依赖 Skill",
    },
    "work_scope_policy": {
        "single-ticket": "完成当前 Ticket 后停止",
        "ready-frontier": "可连做阻塞者已完成的 Ticket",
        "approved-plan": "可按依赖完成同一已批准计划的全部 Ticket",
    },
    "decision_policy": {
        "ask": "遇到决策时询问",
        "autonomous": "记录证据后自行判断",
        "halt": "遇决策停止",
    },
    "default_execution_agent": {
        "auto": "由安装状态或当前执行环境解析",
        "codex": "默认由 Codex 实施",
        "cursor": "默认由 Cursor 实施",
        "claude": "默认由 Claude 实施",
    },
}

# Only workflow artefacts belong in a repository. Agent configuration directories
# are often checked in by teams, so they must never be added to .gitignore here.
PERSONAL_IGNORES = (".agent/",)


def _is_empty(value: Any) -> bool:
    return value is None or value == ""


def _coalesce(config: dict[str, Any], key: str, default: Any) -> Any:
    if key not in config or _is_empty(config.get(key)):
        return default
    return config[key]


def resolve_preset_name(name: str) -> str:
    """Map preset aliases to canonical five-tier names."""
    if name in POLICY_PRESET_ALIASES:
        return POLICY_PRESET_ALIASES[name]
    if name in POLICY_PRESETS:
        return name
    raise ProfileError(
        "未知预设："
        f"{name!r}；可选：{', '.join(POLICY_PRESETS)}"
        f"；兼容别名：{', '.join(sorted(POLICY_PRESET_ALIASES))}"
    )


def get_policy_preset(name: str) -> dict[str, str]:
    """Return a copy of a preset, resolving legacy aliases."""
    return dict(POLICY_PRESETS[resolve_preset_name(name)])


def preset_cli_choices() -> list[str]:
    """CLI accepts canonical names plus legacy aliases."""
    return sorted(set(POLICY_PRESETS) | set(POLICY_PRESET_ALIASES))


def effective_profile(config: dict[str, Any]) -> dict[str, Any]:
    """Fill missing/empty keys from strict-control and base defaults."""
    strict = POLICY_PRESETS["strict-control"]
    result: dict[str, Any] = dict(BASE_DEFAULTS)
    result.update(strict)
    for key, value in config.items():
        if _is_empty(value):
            continue
        result[key] = value
    return result


def format_policy_catalog() -> str:
    """Authoritative value catalog shared by docs, render comments, and tests."""
    lines = [
        "配置取值说明（与校验同源）：",
        "",
        "日常主路径：五档预设 strict-control / light-control / review / "
        "semi-auto / full-auto。",
        "兼容别名：supervised→strict-control，unattended→full-auto。",
        "正交细项（branch/commit/external_write/docs_writeback/humanizer/"
        "composition/work_scope/decision 等）可逐项覆盖，属高级用法；"
        "ready-frontier、halt、deny 等枚举仍合法但非日常主路径。",
        "",
    ]
    defaults = effective_profile({})
    for key in PROFILE_FIELD_ORDER:
        if key in {"schema_version", "default_base_branch", "default_execution_agent", "test_commands",
                   "standards_sources", "domain_sources"}:
            lines.append(f"- {key}: 默认 {defaults[key]!r}")
            continue
        meanings = POLICY_VALUE_MEANINGS.get(key, {})
        if key == "task_backend":
            allowed = sorted(TASK_BACKENDS)
        elif key in {
            "branch_policy",
            "commit_policy",
            "external_write_policy",
            "docs_writeback",
            "humanizer_policy",
        }:
            allowed = sorted(POLICIES)
        elif key == "composition_policy":
            allowed = sorted(COMPOSITION_POLICIES)
        elif key == "work_scope_policy":
            allowed = sorted(WORK_SCOPE_POLICIES)
        elif key == "decision_policy":
            allowed = sorted(DECISION_POLICIES)
        elif key == "default_execution_agent":
            allowed = ["auto", *sorted(EXECUTION_AGENTS)]
        else:
            allowed = []
        detail = "; ".join(
            f"{value}（{meanings[value]}）" if value in meanings else value
            for value in allowed
        )
        lines.append(
            f"- {key}: 合法值 {', '.join(allowed)}；默认 {defaults[key]!r}"
            + (f"。{detail}" if detail else "")
        )
    lines.append("")
    lines.append("五档预设字段：")
    for name, label in POLICY_PRESET_LABELS.items():
        fields = ", ".join(
            f"{key}={value}" for key, value in POLICY_PRESETS[name].items()
        )
        lines.append(f"- {name}（{label}）: {fields}")
    return "\n".join(lines) + "\n"


def _parse_value(raw: str) -> Any:
    value = raw.strip()
    if value.startswith("[") and value.endswith("]"):
        try:
            parsed = json.loads(value.replace("'", '"'))
        except json.JSONDecodeError as exc:
            raise ProfileError(f"无效列表：{value}") from exc
        if not isinstance(parsed, list):
            raise ProfileError(f"预期列表：{value}")
        return parsed
    if value.isdigit():
        return int(value)
    if value in {"true", "false"}:
        return value == "true"
    return value.strip("\"'")


def _validate(config: dict[str, Any]) -> None:
    version = _coalesce(config, "schema_version", BASE_DEFAULTS["schema_version"])
    if version != SUPPORTED_SCHEMA_VERSION:
        raise ProfileError(
            f"不支持 schema_version={version!r}，当前仅支持 {SUPPORTED_SCHEMA_VERSION}"
        )
    backend = _coalesce(config, "task_backend", BASE_DEFAULTS["task_backend"])
    if backend not in TASK_BACKENDS:
        raise ProfileError(
            f"task_backend 必须是：{', '.join(sorted(TASK_BACKENDS))}"
        )
    composition = _coalesce(
        config, "composition_policy", POLICY_PRESETS["strict-control"]["composition_policy"]
    )
    if composition not in COMPOSITION_POLICIES:
        raise ProfileError(
            "composition_policy 必须是："
            f"{', '.join(sorted(COMPOSITION_POLICIES))}"
        )
    work_scope = _coalesce(
        config, "work_scope_policy", POLICY_PRESETS["strict-control"]["work_scope_policy"]
    )
    if work_scope not in WORK_SCOPE_POLICIES:
        raise ProfileError(
            "work_scope_policy 必须是："
            f"{', '.join(sorted(WORK_SCOPE_POLICIES))}"
        )
    decision = _coalesce(
        config, "decision_policy", POLICY_PRESETS["strict-control"]["decision_policy"]
    )
    if decision not in DECISION_POLICIES:
        raise ProfileError(
            "decision_policy 必须是："
            f"{', '.join(sorted(DECISION_POLICIES))}"
        )
    execution_agent = _coalesce(
        config, "default_execution_agent", BASE_DEFAULTS["default_execution_agent"]
    )
    if execution_agent != "auto" and execution_agent not in EXECUTION_AGENTS:
        raise ProfileError("default_execution_agent 必须是 auto、codex、cursor 或 claude")
    for field in (
        "branch_policy",
        "commit_policy",
        "external_write_policy",
        "docs_writeback",
        "humanizer_policy",
    ):
        if field in config and not _is_empty(config[field]) and config[field] not in POLICIES:
            raise ProfileError(f"{field} 必须是：{', '.join(sorted(POLICIES))}")


def parse_profile(text: str) -> tuple[dict[str, Any], str]:
    """Parse the supported YAML-frontmatter subset and trailing Markdown."""
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise ProfileError("配置必须以 YAML Frontmatter 开始")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ProfileError("配置缺少 Frontmatter 结束标记") from exc

    config: dict[str, Any] = {}
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            raise ProfileError(f"无效配置行：{line}")
        key, raw = line.split(":", 1)
        config[key.strip()] = _parse_value(raw)

    _validate(config)
    notes = "\n".join(lines[end + 1 :]).strip()
    return config, notes


def render_profile(config: dict[str, Any], notes: str = "") -> str:
    """Render a validated profile with every known key made explicit."""
    effective = effective_profile(config)
    _validate(effective)
    lines = [
        "---",
        "# 策略预设：",
    ]
    for name, label in POLICY_PRESET_LABELS.items():
        preset = POLICY_PRESETS[name]
        summary = (
            f"{preset['composition_policy']}/"
            f"{preset['work_scope_policy']}/"
            f"{preset['decision_policy']}，"
            f"humanizer={preset['humanizer_policy']}"
        )
        marker = "（默认）" if name == "strict-control" else ""
        lines.append(f"# {name}{marker}：{label}；{summary}。")
    lines.extend(
        [
            "# 兼容别名：supervised→strict-control，unattended→full-auto。",
            "# 可用 `workflow.py setup --preset <"
            "strict-control|light-control|review|semi-auto|full-auto"
            "> --apply` 切换。",
            "# 「继续 / 提交并继续」只在当前已生效策略下推进，不升档、"
            "不放宽 work_scope_policy。",
            "# 缺键或空值按 strict-control 生效。",
            "# 下列值是本项目当前实际生效的策略。",
        ]
    )
    for key in PROFILE_FIELD_ORDER:
        value = effective[key]
        if isinstance(value, list):
            rendered = json.dumps(value, ensure_ascii=False)
        elif isinstance(value, bool):
            rendered = str(value).lower()
        else:
            rendered = str(value)
        lines.append(f"{key}: {rendered}")
    for key, value in effective.items():
        if key in PROFILE_FIELD_ORDER:
            continue
        if isinstance(value, list):
            rendered = json.dumps(value, ensure_ascii=False)
        elif isinstance(value, bool):
            rendered = str(value).lower()
        else:
            rendered = str(value)
        lines.append(f"{key}: {rendered}")
    lines.append("---")
    if notes.strip():
        lines.extend(("", notes.strip()))
    return "\n".join(lines) + "\n"


def merge_profile(
    existing: dict[str, Any],
    overrides: dict[str, Any],
) -> dict[str, Any]:
    """Merge confirmed refresh values without erasing prior configuration."""
    merged = dict(existing)
    merged.update({key: value for key, value in overrides.items() if value is not None})
    _validate(merged)
    return merged


def _tracked_under(repo: Path, directory: str) -> bool:
    result = subprocess.run(
        ["git", "ls-files", "--", directory],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return bool(result.stdout.strip())


def is_git_repository(repo: Path) -> bool:
    """Return whether the project is backed by a Git work tree."""
    result = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


def apply_personal_ignores(repo: Path) -> tuple[list[str], list[str]]:
    """Append safe personal ignores without hiding tracked team files.

    Non-Git projects still use `.agent/` as their workflow directory, but have
    no `.gitignore` to maintain.
    """
    if not is_git_repository(repo):
        return [], []

    gitignore = repo / ".gitignore"
    existing_text = gitignore.read_text() if gitignore.exists() else ""
    existing = {line.strip() for line in existing_text.splitlines()}
    added: list[str] = []
    conflicts: list[str] = []

    for entry in PERSONAL_IGNORES:
        if entry in existing:
            continue
        if _tracked_under(repo, entry.rstrip("/")):
            conflicts.append(entry)
            continue
        added.append(entry)

    if added:
        prefix = existing_text
        if prefix and not prefix.endswith("\n"):
            prefix += "\n"
        gitignore.write_text(prefix + "".join(f"{entry}\n" for entry in added))
    elif not gitignore.exists():
        gitignore.write_text("")

    return added, conflicts
