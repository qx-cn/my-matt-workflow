"""Composition manifest parsing, validation, and dependency resolution."""

from __future__ import annotations

import heapq
import json
from dataclasses import dataclass
from pathlib import Path


COMPOSITION_POLICY_MEANINGS = {
    "manual": "内部 method 同轮执行；已授权 handoff 输出显式调用后停止",
    "automatic": "内部 method 同轮执行；已授权 handoff 同轮继续",
}


class CompositionError(RuntimeError):
    """Raised when Skill composition declarations are invalid."""


@dataclass(frozen=True)
class DependencyEdge:
    skill: str
    when: str
    kind: str


@dataclass(frozen=True)
class CompositionManifest:
    version: int
    callers: dict[str, tuple[DependencyEdge, ...]]
    routable_entries: dict[str, tuple[str, ...]]


def _skill_name(value: object, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CompositionError(f"{location}: Skill 名称不能为空")
    return value


def load_composition_manifest(path: Path) -> CompositionManifest:
    """Load a strict version-2 composition manifest."""
    try:
        raw = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise CompositionError(f"组合清单无法读取：{path}") from exc
    if not isinstance(raw, dict) or set(raw) != {
        "version",
        "callers",
        "routable_entries",
    }:
        raise CompositionError("组合清单字段必须为 version、callers、routable_entries")
    if raw["version"] != 2:
        raise CompositionError(f"不支持的组合清单版本：{raw['version']!r}")
    if not isinstance(raw["callers"], dict):
        raise CompositionError("callers 必须是对象")
    if not isinstance(raw["routable_entries"], dict):
        raise CompositionError("routable_entries 必须是对象")

    callers: dict[str, tuple[DependencyEdge, ...]] = {}
    for caller_value, edge_values in raw["callers"].items():
        caller = _skill_name(caller_value, "callers")
        if not isinstance(edge_values, list):
            raise CompositionError(f"{caller}: 依赖必须是数组")
        edges: list[DependencyEdge] = []
        seen: set[str] = set()
        for index, edge_value in enumerate(edge_values):
            if not isinstance(edge_value, dict) or set(edge_value) != {"skill", "when", "kind"}:
                raise CompositionError(f"{caller}[{index}]: 依赖字段必须为 skill、when、kind")
            skill = _skill_name(edge_value["skill"], f"{caller}[{index}]")
            when = edge_value["when"]
            if not isinstance(when, str) or not when.strip():
                raise CompositionError(f"{caller}[{index}]: when 不能为空")
            kind = edge_value["kind"]
            if kind not in {"method", "handoff", "chain"}:
                raise CompositionError(
                    f"{caller}[{index}]: kind 必须为 method、handoff 或 chain"
                )
            if skill in seen:
                raise CompositionError(f"{caller}: 重复依赖 {skill}")
            seen.add(skill)
            edges.append(DependencyEdge(skill, when, kind))
        callers[caller] = tuple(edges)

    routable_entries: dict[str, tuple[str, ...]] = {}
    for router_value, entry_values in raw["routable_entries"].items():
        router = _skill_name(router_value, "routable_entries")
        if not isinstance(entry_values, list):
            raise CompositionError(f"{router}: 路由入口必须是数组")
        entries = tuple(
            _skill_name(entry, f"{router}[{index}]")
            for index, entry in enumerate(entry_values)
        )
        if len(entries) != len(set(entries)):
            raise CompositionError(f"{router}: 路由入口重复")
        routable_entries[router] = entries

    return CompositionManifest(2, callers, routable_entries)


def validate_composition_manifest(
    manifest: CompositionManifest, skills_dir: Path
) -> None:
    """Validate declared Skills and reject every graph cycle."""
    if manifest.version != 2:
        raise CompositionError(f"不支持的组合清单版本：{manifest.version}")
    for caller, edges in sorted(manifest.callers.items()):
        if not (skills_dir / caller).is_dir():
            raise CompositionError(f"组合清单调用方不存在：{caller}")
        for edge in edges:
            if not (skills_dir / edge.skill).is_dir():
                raise CompositionError(
                    f"{caller}: 组合清单引用未知 Skill：{edge.skill}"
                )
    for router, entries in sorted(manifest.routable_entries.items()):
        if not (skills_dir / router).is_dir():
            raise CompositionError(f"路由调用方不存在：{router}")
        for entry in entries:
            if not (skills_dir / entry).is_dir():
                raise CompositionError(
                    f"{router}: 路由引用未知 Skill：{entry}"
                )

    if manifest.routable_entries:
        declared = set(manifest.callers) | set(manifest.routable_entries)
        declared.update(edge.skill for edges in manifest.callers.values() for edge in edges)
        declared.update(entry for entries in manifest.routable_entries.values() for entry in entries)
        actual = {p.name for p in skills_dir.iterdir() if p.is_dir()}
        if actual != declared:
            raise CompositionError(f"Skill 集合与组合清单不一致：{sorted(actual ^ declared)}")

    state: dict[str, int] = {}
    stack: list[str] = []

    def visit(skill: str) -> None:
        current = state.get(skill, 0)
        if current == 2:
            return
        if current == 1:
            start = stack.index(skill)
            cycle = stack[start:] + [skill]
            raise CompositionError(f"组合图存在循环：{' -> '.join(cycle)}")
        state[skill] = 1
        stack.append(skill)
        for edge in sorted(manifest.callers.get(skill, ()), key=lambda item: item.skill):
            visit(edge.skill)
        stack.pop()
        state[skill] = 2

    for caller in sorted(set(manifest.callers) | set(manifest.routable_entries)):
        visit(caller)


def resolve_transitive_closure(
    manifest: CompositionManifest, caller: str
) -> list[str]:
    """Return dependencies in deterministic dependency-first topological order."""
    dependencies: set[str] = set()

    def collect(skill: str) -> None:
        for edge in manifest.callers.get(skill, ()):
            if edge.skill not in dependencies:
                dependencies.add(edge.skill)
                collect(edge.skill)

    collect(caller)
    indegree = {skill: 0 for skill in dependencies}
    followers: dict[str, set[str]] = {skill: set() for skill in dependencies}
    for skill in dependencies:
        for edge in manifest.callers.get(skill, ()):
            if edge.skill in dependencies:
                followers[edge.skill].add(skill)
                indegree[skill] += 1

    ready = [skill for skill, count in indegree.items() if count == 0]
    heapq.heapify(ready)
    result: list[str] = []
    while ready:
        skill = heapq.heappop(ready)
        result.append(skill)
        for follower in sorted(followers[skill]):
            indegree[follower] -= 1
            if indegree[follower] == 0:
                heapq.heappush(ready, follower)
    if len(result) != len(dependencies):
        raise CompositionError(f"{caller}: 组合依赖无法拓扑排序")
    return result



def model_invocable_skills(manifest: CompositionManifest | None) -> set[str]:
    """Only declared call targets are model-invocable; routes are not calls."""
    return {edge.skill for edges in manifest.callers.values() for edge in edges} if manifest else set()
