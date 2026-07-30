"""Deterministic, repository-local behavioral evaluation validation."""

from __future__ import annotations

import hashlib
import json
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .artifact_resolver import ArtifactResolverError, resolve_work_artifact
from .tickets import TicketError, load_tickets, select_implementation_ticket


class EvalError(RuntimeError):
    """Raised for malformed or unverifiable deterministic eval records."""


SCENARIO_VERSION = 2
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
_SCENARIO_TYPES = frozenset(
    {
        "implementation-selection",
        "tdd-contract",
        "grilling-contract",
        "diagnosing-contract",
        "skill-writing-contract",
        "artifact-resolver",
    }
)


@dataclass(frozen=True)
class Scenario:
    identifier: str
    path: Path
    case_type: str
    skills: tuple[str, ...]
    input: dict[str, object]
    expected: dict[str, object]
    evidence: dict[str, object] | None


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
            {"version", "id", "type", "skills", "input", "expected"},
            {"version", "id", "type", "skills", "input", "expected", "evidence"},
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
        case_type = raw["type"]
        if not isinstance(case_type, str) or case_type not in _SCENARIO_TYPES:
            raise EvalError(f"{path}: unsupported scenario type")
        skills = _nonempty_strings(raw["skills"], f"{path}.skills")
        if not all(re.fullmatch(r"my-[a-z0-9-]+", skill) for skill in skills):
            raise EvalError(f"{path}: skills must be local my-* skills")
        if not isinstance(raw["input"], dict) or not raw["input"]:
            raise EvalError(f"{path}.input: must be a non-empty object")
        if not isinstance(raw["expected"], dict) or not raw["expected"]:
            raise EvalError(f"{path}.expected: must be a non-empty object")
        evidence = raw.get("evidence")
        scenarios.append(
            Scenario(identifier, path, case_type, skills, raw["input"], raw["expected"], evidence)
        )
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


def _require_fields(
    value: object, fields: set[str], location: str
) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != fields:
        raise EvalError(f"{location}: fields must be {', '.join(sorted(fields))}")
    return value


def _ticket_document(raw: object, location: str) -> str:
    ticket = _require_fields(
        raw,
        {
            "filename",
            "id",
            "title",
            "ticket_kind",
            "status",
            "blocked_by",
            "claimed_by",
            "tags",
            "sequence",
            "acceptance",
        },
        location,
    )
    filename = ticket["filename"]
    if not isinstance(filename, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]*\.md", filename):
        raise EvalError(f"{location}.filename: must be a normalized Markdown filename")
    for field in ("id", "title", "ticket_kind", "status"):
        if not isinstance(ticket[field], str) or not ticket[field]:
            raise EvalError(f"{location}.{field}: must be a non-empty string")
    if ticket["claimed_by"] is not None and (
        not isinstance(ticket["claimed_by"], str) or not ticket["claimed_by"]
    ):
        raise EvalError(f"{location}.claimed_by: must be a string or null")
    if not isinstance(ticket["sequence"], int) or ticket["sequence"] < 0:
        raise EvalError(f"{location}.sequence: must be a non-negative integer")
    for field in ("blocked_by", "tags"):
        if not isinstance(ticket[field], list) or not all(
            isinstance(value, str) and value for value in ticket[field]
        ):
            raise EvalError(f"{location}.{field}: must be a string list")
    acceptance = _require_fields(
        ticket["acceptance"], {"checked", "unchecked"}, f"{location}.acceptance"
    )
    if not all(isinstance(acceptance[key], int) and acceptance[key] >= 0 for key in acceptance):
        raise EvalError(f"{location}.acceptance: checkbox counts must be non-negative integers")
    claimed_by = "" if ticket["claimed_by"] is None else str(ticket["claimed_by"])
    lines = [
        "---",
        f"id: {ticket['id']}",
        f"title: {ticket['title']}",
        f"ticket_kind: {ticket['ticket_kind']}",
        f"status: {ticket['status']}",
        f"blocked_by: [{', '.join(ticket['blocked_by'])}]",
        f"claimed_by: {claimed_by}",
        f"tags: [{', '.join(ticket['tags'])}]",
        f"sequence: {ticket['sequence']}",
        "---",
        f"# {ticket['title']}",
    ]
    lines.extend("- [x] accepted" for _ in range(acceptance["checked"]))
    lines.extend("- [ ] pending" for _ in range(acceptance["unchecked"]))
    return "\n".join(lines) + "\n"


def _evaluate_implementation_selection(input_value: dict[str, object]) -> dict[str, object]:
    policy = input_value.get("policy")
    tickets = input_value.get("tickets")
    if policy not in {"automatic", "manual"}:
        raise EvalError("implementation-selection.input.policy: must be automatic or manual")
    if not isinstance(tickets, list) or not tickets:
        raise EvalError("implementation-selection.input.tickets: must be a non-empty list")
    if policy == "manual":
        return {"status": "manual-selection-required", "selected": None}
    with tempfile.TemporaryDirectory(prefix="my-matt-eval-tickets-") as directory:
        root = Path(directory)
        paths: list[Path] = []
        for index, raw in enumerate(tickets):
            document = _ticket_document(raw, f"implementation-selection.input.tickets[{index}]")
            filename = _require_fields(
                raw,
                {
                    "filename",
                    "id",
                    "title",
                    "ticket_kind",
                    "status",
                    "blocked_by",
                    "claimed_by",
                    "tags",
                    "sequence",
                    "acceptance",
                },
                f"implementation-selection.input.tickets[{index}]",
            )["filename"]
            path = root / str(filename)
            path.write_text(document, encoding="utf-8")
            paths.append(path)
        try:
            selected = select_implementation_ticket(load_tickets(paths))
        except TicketError as exc:
            raise EvalError(f"implementation-selection runtime failed: {exc}") from exc
    return {"status": "selected", "selected": selected.identifier}


def _evaluate_tdd_contract(input_value: dict[str, object]) -> dict[str, object]:
    case = _require_fields(
        input_value, {"dependency", "seam", "slice"}, "tdd-contract.input"
    )
    if case["dependency"] != "hard-to-test":
        raise EvalError("tdd-contract.input.dependency: must be hard-to-test")
    seam = _require_fields(case["seam"], {"confirmed", "visibility"}, "tdd-contract.input.seam")
    if seam["visibility"] != "public" or not isinstance(seam["confirmed"], bool):
        raise EvalError("tdd-contract.input.seam: requires a public confirmed boolean")
    if case["slice"] != "single":
        raise EvalError("tdd-contract.input.slice: must be single")
    if not seam["confirmed"]:
        return {
            "status": "stop",
            "rule": "confirm-public-seam-before-test",
            "next": "await-user-confirmation",
        }
    return {
        "status": "proceed",
        "rule": "one-test-one-minimal-implementation",
        "next": "write-red-test",
    }


def _evaluate_grilling_contract(input_value: dict[str, object]) -> dict[str, object]:
    case = _require_fields(
        input_value, {"questions_asked", "human_response", "understanding_confirmed"}, "grilling-contract.input"
    )
    if not isinstance(case["questions_asked"], int) or case["questions_asked"] < 0:
        raise EvalError("grilling-contract.input.questions_asked: must be a non-negative integer")
    if not isinstance(case["human_response"], bool) or not isinstance(
        case["understanding_confirmed"], bool
    ):
        raise EvalError("grilling-contract.input: response flags must be booleans")
    if case["questions_asked"] != 1:
        return {"status": "stop", "rule": "exactly-one-question", "next": "ask-one-question"}
    if not case["human_response"]:
        return {"status": "stop", "rule": "human-in-the-loop", "next": "await-human-response"}
    return {
        "status": "proceed" if case["understanding_confirmed"] else "ask-next",
        "rule": "human-in-the-loop",
        "next": "execute" if case["understanding_confirmed"] else "ask-one-question",
    }


def _evaluate_diagnosing_contract(input_value: dict[str, object]) -> dict[str, object]:
    case = _require_fields(
        input_value, {"red_loop", "new_discriminating_hypothesis", "decision_policy"}, "diagnosing-contract.input"
    )
    if not isinstance(case["red_loop"], bool) or not isinstance(
        case["new_discriminating_hypothesis"], bool
    ):
        raise EvalError("diagnosing-contract.input: loop fields must be booleans")
    if case["decision_policy"] not in {"ask", "halt", "autonomous"}:
        raise EvalError("diagnosing-contract.input.decision_policy: invalid policy")
    if case["red_loop"] and not case["new_discriminating_hypothesis"]:
        return {
            "status": "stop",
            "rule": "no-repeat-red-loop",
            "next": "form-discriminating-hypothesis",
        }
    return {"status": "proceed", "rule": "evidence-led-diagnosis", "next": "test-hypothesis"}


def _evaluate_skill_writing_contract(input_value: dict[str, object]) -> dict[str, object]:
    case = _require_fields(
        input_value, {"baseline", "fixed", "stress"}, "skill-writing-contract.input"
    )
    baseline = _require_fields(case["baseline"], {"metric", "value"}, "skill-writing-contract.input.baseline")
    fixed = _require_fields(case["fixed"], {"metric", "value"}, "skill-writing-contract.input.fixed")
    stress = _require_fields(case["stress"], {"metric", "values"}, "skill-writing-contract.input.stress")
    if not all(item["metric"] == "pass-rate" for item in (baseline, fixed, stress)):
        raise EvalError("skill-writing-contract.input: metric must be pass-rate")
    if not isinstance(baseline["value"], int) or not isinstance(fixed["value"], int):
        raise EvalError("skill-writing-contract.input: baseline and fixed values must be integers")
    values = stress["values"]
    if not isinstance(values, list) or not values or not all(isinstance(value, int) for value in values):
        raise EvalError("skill-writing-contract.input.stress.values: must be a non-empty integer list")
    if fixed["value"] < baseline["value"] or any(value < baseline["value"] for value in values):
        return {"status": "stop", "rule": "preserve-measured-baseline", "next": "fix-regression"}
    return {
        "status": "valid",
        "rule": "baseline-fixed-stress",
        "baseline": baseline["value"],
        "fixed": fixed["value"],
        "stress_minimum": min(values),
    }


def _evaluate_artifact_resolver(input_value: dict[str, object]) -> dict[str, object]:
    attacks = input_value.get("attacks")
    if not isinstance(attacks, list) or not attacks:
        raise EvalError("artifact-resolver.input.attacks: must be a non-empty list")
    outcomes: list[dict[str, str]] = []
    with tempfile.TemporaryDirectory(prefix="my-matt-eval-artifacts-") as directory:
        root = Path(directory)
        work = root / ".agent" / "work" / "checkout" / "specs"
        work.mkdir(parents=True)
        (work / "specs-checkout-01.md").write_text("# safe\n", encoding="utf-8")
        outside = root / "outside.md"
        outside.write_text("# outside\n", encoding="utf-8")
        (work / "escape.md").symlink_to(outside)
        for index, raw in enumerate(attacks):
            attack = _require_fields(
                raw, {"name", "selector", "error"}, f"artifact-resolver.input.attacks[{index}]"
            )
            if not all(isinstance(attack[key], str) and attack[key] for key in attack):
                raise EvalError(f"artifact-resolver.input.attacks[{index}]: values must be strings")
            try:
                resolve_work_artifact(root, "checkout", "specs", attack["selector"])
            except ArtifactResolverError as exc:
                message = str(exc)
                if attack["error"] not in message:
                    raise EvalError(
                        f"artifact-resolver runtime mismatch for {attack['name']}: {message}"
                    ) from exc
                outcomes.append({"name": attack["name"], "error": attack["error"]})
            else:
                raise EvalError(f"artifact-resolver attack was accepted: {attack['name']}")
    return {"status": "rejected", "attacks": outcomes}


def run_scenario(repo_root: Path, scenario: Scenario) -> dict[str, object]:
    """Execute one structured deterministic scenario and assert its exact outcome."""
    evaluators = {
        "implementation-selection": _evaluate_implementation_selection,
        "tdd-contract": _evaluate_tdd_contract,
        "grilling-contract": _evaluate_grilling_contract,
        "diagnosing-contract": _evaluate_diagnosing_contract,
        "skill-writing-contract": _evaluate_skill_writing_contract,
        "artifact-resolver": _evaluate_artifact_resolver,
    }
    outcome = evaluators[scenario.case_type](scenario.input)
    if outcome != scenario.expected:
        raise EvalError(
            f"{scenario.path}: outcome mismatch: expected "
            f"{json.dumps(scenario.expected, sort_keys=True)}, got "
            f"{json.dumps(outcome, sort_keys=True)}"
        )
    return outcome


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
            run_scenario(root, scenario)
        except EvalError:
            if allow_missing and scenario.evidence is None:
                continue
            raise
    return {
        "status": "valid",
        "scenarios": len(scenarios),
        "required_scenarios": len(REQUIRED_SCENARIOS),
    }
