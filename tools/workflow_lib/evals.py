"""Deterministic, repository-local behavioral evaluation validation."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path


class EvalError(RuntimeError):
    """Raised for malformed or unverifiable deterministic eval records."""


SCENARIO_VERSION = 1
EVIDENCE_VERSION = 1
REQUIRED_SCENARIOS = frozenset(
    {
        "implement-automatic-ticket",
        "implement-manual-ticket",
        "implement-mixed-ticket",
        "tdd-seam-pressure",
        "grilling-one-question-hitl",
        "diagnosing-bugs-no-red-loop",
        "writing-great-skills-baseline-discipline",
        "artifact-resolver-boundary-escape",
    }
)
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_SKILL_PATH = re.compile(r"^skills/(my-[a-z0-9-]+)/.+$")


@dataclass(frozen=True)
class Scenario:
    identifier: str
    path: Path
    skills: tuple[str, ...]
    evidence: object


def _read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvalError(f"{path}: invalid JSON") from exc


def _nonempty_strings(value: object, location: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise EvalError(f"{location}: must be a non-empty string list")
    return tuple(value)


def load_scenarios(evals_dir: Path) -> tuple[Scenario, ...]:
    """Load strict versioned scenarios in deterministic filename order."""
    root = evals_dir.resolve()
    scenarios_dir = root / "scenarios"
    if not scenarios_dir.is_dir():
        raise EvalError(f"{scenarios_dir}: scenario directory is missing")
    scenarios: list[Scenario] = []
    identifiers: set[str] = set()
    for path in sorted(scenarios_dir.glob("*.json")):
        raw = _read_json(path)
        fields = set(raw) if isinstance(raw, dict) else set()
        if fields not in (
            {"version", "id", "skills", "assertions"},
            {"version", "id", "skills", "assertions", "evidence"},
        ):
            raise EvalError(f"{path}: scenario fields are invalid")
        identifier = raw["id"]
        if not isinstance(identifier, str) or not re.fullmatch(
            r"[a-z0-9][a-z0-9-]{2,80}", identifier
        ):
            raise EvalError(f"{path}: id is invalid")
        if identifier in identifiers:
            raise EvalError(f"{path}: duplicate scenario id: {identifier}")
        identifiers.add(identifier)
        if raw["version"] != SCENARIO_VERSION:
            raise EvalError(f"{path}: unsupported scenario version")
        skills = _nonempty_strings(raw["skills"], f"{path}.skills")
        if not all(re.fullmatch(r"my-[a-z0-9-]+", skill) for skill in skills):
            raise EvalError(f"{path}: skills must be local my-* skills")
        _nonempty_strings(raw["assertions"], f"{path}.assertions")
        evidence = raw.get("evidence")
        scenarios.append(Scenario(identifier, path, skills, evidence))
    if not scenarios:
        raise EvalError(f"{scenarios_dir}: no scenarios found")
    return tuple(scenarios)


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def validate_scenario_evidence(repo_root: Path, scenario: Scenario) -> None:
    """Validate exact local source hashes referenced by one evidence record."""
    root = repo_root.resolve()
    raw = scenario.evidence
    if not isinstance(raw, dict) or set(raw) != {"version", "scenario", "sources"}:
        raise EvalError(f"{scenario.path}.evidence: evidence fields are invalid")
    if raw["version"] != EVIDENCE_VERSION:
        raise EvalError(f"{scenario.path}.evidence: unsupported evidence version")
    if raw["scenario"] != scenario.identifier:
        raise EvalError(
            f"{scenario.path}.evidence: scenario does not match {scenario.identifier}"
        )
    sources = raw["sources"]
    if not isinstance(sources, list) or not sources:
        raise EvalError(f"{scenario.path}.evidence: sources must be a non-empty list")
    found_skills: set[str] = set()
    seen_paths: set[str] = set()
    for index, source in enumerate(sources):
        location = f"{scenario.path}.evidence.sources[{index}]"
        if not isinstance(source, dict) or set(source) != {"path", "sha256"}:
            raise EvalError(f"{location}: fields must be path and sha256")
        source_path = source["path"]
        digest = source["sha256"]
        if not isinstance(source_path, str) or not _SKILL_PATH.fullmatch(source_path):
            raise EvalError(f"{location}: source path must be a skill file")
        if source_path in seen_paths:
            raise EvalError(f"{location}: duplicate source path: {source_path}")
        seen_paths.add(source_path)
        if not isinstance(digest, str) or not _DIGEST.fullmatch(digest):
            raise EvalError(f"{location}: sha256 must use sha256:<hex>")
        file_path = (root / source_path).resolve()
        try:
            file_path.relative_to((root / "skills").resolve())
        except ValueError as exc:
            raise EvalError(f"{location}: source path escapes skills") from exc
        if not file_path.is_file():
            raise EvalError(f"{location}: source file is missing: {source_path}")
        if digest != _sha256(file_path):
            raise EvalError(f"{location}: source hash is stale: {source_path}")
        found_skills.add(_SKILL_PATH.fullmatch(source_path).group(1))  # type: ignore[union-attr]
    missing = set(scenario.skills) - found_skills
    if missing:
        raise EvalError(
            f"{scenario.path}.evidence: missing evidence for skills: "
            f"{', '.join(sorted(missing))}"
        )


def validate_evals(repo_root: Path, *, allow_missing: bool = False) -> dict[str, object]:
    """Strictly validate scenarios and local evidence, optionally skipping absence."""
    root = repo_root.resolve()
    try:
        scenarios = load_scenarios(root / "evals")
    except EvalError:
        if allow_missing and not (root / "evals").exists():
            return {"status": "skipped", "reason": "evals directory is missing", "scenarios": 0}
        raise
    identifiers = {scenario.identifier for scenario in scenarios}
    missing = REQUIRED_SCENARIOS - identifiers
    if missing:
        raise EvalError("missing required scenarios: " + ", ".join(sorted(missing)))
    for scenario in scenarios:
        try:
            validate_scenario_evidence(root, scenario)
        except EvalError:
            if allow_missing and scenario.evidence is None:
                continue
            raise
    return {
        "status": "valid",
        "scenarios": len(scenarios),
        "required_scenarios": len(REQUIRED_SCENARIOS),
    }
