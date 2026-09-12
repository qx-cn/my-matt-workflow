"""Immutable artifact snapshots for review."""

from __future__ import annotations

import hashlib
import json
import tempfile
from pathlib import Path

from .fs_safety import (
    FilesystemSafetyError,
    exclusive_lock,
    quarantine_and_remove,
    register_owned_directory,
    verify_owned_directory,
)


class ArtifactReviewError(ValueError):
    """Raised when an artifact review snapshot cannot be built or verified."""


_SNAPSHOT_PREFIX = "my-matt-review-"
_UNIT_FILE = ".review-unit.json"
REQUIRED_REVIEW_CHECKS = (
    "my-final-state-writing",
    "my-reader-first-writing",
    "my-visual-communication",
    "my-humanizer",
    "my-artifact-finalization",
)
ARTIFACT_REQUIRED_CHECKS = {
    "general": REQUIRED_REVIEW_CHECKS,
    "design": REQUIRED_REVIEW_CHECKS + ("my-review-design",),
    "repair-plan": ("my-review-design",),
}
ARTIFACT_KINDS = frozenset(ARTIFACT_REQUIRED_CHECKS)
REVIEW_CHECK_STATUSES = frozenset(
    {"pass", "finding", "inconclusive", "not-applicable"}
)


def required_checks_for_artifact_kind(artifact_kind: str) -> tuple[str, ...]:
    """Return the sole declared review-method set for one artifact kind."""
    try:
        return ARTIFACT_REQUIRED_CHECKS[artifact_kind]
    except KeyError as exc:
        raise ArtifactReviewError(f"未知 artifact kind：{artifact_kind}") from exc


def _read_artifacts(artifacts: list[Path]) -> tuple[str, list[tuple[Path, bytes]]]:
    if not artifacts:
        raise ArtifactReviewError("产物 review 至少需要一个文件")

    digest = hashlib.sha256()
    captured: list[tuple[Path, bytes]] = []
    paths = sorted({raw_path.resolve() for raw_path in artifacts}, key=str)
    for path in paths:
        if not path.is_file():
            raise ArtifactReviewError(f"review 产物不存在：{path}")
        try:
            content = path.read_bytes()
        except OSError as exc:
            raise ArtifactReviewError(f"无法读取 review 产物：{path}") from exc
        digest.update(str(path).encode("utf-8"))
        digest.update(b"\0")
        digest.update(content)
        captured.append((path, content))
    return digest.hexdigest(), captured


def build_artifact_review_snapshot(
    artifacts: list[Path],
    *,
    snapshot_root: Path | None = None,
    parallel: bool = False,
    artifact_kind: str = "general",
) -> dict[str, object]:
    """Capture one immutable byte copy for every reviewer to consume."""
    required_checks = required_checks_for_artifact_kind(artifact_kind)
    content_id, captured = _read_artifacts(artifacts)
    snapshot_root = (
        snapshot_root.resolve()
        if snapshot_root is not None
        else Path(tempfile.gettempdir()) / "my-matt-review-snapshots"
    )
    snapshot_root.mkdir(parents=True, exist_ok=True)
    try:
        directory = Path(
            tempfile.mkdtemp(
                prefix=f"{_SNAPSHOT_PREFIX}{content_id[:12]}-",
                dir=str(snapshot_root),
            )
        )
    except OSError as exc:
        raise ArtifactReviewError("无法创建 review snapshot") from exc
    frozen: list[dict[str, object]] = []
    for index, (source, content) in enumerate(captured):
        snapshot = directory / f"{index:03d}-{source.name}"
        try:
            snapshot.write_bytes(content)
            snapshot.chmod(0o400)
        except OSError as exc:
            raise ArtifactReviewError(f"无法写入 review snapshot：{snapshot}") from exc
        frozen.append(
            {
                "source_path": str(source),
                "snapshot_path": str(snapshot),
                "sha256": hashlib.sha256(content).hexdigest(),
                "size": len(content),
            }
        )
    lanes = [
        {
            "lane_id": check,
            "method": check,
            "depends_on": [] if parallel or index == 0 else [required_checks[index - 1]],
        }
        for index, check in enumerate(required_checks)
    ]
    unit = {
        "content_id": content_id,
        "artifact_kind": artifact_kind,
        "artifacts": frozen,
        "execution_mode": "parallel" if parallel else "serial",
        "required_checks": list(required_checks),
        "dispatch": {"mode": "parallel" if parallel else "serial", "lanes": lanes},
    }
    try:
        marker = directory / _UNIT_FILE
        marker.write_text(json.dumps(unit, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        marker.chmod(0o400)
        directory.chmod(0o500)
        register_owned_directory(
            snapshot_root, directory, purpose="artifact-review-snapshot"
        )
    except (OSError, FilesystemSafetyError) as exc:
        raise ArtifactReviewError(f"无法保护 review snapshot：{directory}") from exc
    return {
        "status": "ready",
        "content_id": content_id,
        "snapshot_dir": str(directory),
        "artifacts": frozen,
        "review_unit": unit,
    }


def verify_artifact_review_snapshot(
    artifacts: list[Path], expected_content_id: str
) -> dict[str, object]:
    """Compare live sources with the content captured for review."""
    content_id, _ = _read_artifacts(artifacts)
    return {
        "status": "match" if content_id == expected_content_id else "stale",
        "content_id": content_id,
        "expected_content_id": expected_content_id,
    }


def finalize_artifact_review_snapshot(
    artifacts: list[Path], expected_content_id: str, snapshot_dir: Path
) -> dict[str, object]:
    """Verify a review unit against its sources, then release its private snapshot."""
    directory = snapshot_dir.resolve()
    if not directory.is_dir() or not directory.name.startswith(_SNAPSHOT_PREFIX):
        raise ArtifactReviewError("无效的 review snapshot 目录")
    snapshot_root = directory.parent
    try:
        verify_owned_directory(
            snapshot_root, directory, purpose="artifact-review-snapshot"
        )
    except FilesystemSafetyError as exc:
        raise ArtifactReviewError("review snapshot 缺少可信 ownership capability") from exc
    marker = directory / _UNIT_FILE
    try:
        unit = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ArtifactReviewError("review snapshot 缺少有效生命周期标记") from exc
    if not isinstance(unit, dict) or unit.get("content_id") != expected_content_id:
        raise ArtifactReviewError("review snapshot 与 content_id 不匹配")
    frozen = unit.get("artifacts")
    if not isinstance(frozen, list) or not frozen:
        raise ArtifactReviewError("review snapshot inventory 无效")
    try:
        for entry in frozen:
            if not isinstance(entry, dict) or set(entry) != {
                "source_path", "snapshot_path", "sha256", "size"
            }:
                raise ArtifactReviewError("review snapshot inventory 无效")
            snapshot = Path(str(entry["snapshot_path"]))
            if snapshot.parent.resolve() != directory or not snapshot.is_file():
                raise ArtifactReviewError("review snapshot inventory 路径无效")
            content = snapshot.read_bytes()
            if (
                len(content) != entry["size"]
                or hashlib.sha256(content).hexdigest() != entry["sha256"]
            ):
                raise ArtifactReviewError("review snapshot bytes 已漂移")
    except OSError as exc:
        raise ArtifactReviewError("无法验证 review snapshot bytes") from exc
    verification: dict[str, object] | None = None
    verification_error: ArtifactReviewError | None = None
    try:
        verification = verify_artifact_review_snapshot(artifacts, expected_content_id)
    except ArtifactReviewError as exc:
        verification_error = exc
    try:
        with exclusive_lock(snapshot_root, "artifact-review"):
            directory.chmod(0o700)
            quarantine_and_remove(
                snapshot_root, directory, purpose="artifact-review-snapshot"
            )
    except (OSError, FilesystemSafetyError) as exc:
        raise ArtifactReviewError("无法释放 review snapshot") from exc
    if verification_error is not None:
        raise ArtifactReviewError(f"{verification_error}；review snapshot 已释放")
    assert verification is not None
    return {**verification, "released": True}


def _validate_review_items(
    items: object,
    *,
    label: str,
    allowed_checks: set[str],
) -> set[str]:
    if not isinstance(items, list):
        raise ArtifactReviewError(f"artifact review result.{label} 必须是列表")
    covered: set[str] = set()
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("checks"), list):
            raise ArtifactReviewError(f"artifact review result.{label} 项必须包含 checks")
        checks = item["checks"]
        if not checks or not all(isinstance(check, str) for check in checks):
            raise ArtifactReviewError(f"artifact review result.{label}.checks 无效")
        unknown = set(checks) - allowed_checks
        if unknown:
            raise ArtifactReviewError(
                f"artifact review result.{label} 包含未知 check：{', '.join(sorted(unknown))}"
            )
        covered.update(checks)
    return covered


def submit_artifact_review_result(
    artifacts: list[Path], snapshot_dir: Path, result: dict[str, object]
) -> dict[str, object]:
    """Require complete method closure, then verify and release the snapshot."""
    expected_fields = {"content_id", "checks", "findings", "inconclusive"}
    if set(result) != expected_fields:
        raise ArtifactReviewError("artifact review result 字段无效")
    directory = snapshot_dir.resolve()
    marker = directory / _UNIT_FILE
    try:
        unit = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ArtifactReviewError("review snapshot 缺少有效生命周期标记") from exc
    if not isinstance(unit, dict) or result.get("content_id") != unit.get("content_id"):
        raise ArtifactReviewError("artifact review result 与 review_unit content_id 不匹配")
    required = unit.get("required_checks")
    checks = result.get("checks")
    if not isinstance(required, list) or not all(isinstance(item, str) for item in required):
        raise ArtifactReviewError("review_unit.required_checks 无效")
    if not isinstance(checks, dict) or set(checks) != set(required):
        raise ArtifactReviewError("artifact review result 必须完整覆盖 required_checks")
    invalid_entries = {
        check
        for check, entry in checks.items()
        if not isinstance(entry, dict)
        or set(entry) != {"status", "reason"}
        or entry.get("status") not in REVIEW_CHECK_STATUSES
    }
    if invalid_entries:
        raise ArtifactReviewError(
            f"artifact review check entry 无效：{', '.join(sorted(invalid_entries))}"
        )
    missing_reasons = {
        check
        for check, entry in checks.items()
        if entry["status"] == "not-applicable"
        and (not isinstance(entry["reason"], str) or not entry["reason"].strip())
    }
    if missing_reasons:
        raise ArtifactReviewError(
            "not-applicable check 必须说明 reason：" + ", ".join(sorted(missing_reasons))
        )
    finding_checks = {
        check for check, entry in checks.items() if entry["status"] == "finding"
    }
    inconclusive_checks = {
        check for check, entry in checks.items() if entry["status"] == "inconclusive"
    }
    covered_findings = _validate_review_items(
        result.get("findings"), label="findings", allowed_checks=finding_checks
    )
    covered_inconclusive = _validate_review_items(
        result.get("inconclusive"),
        label="inconclusive",
        allowed_checks=inconclusive_checks,
    )
    if covered_findings != finding_checks:
        raise ArtifactReviewError("finding 状态必须由 findings 完整解释")
    if covered_inconclusive != inconclusive_checks:
        raise ArtifactReviewError("inconclusive 状态必须由 inconclusive 项完整解释")
    verification = finalize_artifact_review_snapshot(
        artifacts, str(result["content_id"]), directory
    )
    return {
        "status": "accepted" if verification["status"] == "match" else "stale",
        "content_id": result["content_id"],
        "checks": checks,
        "findings": result["findings"],
        "inconclusive": result["inconclusive"],
        "released": verification["released"],
    }
