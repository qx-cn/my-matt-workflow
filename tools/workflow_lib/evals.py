"""Deterministic, repository-local behavioral evaluation validation."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path


class EvalError(RuntimeError):
    """Raised for malformed or unverifiable deterministic eval records."""


SCENARIO_VERSION = 2
EVIDENCE_VERSION = 1
IMPLEMENTATION_REVIEW_STATUSES = frozenset({"pass", "findings", "inconclusive"})
REQUIRED_SCENARIOS = frozenset(
    {
        "tdd-seam-pressure",
        "grilling-one-question-hitl",
        "diagnosing-bugs-no-red-loop",
        "writing-great-skills-baseline-discipline",
        "main-workflow-fresh-context",
        "artifact-review-method-boundary",
        "skill-review-root-before-wording",
        "handoff-round-trip",
        "requirement-analysis-clear-request",
        "requirement-analysis-misleading-analogy",
        "artifact-review-design-method-boundary",
        "implementation-review-baseline-reachability",
        "implementation-review-repeated-root-cause",
    }
)
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_SKILL_PATH = re.compile(r"^skills/(my-[a-z0-9-]+)/.+$")
_SCENARIO_TYPES = frozenset(
    {
        "tdd-contract",
        "grilling-contract",
        "diagnosing-contract",
        "skill-writing-contract",
        "rule-contract",
        "main-workflow-contract",
        "artifact-review-contract",
        "skill-review-contract",
        "handoff-contract",
        "requirement-analysis-contract",
        "implementation-review-contract",
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


def _evaluate_handoff_contract(input_value: dict[str, object]) -> dict[str, object]:
    case = _require_fields(
        input_value,
        {
            "source_fields",
            "reconstructed_fields",
            "references_valid",
            "sensitive_data_removed",
            "independent_context",
        },
        "handoff-contract.input",
    )
    required = {
        "goal",
        "out_of_scope",
        "decisions",
        "evidence",
        "risks",
        "references",
        "first_step",
    }
    source = case["source_fields"]
    reconstructed = case["reconstructed_fields"]
    if not isinstance(source, list) or not all(isinstance(item, str) for item in source):
        raise EvalError("handoff-contract.input.source_fields: must be strings")
    if not isinstance(reconstructed, list) or not all(
        isinstance(item, str) for item in reconstructed
    ):
        raise EvalError("handoff-contract.input.reconstructed_fields: must be strings")
    for field in ("references_valid", "sensitive_data_removed", "independent_context"):
        if not isinstance(case[field], bool):
            raise EvalError(f"handoff-contract.input.{field}: must be boolean")
    if not case["sensitive_data_removed"]:
        return {"status": "stop", "rule": "redact-sensitive-data", "next": "repair-handoff"}
    if not case["references_valid"]:
        return {"status": "stop", "rule": "verify-references", "next": "repair-handoff"}
    if set(source) != required or set(reconstructed) != required:
        return {"status": "stop", "rule": "reader-reconstruction", "next": "repair-handoff"}
    if not case["independent_context"]:
        return {
            "status": "inconclusive",
            "rule": "reader-reconstruction-evidence-gap",
            "next": "deliver-draft-with-gap",
        }
    return {"status": "valid", "rule": "handoff-round-trip", "next": "resume-first-step"}


def _evaluate_requirement_analysis_contract(
    input_value: dict[str, object],
) -> dict[str, object]:
    case = _require_fields(
        input_value,
        {
            "request_shape",
            "traceable_fields",
            "summary_matches_input",
            "result_changing_ambiguity",
        },
        "requirement-analysis-contract.input",
    )
    if case["request_shape"] not in {"clear", "complex", "implicit", "analogy"}:
        raise EvalError("requirement-analysis-contract.input.request_shape: invalid shape")
    traceable = case["traceable_fields"]
    if not isinstance(traceable, list) or not all(
        isinstance(item, str) for item in traceable
    ):
        raise EvalError(
            "requirement-analysis-contract.input.traceable_fields: must be strings"
        )
    for field in ("summary_matches_input", "result_changing_ambiguity"):
        if not isinstance(case[field], bool):
            raise EvalError(
                f"requirement-analysis-contract.input.{field}: must be boolean"
            )
    review_mode = "quick-pass" if case["request_shape"] == "clear" else "independent"
    if set(traceable) != {"goal", "scope", "constraints", "acceptance"}:
        return {
            "verdict": "NEEDS_CLARIFICATION",
            "rule": "traceable-requirement-contract",
            "review_mode": review_mode,
            "next": "complete-summary",
        }
    if not case["summary_matches_input"]:
        return {
            "verdict": "MISUNDERSTANDING",
            "rule": "preserve-user-intent",
            "review_mode": review_mode,
            "next": "correct-summary",
        }
    if case["result_changing_ambiguity"]:
        return {
            "verdict": "NEEDS_CLARIFICATION",
            "rule": "result-changing-ambiguity",
            "review_mode": review_mode,
            "next": "ask-minimal-question",
        }
    return {
        "verdict": "PASS",
        "rule": "traceable-requirement-contract",
        "review_mode": review_mode,
        "next": "plan",
    }


def _evaluate_implementation_review_contract(
    input_value: dict[str, object],
) -> dict[str, object]:
    case = _require_fields(
        input_value,
        {
            "outcome",
            "baseline_reachable",
            "previous_root_causes",
            "current_root_causes",
            "snapshot_released",
        },
        "implementation-review-contract.input",
    )
    if case["outcome"] not in IMPLEMENTATION_REVIEW_STATUSES:
        raise EvalError("implementation-review-contract.input.outcome: invalid status")
    if case["baseline_reachable"] not in {True, False, None}:
        raise EvalError("implementation-review-contract.input.baseline_reachable: invalid value")
    for field in ("previous_root_causes", "current_root_causes"):
        if not isinstance(case[field], list) or not all(
            isinstance(item, str) and item for item in case[field]
        ):
            raise EvalError(f"implementation-review-contract.input.{field}: invalid roots")
    if not isinstance(case["snapshot_released"], bool):
        raise EvalError("implementation-review-contract.input.snapshot_released: must be boolean")
    if not case["snapshot_released"]:
        return {"status": "stop", "rule": "release-review-snapshot", "next": "cleanup"}
    if case["outcome"] == "findings" and case["baseline_reachable"] is not True:
        return {
            "status": "inconclusive",
            "rule": "formal-baseline-reachability",
            "next": "blocked-by-evidence",
        }
    repeated = set(case["previous_root_causes"]) & set(case["current_root_causes"])
    if case["outcome"] == "findings" and repeated:
        return {
            "status": "stop",
            "rule": "repeated-review-root-cause",
            "next": "blocked-by-design",
        }
    if case["outcome"] == "findings":
        return {"status": "proceed", "rule": "persist-review-attempt", "next": "fix-findings"}
    if case["outcome"] == "inconclusive":
        return {"status": "stop", "rule": "persist-review-attempt", "next": "blocked-by-evidence"}
    return {"status": "valid", "rule": "code-bound-review-receipt", "next": "submit-completed"}


def _evaluate_rule_contract(input_value: dict[str, object]) -> dict[str, object]:
    case = _require_fields(
        input_value,
        {"execution_agent", "rule_evidence", "ticket_admission", "implementation_recheck"},
        "rule-contract.input",
    )
    if case["execution_agent"] not in {"codex", "cursor", "claude"}:
        raise EvalError("rule-contract.input.execution_agent: invalid agent")
    if not isinstance(case["rule_evidence"], bool) or not isinstance(case["ticket_admission"], bool) or not isinstance(case["implementation_recheck"], bool):
        raise EvalError("rule-contract.input: rule lifecycle values must be booleans")
    if not case["rule_evidence"]:
        return {"status": "stop", "rule": "resolve-target-agent-rules", "next": "collect-rule-evidence"}
    if not case["ticket_admission"]:
        return {"status": "stop", "rule": "ticket-rule-admission", "next": "complete-ticket-rule-fields"}
    if not case["implementation_recheck"]:
        return {"status": "stop", "rule": "recheck-real-paths", "next": "resolve-rules-before-edit"}
    return {"status": "valid", "rule": "rule-plan-ticket-implementation-loop", "next": "implement"}


def _evaluate_main_workflow_contract(input_value: dict[str, object]) -> dict[str, object]:
    fields = {
        "fresh_context",
        "finalization_gates",
        "spec_lineage",
        "ticket_lineage",
        "review_snapshot",
        "evidence_report",
    }
    case = _require_fields(input_value, fields, "main-workflow-contract.input")
    if not all(isinstance(case[field], bool) for field in fields):
        raise EvalError("main-workflow-contract.input: all fields must be booleans")
    ordered_gates = (
        ("fresh_context", "fresh-context-reconstruction"),
        ("finalization_gates", "artifact-finalization"),
        ("spec_lineage", "spec-revision-lineage"),
        ("ticket_lineage", "ticket-spec-lineage"),
        ("review_snapshot", "review-content-snapshot"),
        ("evidence_report", "test-evidence-report"),
    )
    for field, rule in ordered_gates:
        if not case[field]:
            return {"status": "stop", "rule": rule, "next": "repair-handoff"}
    return {
        "status": "valid",
        "rule": "fresh-context-main-workflow",
        "next": "report-evidence",
    }


def _evaluate_artifact_review_contract(input_value: dict[str, object]) -> dict[str, object]:
    case = _require_fields(
        input_value,
        {
            "fixed_review_unit",
            "artifact_kind",
            "required_checks",
            "completed_checks",
            "material_root_causes",
            "inconclusive_count",
        },
        "artifact-review-contract.input",
    )
    if not isinstance(case["fixed_review_unit"], bool):
        raise EvalError("artifact-review-contract.input.fixed_review_unit: must be boolean")
    if case["artifact_kind"] not in {"general", "design"}:
        raise EvalError("artifact-review-contract.input.artifact_kind: invalid kind")
    required_checks = case["required_checks"]
    completed_checks = case["completed_checks"]
    if (
        not isinstance(required_checks, list)
        or not required_checks
        or not all(isinstance(check, str) and check for check in required_checks)
        or len(required_checks) != len(set(required_checks))
    ):
        raise EvalError("artifact-review-contract.input.required_checks: must be unique strings")
    if not isinstance(completed_checks, list) or not all(
        isinstance(check, str) and check for check in completed_checks
    ):
        raise EvalError("artifact-review-contract.input.completed_checks: must be strings")
    roots = case["material_root_causes"]
    if not isinstance(roots, list) or not all(
        isinstance(root, str) and root for root in roots
    ):
        raise EvalError(
            "artifact-review-contract.input.material_root_causes: must be a string list"
        )
    inconclusive = case["inconclusive_count"]
    if not isinstance(inconclusive, int) or inconclusive < 0:
        raise EvalError(
            "artifact-review-contract.input.inconclusive_count: must be non-negative"
        )
    if not case["fixed_review_unit"]:
        return {
            "status": "stop",
            "rule": "fixed-review-unit",
            "next": "prepare-review-unit",
        }
    expected_checks = {
        "my-final-state-writing",
        "my-reader-first-writing",
        "my-visual-communication",
        "my-humanizer",
        "my-artifact-finalization",
    }
    if case["artifact_kind"] == "design":
        expected_checks.add("my-review-design")
    if set(required_checks) != expected_checks:
        return {
            "status": "stop",
            "rule": "artifact-kind-method-set",
            "next": "rebuild-review-unit",
        }
    if set(completed_checks) != set(required_checks):
        return {
            "status": "stop",
            "rule": "complete-required-review-checks",
            "next": "finish-review-methods",
        }
    return {
        "status": "valid",
        "rule": "semantic-evidence-review",
        "findings": len(set(roots)),
        "inconclusive": inconclusive,
        "next": "verify-content-id",
    }


def _evaluate_skill_review_contract(input_value: dict[str, object]) -> dict[str, object]:
    case = _require_fields(
        input_value,
        {
            "fixed_review_unit",
            "runtime_snapshot_ready",
            "scope_inventory_complete",
            "existence_gate_complete",
            "walkthrough_coverage_complete",
            "snapshot_verified",
            "evidence_level",
            "comparative_dispute",
            "user_authorized_comparative",
            "root_causes",
            "editorial_candidates",
        },
        "skill-review-contract.input",
    )
    gate_fields = (
        "fixed_review_unit",
        "runtime_snapshot_ready",
        "scope_inventory_complete",
        "existence_gate_complete",
        "walkthrough_coverage_complete",
        "snapshot_verified",
    )
    if not all(isinstance(case[field], bool) for field in gate_fields):
        raise EvalError("skill-review-contract.input: gate fields must be booleans")
    if case["evidence_level"] not in {"static", "observed", "comparative"}:
        raise EvalError("skill-review-contract.input.evidence_level: invalid level")
    if not isinstance(case["comparative_dispute"], bool) or not isinstance(
        case["user_authorized_comparative"], bool
    ):
        raise EvalError("skill-review-contract.input: comparative gates must be booleans")
    roots = case["root_causes"]
    if not isinstance(roots, list) or not all(
        isinstance(root, str) and root for root in roots
    ):
        raise EvalError(
            "skill-review-contract.input.root_causes: must be a string list"
        )
    editorial = case["editorial_candidates"]
    if not isinstance(editorial, int) or editorial < 0:
        raise EvalError(
            "skill-review-contract.input.editorial_candidates: must be non-negative"
        )
    if not case["fixed_review_unit"] or not case["runtime_snapshot_ready"]:
        return {
            "status": "stop",
            "rule": "fixed-review-unit",
            "next": "build-runtime-snapshot",
        }
    if not case["scope_inventory_complete"]:
        return {
            "status": "stop",
            "rule": "complete-scope-inventory",
            "next": "resolve-skill-relations",
        }
    if not case["existence_gate_complete"]:
        return {
            "status": "stop",
            "rule": "existence-before-instruction-design",
            "next": "evaluate-skill-destination",
        }
    if not case["walkthrough_coverage_complete"]:
        return {
            "status": "stop",
            "rule": "complete-walkthrough-coverage",
            "next": "map-uncovered-paths",
        }
    if not case["snapshot_verified"]:
        return {
            "status": "stop",
            "rule": "verify-review-snapshot",
            "next": "finalize-review-unit",
        }
    if case["evidence_level"] == "comparative" and not (
        case["comparative_dispute"] and case["user_authorized_comparative"]
    ):
        return {
            "status": "stop",
            "rule": "authorized-disputed-comparative",
            "next": "report-current-evidence",
        }
    comparative = case["evidence_level"] == "comparative"
    return {
        "status": "valid",
        "rule": "root-before-wording",
        "findings": len(set(roots)),
        "suppressed_editorial": editorial if roots else 0,
        "verdict": "EVIDENCE_BACKED" if comparative else "INCONCLUSIVE",
        "next": "report",
    }


def run_scenario(repo_root: Path, scenario: Scenario) -> dict[str, object]:
    """Execute one structured deterministic scenario and assert its exact outcome."""
    evaluators = {
        "tdd-contract": _evaluate_tdd_contract,
        "grilling-contract": _evaluate_grilling_contract,
        "diagnosing-contract": _evaluate_diagnosing_contract,
        "skill-writing-contract": _evaluate_skill_writing_contract,
        "rule-contract": _evaluate_rule_contract,
        "main-workflow-contract": _evaluate_main_workflow_contract,
        "artifact-review-contract": _evaluate_artifact_review_contract,
        "skill-review-contract": _evaluate_skill_review_contract,
        "handoff-contract": _evaluate_handoff_contract,
        "requirement-analysis-contract": _evaluate_requirement_analysis_contract,
        "implementation-review-contract": _evaluate_implementation_review_contract,
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
        "evidence_level": "deterministic-contract",
        "scenarios": len(scenarios),
        "required_scenarios": len(REQUIRED_SCENARIOS),
    }
