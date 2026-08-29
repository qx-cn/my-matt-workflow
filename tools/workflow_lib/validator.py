"""Repository-local static gates shared by build and check."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from .release import LINK_PATTERN, ReleaseError, _prose_markdown, validate_skills


class ValidationError(RuntimeError):
    """Raised when a source-tree gate has an actionable failure."""


EXPECTED_MANUAL_SKILLS = 30
_PLACEHOLDER = re.compile(r"(<[^>]+>|\{\{.+?\}\}|^\s*link\s*$)", re.IGNORECASE)
_SCRIPT_SUFFIXES = {".sh", ".bash"}


def _is_placeholder(markdown: Path, target: str) -> bool:
    """Recognize documented template links without accepting arbitrary misses."""
    return bool(
        _PLACEHOLDER.search(target)
        or "FORMAT" in markdown.name
        or "TEMPLATE" in markdown.name
    )


def _markdown_references(root: Path) -> list[tuple[Path, str]]:
    """Return prose-only local Markdown references from tracked source docs."""
    references: list[tuple[Path, str]] = []
    ignored_parts = {
        ".git",
        ".worktrees",
        ".superpowers",
        "releases",
        "__pycache__",
    }
    for markdown in sorted(root.rglob("*.md")):
        if ignored_parts & set(markdown.relative_to(root).parts):
            continue
        # validate_skills already resolves source Skill links against declared
        # composition/resource outputs; checking them as raw files would reject
        # intentional release-time references.
        if markdown.is_relative_to(root / "skills"):
            continue
        for reference in LINK_PATTERN.findall(_prose_markdown(markdown.read_text())):
            target = reference.split("#", 1)[0].strip()
            if (
                not target
                or "://" in target
                or target.startswith(("mailto:", "#"))
                or _is_placeholder(markdown, target)
            ):
                continue
            references.append((markdown, target))
    return references


def validate_markdown_references(root: Path) -> None:
    """Ensure every prose local Markdown reference stays in this repository."""
    source_root = root.resolve()
    for markdown, target in _markdown_references(source_root):
        destination = (markdown.parent / target).resolve()
        try:
            destination.relative_to(source_root)
        except ValueError as exc:
            raise ValidationError(
                f"{markdown.relative_to(source_root)}: Markdown reference escapes "
                f"repository: {target}"
            ) from exc
        if not destination.is_file():
            raise ValidationError(
                f"{markdown.relative_to(source_root)}: Markdown reference missing: {target}"
            )


def validate_manual_metadata(skills_dir: Path, *, expected_count: int | None) -> None:
    """Require every shipped Skill to be explicit/manual for all supported agents."""
    skill_dirs = sorted(path for path in skills_dir.iterdir() if path.is_dir())
    if expected_count is not None and len(skill_dirs) != expected_count:
        raise ValidationError(
            f"skills: expected {expected_count} manual-only skills, found {len(skill_dirs)}"
        )
    for skill_dir in skill_dirs:
        metadata = skill_dir / "agents" / "openai.yaml"
        if not metadata.is_file():
            raise ValidationError(f"{skill_dir.name}: missing agents/openai.yaml")
        if not re.search(
            r"(?m)^\s*allow_implicit_invocation:\s*false\s*$",
            metadata.read_text(),
        ):
            raise ValidationError(
                f"{skill_dir.name}: agents/openai.yaml must set "
                "allow_implicit_invocation: false"
            )


def validate_scripts(root: Path) -> None:
    """Parse every shipped shell script before it can enter a release."""
    for script in sorted(root.rglob("*")):
        if not script.is_file() or script.suffix not in _SCRIPT_SUFFIXES:
            continue
        if {".git", ".worktrees", "releases"} & set(script.relative_to(root).parts):
            continue
        result = subprocess.run(
            ["bash", "-n", str(script)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            message = result.stderr.strip() or "bash -n failed"
            raise ValidationError(
                f"{script.relative_to(root)}: shell syntax invalid: {message}"
            )


def _script_count(root: Path) -> int:
    return sum(
        1
        for path in root.rglob("*")
        if path.is_file()
        and path.suffix in _SCRIPT_SUFFIXES
        and not {".git", ".worktrees", "releases"} & set(path.relative_to(root).parts)
    )


def validate_contract_boundaries(skills_dir: Path) -> None:
    """Reject known policy/control copies that belong to shared adapters."""
    prohibited = (
        "项目策略优先",
        "## 项目策略",
        "## Policy Controls",
    )
    for skill_file in sorted(skills_dir.glob("*/SKILL.md")):
        text = skill_file.read_text()
        for marker in prohibited:
            if marker in text:
                raise ValidationError(
                    f"{skill_file.relative_to(skills_dir.parent)}: duplicate policy "
                    f"control boundary: {marker}"
                )


def validate_repository(repo_root: Path) -> dict[str, int]:
    """Run the complete source validation gate without requiring Git."""
    root = repo_root.resolve()
    skills_dir = root / "skills"
    if not skills_dir.is_dir():
        raise ValidationError("skills: directory is missing")
    try:
        skill_dirs = validate_skills(skills_dir, repo_root=root)
    except ReleaseError as exc:
        raise ValidationError(str(exc)) from exc
    canonical = (root / "composition" / "manifest.json").is_file()
    validate_manual_metadata(
        skills_dir, expected_count=EXPECTED_MANUAL_SKILLS if canonical else None
    )
    validate_markdown_references(root)
    validate_scripts(root)
    validate_contract_boundaries(skills_dir)
    return {"skills": len(skill_dirs), "scripts": _script_count(root)}


def preflight_build(repo_root: Path, skills_dir: Path) -> None:
    """Require all source gates for canonical package builds."""
    root = repo_root.resolve()
    canonical = all(
        (
            (root / "composition" / "manifest.json").is_file(),
            (root / "resources" / "manifest.json").is_file(),
        )
    )
    if not canonical:
        # Deliberately minimal library fixtures may include a focused
        # composition manifest but not the complete package manifests.
        validate_skills(skills_dir, repo_root=root)
        return

    validate_repository(root)
    from .evals import EvalError, validate_evals
    from .smoke_registry import SmokeRegistryError, validate_smoke_registry

    try:
        validate_evals(root)
    except EvalError as exc:
        raise ValidationError(str(exc)) from exc
    try:
        validate_smoke_registry(root)
    except SmokeRegistryError as exc:
        raise ValidationError(str(exc)) from exc
