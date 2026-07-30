"""Create reviewable upstream-change bundles without merging them."""

from __future__ import annotations


def build_review_bundle(
    changes: dict[str, list[str]],
    adaptation_map: dict[str, list[str]],
) -> dict[str, dict]:
    """Map changed upstream files to sorted affected personal Skills."""
    return {
        upstream_skill: {
            "files": files,
            "affected_skills": sorted(adaptation_map.get(upstream_skill, [])),
            "decision": None,
        }
        for upstream_skill, files in sorted(changes.items())
    }
