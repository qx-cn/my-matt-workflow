"""Checked-in Skill-to-scenario mappings used by the smoke command."""

from __future__ import annotations

import json
import re
from pathlib import Path

from .evals import EvalError, Scenario, load_scenarios


class SmokeRegistryError(RuntimeError):
    """Raised when the checked-in smoke registry is malformed."""


def load_smoke_registry(repo_root: Path) -> dict[str, tuple[str, ...]]:
    """Load a strict, repository-local mapping from skills to scenario ids."""
    path = repo_root / "evals" / "smoke-registry.json"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SmokeRegistryError(f"{path}: invalid smoke registry JSON") from exc
    if not isinstance(raw, dict) or set(raw) != {"version", "skills"}:
        raise SmokeRegistryError(f"{path}: fields must be version and skills")
    if raw["version"] != 1 or not isinstance(raw["skills"], dict):
        raise SmokeRegistryError(f"{path}: unsupported smoke registry")
    registry: dict[str, tuple[str, ...]] = {}
    for skill, scenario_ids in sorted(raw["skills"].items()):
        if not isinstance(skill, str) or not re.fullmatch(r"my-[a-z0-9-]+", skill):
            raise SmokeRegistryError(f"{path}: invalid skill key: {skill!r}")
        if not isinstance(scenario_ids, list) or not scenario_ids or not all(
            isinstance(identifier, str) and identifier for identifier in scenario_ids
        ):
            raise SmokeRegistryError(f"{path}: {skill} must map to scenario ids")
        if len(scenario_ids) != len(set(scenario_ids)):
            raise SmokeRegistryError(f"{path}: {skill} maps a scenario more than once")
        registry[skill] = tuple(scenario_ids)
    return registry


def resolve_smoke_scenarios(
    repo_root: Path, skills: list[str]
) -> tuple[Scenario, ...]:
    """Resolve selected skills to existing scenarios, failing bad registry targets."""
    registry = load_smoke_registry(repo_root)
    try:
        scenarios = {item.identifier: item for item in load_scenarios(repo_root / "evals")}
    except EvalError as exc:
        raise SmokeRegistryError(str(exc)) from exc
    selected: dict[str, Scenario] = {}
    for skill in sorted(set(skills)):
        for identifier in registry.get(skill, ()):
            if identifier not in scenarios:
                raise SmokeRegistryError(
                    f"evals/smoke-registry.json: {skill} references unknown "
                    f"scenario {identifier}"
                )
            selected[identifier] = scenarios[identifier]
    return tuple(selected[key] for key in sorted(selected))
