"""Strict definitions and records for real fresh-agent behavior evidence."""

from __future__ import annotations

import json
import hashlib
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

EXECUTION_REGISTRY_FIELDS = {"version", "records"}
EXECUTION_RECORD_FIELDS = {"evidence_path", "sha256"}


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
    release_ids: set[str] = set()
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
        release_ids.add(run["release_id"])
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
        "release_ids": sorted(release_ids),
    }


def validate_execution_evidence_registry(
    root: Path, registry_path: Path, suite_path: Path
) -> dict[str, object]:
    """Validate checked-in indexes of actual behavior runs without inventing evidence."""
    source_root = root.resolve()
    raw = _read_json(registry_path)
    if not isinstance(raw, dict) or set(raw) != EXECUTION_REGISTRY_FIELDS:
        raise BehaviorEvidenceError(f"{registry_path}: execution registry 字段无效")
    records = raw["records"]
    if raw["version"] != 1 or not isinstance(records, list):
        raise BehaviorEvidenceError(f"{registry_path}: execution registry 版本或 records 无效")

    reports: list[dict[str, object]] = []
    seen: set[str] = set()
    for record in records:
        if not isinstance(record, dict) or set(record) != EXECUTION_RECORD_FIELDS:
            raise BehaviorEvidenceError(f"{registry_path}: execution record 字段无效")
        relative = record["evidence_path"]
        digest = record["sha256"]
        if (
            not isinstance(relative, str)
            or not relative
            or relative in seen
            or Path(relative).is_absolute()
            or not isinstance(digest, str)
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
        ):
            raise BehaviorEvidenceError(f"{registry_path}: execution record 标识无效")
        evidence_path = (source_root / relative).resolve()
        try:
            evidence_path.relative_to(source_root)
        except ValueError as exc:
            raise BehaviorEvidenceError(
                f"{registry_path}: evidence_path 越出仓库：{relative}"
            ) from exc
        if not evidence_path.is_file():
            raise BehaviorEvidenceError(f"{registry_path}: evidence 文件不存在：{relative}")
        actual = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
        if actual != digest:
            raise BehaviorEvidenceError(f"{registry_path}: evidence digest 不匹配：{relative}")
        report = validate_behavior_evidence(suite_path, evidence_path)
        if report["runs"] == 0:
            raise BehaviorEvidenceError(
                f"{registry_path}: execution evidence 不含运行记录：{relative}"
            )
        reports.append({"evidence_path": relative, "sha256": digest, **report})
        seen.add(relative)

    release_ids = sorted({
        release_id
        for report in reports
        for release_id in report["release_ids"]
    })
    return {
        "status": "valid" if reports else "not-recorded",
        "evidence_level": "fresh-agent-execution",
        "release_ids": release_ids,
        "release_relation": "unbound" if reports else "not-recorded",
        "records": reports,
    }


def execution_evidence_release_relation(
    report: dict[str, object], current_release_id: str | None
) -> str:
    """Classify actual execution records against the selected current release."""
    release_ids = report.get("release_ids")
    if report.get("status") == "not-recorded":
        return "not-recorded"
    if not isinstance(release_ids, list) or not all(
        isinstance(value, str) and value for value in release_ids
    ):
        raise BehaviorEvidenceError("execution evidence release_ids 无效")
    if current_release_id is None:
        return "unbound"
    releases = set(release_ids)
    if releases == {current_release_id}:
        return "current"
    if current_release_id in releases:
        return "mixed"
    return "historical"
