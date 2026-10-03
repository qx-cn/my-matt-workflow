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


_EPHEMERAL_NAMES = {"__pycache__", ".DS_Store"}
_EPHEMERAL_SUFFIXES = {".pyc", ".pyo"}


def _is_ephemeral(relative: Path) -> bool:
    return any(part in _EPHEMERAL_NAMES for part in relative.parts) or (
        relative.suffix in _EPHEMERAL_SUFFIXES
    )


def directory_inventory(root: Path) -> dict[str, str]:
    """Return the exact regular-file inventory under one directory.

    Bytecode caches and Finder metadata are execution by-products, never
    release content; they must not drift an inventory of a managed tree.
    """
    return {
        path.relative_to(root).as_posix(): file_digest(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
        and not path.is_symlink()
        and not _is_ephemeral(path.relative_to(root))
    }


def skills_inventory(skills_root: Path) -> dict[str, dict[str, str]]:
    """Return an exact inventory for every direct-child Skill directory."""
    return {
        skill_dir.name: directory_inventory(skill_dir)
        for skill_dir in sorted(skills_root.iterdir())
        if skill_dir.is_dir() and not skill_dir.is_symlink()
    }


def projected_skill_inventory(skill_dir: Path, target: str) -> dict[str, str]:
    """Calculate the physical projection's exact file bytes without a copy.

    Match read_text/write_text newline behavior, including Codex's unconditional
    SKILL metadata write and the conditional macro writes on other Markdown.
    """
    if target not in TARGETS:
        raise ValueError(f"unknown projection target: {target}")
    result = {}
    for path in sorted(skill_dir.rglob('*')):
        relative = path.relative_to(skill_dir)
        if path.is_symlink():
            raise ValueError(f"projection source contains symlink: {relative}")
        if not path.is_file() or _is_ephemeral(relative):
            continue
        if target in {'cursor', 'claude'} and relative == Path('agents/openai.yaml'):
            continue
        contents = path.read_bytes()
        if target != 'portable' and path.suffix == '.md':
            text = path.read_text(encoding='utf-8')
            projected = text
            rewrite = target == 'codex' and relative == Path('SKILL.md')
            if rewrite:
                projected = re.sub(r'(?m)^disable-model-invocation:\s*true\s*\n?', '', projected, count=1)
            prefix = '$' if target == 'codex' else '/'
            with_macros = re.sub(r'\{\{skill-call:(my-[a-z0-9-]+)\}\}',
                                lambda match: f'{prefix}{match.group(1)}', projected)
            if rewrite or with_macros != text:
                contents = with_macros.encode('utf-8')
        result[relative.as_posix()] = hashlib.sha256(contents).hexdigest()
    return result


def projected_skills_inventory(skills_root: Path, target: str) -> dict[str, dict[str, str]]:
    return {skill.name: projected_skill_inventory(skill, target)
            for skill in sorted(skills_root.iterdir()) if skill.is_dir() and not skill.is_symlink()}
