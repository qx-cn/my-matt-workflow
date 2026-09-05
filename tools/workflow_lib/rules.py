"""Agent-specific project-rule discovery and path matching."""

from __future__ import annotations

import fnmatch
import json
from pathlib import Path, PurePosixPath


EXECUTION_AGENTS = {"codex", "cursor", "claude"}


class RuleError(ValueError):
    """Raised when rule resolution inputs are invalid."""


def _frontmatter(path: Path) -> dict[str, object]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        return {}
    try:
        end = lines.index("---", 1)
    except ValueError:
        return {}
    result: dict[str, object] = {}
    active_list: str | None = None
    for raw in lines[1:end]:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("- ") and active_list:
            result.setdefault(active_list, []).append(line[2:].strip("\"'"))
            continue
        if ":" not in line:
            active_list = None
            continue
        key, value = (part.strip() for part in line.split(":", 1))
        active_list = key if not value else None
        if value in {"true", "false"}:
            result[key] = value == "true"
        elif value.startswith("[") and value.endswith("]"):
            try:
                result[key] = json.loads(value.replace("'", '"'))
            except json.JSONDecodeError:
                result[key] = [value]
        elif value:
            result[key] = value.strip("\"'")
    return result


def _patterns(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    return []


def _matches(path: str, patterns: list[str]) -> bool:
    candidate = PurePosixPath(path)
    return any(candidate.match(pattern) or fnmatch.fnmatch(path, pattern) for pattern in patterns)


def _entry(repo: Path, source: Path, applies_by: str, scope: list[str], **details: object) -> dict[str, object]:
    return {
        "source": source.relative_to(repo).as_posix(),
        "applies_by": applies_by,
        "scope": scope,
        **details,
    }


def _normalize_paths(paths: list[str]) -> list[str]:
    normalized: list[str] = []
    for raw in paths:
        value = raw.replace("\\", "/").rstrip("/")
        candidate = PurePosixPath(value)
        if not value or candidate.is_absolute() or ".." in candidate.parts:
            raise RuleError(f"规则目标路径必须是仓库内相对路径：{raw!r}")
        normalized.append(candidate.as_posix())
    return normalized


def _codex_directories(root: Path, path: str) -> list[Path]:
    target = root / path
    parent = target if target.is_dir() else target.parent
    directories = [parent]
    while directories[-1] != root:
        next_parent = directories[-1].parent
        if not next_parent.is_relative_to(root):
            raise RuleError(f"规则目标路径越界：{path!r}")
        directories.append(next_parent)
    return list(reversed(directories))


def _codex_rules(
    root: Path, paths: list[str], fallback_filenames: list[str]
) -> list[dict[str, object]]:
    candidates: list[tuple[str, str]] = [
        ("AGENTS.override.md", "override"),
        ("AGENTS.md", "agents"),
    ]
    for name in fallback_filenames:
        fallback = PurePosixPath(name)
        if fallback.name != name or name in {item[0] for item in candidates}:
            raise RuleError(f"Codex fallback 必须是唯一的文件名：{name!r}")
        candidates.append((name, "fallback"))

    scopes: dict[Path, set[str]] = {}
    selected_by: dict[Path, str] = {}
    targets = paths or ["**"]
    for target in targets:
        directories = [root] if target == "**" else _codex_directories(root, target)
        for directory in directories:
            for filename, selector in candidates:
                source = directory / filename
                if source.is_file() and source.read_text(encoding="utf-8").strip():
                    scopes.setdefault(source, set()).add(target)
                    selected_by[source] = selector
                    break

    entries: list[dict[str, object]] = []
    for source in sorted(
        scopes,
        key=lambda item: (len(item.parent.relative_to(root).parts), item.as_posix()),
    ):
        directory = source.parent.relative_to(root).as_posix() or "."
        entries.append(
            _entry(
                root,
                source,
                "codex-native",
                sorted(scopes[source]),
                directory=directory,
                selected_by=selected_by[source],
                precedence_index=len(source.parent.relative_to(root).parts),
            )
        )
    return entries


def resolve_rules(
    repo: Path,
    agent: str,
    paths: list[str],
    *,
    codex_fallback_filenames: list[str] | None = None,
) -> list[dict[str, object]]:
    """Resolve shared and target-agent rules without mixing other agents' rules."""
    if agent not in EXECUTION_AGENTS:
        raise RuleError(f"未知 execution agent: {agent}")
    root = repo.resolve()
    normalized_paths = _normalize_paths(paths)
    rules: list[dict[str, object]] = []
    for relative in ("CONTRIBUTING.md", "CODING_STANDARDS.md"):
        source = root / relative
        if source.is_file():
            rules.append(_entry(root, source, "shared-standard", ["**"]))
    if agent == "codex":
        rules.extend(
            _codex_rules(root, normalized_paths, codex_fallback_filenames or [])
        )
        return rules
    agents = root / "AGENTS.md"
    if agents.is_file():
        rules.insert(0, _entry(root, agents, "shared", ["**"]))
    if agent == "cursor":
        legacy = root / ".cursorrules"
        if legacy.is_file():
            rules.append(_entry(root, legacy, "legacy-always", ["**"]))
        rule_dir = root / ".cursor" / "rules"
        for source in sorted(rule_dir.rglob("*.mdc")) if rule_dir.is_dir() else []:
            meta = _frontmatter(source)
            if meta.get("alwaysApply") is True:
                rules.append(_entry(root, source, "always", ["**"]))
            elif patterns := _patterns(meta.get("globs")):
                if not normalized_paths or any(_matches(path, patterns) for path in normalized_paths):
                    rules.append(_entry(root, source, "glob", patterns))
            elif isinstance(meta.get("description"), str):
                rules.append(_entry(root, source, "relevance-judgment", []))
        return rules
    for relative in ("CLAUDE.md", ".claude/CLAUDE.md"):
        source = root / relative
        if source.is_file():
            rules.append(_entry(root, source, "always", ["**"]))
    rule_dir = root / ".claude" / "rules"
    for source in sorted(rule_dir.rglob("*.md")) if rule_dir.is_dir() else []:
        patterns = _patterns(_frontmatter(source).get("paths"))
        if not patterns or not normalized_paths or any(_matches(path, patterns) for path in normalized_paths):
            rules.append(_entry(root, source, "paths" if patterns else "always", patterns or ["**"]))
    return rules
