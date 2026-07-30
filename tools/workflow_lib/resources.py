"""Shared release resource parsing and bundling."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path


class ResourceError(RuntimeError):
    """Raised when a shared resource declaration is invalid."""


@dataclass(frozen=True)
class SharedResource:
    source: str
    source_is_dir: bool
    release_path: str
    consumers: str | tuple[str, ...]


@dataclass(frozen=True)
class SharedResourceManifest:
    version: int
    resources: dict[str, SharedResource]


def _relative_path(value: object, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ResourceError(f"{location}: 路径不能为空")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ResourceError(f"{location}: 路径必须位于仓库内：{value}")
    return value


def load_resource_manifest(path: Path) -> SharedResourceManifest:
    """Load a strict version-1 shared resource manifest."""
    try:
        raw = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ResourceError(f"资源清单无法读取：{path}") from exc
    if not isinstance(raw, dict) or set(raw) != {"version", "resources"}:
        raise ResourceError("资源清单字段必须为 version、resources")
    if raw["version"] != 1:
        raise ResourceError(f"不支持的资源清单版本：{raw['version']!r}")
    if not isinstance(raw["resources"], dict):
        raise ResourceError("resources 必须是对象")

    resources: dict[str, SharedResource] = {}
    release_paths: set[str] = set()
    for name, value in raw["resources"].items():
        if not isinstance(name, str) or not name.strip():
            raise ResourceError("资源名称不能为空")
        if not isinstance(value, dict):
            raise ResourceError(f"{name}: 资源声明必须是对象")
        source_keys = {"source", "source_dir"} & set(value)
        if len(source_keys) != 1:
            raise ResourceError(f"{name}: 必须声明且只能声明 source 或 source_dir")
        expected = {next(iter(source_keys)), "release_path", "consumers"}
        if set(value) != expected:
            raise ResourceError(f"{name}: 资源声明含未知或缺失字段")
        source_key = next(iter(source_keys))
        source = _relative_path(value[source_key], f"{name}.{source_key}")
        release_path = _relative_path(
            value["release_path"], f"{name}.release_path"
        )
        if release_path in release_paths:
            raise ResourceError(f"{name}: release_path 重复：{release_path}")
        release_paths.add(release_path)
        raw_consumers = value["consumers"]
        if raw_consumers == "*":
            consumers: str | tuple[str, ...] = "*"
        elif (
            isinstance(raw_consumers, list)
            and raw_consumers
            and all(
                isinstance(consumer, str) and consumer.strip()
                for consumer in raw_consumers
            )
        ):
            consumers = tuple(raw_consumers)
            if len(consumers) != len(set(consumers)):
                raise ResourceError(f"{name}: consumer 重复")
        else:
            raise ResourceError(f"{name}: consumers 必须为 '*' 或非空数组")
        resources[name] = SharedResource(
            source,
            source_key == "source_dir",
            release_path,
            consumers,
        )
    return SharedResourceManifest(1, resources)


def bundle_resources_for_skill(
    manifest: SharedResourceManifest,
    repo_root: Path,
    skill_name: str,
    target_skill_dir: Path,
) -> list[str]:
    """Bundle resources declared for one Skill into its staged directory."""
    root = repo_root.resolve()
    selected = [
        resource
        for _, resource in sorted(manifest.resources.items())
        if resource.consumers == "*" or skill_name in resource.consumers
    ]
    operations: list[tuple[Path, Path]] = []
    for resource in selected:
        source = (root / resource.source).resolve()
        if not source.is_relative_to(root):
            raise ResourceError(
                f"{skill_name}: 资源源路径越界：{resource.source}"
            )
        target = target_skill_dir / resource.release_path
        if resource.source_is_dir:
            if not source.is_dir():
                raise ResourceError(
                    f"{skill_name}: 资源目录不存在：{resource.source}"
                )
            for path in sorted(source.rglob("*")):
                resolved = path.resolve()
                if (
                    not resolved.is_relative_to(source)
                    or not resolved.is_relative_to(root)
                ):
                    raise ResourceError(
                        f"{skill_name}: 资源文件越界："
                        f"{path.relative_to(source)}"
                    )
                if path.is_file():
                    operations.append((path, target / path.relative_to(source)))
        else:
            if not source.is_file():
                raise ResourceError(
                    f"{skill_name}: 资源文件不存在：{resource.source}"
                )
            operations.append((source, target))

    destinations = [target for _, target in operations]
    if len(destinations) != len(set(destinations)):
        raise ResourceError(f"{skill_name}: 资源 release path 重复")
    for target in destinations:
        if target.exists():
            raise ResourceError(f"{skill_name}: 资源目标已存在：{target}")

    written: list[str] = []
    for source, target in operations:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        written.append(str(target.relative_to(target_skill_dir)))
    return sorted(written)
