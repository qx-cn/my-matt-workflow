"""Reachability-based source inventory shared by validation and release build."""

from __future__ import annotations

import json
import re
from collections import deque
from pathlib import Path


class SourceWalkError(RuntimeError):
    """Raised when a Skill source inventory is unsafe or not closed."""


_IGNORED_NAMES = {"__pycache__", ".DS_Store"}
_IGNORED_SUFFIXES = {".pyc", ".pyo", ".log", ".tmp"}
_INVENTORY_FILE = ".source-inventory.json"
_MARKDOWN_LINK = re.compile(
    r"!?\[[^\]]*\]\((?P<target><[^>]+>|[^)\s]+)(?:\s+[^)]*)?\)"
)
_PATH_TOKEN = re.compile(
    r"(?<![A-Za-z0-9_.-])"
    r"(?P<target>(?:\.{1,2}/)?(?:[A-Za-z0-9_.-]+/)*"
    r"[A-Za-z0-9_.-]+\.(?:md|py|sh|html|css|js|json|ya?ml))"
)
_TEXT_SUFFIXES = {".md", ".py", ".sh", ".html", ".css", ".js", ".json", ".yaml", ".yml"}


def markdown_link_targets(text: str) -> list[str]:
    """Return normalized local-or-remote Markdown link targets."""
    return [
        match.group("target").strip("<>")
        for match in _MARKDOWN_LINK.finditer(text)
    ]


def ignored_source(path: Path) -> bool:
    return (
        any(part in _IGNORED_NAMES for part in path.parts)
        or path.suffix.lower() in _IGNORED_SUFFIXES
    )


def _declared_inventory(skill_root: Path) -> set[Path]:
    declaration = skill_root / _INVENTORY_FILE
    if not declaration.exists():
        return set()
    try:
        raw = json.loads(declaration.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SourceWalkError(f"{skill_root.name}: source inventory 无法读取") from exc
    if (
        not isinstance(raw, dict)
        or set(raw) != {"version", "files"}
        or raw.get("version") != 1
        or not isinstance(raw.get("files"), list)
        or any(not isinstance(value, str) for value in raw["files"])
        or len(set(raw["files"])) != len(raw["files"])
    ):
        raise SourceWalkError(f"{skill_root.name}: source inventory schema 无效")
    declared: set[Path] = {declaration}
    root = skill_root.resolve()
    for value in raw["files"]:
        relative = Path(value)
        if relative.is_absolute() or ".." in relative.parts or relative == Path("."):
            raise SourceWalkError(f"{skill_root.name}: source inventory 路径无效：{value}")
        candidate = skill_root / relative
        if (
            not candidate.is_file()
            or candidate.is_symlink()
            or not candidate.resolve().is_relative_to(root)
        ):
            raise SourceWalkError(f"{skill_root.name}: source inventory 文件无效：{value}")
        declared.add(candidate)
    return declared


def _references(path: Path, skill_root: Path) -> set[Path]:
    if path.suffix.lower() not in _TEXT_SUFFIXES:
        return set()
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise SourceWalkError(f"{skill_root.name}: 无法读取 source：{path.name}") from exc
    values = {
        value.split("#", 1)[0] for value in markdown_link_targets(text)
    }
    values.update(match.group("target") for match in _PATH_TOKEN.finditer(text))
    root = skill_root.resolve()
    references: set[Path] = set()
    for value in values:
        if not value or "://" in value or value.startswith(("/", "#")):
            continue
        candidates = (path.parent / value, skill_root / value)
        for candidate in candidates:
            if not candidate.is_file() or candidate.is_symlink():
                continue
            resolved = candidate.resolve()
            if not resolved.is_relative_to(root):
                raise SourceWalkError(
                    f"{skill_root.name}: source 引用越界：{value}"
                )
            references.add(candidate)
            break
    return references


def walk_skill_sources(skill_root: Path) -> list[Path]:
    """Return the closed reachable file set for one source Skill."""
    skill_root = skill_root.resolve()
    if not skill_root.is_dir() or skill_root.is_symlink():
        raise SourceWalkError(f"{skill_root.name}: Skill source 目录无效")
    actual: set[Path] = set()
    for path in sorted(skill_root.rglob("*")):
        relative = path.relative_to(skill_root)
        if path.is_symlink():
            raise SourceWalkError(
                f"{skill_root.name}: source inventory symlink 可能越界：{relative}"
            )
        if ignored_source(relative):
            continue
        if path.is_file():
            actual.add(path)

    roots = {skill_root / "SKILL.md"}
    metadata = skill_root / "agents/openai.yaml"
    if metadata.is_file():
        roots.add(metadata)
    roots.update(_declared_inventory(skill_root))
    if any(not path.is_file() for path in roots):
        raise SourceWalkError(f"{skill_root.name}: source roots 不完整")

    reachable: set[Path] = set()
    queue = deque(sorted(roots))
    while queue:
        path = queue.popleft()
        if path in reachable:
            continue
        reachable.add(path)
        for reference in sorted(_references(path, skill_root)):
            if reference not in reachable:
                queue.append(reference)

    unreferenced = sorted(
        path.relative_to(skill_root).as_posix() for path in actual - reachable
    )
    if unreferenced:
        raise SourceWalkError(
            f"{skill_root.name}: 存在未引用 source 文件：{', '.join(unreferenced)}"
        )
    return sorted(reachable)
