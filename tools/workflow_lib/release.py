"""Skill validation and immutable release building."""

from __future__ import annotations

import json
import hashlib
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Callable

from .composition import (
    CompositionManifest,
    compose_dependency_references,
    load_composition_manifest,
    resolve_transitive_closure,
    validate_composition_manifest,
)
from .resources import (
    SharedResourceManifest,
    bundle_resources_for_skill,
    load_resource_manifest,
)
from .fs_safety import (
    FilesystemSafetyError,
    RELEASES_MUTATION_LOCK,
    exclusive_lock,
    quarantine_and_remove,
    refresh_owned_directory,
    register_owned_directory,
    release_ownership,
)
from .projection import (
    TARGETS,
    directory_inventory,
    project_skill_directory,
    skills_inventory,
)
from .source_walker import (
    SourceWalkError,
    ignored_source,
    markdown_link_targets,
    walk_skill_sources,
)


class ReleaseError(RuntimeError):
    """Raised when source Skills cannot produce a valid release."""


class SourceSnapshotChanged(ReleaseError):
    """Raised when repository inputs change while a build snapshot is copied."""


LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+\.md(?:#[^)]+)?)\)")
MARKDOWN_LINK_PATTERN = re.compile(
    r"(?P<prefix>!?\[[^\]]*\]\()(?P<target><[^>]+>|[^)\s]+)(?P<suffix>\))"
)
_SNAPSHOT_IGNORED_ROOTS = {
    ".agent", ".git", ".worktrees", "releases", "current.json"
}


def _snapshot_inventory(root: Path) -> dict[str, str]:
    """Hash build-relevant repository bytes without following symlinks."""
    inventory: dict[str, str] = {}
    try:
        for path in sorted(root.rglob("*")):
            relative = path.relative_to(root)
            if not relative.parts or relative.parts[0] in _SNAPSHOT_IGNORED_ROOTS:
                continue
            if ignored_source(relative):
                continue
            key = relative.as_posix()
            if path.is_symlink():
                inventory[key] = "link:" + os.readlink(path)
            elif path.is_file():
                inventory[key] = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise SourceSnapshotChanged("build source 在快照期间发生变化") from exc
    return inventory


def _copy_stable_source_snapshot(root: Path, destination: Path) -> dict[str, str]:
    """Copy one byte-exact source view and reject mixed concurrent states."""
    before = _snapshot_inventory(root)
    destination.mkdir(parents=True)
    try:
        for relative_text in before:
            relative = Path(relative_text)
            source = root / relative
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if source.is_symlink():
                target.symlink_to(os.readlink(source))
            else:
                shutil.copy2(source, target)
    except OSError as exc:
        raise SourceSnapshotChanged("build source 在复制期间发生变化") from exc
    after = _snapshot_inventory(root)
    copied = _snapshot_inventory(destination)
    if before != after or copied != after:
        raise SourceSnapshotChanged("build source 在快照期间发生变化")
    return copied
def _copy_source_tree(source: Path, destination: Path) -> None:
    """Copy exactly the reachability-closed source inventory."""
    source = source.resolve()
    destination.mkdir(parents=True)
    for path in walk_skill_sources(source):
        relative = path.relative_to(source)
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def _prose_markdown(text: str) -> str:
    """Remove fenced examples before validating executable references."""
    prose: list[str] = []
    fence: str | None = None
    for line in text.splitlines():
        stripped = line.lstrip()
        marker = (
            "```"
            if stripped.startswith("```")
            else "~~~"
            if stripped.startswith("~~~")
            else None
        )
        if marker is not None:
            if fence is None:
                fence = marker
            elif fence == marker:
                fence = None
            continue
        if fence is None:
            prose.append(line)
    return "\n".join(prose)


def _metadata(skill_file: Path) -> dict[str, str]:
    lines = skill_file.read_text().splitlines()
    if len(lines) < 4 or lines[0] != "---":
        raise ReleaseError(f"{skill_file}: 缺少 Frontmatter")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ReleaseError(f"{skill_file}: Frontmatter 未结束") from exc
    metadata: dict[str, str] = {}
    for line in lines[1:end]:
        if ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip()
    return metadata


def _optional_manifests(
    repo_root: Path,
    composition_manifest_path: Path | None = None,
    resources_manifest_path: Path | None = None,
) -> tuple[CompositionManifest | None, SharedResourceManifest | None]:
    composition_path = composition_manifest_path or (
        repo_root / "composition" / "manifest.json"
    )
    resources_path = resources_manifest_path or (
        repo_root / "resources" / "manifest.json"
    )
    composition = (
        load_composition_manifest(composition_path)
        if composition_path.is_file()
        else None
    )
    resources = (
        load_resource_manifest(resources_path)
        if resources_path.is_file()
        else None
    )
    return composition, resources


def _declared_generated_targets(
    skills_dir: Path,
    repo_root: Path,
    composition: CompositionManifest | None,
    resources: SharedResourceManifest | None,
) -> dict[str, set[str]]:
    skill_names = {
        path.name for path in skills_dir.iterdir() if path.is_dir()
    }
    targets = {skill: set() for skill in skill_names}
    if composition is not None:
        validate_composition_manifest(composition, skills_dir)
        declared_dependencies = {
            caller: resolve_transitive_closure(composition, caller)
            for caller in composition.callers
        }
        for caller, dependencies in declared_dependencies.items():
            for dependency in sorted(set(dependencies)):
                source = (skills_dir / dependency).resolve()
                for path in walk_skill_sources(source):
                    relative = path.relative_to(source)
                    if relative == Path("agents/openai.yaml"):
                        continue
                    if relative.name == "SKILL.md":
                        relative = relative.with_name("COMPOSED.md")
                    targets[caller].add(
                        str(
                            Path("references/composed")
                            / dependency
                            / relative
                        )
                    )
    if resources is not None:
        _, effective_consumers = resource_consumer_maps(
            resources, skill_names, composition, repo_root
        )
        for resource_name, resource in resources.resources.items():
            if resource.consumers != "*":
                unknown = set(resource.consumers) - skill_names
                if unknown:
                    raise ReleaseError(
                        f"{resource_name}: 未知共享资源 consumer："
                        f"{', '.join(sorted(unknown))}"
                    )
            consumers = effective_consumers[resource_name]
            source = (repo_root / resource.source).resolve()
            if not source.is_relative_to(repo_root.resolve()):
                raise ReleaseError(
                    f"{resource_name}: 共享资源源路径越界："
                    f"{resource.source}"
                )
            if resource.source_is_dir:
                if not source.is_dir():
                    raise ReleaseError(
                        f"{resource_name}: 共享资源目录不存在：{resource.source}"
                    )
                relative_files = [
                    path.relative_to(source)
                    for path in source.rglob("*")
                    if path.is_file()
                ]
                for consumer in consumers:
                    targets[consumer].update(
                        str(Path(resource.release_path) / relative)
                        for relative in relative_files
                    )
            else:
                if not source.is_file():
                    raise ReleaseError(
                        f"{resource_name}: 共享资源文件不存在：{resource.source}"
                    )
                for consumer in consumers:
                    targets[consumer].add(resource.release_path)
    return targets


def resource_consumer_maps(
    resources: SharedResourceManifest,
    skill_names: set[str],
    composition: CompositionManifest | None,
    repo_root: Path,
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """Return direct consumers and all composition/resource-derived consumers."""
    direct: dict[str, set[str]] = {}
    for name, resource in resources.resources.items():
        consumers = (
            set(skill_names)
            if resource.consumers == "*"
            else set(resource.consumers)
        )
        unknown = consumers - skill_names
        if unknown:
            raise ReleaseError(
                f"{name}: 未知共享资源 consumer：{', '.join(sorted(unknown))}"
            )
        direct[name] = consumers
    effective = {name: set(consumers) for name, consumers in direct.items()}
    if composition is not None:
        for caller in composition.callers:
            dependencies = set(resolve_transitive_closure(composition, caller))
            for name, consumers in direct.items():
                if dependencies & consumers:
                    effective[name].add(caller)
    source_root = repo_root.resolve()
    owners: list[tuple[str, Path, bool]] = []
    for name, resource in resources.resources.items():
        raw_source = source_root / resource.source
        resolved_source = raw_source.resolve()
        relative_parts = Path(resource.source).parts
        ancestors = [
            source_root.joinpath(*relative_parts[:index])
            for index in range(1, len(relative_parts) + 1)
        ]
        if (
            not resolved_source.is_relative_to(source_root)
            or any(path.is_symlink() for path in ancestors)
            or (
                resource.source_is_dir
                and raw_source.is_dir()
                and any(path.is_symlink() for path in raw_source.rglob("*"))
            )
        ):
            raise ReleaseError(f"{name}: 共享资源 source 含 symlink 或越界")
        owners.append((name, resolved_source, resource.source_is_dir))
    resource_dependencies: dict[str, set[str]] = {
        name: set() for name in resources.resources
    }
    for name, resource in resources.resources.items():
        source = (source_root / resource.source).resolve()
        markdown_files = (
            sorted(source.rglob("*.md"))
            if resource.source_is_dir and source.is_dir()
            else [source]
            if source.is_file() and source.suffix.lower() == ".md"
            else []
        )
        for markdown in markdown_files:
            for reference in markdown_link_targets(
                _prose_markdown(markdown.read_text())
            ):
                target = reference.split("#", 1)[0]
                if not target or "://" in target:
                    continue
                destination = (markdown.parent / target).resolve()
                for owner_name, owner_source, owner_is_dir in owners:
                    if owner_name == name:
                        continue
                    if destination == owner_source or (
                        owner_is_dir and destination.is_relative_to(owner_source)
                    ):
                        resource_dependencies[name].add(owner_name)
                        break
    changed = True
    while changed:
        changed = False
        for name, dependencies in resource_dependencies.items():
            for dependency in dependencies:
                inherited = effective[name] - effective[dependency]
                if inherited:
                    effective[dependency].update(inherited)
                    changed = True
    return direct, effective


def _validate_direct_resource_consumers(
    resources: SharedResourceManifest,
    source_inventories: dict[Path, list[Path]],
) -> None:
    """Keep the source manifest factual; inheritance belongs to composition."""
    skill_references: dict[str, set[str]] = {}
    for skill_dir, paths in source_inventories.items():
        references: set[str] = set()
        skill_root = skill_dir.resolve()
        for path in paths:
            if path.suffix.lower() not in {".md", ".yaml", ".yml", ".json"}:
                continue
            text = path.read_text()
            for resource in resources.resources.values():
                if resource.release_path.rstrip("/") in text:
                    references.add(resource.release_path.rstrip("/"))
            if path.suffix.lower() != ".md":
                continue
            for reference in markdown_link_targets(_prose_markdown(text)):
                target = reference.split("#", 1)[0]
                if not target or "://" in target:
                    continue
                destination = (path.parent / target).resolve()
                try:
                    references.add(str(destination.relative_to(skill_root)))
                except ValueError:
                    continue
        skill_references[skill_dir.name] = references
    for resource_name, resource in resources.resources.items():
        if resource.consumers == "*":
            continue
        marker = resource.release_path.rstrip("/")
        referenced = {
            skill
            for skill, references in skill_references.items()
            if any(
                reference == marker
                or (
                    resource.source_is_dir
                    and reference.startswith(marker + "/")
                )
                for reference in references
            )
        }
        declared = set(resource.consumers)
        if referenced != declared:
            raise ReleaseError(
                f"{resource_name}: direct consumers 与源码引用不一致；"
                f"未声明={sorted(referenced - declared)} "
                f"无直接引用={sorted(declared - referenced)}"
            )


def validate_skills(
    skills_dir: Path,
    *,
    repo_root: Path | None = None,
    composition_manifest_path: Path | None = None,
    resources_manifest_path: Path | None = None,
) -> list[Path]:
    repo_root = (repo_root or skills_dir.parent).resolve()
    skills_root = skills_dir.resolve()
    skill_dirs = sorted(path for path in skills_dir.iterdir() if path.is_dir())
    if not skill_dirs:
        raise ReleaseError("没有可构建的 Skills")
    source_inventories: dict[Path, list[Path]] = {}
    for skill_dir in skill_dirs:
        skill_root = skill_dir.resolve()
        if not skill_root.is_relative_to(skills_root):
            raise ReleaseError(f"{skill_dir.name}: Skill 目录越界")
        try:
            source_files = walk_skill_sources(skill_dir)
        except SourceWalkError as exc:
            raise ReleaseError(str(exc)) from exc
        source_inventories[skill_dir] = source_files
        if any(
            not path.resolve().is_relative_to(skill_root)
            or not path.resolve().is_relative_to(skills_root)
            for path in source_files
        ):
            raise ReleaseError(f"{skill_dir.name}: source inventory 文件越界")
    composition, resources = _optional_manifests(
        repo_root,
        composition_manifest_path,
        resources_manifest_path,
    )
    generated_targets = _declared_generated_targets(
        skills_dir, repo_root, composition, resources
    )
    if resources is not None:
        _validate_direct_resource_consumers(resources, source_inventories)
    seen: set[str] = set()
    for skill_dir in skill_dirs:
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.is_file():
            raise ReleaseError(f"{skill_dir.name}: 缺少 SKILL.md")
        text = skill_file.read_text()
        metadata = _metadata(skill_file)
        name = metadata.get("name")
        if name != skill_dir.name or not re.fullmatch(r"[a-z0-9-]{1,64}", name or ""):
            raise ReleaseError(f"{skill_dir.name}: name 无效或与目录不一致")
        if name in seen:
            raise ReleaseError(f"Skill 名称重复：{name}")
        seen.add(name)
        if not metadata.get("description"):
            raise ReleaseError(f"{name}: 缺少 description")
        if metadata.get("disable-model-invocation") != "true":
            raise ReleaseError(f"{name}: 必须设置 disable-model-invocation: true")
        if len(text.splitlines()) > 500:
            raise ReleaseError(f"{name}: SKILL.md 超过 500 行")
        skill_root = skill_dir.resolve()
        for markdown in sorted(
            path
            for path in source_inventories[skill_dir]
            if path.suffix.lower() == ".md"
        ):
            for reference in markdown_link_targets(
                _prose_markdown(markdown.read_text())
            ):
                target = reference.split("#", 1)[0]
                if not target or "://" in target:
                    continue
                destination = (markdown.parent / target).resolve()
                try:
                    relative_target = str(
                        destination.relative_to(skill_root)
                    )
                except ValueError:
                    relative_target = ""
                if (
                    not destination.is_file()
                    and relative_target not in generated_targets[name]
                ):
                    source = markdown.relative_to(skill_root)
                    raise ReleaseError(
                        f"{name}: {source} 引用不存在：{reference}"
                    )
    return skill_dirs


def _validate_staged_references(staged_skills_dir: Path) -> None:
    for skill_dir in sorted(
        path for path in staged_skills_dir.iterdir() if path.is_dir()
    ):
        for markdown in sorted(skill_dir.rglob("*.md")):
            for reference in markdown_link_targets(
                _prose_markdown(markdown.read_text())
            ):
                target = reference.split("#", 1)[0]
                if not target or "://" in target:
                    continue
                destination = markdown.parent / target
                if not destination.is_file():
                    source = markdown.relative_to(skill_dir)
                    raise ReleaseError(
                        f"{skill_dir.name}: {source} 引用不存在：{reference}"
                    )
        composed = skill_dir / "references" / "composed"
        if composed.is_dir():
            forbidden = sorted(composed.rglob("agents/openai.yaml"))
            if forbidden:
                raise ReleaseError(
                    f"{skill_dir.name}: 组合目录包含运行时元数据："
                    f"{forbidden[0].relative_to(skill_dir)}"
                )
            invocable = sorted(composed.rglob("SKILL.md"))
            if invocable:
                raise ReleaseError(
                    f"{skill_dir.name}: 组合目录包含可注册 Skill："
                    f"{invocable[0].relative_to(skill_dir)}"
                )
            named_composed = [
                path
                for path in sorted(composed.rglob("COMPOSED.md"))
                if re.search(r"(?m)^name:\s*", path.read_text())
            ]
            if named_composed:
                raise ReleaseError(
                    f"{skill_dir.name}: 组合正文包含可注册 name："
                    f"{named_composed[0].relative_to(skill_dir)}"
                )
            embedded_resources = [
                path
                for path in sorted(composed.rglob("*"))
                if path.is_dir()
                and path.name in {"policies", "shared"}
                and path.parent.name == "references"
            ]
            if embedded_resources:
                raise ReleaseError(
                    f"{skill_dir.name}: 组合目录包含重复共享资源："
                    f"{embedded_resources[0].relative_to(skill_dir)}"
                )


def _rewrite_composed_resource_links(skill_dir: Path) -> None:
    """Point composed references at the host Skill's shared resource bundle."""
    composed = skill_dir / "references" / "composed"
    if not composed.is_dir():
        return
    root = skill_dir.resolve()

    def rewrite(markdown: Path, text: str) -> str:
        def replace(match: re.Match[str]) -> str:
            target = match.group("target")
            wrapped = target.startswith("<") and target.endswith(">")
            value = target[1:-1] if wrapped else target
            if value.startswith(("http://", "https://")):
                return match.group(0)
            path, separator, fragment = value.partition("#")
            candidate = (markdown.parent / path).resolve()
            try:
                parts = candidate.relative_to(root).parts
            except ValueError:
                return match.group(0)
            resource_start = next(
                (
                    index
                    for index in range(len(parts) - 1)
                    if parts[index] == "references"
                    and parts[index + 1] in {"policies", "shared"}
                ),
                None,
            )
            if resource_start is None:
                return match.group(0)
            destination = root.joinpath(*parts[resource_start:])
            if not destination.is_file():
                raise ReleaseError(
                    f"{skill_dir.name}: {markdown.relative_to(skill_dir)} "
                    f"组合引用的共享资源未打包：{value}"
                )
            source = markdown.parent.resolve().relative_to(root)
            target_path = destination.relative_to(root)
            rewritten = os.path.relpath(target_path, source).replace(os.sep, "/")
            if separator:
                rewritten += separator + fragment
            if wrapped:
                rewritten = f"<{rewritten}>"
            return f"{match.group('prefix')}{rewritten}{match.group('suffix')}"

        return MARKDOWN_LINK_PATTERN.sub(replace, text)

    for markdown in sorted(composed.rglob("*.md")):
        markdown.write_text(rewrite(markdown, markdown.read_text()))


def _manifest_for_staged_tree(
    staged_skills_dir: Path,
    staged_runtime_dir: Path,
    *,
    upstream_id: str,
    composed: dict[str, list[str]],
    shared_resources: dict[str, list[str]],
    resource_consumers: dict[str, dict[str, list[str]]],
) -> dict[str, object]:
    portable_skills = skills_inventory(staged_skills_dir)
    runtime = directory_inventory(staged_runtime_dir)
    target_manifests: dict[str, dict[str, object]] = {}
    for target in TARGETS:
        if target == "portable":
            projected_skills = portable_skills
        else:
            with tempfile.TemporaryDirectory(
                prefix=f"my-matt-{target}-projection-"
            ) as tmp:
                projected_root = Path(tmp) / "skills"
                shutil.copytree(staged_skills_dir, projected_root)
                for skill_dir in sorted(projected_root.iterdir()):
                    if skill_dir.is_dir():
                        project_skill_directory(skill_dir, target)
                projected_skills = skills_inventory(projected_root)
        target_manifests[target] = {
            "skills": projected_skills,
            "runtime": runtime,
        }
    return {
        "upstream_id": upstream_id,
        "skills": portable_skills,
        "runtime": runtime,
        "composed": composed,
        "shared_resources": shared_resources,
        "resource_consumers": resource_consumers,
        "target_manifests": target_manifests,
    }


def _stage_release_tree(
    skills_dir: Path,
    repo_root: Path,
    staging_root: Path,
    *,
    upstream_id: str,
    composition_manifest_path: Path | None,
    resources_manifest_path: Path | None,
) -> dict[str, object]:
    skill_dirs = validate_skills(
        skills_dir,
        repo_root=repo_root,
        composition_manifest_path=composition_manifest_path,
        resources_manifest_path=resources_manifest_path,
    )
    composition, resources = _optional_manifests(
        repo_root,
        composition_manifest_path,
        resources_manifest_path,
    )
    staged_skills = staging_root / "skills"
    staged_skills.mkdir(parents=True)
    for skill_dir in skill_dirs:
        _copy_source_tree(skill_dir, staged_skills / skill_dir.name)

    staged_runtime = staging_root / "runtime"
    runtime_source = repo_root / "tools"
    if not (runtime_source / "workflow.py").is_file():
        runtime_source = Path(__file__).resolve().parents[1]
    workflow_entry = runtime_source / "workflow.py"
    runtime_library = runtime_source / "workflow_lib"
    if not workflow_entry.is_file() or not runtime_library.is_dir():
        raise ReleaseError("release runtime 缺少 tools/workflow.py 或 workflow_lib")
    (staged_runtime / "tools" / "workflow_lib").mkdir(parents=True)
    shutil.copy2(workflow_entry, staged_runtime / "tools" / "workflow.py")
    for source in sorted(runtime_library.glob("*.py")):
        shutil.copy2(source, staged_runtime / "tools" / "workflow_lib" / source.name)

    composed: dict[str, list[str]] = {}
    if composition is not None:
        materialized: set[str] = set()

        def materialize(caller: str) -> None:
            if caller in materialized:
                return
            for edge in composition.callers.get(caller, ()):
                materialize(edge.skill)
            dependencies = resolve_transitive_closure(composition, caller)
            if dependencies:
                compose_dependency_references(
                    staged_skills,
                    staged_skills / caller,
                    dependencies,
                )
                composed[caller] = dependencies
            materialized.add(caller)

        for caller in sorted(composition.callers):
            materialize(caller)

    shared_resources: dict[str, list[str]] = {}
    resource_consumers: dict[str, dict[str, list[str]]] = {
        "direct": {},
        "effective": {},
    }
    if resources is not None:
        direct, effective = resource_consumer_maps(
            resources,
            {skill_dir.name for skill_dir in skill_dirs},
            composition,
            repo_root,
        )
        resource_consumers = {
            "direct": {
                name: sorted(consumers) for name, consumers in sorted(direct.items())
            },
            "effective": {
                name: sorted(consumers) for name, consumers in sorted(effective.items())
            },
        }
        for skill_dir in skill_dirs:
            written = bundle_resources_for_skill(
                resources,
                repo_root,
                skill_dir.name,
                staged_skills / skill_dir.name,
                effective_consumers=effective,
            )
            if written:
                shared_resources[skill_dir.name] = written
    for skill_dir in skill_dirs:
        _rewrite_composed_resource_links(staged_skills / skill_dir.name)

    _validate_staged_references(staged_skills)
    return _manifest_for_staged_tree(
        staged_skills,
        staged_runtime,
        upstream_id=upstream_id,
        composed=composed,
        shared_resources=shared_resources,
        resource_consumers=resource_consumers,
    )


def stage_release_tree(
    repo_root: Path, staging_root: Path
) -> dict[str, object]:
    """Build and validate a complete generated tree at ``staging_root``."""
    return _stage_release_tree(
        repo_root / "skills",
        repo_root,
        staging_root,
        upstream_id="local-matt-skills",
        composition_manifest_path=None,
        resources_manifest_path=None,
    )


def source_manifest(
    skills_dir: Path,
    *,
    upstream_id: str,
    repo_root: Path | None = None,
    composition_manifest_path: Path | None = None,
    resources_manifest_path: Path | None = None,
) -> dict[str, object]:
    """Return the immutable manifest that would be built from source Skills."""
    root = (repo_root or skills_dir.parent).resolve()
    with tempfile.TemporaryDirectory(prefix="my-matt-release-source-") as tmp:
        return _stage_release_tree(
            skills_dir,
            root,
            Path(tmp),
            upstream_id=upstream_id,
            composition_manifest_path=composition_manifest_path,
            resources_manifest_path=resources_manifest_path,
        )


def release_matches_source(
    release: Path,
    skills_dir: Path,
    *,
    upstream_id: str,
    repo_root: Path | None = None,
    composition_manifest_path: Path | None = None,
    resources_manifest_path: Path | None = None,
) -> bool:
    """Whether a release has exactly the content that source Skills would build."""
    try:
        manifest = json.loads((release / "manifest.json").read_text())
    except (OSError, json.JSONDecodeError):
        return False
    expected = source_manifest(
        skills_dir,
        upstream_id=upstream_id,
        repo_root=repo_root,
        composition_manifest_path=composition_manifest_path,
        resources_manifest_path=resources_manifest_path,
    )
    return (
        manifest.get("release_id") == release.name
        and set(manifest) == {"release_id", *expected}
        and all(manifest.get(key) == value for key, value in expected.items())
    )


def build_release(
    skills_dir: Path,
    releases_dir: Path,
    *,
    release_id: str,
    upstream_id: str,
    repo_root: Path | None = None,
    composition_manifest_path: Path | None = None,
    resources_manifest_path: Path | None = None,
    source_gate: Callable[[Path], None] | None = None,
    current_pointer: Path | None = None,
) -> Path:
    """Validate one stable source snapshot and build an immutable release."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", release_id):
        raise ReleaseError(f"release_id 非法：{release_id}")
    root = (repo_root or skills_dir.parent).resolve()
    if current_pointer is not None and (
        current_pointer.parent.resolve() != root
        or current_pointer.name != "current.json"
        or current_pointer.is_symlink()
    ):
        raise ReleaseError("current pointer 必须是 repo_root/current.json")
    try:
        skills_relative = skills_dir.resolve().relative_to(root)
        composition_relative = (
            composition_manifest_path.resolve().relative_to(root)
            if composition_manifest_path is not None
            else None
        )
        resources_relative = (
            resources_manifest_path.resolve().relative_to(root)
            if resources_manifest_path is not None
            else None
        )
    except ValueError as exc:
        raise ReleaseError("build 输入必须位于 repo_root 内") from exc
    # Keep direct library callers behind the same source/evidence preflight as
    # the CLI, while allowing deliberately minimal unit fixtures.
    from .validator import preflight_build

    releases_dir.mkdir(parents=True, exist_ok=True)
    release = releases_dir / release_id
    staged = releases_dir / f".{release_id}.staging"
    try:
        with exclusive_lock(releases_dir, RELEASES_MUTATION_LOCK):
            if release.exists():
                raise ReleaseError(f"release 已存在：{release_id}")
            # A prior-looking directory without this process's capability is
            # retained for diagnosis; build never guesses that it is stale.
            if staged.exists():
                raise ReleaseError(f"未知或活动中的 staging 已存在：{staged.name}")
            snapshot_error: SourceSnapshotChanged | None = None
            for attempt in range(3):
                with tempfile.TemporaryDirectory(
                    prefix="my-matt-build-source-"
                ) as tmp:
                    snapshot_root = Path(tmp) / "repo"
                    try:
                        snapshot_inventory = _copy_stable_source_snapshot(
                            root, snapshot_root
                        )
                    except SourceSnapshotChanged as exc:
                        snapshot_error = exc
                        continue
                    snapshot_skills = snapshot_root / skills_relative
                    try:
                        preflight_build(snapshot_root, snapshot_skills)
                        if source_gate is not None:
                            source_gate(snapshot_root)
                    except (Exception, SystemExit):
                        try:
                            changed = _snapshot_inventory(root) != snapshot_inventory
                        except SourceSnapshotChanged:
                            changed = True
                        if changed and attempt < 2:
                            snapshot_error = SourceSnapshotChanged(
                                "build source 在门禁期间发生变化"
                            )
                            continue
                        raise
                    try:
                        changed = _snapshot_inventory(root) != snapshot_inventory
                    except SourceSnapshotChanged:
                        changed = True
                    if changed:
                        snapshot_error = SourceSnapshotChanged(
                            "build source 在门禁期间发生变化"
                        )
                        continue
                    staged.mkdir()
                    register_owned_directory(
                        releases_dir,
                        staged,
                        purpose="release-staging",
                    )
                    try:
                        source = _stage_release_tree(
                            snapshot_skills,
                            snapshot_root,
                            staged,
                            upstream_id=upstream_id,
                            composition_manifest_path=(
                                snapshot_root / composition_relative
                                if composition_relative is not None
                                else None
                            ),
                            resources_manifest_path=(
                                snapshot_root / resources_relative
                                if resources_relative is not None
                                else None
                            ),
                        )
                        manifest = {"release_id": release_id, **source}
                        (staged / "manifest.json").write_text(
                            json.dumps(manifest, ensure_ascii=False, indent=2)
                            + "\n"
                        )
                        refresh_owned_directory(
                            releases_dir,
                            staged,
                            purpose="release-staging",
                        )
                        release_ownership(
                            releases_dir,
                            staged,
                            purpose="release-staging",
                        )
                        staged.rename(release)
                        register_owned_directory(
                            releases_dir,
                            release,
                            purpose="release",
                        )
                        if current_pointer is not None:
                            temporary_pointer: Path | None = None
                            try:
                                with tempfile.NamedTemporaryFile(
                                    mode="w",
                                    encoding="utf-8",
                                    dir=current_pointer.parent,
                                    prefix=".current.json.",
                                    suffix=".tmp",
                                    delete=False,
                                ) as handle:
                                    temporary_pointer = Path(handle.name)
                                    json.dump(
                                        {"release_id": release_id},
                                        handle,
                                        ensure_ascii=False,
                                        indent=2,
                                    )
                                    handle.write("\n")
                                    handle.flush()
                                    os.fsync(handle.fileno())
                                os.replace(temporary_pointer, current_pointer)
                            finally:
                                if (
                                    temporary_pointer is not None
                                    and temporary_pointer.exists()
                                ):
                                    temporary_pointer.unlink()
                    except Exception:
                        if staged.exists():
                            refresh_owned_directory(
                                releases_dir,
                                staged,
                                purpose="release-staging",
                            )
                            quarantine_and_remove(
                                releases_dir,
                                staged,
                                purpose="release-staging",
                            )
                        raise
                    break
            else:
                raise snapshot_error or SourceSnapshotChanged(
                    "无法取得稳定的 build source 快照"
                )
    except FilesystemSafetyError as exc:
        raise ReleaseError(str(exc)) from exc
    return release
