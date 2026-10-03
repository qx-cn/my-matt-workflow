"""Repository-local static gates shared by build and check."""

from __future__ import annotations

import re
import hashlib
import json
import subprocess
from pathlib import Path

from .release import LINK_PATTERN, ReleaseError, _prose_markdown, validate_skills
from .resource_governance import (
    ResourceGovernanceError,
    validate_resource_governance,
)
from .resources import ResourceError, load_resource_manifest
from .composition import load_composition_manifest, model_invocable_skills


class ValidationError(RuntimeError):
    """Raised when a source-tree gate has an actionable failure."""


_PLACEHOLDER = re.compile(r"(<[^>]+>|\{\{.+?\}\}|^\s*link\s*$)", re.IGNORECASE)
_SCRIPT_SUFFIXES = {".sh", ".bash"}


def _is_placeholder(markdown: Path, target: str) -> bool:
    """Recognize documented template links without accepting arbitrary misses."""
    return bool(
        _PLACEHOLDER.search(target)
        or "FORMAT" in markdown.name
        or "TEMPLATE" in markdown.name
    )


def _archived_review_inputs(root: Path) -> set[Path]:
    """Recognize recorded frozen blobs, retaining normal archive link checks.

    Blob links belong to their original source context. Their archive contract
    is identity and byte integrity, not link resolution beside serialized blobs.
    Rebase only declared snapshot files after the whole Topic has moved.
    """
    frozen = set()
    for topic in (root / '.agent' / 'archive').glob('*'):
        records = [*topic.glob('implementations/*.json'), *topic.glob('batches/*.json'),
                   *topic.glob('branch-review.json')]
        for record in records:
            try:
                if record.is_symlink():
                    raise ValueError('unsafe review record')
                unit = json.loads(record.read_text())
                if not isinstance(unit, dict):
                    raise ValueError('invalid review record')
                for entry in [*unit.get('reviews', []), *unit.get('past_reviews', [])]:
                    original = Path(entry['manifest'])
                    if original.name != 'manifest.json' or not original.parent.name.endswith('-' + entry['unit_id']):
                        raise ValueError('invalid recorded review location')
                    directory = topic / 'reviews' / original.parent.name
                    manifest_path = directory / 'manifest.json'
                    if directory.resolve() != directory or manifest_path.is_symlink() or not manifest_path.is_file():
                        raise ValueError('unsafe or missing recorded manifest')
                    raw = manifest_path.read_bytes()
                    manifest = json.loads(raw)
                    for key in ('unit_id', 'content_id', 'round'):
                        if manifest[key] != entry[key]:
                            raise ValueError('recorded review identity mismatch')
                    active = unit.get('active_review', {})
                    if active.get('manifest') == str(original):
                        if hashlib.sha256(raw).hexdigest() != active['manifest_sha256']:
                            raise ValueError('recorded manifest hash mismatch')
                    rows = manifest['inputs'] + [value for change in manifest['changes']
                                                 for value in (change['base'], change['current']) if value]
                    declared = set()
                    for row in rows:
                        relative = Path(row['snapshot_path']).relative_to(original.parent)
                        if len(relative.parts) != 1 or relative.name in ('.', '..'):
                            raise ValueError('snapshot path is not a local blob')
                        if relative.suffix == '.md' and relative.name not in {
                                'rules.md', 'spec.md', 'specs.md', 'review-loop-rules.md',
                                'decided.md', 'ticket.md', 'tickets.md', 'impact-declarations.md'}:
                            raise ValueError('unknown Markdown input blob')
                        path = directory / relative
                        if path.is_symlink() or directory.resolve() != directory or not path.is_file():
                            raise ValueError('unsafe or missing snapshot blob')
                        data = path.read_bytes()
                        if hashlib.sha256(data).hexdigest() != row['sha256'] or len(data) != row['size']:
                            raise ValueError('snapshot byte integrity mismatch')
                        declared.add(path)
                    frozen.update(declared)
            except (OSError, ValueError, KeyError, TypeError) as exc:
                raise ValidationError(f'{record.relative_to(root)}: archived review integrity: {exc}') from exc
    return frozen


def _markdown_references(root: Path) -> list[tuple[Path, str]]:
    """Return prose-only local Markdown references from tracked source docs."""
    references: list[tuple[Path, str]] = []
    archived_inputs = _archived_review_inputs(root)
    ignored_parts = {
        ".git",
        ".worktrees",
        ".superpowers",
        "releases",
        "__pycache__",
    }
    for markdown in sorted(root.rglob("*.md")):
        relative = markdown.relative_to(root)
        # Active Topic history, immutable review evidence and embedded synthetic
        # repositories are runtime data excluded from the build snapshot.
        # Keep repository configuration and other .agent documents in scope.
        if markdown.is_relative_to(root / ".agent" / "work"):
            continue
        if markdown in archived_inputs:
            continue
        if ignored_parts & set(relative.parts):
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
    manifest_path = skills_dir.parent / "composition/manifest.json"
    manifest = load_composition_manifest(manifest_path) if manifest_path.is_file() else None
    invocable = model_invocable_skills(manifest)
    for skill_dir in skill_dirs:
        metadata = skill_dir / "agents" / "openai.yaml"
        if not metadata.is_file():
            raise ValidationError(f"{skill_dir.name}: missing agents/openai.yaml")
        expected = "true" if skill_dir.name in invocable else "false"
        if not re.search(
            rf"(?m)^\s*allow_implicit_invocation:\s*{expected}\s*$",
            metadata.read_text(),
        ):
            raise ValidationError(
                f"{skill_dir.name}: agents/openai.yaml must set "
                f"allow_implicit_invocation: {expected}"
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
    if canonical:
        try:
            resource_manifest = load_resource_manifest(
                root / "resources" / "manifest.json"
            )
            validate_resource_governance(
                root,
                resource_manifest,
                root / "resources" / "governance.json",
            )
        except (OSError, ResourceError, ResourceGovernanceError) as exc:
            raise ValidationError(str(exc)) from exc
    validate_manual_metadata(
        skills_dir, expected_count=None
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
