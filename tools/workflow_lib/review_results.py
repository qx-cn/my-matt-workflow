"""Pure validation for semantic implementation review results."""

from __future__ import annotations

import re
from collections.abc import Callable


REVIEW_STATUSES = frozenset({"pass", "findings", "inconclusive", "blocked-by-design"})
REVIEW_SEVERITIES = frozenset({"P0", "P1", "P2"})
REVIEW_PROVENANCE_KINDS = frozenset({"self", "independent_session"})
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def _validate_self_review_coverage(
    unit: dict[str, object],
    coverage: object,
    validate_evidence_refs: Callable[[object], None],
    error_type: type[ValueError],
) -> None:
    if not isinstance(coverage, dict) or set(coverage) != {"acceptance", "probes"}:
        raise error_type("self review coverage schema 无效")
    boundary = unit.get("ticket_boundary")
    if not isinstance(boundary, dict):
        raise error_type("review Ticket boundary 无效")
    current = boundary.get("current")
    expected_acceptance = {
        item.get("id")
        for item in current.get("acceptance", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    } if isinstance(current, dict) else set()
    acceptance = coverage.get("acceptance")
    if not isinstance(acceptance, list):
        raise error_type("self review acceptance coverage 无效")
    seen_acceptance: set[str] = set()
    for item in acceptance:
        if not isinstance(item, dict) or set(item) != {"acceptance_id", "evidence_refs"}:
            raise error_type("self review acceptance 条目无效")
        identifier = item.get("acceptance_id")
        if not isinstance(identifier, str) or identifier in seen_acceptance:
            raise error_type("self review acceptance_id 重复或无效")
        seen_acceptance.add(identifier)
        validate_evidence_refs(item.get("evidence_refs"))
    if seen_acceptance != expected_acceptance:
        raise error_type("self review 未完整覆盖当前 Ticket 验收")

    expected_probes = set(boundary.get("required_probes", []))
    probes = coverage.get("probes")
    if not isinstance(probes, list):
        raise error_type("self review probe coverage 无效")
    seen_probes: set[str] = set()
    for item in probes:
        if not isinstance(item, dict) or set(item) != {"probe", "summary", "evidence_refs"}:
            raise error_type("self review probe 条目无效")
        probe = item.get("probe")
        if (
            not isinstance(probe, str)
            or probe in seen_probes
            or not isinstance(item.get("summary"), str)
            or not item["summary"].strip()
        ):
            raise error_type("self review probe 重复或无效")
        seen_probes.add(probe)
        validate_evidence_refs(item.get("evidence_refs"))
    if seen_probes != expected_probes:
        raise error_type("self review 未完整覆盖必需风险探针")


def validate_review_result(
    result: dict[str, object],
    unit: dict[str, object],
    code: dict[str, object],
    *,
    validate_evidence_refs: Callable[[object], None],
    error_type: type[ValueError] = ValueError,
) -> tuple[str, set[str]]:
    """Validate review semantics independently from journal persistence."""
    if set(result) != {
        "review_id", "status", "code_content_id", "reviewer_provenance", "findings",
        "follow_ons", "design_gap", "self_review_coverage",
    }:
        raise error_type("review result 字段无效")
    status = result.get("status")
    findings = result.get("findings")
    follow_ons = result.get("follow_ons")
    provenance = result.get("reviewer_provenance")
    if (
        status not in REVIEW_STATUSES
        or result.get("review_id") != unit.get("review_id")
        or result.get("code_content_id") != code.get("content_id")
        or not isinstance(findings, list)
        or not isinstance(follow_ons, list)
        or not isinstance(provenance, dict)
        or set(provenance) != {"kind", "session_id"}
        or provenance.get("kind") not in REVIEW_PROVENANCE_KINDS
        or not isinstance(provenance.get("session_id"), str)
        or not _SAFE_ID.fullmatch(str(provenance.get("session_id")))
    ):
        raise error_type("review result 与当前 review snapshot 不匹配")
    if provenance["kind"] == "self":
        if provenance["session_id"] != unit.get("implementation_session_id"):
            raise error_type("self review 必须使用当前 implementation session")
        _validate_self_review_coverage(
            unit, result.get("self_review_coverage"), validate_evidence_refs, error_type
        )
    elif (
        provenance["session_id"] == unit.get("implementation_session_id")
        or result.get("self_review_coverage") is not None
    ):
        raise error_type("independent session provenance 或 coverage 无效")

    boundary = unit.get("ticket_boundary")
    current = boundary.get("current") if isinstance(boundary, dict) else None
    acceptance_ids = {
        item.get("id")
        for item in current.get("acceptance", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    } if isinstance(current, dict) else set()
    successors = {
        item.get("id"): {
            entry.get("id")
            for entry in item.get("acceptance", [])
            if isinstance(entry, dict) and isinstance(entry.get("id"), str)
        }
        for item in boundary.get("successors", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    } if isinstance(boundary, dict) else {}
    for item in follow_ons:
        if not isinstance(item, dict) or set(item) != {
            "id", "root_cause", "owner_ticket_id", "acceptance_ids", "summary", "baseline_reachable"
        }:
            raise error_type("review follow-on schema 无效")
        owner = item.get("owner_ticket_id")
        refs = item.get("acceptance_ids")
        if (
            not all(
                isinstance(item.get(field), str) and str(item[field]).strip()
                for field in ("id", "root_cause", "summary")
            )
            or owner not in successors
            or not isinstance(refs, list)
            or not refs
            or not all(isinstance(ref, str) for ref in refs)
            or not set(refs).issubset(successors[owner])
            or item.get("baseline_reachable") not in {True, False}
        ):
            raise error_type("review follow-on 不属于当前 Ticket 的直接下游")

    design_gap = result.get("design_gap")
    if status == "blocked-by-design":
        if (
            findings
            or follow_ons
            or not isinstance(design_gap, dict)
            or set(design_gap) != {"root_cause", "summary", "evidence_refs"}
        ):
            raise error_type("design gap review result 无效")
        if not all(
            isinstance(design_gap.get(field), str) and str(design_gap[field]).strip()
            for field in ("root_cause", "summary")
        ):
            raise error_type("design gap 缺少根因或摘要")
        validate_evidence_refs(design_gap.get("evidence_refs"))
        return str(status), {str(design_gap["root_cause"])}
    if design_gap is not None:
        raise error_type("仅 blocked-by-design review 可包含 design_gap")
    if status == "pass":
        if findings:
            raise error_type("pass review 不得包含 findings")
        return str(status), set()
    if not findings:
        raise error_type(f"{status} review 必须包含结构化条目")

    roots: set[str] = set()
    for item in findings:
        if not isinstance(item, dict) or set(item) != {
            "id", "root_cause", "severity", "summary", "baseline_reachable", "acceptance_ids"
        }:
            raise error_type("review finding schema 无效")
        if not all(
            isinstance(item.get(field), str) and str(item[field]).strip()
            for field in ("id", "root_cause", "summary")
        ):
            raise error_type("review finding 缺少 id、root_cause 或 summary")
        item_acceptance = item.get("acceptance_ids")
        if (
            not isinstance(item_acceptance, list)
            or not item_acceptance
            or not all(isinstance(value, str) for value in item_acceptance)
            or not set(item_acceptance).issubset(acceptance_ids)
        ):
            raise error_type("review finding 必须引用当前 Ticket 验收")
        if status == "findings":
            if item.get("severity") not in REVIEW_SEVERITIES:
                raise error_type("review finding severity 无效")
            if item.get("baseline_reachable") is not True:
                raise error_type(
                    "review finding 必须能从固定基线到当前快照证明；否则标记 inconclusive"
                )
        elif (
            item.get("severity") is not None
            or item.get("baseline_reachable") not in {None, False}
        ):
            raise error_type("inconclusive 条目不得伪造 severity 或基线可达性")
        roots.add(str(item["root_cause"]))
    return str(status), roots
