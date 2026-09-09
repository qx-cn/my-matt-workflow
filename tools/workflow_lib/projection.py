"""Deterministic host projection and file inventories for Skill trees."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path


TARGETS = ("portable", "codex", "cursor", "claude")


def project_skill_directory(skill_dir: Path, target: str) -> None:
    """Project portable metadata and call macros in one staged Skill."""
    if target not in TARGETS:
        raise ValueError(f"unknown projection target: {target}")
    if target == "codex":
        skill_file = skill_dir / "SKILL.md"
        text = skill_file.read_text(encoding="utf-8")
        projected = re.sub(
            r"(?m)^disable-model-invocation:\s*true\s*\n?", "", text, count=1
        )
        skill_file.write_text(projected, encoding="utf-8")
    elif target in {"cursor", "claude"}:
        metadata = skill_dir / "agents" / "openai.yaml"
        if metadata.is_file():
            metadata.unlink()
            try:
                metadata.parent.rmdir()
            except OSError:
                pass
    if target != "portable":
        prefix = "$" if target == "codex" else "/"
        for markdown in sorted(skill_dir.rglob("*.md")):
            text = markdown.read_text(encoding="utf-8")
            projected = re.sub(
                r"\{\{skill-call:(my-[a-z0-9-]+)\}\}",
                lambda match: f"{prefix}{match.group(1)}",
                text,
            )
            if projected != text:
                markdown.write_text(projected, encoding="utf-8")


def file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def directory_inventory(root: Path) -> dict[str, str]:
    """Return the exact regular-file inventory under one directory."""
    return {
        path.relative_to(root).as_posix(): file_digest(path)
        for path in sorted(root.rglob("*"))
        if path.is_file() and not path.is_symlink()
    }


def skills_inventory(skills_root: Path) -> dict[str, dict[str, str]]:
    """Return an exact inventory for every direct-child Skill directory."""
    return {
        skill_dir.name: directory_inventory(skill_dir)
        for skill_dir in sorted(skills_root.iterdir())
        if skill_dir.is_dir() and not skill_dir.is_symlink()
    }
