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


def _entry(repo: Path, source: Path, applies_by: str, scope: list[str]) -> dict[str, object]:
    return {"source": source.relative_to(repo).as_posix(), "applies_by": applies_by, "scope": scope}


def _files_under(directory: Path) -> list[Path]:
    """Return regular files below a rule directory in stable order."""
    if not directory.is_dir():
        return []
    return sorted(path for path in directory.rglob("*") if path.is_file())


def resolve_rules(repo: Path, agent: str, paths: list[str]) -> list[dict[str, object]]:
    """Resolve shared and target-agent rules without mixing other agents' rules."""
    if agent not in EXECUTION_AGENTS:
        raise RuleError(f"未知 execution agent: {agent}")
    root = repo.resolve()
    normalized_paths = [path.replace("\\", "/").lstrip("/") for path in paths]
    rules: list[dict[str, object]] = []
    for relative in ("AGENTS.override.md", "AGENTS.md", "CONTRIBUTING.md", "CODING_STANDARDS.md"):
        source = root / relative
        if source.is_file():
            rules.append(_entry(root, source, "shared", ["**"]))
    if agent == "codex":
        for source in _files_under(root / ".agent" / "rules"):
            rules.append(_entry(root, source, "always", ["**"]))
        return rules
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
