"""Skill validation and immutable release building."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path

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


class ReleaseError(RuntimeError):
    """Raised when source Skills cannot produce a valid release."""


LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+\.md(?:#[^)]+)?)\)")
MARKDOWN_LINK_PATTERN = re.compile(
    r"(?P<prefix>!?\[[^\]]*\]\()(?P<target><[^>]+>|[^)\s]+)(?P<suffix>\))"
)


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
                source = skills_dir / dependency
                for path in source.rglob("*"):
                    if not path.is_file():
                        continue
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
        for resource_name, resource in resources.resources.items():
            if resource.consumers != "*":
                unknown = set(resource.consumers) - skill_names
                if unknown:
                    raise ReleaseError(
                        f"{resource_name}: 未知共享资源 consumer："
                        f"{', '.join(sorted(unknown))}"
                    )
            consumers = (
                skill_names
                if resource.consumers == "*"
                else set(resource.consumers)
            )
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
    for skill_dir in skill_dirs:
        skill_root = skill_dir.resolve()
        if not skill_root.is_relative_to(skills_root):
            raise ReleaseError(f"{skill_dir.name}: Skill 目录越界")
        for path in sorted(skill_dir.rglob("*")):
            resolved = path.resolve()
            if (
                not resolved.is_relative_to(skill_root)
                or not resolved.is_relative_to(skills_root)
            ):
                raise ReleaseError(
                    f"{skill_dir.name}: 文件越界："
                    f"{path.relative_to(skill_dir)}"
                )
    composition, resources = _optional_manifests(
        repo_root,
        composition_manifest_path,
        resources_manifest_path,
    )
    generated_targets = _declared_generated_targets(
        skills_dir, repo_root, composition, resources
    )
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
        for markdown in sorted(skill_dir.rglob("*.md")):
            for reference in LINK_PATTERN.findall(
                _prose_markdown(markdown.read_text())
            ):
                target = reference.split("#", 1)[0]
                if "://" in target:
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
                    source = markdown.relative_to(skill_dir)
                    raise ReleaseError(
                        f"{name}: {source} 引用不存在：{reference}"
                    )
    return skill_dirs


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_staged_references(staged_skills_dir: Path) -> None:
    for skill_dir in sorted(
        path for path in staged_skills_dir.iterdir() if path.is_dir()
    ):
        for markdown in sorted(skill_dir.rglob("*.md")):
            for reference in LINK_PATTERN.findall(
                _prose_markdown(markdown.read_text())
            ):
                target = reference.split("#", 1)[0]
                if "://" in target:
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
) -> dict[str, object]:
    return {
        "upstream_id": upstream_id,
        "skills": {
            skill_dir.name: {
                str(path.relative_to(skill_dir)): _digest(path)
                for path in sorted(skill_dir.rglob("*"))
                if path.is_file()
            }
            for skill_dir in sorted(staged_skills_dir.iterdir())
            if skill_dir.is_dir()
        },
        "runtime": {
            str(path.relative_to(staged_runtime_dir)): _digest(path)
            for path in sorted(staged_runtime_dir.rglob("*"))
            if path.is_file()
        },
        "composed": composed,
        "shared_resources": shared_resources,
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
        shutil.copytree(skill_dir, staged_skills / skill_dir.name)

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
    if resources is not None:
        for skill_dir in skill_dirs:
            written = bundle_resources_for_skill(
                resources,
                repo_root,
                skill_dir.name,
                staged_skills / skill_dir.name,
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
    return all(manifest.get(key) == value for key, value in expected.items())


def build_release(
    skills_dir: Path,
    releases_dir: Path,
    *,
    release_id: str,
    upstream_id: str,
    repo_root: Path | None = None,
    composition_manifest_path: Path | None = None,
    resources_manifest_path: Path | None = None,
) -> Path:
    """Validate Skills and build a new immutable release directory."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", release_id):
        raise ReleaseError(f"release_id 非法：{release_id}")
    root = (repo_root or skills_dir.parent).resolve()
    # Keep direct library callers behind the same source/evidence preflight as
    # the CLI, while allowing deliberately minimal unit fixtures.
    from .validator import preflight_build

    preflight_build(root, skills_dir)
    release = releases_dir / release_id
    if release.exists():
        raise ReleaseError(f"release 已存在：{release_id}")
    staged = releases_dir / f".{release_id}.staging"
    if staged.exists():
        shutil.rmtree(staged)
    try:
        source = _stage_release_tree(
            skills_dir,
            root,
            staged,
            upstream_id=upstream_id,
            composition_manifest_path=composition_manifest_path,
            resources_manifest_path=resources_manifest_path,
        )
        manifest = {"release_id": release_id, **source}
        (staged / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
        )
        staged.rename(release)
    except Exception:
        if staged.exists():
            shutil.rmtree(staged)
        raise
    return release
