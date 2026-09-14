"""Pure rendering and validation for review repair plans."""

from __future__ import annotations

import re


_FINDING_HEADING = re.compile(
    r"^## Finding ([A-Za-z0-9][A-Za-z0-9._-]{0,127})$", re.MULTILINE
)
_REQUIRED_FIELDS = (
    "Acceptance IDs",
    "Root cause",
    "Change",
    "Verification",
    "Out of scope",
)


def render_repair_plan(findings: list[dict[str, object]]) -> str:
    """Render the sole mutable plan for the supplied current-Ticket findings."""
    sections: list[str] = ["# Repair plan", "", "仅修复以下当前 Ticket findings。"]
    for finding in findings:
        identifier = finding["id"]
        acceptance = ", ".join(str(value) for value in finding["acceptance_ids"])
        sections.extend([
            "",
            f"## Finding {identifier}",
            f"- Acceptance IDs: {acceptance}",
            f"- Root cause: {finding['root_cause']}",
            "- Change: ",
            "- Verification: ",
            "- Out of scope: ",
        ])
    return "\n".join(sections) + "\n"


def validate_repair_plan_text(
    text: str,
    expected_finding_ids: object,
    *,
    error_type: type[ValueError] = ValueError,
) -> None:
    """Require one complete decision section for every expected finding only."""
    identifiers = _FINDING_HEADING.findall(text)
    if (
        not isinstance(expected_finding_ids, list)
        or not all(isinstance(value, str) for value in expected_finding_ids)
        or sorted(identifiers) != sorted(expected_finding_ids)
        or len(identifiers) != len(set(identifiers))
    ):
        raise error_type("repair plan 必须逐项覆盖且仅覆盖当前 findings")
    for identifier in identifiers:
        section = re.search(
            rf"^## Finding {re.escape(identifier)}$([\s\S]*?)(?=^## Finding |\Z)",
            text,
            flags=re.MULTILINE,
        )
        if section is None or any(
            not re.search(rf"^- {field}: .+", section.group(1), flags=re.MULTILINE)
            for field in _REQUIRED_FIELDS
        ):
            raise error_type("repair plan finding 缺少必填决策")
