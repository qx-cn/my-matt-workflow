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


def validate_smoke_registry(
    repo_root: Path, scenarios: tuple[Scenario, ...] | None = None
) -> dict[str, tuple[str, ...]]:
    """Require registry entries and scenarios to form one complete valid mapping."""
    root = repo_root.resolve()
    registry = load_smoke_registry(root)
    if not registry:
        raise SmokeRegistryError("evals/smoke-registry.json: skills mapping is empty")
    if scenarios is None:
        try:
            scenarios = load_scenarios(root / "evals")
        except EvalError as exc:
            raise SmokeRegistryError(str(exc)) from exc
    known = {scenario.identifier: scenario for scenario in scenarios}
    registered: set[str] = set()
    for skill, scenario_ids in registry.items():
        if not (root / "skills" / skill / "SKILL.md").is_file():
            raise SmokeRegistryError(
                f"evals/smoke-registry.json: registered skill is missing: {skill}"
            )
        for identifier in scenario_ids:
            scenario = known.get(identifier)
            if scenario is None:
                raise SmokeRegistryError(
                    f"evals/smoke-registry.json: {skill} references unknown "
                    f"scenario {identifier}"
                )
            if skill not in scenario.skills:
                raise SmokeRegistryError(
                    f"evals/smoke-registry.json: {skill} is not covered by "
                    f"scenario {identifier}"
                )
            registered.add(identifier)
    missing = set(known) - registered
    if missing:
        raise SmokeRegistryError(
            "evals/smoke-registry.json: scenarios are unregistered: "
            + ", ".join(sorted(missing))
        )
    return registry


def resolve_smoke_scenarios(
    repo_root: Path, skills: list[str]
) -> tuple[Scenario, ...]:
    """Resolve selected skills to existing scenarios, failing bad registry targets."""
    try:
        loaded = load_scenarios(repo_root / "evals")
    except EvalError as exc:
        raise SmokeRegistryError(str(exc)) from exc
    registry = validate_smoke_registry(repo_root, loaded)
    scenarios = {item.identifier: item for item in loaded}
    selected: dict[str, Scenario] = {}
    for skill in sorted(set(skills)):
        if skill not in registry:
            raise SmokeRegistryError(
                f"evals/smoke-registry.json: skill is not registered: {skill}"
            )
        for identifier in registry[skill]:
            selected[identifier] = scenarios[identifier]
    return tuple(selected[key] for key in sorted(selected))
