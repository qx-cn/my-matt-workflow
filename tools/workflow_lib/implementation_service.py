"""Application-level next-action decisions for implementation sessions."""

from __future__ import annotations


def next_implementation_action(
    journal: dict[str, object], *, error_type: type[ValueError] = ValueError
) -> dict[str, object]:
    """Return the one coarse action allowed by durable session state."""
    phase = journal.get("phase")
    submission = journal.get("submission")
    active = journal.get("active_review")
    recovery = journal.get("recovery")
    repair = journal.get("repair_plan")
    if isinstance(submission, dict):
        action = (
            "complete"
            if submission.get("outcome") == "completed"
            else "formal-blocked"
        )
    elif phase == "complete":
        action = "complete"
    elif phase == "reviewing":
        if isinstance(active, dict):
            action = "correct-review-result" if isinstance(recovery, dict) else "submit-review-result"
        else:
            action = "open-review"
    elif phase == "planning":
        action = (
            "review-repair-plan"
            if isinstance(repair, dict) and repair.get("path")
            else "create-repair-plan"
        )
    elif phase == "plan-reviewing":
        action = "review-repair-plan"
    elif phase == "implementing":
        action = (
            "fix-approved-findings"
            if isinstance(repair, dict) and repair.get("review_receipt")
            else "continue-implementation"
        )
    elif phase == "committing":
        action = "submit-completed"
    elif phase in {"admitted", "testing", "revising", "blocked-by-evidence"}:
        action = "continue-implementation"
    elif phase == "blocked-by-design":
        action = "formal-blocked" if journal.get("blocker") else "continue-implementation"
    else:
        raise error_type("run journal phase 无效")
    return {
        "status": "active" if action not in {"complete", "formal-blocked"} else action,
        "phase": phase,
        "next_action": action,
        "next_gate": action,
        "active_review": active,
        "recovery": recovery,
    }
