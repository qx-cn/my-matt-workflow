"""Upstream Skill fingerprinting and drift detection."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Mapping


class SnapshotError(RuntimeError):
    """Raised when the upstream source is unavailable or incomplete."""


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot_tree(root: Path) -> dict[str, dict[str, str]]:
    """Snapshot a legacy flat directory of Skills."""
    snapshot: dict[str, dict[str, str]] = {}
    if not root.exists():
        return snapshot
    for skill_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        files = {
            str(path.relative_to(skill_dir)): _digest(path)
            for path in sorted(skill_dir.rglob("*"))
            if path.is_file()
        }
        snapshot[skill_dir.name] = files
    return snapshot


def snapshot_mapped_tree(
    root: Path, paths: Mapping[str, str]
) -> dict[str, dict[str, str]]:
    """Snapshot an upstream repository through an explicit logical mapping.

    Matt's repository groups Skills by category. The mapping is deliberate: a
    duplicate basename in a new category can never silently replace a Skill.
    """
    skills_root = root / "skills" if (root / "skills").is_dir() else root
    reverse: dict[str, str] = {}
    snapshot: dict[str, dict[str, str]] = {}
    for logical_name, relative in paths.items():
        if relative in reverse:
            raise SnapshotError(
                f"上游映射冲突：{logical_name} 与 {reverse[relative]} 都映射到 {relative}"
            )
        reverse[relative] = logical_name
        skill_dir = skills_root / relative
        if not skill_dir.is_dir():
            continue
        snapshot[logical_name] = {
            str(path.relative_to(skill_dir)): _digest(path)
            for path in sorted(skill_dir.rglob("*"))
            if path.is_file()
        }
    return snapshot


def discover_unmapped_skills(root: Path, mapped_paths: Mapping[str, str]) -> list[str]:
    """Return upstream Skill directories not deliberately included locally."""
    skills_root = root / "skills" if (root / "skills").is_dir() else root
    known = set(mapped_paths.values())
    discovered = {
        str(skill_file.parent.relative_to(skills_root))
        for skill_file in skills_root.rglob("SKILL.md")
    }
    return sorted(discovered - known)


def compare_snapshots(
    previous: dict[str, dict[str, str]],
    current: dict[str, dict[str, str]],
) -> dict[str, list[str]]:
    """Return only changed Skills and their changed relative files."""
    changes: dict[str, list[str]] = {}
    for skill_name in sorted(set(previous) | set(current)):
        old_files = previous.get(skill_name, {})
        new_files = current.get(skill_name, {})
        changed = [
            relative
            for relative in sorted(set(old_files) | set(new_files))
            if old_files.get(relative) != new_files.get(relative)
        ]
        if changed:
            changes[skill_name] = changed
    return changes


def validate_upstream_snapshot(
    snapshot: dict[str, dict[str, str]],
    expected_skills: set[str],
    *,
    allow_missing: bool = False,
) -> None:
    """Reject missing upstream sources before they can replace a baseline."""
    missing = sorted(expected_skills - set(snapshot))
    if not snapshot or (missing and not allow_missing):
        detail = ", ".join(missing) if missing else "快照为空"
        raise SnapshotError(f"上游快照不完整：{detail}")
