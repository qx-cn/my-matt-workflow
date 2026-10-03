"""Agent-specific project-rule discovery and path matching."""

from __future__ import annotations

import fnmatch
import json
from pathlib import Path, PurePosixPath


EXECUTION_AGENTS = {"codex", "cursor", "claude"}
EXECUTION_AGENT_POLICIES = {"auto", *EXECUTION_AGENTS}


class RuleError(ValueError):
    """Raised when rule resolution inputs are invalid."""


def _without_yaml_comment(value: str) -> str:
    quote: str | None = None
    escaped = False
    for index, char in enumerate(value):
        if quote == '"' and char == "\\" and not escaped:
            escaped = True
            continue
        if char in {"'", '"'} and not escaped:
            if quote is None:
                quote = char
            elif quote == char:
                quote = None
        elif char == "#" and quote is None and (index == 0 or value[index - 1].isspace()):
            return value[:index].rstrip()
        escaped = False
    return value.strip()


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
    block_scalar: tuple[str, str, list[str]] | None = None
    for raw in lines[1:end]:
        if block_scalar is not None:
            if not raw.strip() or raw[0].isspace():
                block_scalar[2].append(raw.strip())
                continue
            key, style, content = block_scalar
            result[key] = (" ".join(content) if style == ">" else "\n".join(content)).strip()
            block_scalar = None
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("- ") and active_list:
            result.setdefault(active_list, []).append(
                _without_yaml_comment(line[2:]).strip("\"'")
            )
            continue
        if ":" not in line:
            active_list = None
            continue
        key, value = (part.strip() for part in line.split(":", 1))
        value = _without_yaml_comment(value)
        active_list = key if not value else None
        if value in {">", "|", ">-", "|-", ">+", "|+"}:
            block_scalar = (key, value[0], [])
        elif value in {"true", "false"}:
            result[key] = value == "true"
        elif value.startswith("[") and value.endswith("]"):
            try:
                result[key] = json.loads(value.replace("'", '"'))
            except json.JSONDecodeError:
                result[key] = [value]
        elif value:
            result[key] = value.strip("\"'")
    if block_scalar is not None:
        key, style, content = block_scalar
        result[key] = (" ".join(content) if style == ">" else "\n".join(content)).strip()
    return result


def _inspect_frontmatter(path: Path) -> tuple[dict[str, object], str, list[str]]:
    """Parse supported rule metadata without hiding malformed frontmatter."""
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        return {}, "valid", []
    try:
        end = lines.index("---", 1)
    except ValueError:
        return {}, "invalid", ["unclosed-frontmatter"]
    metadata = _frontmatter(path)
    diagnostics: list[str] = []
    seen: set[str] = set()
    list_item_allowed = False
    pending_list: str | None = None
    block_scalar = False
    for raw in lines[1:end]:
        if block_scalar:
            if not raw.strip() or raw[0].isspace():
                continue
            block_scalar = False
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("- "):
            if not list_item_allowed or not _without_yaml_comment(line[2:]):
                diagnostics.append("malformed-frontmatter-list")
            pending_list = None
            continue
        if pending_list is not None:
            diagnostics.append("empty-frontmatter-value")
            pending_list = None
        if ":" not in line:
            diagnostics.append("malformed-frontmatter-entry")
            list_item_allowed = False
            continue
        key, value = (part.strip() for part in line.split(":", 1))
        value = _without_yaml_comment(value)
        if not key or key in seen:
            diagnostics.append("duplicate-or-empty-frontmatter-key")
        seen.add(key)
        block_scalar = value in {">", "|", ">-", "|-", ">+", "|+"}
        list_item_allowed = not value
        pending_list = key if not value else None
        if value.startswith("[") and not value.endswith("]"):
            diagnostics.append("malformed-frontmatter-list")
        if value.endswith("]") and not value.startswith("["):
            diagnostics.append("malformed-frontmatter-list")
        if value.startswith("[") and value.endswith("]"):
            try:
                parsed = json.loads(value.replace("'", '"'))
            except json.JSONDecodeError:
                parsed = [part.strip().strip("\"'") for part in value[1:-1].split(",")]
                if not parsed or any(not part for part in parsed):
                    diagnostics.append("malformed-frontmatter-list")
                else:
                    metadata[key] = parsed
            else:
                if not isinstance(parsed, list):
                    diagnostics.append("malformed-frontmatter-list")
    if pending_list is not None:
        diagnostics.append("empty-frontmatter-value")
    return metadata, "invalid" if diagnostics else "valid", sorted(set(diagnostics))


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


def _target_match(paths: list[str], patterns: list[str]) -> bool | None:
    if not paths:
        return None
    return any(_matches(path, patterns) for path in paths)


def _inspected_entry(
    repo: Path,
    source: Path,
    *,
    rule_kind: str,
    activation: str,
    declared_scope: list[str],
    target_match: bool | None,
    metadata_status: str,
    selection: str,
    diagnostics: list[str] | None = None,
) -> dict[str, object]:
    return {
        "source": source.relative_to(repo).as_posix(),
        "rule_kind": rule_kind,
        "activation": activation,
        "declared_scope": declared_scope,
        "target_match": target_match,
        "metadata_status": metadata_status,
        "selection": selection,
        "diagnostics": diagnostics or [],
    }


def _metadata_rule_entry(
    root: Path,
    source: Path,
    *,
    agent: str,
    paths: list[str],
) -> dict[str, object]:
    metadata, status, diagnostics = _inspect_frontmatter(source)
    scope_field = "globs" if agent == "cursor" else "paths"
    patterns = _patterns(metadata.get(scope_field))
    if scope_field in metadata and (
        not patterns or any(not pattern.strip() for pattern in patterns)
    ):
        status = "invalid"
        diagnostics.append(f"invalid-{scope_field}")
    if agent == "cursor" and "alwaysApply" in metadata and not isinstance(
        metadata["alwaysApply"], bool
    ):
        status = "invalid"
        diagnostics.append("invalid-alwaysApply")
    if agent == "cursor" and "description" in metadata and (
        not isinstance(metadata["description"], str)
        or not metadata["description"].strip()
    ):
        status = "invalid"
        diagnostics.append("invalid-description")

    if status == "invalid":
        activation = "invalid"
        scope: list[str] = []
        match = None
        selection = "candidate"
    elif agent == "cursor" and metadata.get("alwaysApply") is True:
        activation = "always"
        scope = ["**"]
        match = True
        selection = "selected"
    elif patterns:
        activation = "glob" if agent == "cursor" else "paths"
        scope = patterns
        match = _target_match(paths, patterns)
        selection = "selected" if match is True else "candidate"
    elif agent == "cursor" and isinstance(metadata.get("description"), str):
        activation = "relevance-judgment"
        scope = []
        match = None
        selection = "candidate"
    elif agent == "cursor":
        activation = "manual"
        scope = []
        match = None
        selection = "candidate"
    else:
        activation = "always"
        scope = ["**"]
        match = True
        selection = "selected"
    return _inspected_entry(
        root,
        source,
        rule_kind=f"{agent}-rule",
        activation=activation,
        declared_scope=scope,
        target_match=match,
        metadata_status=status,
        selection=selection,
        diagnostics=sorted(set(diagnostics)),
    )


def _candidate_files(root: Path, filename: str) -> list[Path]:
    return [
        path
        for path in sorted(root.rglob(filename))
        if ".git" not in path.relative_to(root).parts and path.is_file()
    ]


def inspect_rules(
    repo: Path,
    agent: str,
    paths: list[str],
    *,
    codex_fallback_filenames: list[str] | None = None,
) -> dict[str, object]:
    """Inventory native rule candidates and preserve uncertain applicability."""
    if agent not in EXECUTION_AGENTS:
        raise RuleError(f"未知 execution agent: {agent}")
    root = repo.resolve()
    normalized_paths = _normalize_paths(paths)
    if not root.is_dir():
        raise RuleError(f"规则仓库不存在：{root}")
    entries: list[dict[str, object]] = []

    def add_plain(source: Path, rule_kind: str, activation: str = "always") -> None:
        if source.is_file():
            entries.append(
                _inspected_entry(
                    root,
                    source,
                    rule_kind=rule_kind,
                    activation=activation,
                    declared_scope=["**"],
                    target_match=True,
                    metadata_status="not-applicable",
                    selection="selected",
                    diagnostics=[] if source.read_text(encoding="utf-8").strip() else ["empty-rule-file"],
                )
            )

    for relative in ("CONTRIBUTING.md", "CODING_STANDARDS.md"):
        add_plain(root / relative, "shared-standard")

    if agent == "codex":
        fallback_names = codex_fallback_filenames or []
        candidates = ["AGENTS.override.md", "AGENTS.md", *fallback_names]
        # Reuse validation for fallback names and target paths.
        selected = {
            entry["source"]
            for entry in _codex_rules(root, normalized_paths, fallback_names)
        }
        priority = {name: index for index, name in enumerate(candidates)}
        discovered: list[Path] = []
        for name in candidates:
            discovered.extend(_candidate_files(root, name))
        for source in sorted(set(discovered), key=lambda item: item.as_posix()):
            siblings = [
                source.parent / name
                for name in candidates
                if (source.parent / name).is_file()
                and (source.parent / name).read_text(encoding="utf-8").strip()
            ]
            shadowed = any(
                priority[item.name] < priority[source.name] for item in siblings
            )
            relative = source.relative_to(root).as_posix()
            entries.append(
                _inspected_entry(
                    root,
                    source,
                    rule_kind="codex-native",
                    activation="directory-precedence",
                    declared_scope=[source.parent.relative_to(root).as_posix() or "."],
                    target_match=True if relative in selected else (False if normalized_paths else None),
                    metadata_status="not-applicable",
                    selection="selected" if relative in selected else ("shadowed" if shadowed else "candidate"),
                    diagnostics=[] if source.read_text(encoding="utf-8").strip() else ["empty-rule-file"],
                )
            )
            entries[-1]["precedence_index"] = len(source.parent.relative_to(root).parts)
    elif agent == "cursor":
        add_plain(root / "AGENTS.md", "shared-agent-convention")
        add_plain(root / ".cursorrules", "cursor-legacy")
        rule_dir = root / ".cursor" / "rules"
        for source in sorted(rule_dir.rglob("*.mdc")) if rule_dir.is_dir() else []:
            if source.is_file():
                entries.append(
                    _metadata_rule_entry(
                        root, source, agent="cursor", paths=normalized_paths
                    )
                )
    else:
        add_plain(root / "AGENTS.md", "shared-agent-convention")
        add_plain(root / "CLAUDE.md", "claude-project")
        add_plain(root / ".claude" / "CLAUDE.md", "claude-project")
        rule_dir = root / ".claude" / "rules"
        for source in sorted(rule_dir.rglob("*.md")) if rule_dir.is_dir() else []:
            if source.is_file():
                entries.append(
                    _metadata_rule_entry(
                        root, source, agent="claude", paths=normalized_paths
                    )
                )
    entries.sort(key=lambda entry: str(entry["source"]))
    return {
        "status": "ready",
        "agent": agent,
        "targets": normalized_paths,
        "rules": entries,
    }
