"""Strict definitions and records for real fresh-agent behavior evidence."""

from __future__ import annotations

import json
from pathlib import Path


class BehaviorEvidenceError(ValueError):
    """Raised when a behavior suite or its execution evidence is malformed."""


RUN_STATUSES = {"pass", "fail", "blocked", "inconclusive"}
RUN_FIELDS = {
    "case_id",
    "model",
    "host",
    "release_id",
    "session_id",
    "status",
    "raw_output",
    "observations",
    "artifacts",
    "commands",
    "limitation",
}


def _read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BehaviorEvidenceError(f"{path}: JSON 无法读取") from exc


def validate_behavior_suite(path: Path) -> dict[str, tuple[str, ...]]:
    raw = _read_json(path)
    if not isinstance(raw, dict) or set(raw) != {
        "version", "id", "evidence_level", "cases"
    }:
        raise BehaviorEvidenceError(f"{path}: suite 字段无效")
    if raw["version"] != 1 or raw["id"] != "astra-instruction-following":
        raise BehaviorEvidenceError(f"{path}: suite 版本或 id 无效")
    if raw["evidence_level"] != "fresh-agent-smoke" or not isinstance(raw["cases"], list):
        raise BehaviorEvidenceError(f"{path}: evidence_level 或 cases 无效")
    cases: dict[str, tuple[str, ...]] = {}
    for case in raw["cases"]:
        if not isinstance(case, dict) or set(case) != {"id", "goal", "rubric"}:
            raise BehaviorEvidenceError(f"{path}: case 字段无效")
        identifier, goal, rubric = case["id"], case["goal"], case["rubric"]
        if (
            not isinstance(identifier, str)
            or not identifier
            or identifier in cases
            or not isinstance(goal, str)
            or not goal
            or not isinstance(rubric, list)
            or not rubric
            or any(not isinstance(item, str) or not item for item in rubric)
            or len(rubric) != len(set(rubric))
        ):
            raise BehaviorEvidenceError(f"{path}: case 定义无效：{identifier!r}")
        cases[identifier] = tuple(rubric)
    return cases


def validate_behavior_evidence(
    suite_path: Path, evidence_path: Path, *, require_complete: bool = False
) -> dict[str, object]:
    cases = validate_behavior_suite(suite_path)
    raw = _read_json(evidence_path)
    if not isinstance(raw, dict) or set(raw) != {
        "version", "suite_id", "generated_at", "runs"
    }:
        raise BehaviorEvidenceError(f"{evidence_path}: evidence 字段无效")
    if (
        raw["version"] != 1
        or raw["suite_id"] != "astra-instruction-following"
        or not isinstance(raw["generated_at"], str)
        or not raw["generated_at"]
        or not isinstance(raw["runs"], list)
    ):
        raise BehaviorEvidenceError(f"{evidence_path}: evidence 头无效")
    seen: set[str] = set()
    statuses: dict[str, int] = {status: 0 for status in sorted(RUN_STATUSES)}
    for run in raw["runs"]:
        if not isinstance(run, dict) or set(run) != RUN_FIELDS:
            raise BehaviorEvidenceError(f"{evidence_path}: run 字段无效")
        case_id = run["case_id"]
        if not isinstance(case_id, str) or case_id not in cases or case_id in seen:
            raise BehaviorEvidenceError(f"{evidence_path}: case_id 无效或重复：{case_id!r}")
        seen.add(case_id)
        status = run["status"]
        if status not in RUN_STATUSES:
            raise BehaviorEvidenceError(f"{evidence_path}: status 无效：{status!r}")
        for field in ("model", "host", "release_id", "session_id"):
            if not isinstance(run[field], str) or not run[field]:
                raise BehaviorEvidenceError(f"{evidence_path}: {case_id}.{field} 不能为空")
        if status in {"pass", "fail"} and run["model"] != "gpt-6-astra":
            raise BehaviorEvidenceError(f"{evidence_path}: {case_id} 不是 Astra 行为证据")
        if status in {"pass", "fail"} and not run["raw_output"]:
            raise BehaviorEvidenceError(f"{evidence_path}: {case_id} 缺少原始输出")
        if not isinstance(run["observations"], dict) or set(run["observations"]) != set(cases[case_id]):
            raise BehaviorEvidenceError(f"{evidence_path}: {case_id} rubric 观测不完整")
        observations = run["observations"]
        if any(value not in {True, False, "not-observed"} for value in observations.values()):
            raise BehaviorEvidenceError(f"{evidence_path}: {case_id} rubric 观测值无效")
        if status == "pass" and any(value is not True for value in observations.values()):
            raise BehaviorEvidenceError(f"{evidence_path}: {case_id} 标记 pass 但 rubric 未全部通过")
        if status == "fail" and not any(value is False for value in observations.values()):
            raise BehaviorEvidenceError(f"{evidence_path}: {case_id} 标记 fail 但没有失败观测")
        if not all(isinstance(run[field], list) for field in ("artifacts", "commands")):
            raise BehaviorEvidenceError(f"{evidence_path}: {case_id} artifacts/commands 无效")
        if any(
            not isinstance(item, str) or not item
            for field in ("artifacts", "commands")
            for item in run[field]
        ):
            raise BehaviorEvidenceError(f"{evidence_path}: {case_id} artifacts/commands 含空值")
        if not isinstance(run["limitation"], str):
            raise BehaviorEvidenceError(f"{evidence_path}: {case_id}.limitation 无效")
        statuses[status] += 1
    missing = sorted(set(cases) - seen)
    if require_complete and missing:
        raise BehaviorEvidenceError(
            f"{evidence_path}: 缺少行为场景：{', '.join(missing)}"
        )
    return {
        "status": "valid",
        "evidence_level": "fresh-agent-smoke",
        "runs": len(seen),
        "missing": missing,
        "statuses": statuses,
    }
