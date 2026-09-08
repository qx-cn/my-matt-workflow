"""Deterministic input freezing and reviewer discovery for parallel review."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


class ParallelReviewError(ValueError):
    """Raised when a parallel review plan cannot be built."""


def build_parallel_review_plan(
    governance_path: Path,
    artifacts: list[Path],
) -> dict[str, object]:
    if not artifacts:
        raise ParallelReviewError("并行 review 至少需要一个产物")
    try:
        governance = json.loads(governance_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ParallelReviewError(f"无法读取规则治理清单：{governance_path}") from exc

    lanes = []
    for document, rule in sorted(governance.get("documents", {}).items()):
        if isinstance(rule, dict) and rule.get("kind") == "reviewable-rule":
            lanes.append({"rule": document, "review_skill": rule["review_skill"]})
    if not lanes:
        raise ParallelReviewError("规则治理清单没有 reviewable-rule")

    digest = hashlib.sha256()
    frozen: list[dict[str, object]] = []
    for raw_path in artifacts:
        path = raw_path.resolve()
        if not path.is_file():
            raise ParallelReviewError(f"review 产物不存在：{raw_path}")
        content = path.read_bytes()
        digest.update(str(path).encode("utf-8"))
        digest.update(b"\0")
        digest.update(content)
        frozen.append(
            {
                "path": str(path),
                "sha256": hashlib.sha256(content).hexdigest(),
                "size": len(content),
            }
        )
    content_id = digest.hexdigest()
    return {
        "status": "ready",
        "content_id": content_id,
        "artifacts": frozen,
        "lanes": [{**lane, "content_id": content_id} for lane in lanes],
    }
