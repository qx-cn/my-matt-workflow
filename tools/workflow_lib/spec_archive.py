"""Promote a reviewed, complete local Topic Spec to a readable long-term Spec."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

from .fs_safety import FilesystemSafetyError, _tree_digest, exclusive_lock, strict_relative_path
from .lifecycle import LifecycleError, topic_lifecycle_lock
from .run_journal import RunJournalError, validate_completed_run_history
from .tickets import (
    TicketError, _unchecked_acceptance, frontmatter, ticket_definition_receipt,
    validate_spec_lineage,
)
from .work_overview import WorkOverviewError, work_overview


class SpecArchiveError(ValueError):
    """A canonical Spec cannot be published safely."""


_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")


def _safe_child(root: Path, name: str) -> Path:
    if not _NAME.fullmatch(name):
        raise SpecArchiveError("名称必须是小写 kebab-case")
    try:
        return strict_relative_path(root, name, direct_child=True)
    except FilesystemSafetyError as exc:
        raise SpecArchiveError(str(exc)) from exc


def _ordinary_file(path: Path) -> bool:
    return path.is_file() and not path.is_symlink()


def _atomic_bytes(path: Path, payload: bytes) -> None:
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.",
                                         suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def archive_spec(repo: Path, topic: str, spec_id: str, *, apply: bool = False,
                 expected_sha256: str | None = None,
                 expected_previous_sha256: str | None = None) -> dict[str, object]:
    """Preview or publish a reviewed full-current Spec from a completed Topic.

    The candidate is kept with the Topic at ``archive/canonical-spec.md``. The
    command validates provenance and version order; semantic merging requires
    review of the candidate against the previous canonical and Topic Spec.
    """
    repo = repo.resolve()
    agent = repo / ".agent"
    if agent.is_symlink() or not agent.is_dir():
        raise SpecArchiveError(".agent 必须是普通目录")
    work = agent / "work"
    if work.is_symlink() or not work.is_dir():
        raise SpecArchiveError(".agent/work 必须是普通目录")
    topic_dir = _safe_child(work, topic)
    identifier = _safe_child(agent / "specs", spec_id)
    if not topic_dir.is_dir():
        raise SpecArchiveError(f"Topic 不存在：{topic}")
    try:
        initial_topic_digest = _tree_digest(topic_dir)
    except FilesystemSafetyError as exc:
        raise SpecArchiveError(str(exc)) from exc
    try:
        overview = work_overview(repo, topic=topic)
    except WorkOverviewError as exc:
        raise SpecArchiveError(str(exc)) from exc
    if overview["status"] != "ok":
        raise SpecArchiveError("Topic 存在不一致状态，不能归档 Spec")
    item = overview["topics"][0]
    tickets = item["tickets"]
    if not tickets or any(ticket["status"] != "complete" for ticket in tickets):
        raise SpecArchiveError("Topic 必须有 Ticket 且全部为 complete")
    if any(session["active"] for session in item["sessions"]):
        raise SpecArchiveError("Topic 仍有活动实施会话")
    sources = [spec for spec in item["specs"] if spec["spec_id"] == spec_id]
    if len(sources) != 1 or not sources[0]["is_current"]:
        raise SpecArchiveError("Topic 必须有唯一的 current 来源 Spec")
    if len(item["specs"]) != 1:
        raise SpecArchiveError("一个 Topic 只能包含一个 Spec id，需先拆分混合 Topic")
    source = repo / str(sources[0]["path"])
    if not _ordinary_file(source):
        raise SpecArchiveError("来源 Spec 不是普通文件")
    matching_current_tickets = []
    implementation_sources: dict[str, dict[str, object]] = {}
    for ticket in tickets:
        ticket_path = repo / str(ticket["path"])
        try:
            ticket_meta = frontmatter(ticket_path)
            lineage = validate_spec_lineage(ticket_path, ticket_meta)
        except (OSError, TicketError) as exc:
            raise SpecArchiveError(f"Ticket 血缘无效：{ticket['path']}：{exc}") from exc
        if _unchecked_acceptance(ticket_path):
            raise SpecArchiveError(f"Ticket 验收项尚未全部完成：{ticket['path']}")
        if ticket_meta.get("ticket_kind") != "implementation" or lineage is None:
            raise SpecArchiveError(f"Ticket 缺少实施类型或本地 Spec 血缘：{ticket['path']}")
        implementation_sources[str(ticket["id"])] = {
            "spec_id": lineage["spec_id"], "revision": lineage["revision"],
            "ref": ticket_meta["spec_ref"],
            "sha256": hashlib.sha256(Path(str(lineage["path"])).read_bytes()).hexdigest(),
            "ticket_definition_sha256": ticket_definition_receipt(ticket_path)["sha256"],
        }
        if (ticket_meta.get("spec_id") == spec_id
                and lineage["revision"] == sources[0]["revision"]
                and lineage["path"] == str(source)):
            matching_current_tickets.append(ticket["path"])
    if not matching_current_tickets:
        raise SpecArchiveError("当前来源 Spec revision 没有已完成且血缘匹配的 Ticket")
    source_digest = hashlib.sha256(source.read_bytes()).hexdigest()
    completed_evidence: dict[str, str] = {}
    for session in item["sessions"]:
        ticket_id = str(session["ticket_id"])
        expected = implementation_sources.get(ticket_id)
        if expected is None or session["submission_outcome"] != "completed":
            continue
        journal_path = repo / str(session["path"])
        try:
            journal = json.loads(journal_path.read_text(encoding="utf-8"))
            context = journal["context"]
            frozen_spec = context["spec"]
            frozen_ticket = context["ticket"]
            if (
                context["repo"] == str(repo)
                and context["topic"] == topic
                and frozen_ticket["id"] == ticket_id
                and frozen_spec["id"] == expected["spec_id"]
                and int(frozen_spec["revision"]) == expected["revision"]
                and frozen_spec["ref"] == expected["ref"]
                and frozen_spec["content"]["sha256"] == expected["sha256"]
                and frozen_ticket["definition"]["sha256"] == expected["ticket_definition_sha256"]
                and journal["phase"] == "complete"
                and journal["submission"]["outcome"] == "completed"
            ):
                validate_completed_run_history(journal_path)
                completed_evidence[ticket_id] = str(session["path"])
        except (OSError, ValueError, KeyError, TypeError, AttributeError, RunJournalError):
            continue
    missing_evidence = set(implementation_sources) - set(completed_evidence)
    if missing_evidence:
        raise SpecArchiveError(
            "以下 Ticket 缺少与来源 Spec 哈希匹配的已完成实施会话："
            + ", ".join(sorted(missing_evidence))
        )
    draft_dir = topic_dir / "archive"
    if draft_dir.is_symlink():
        raise SpecArchiveError("Topic archive 目录不能是符号链接")
    candidate = draft_dir / "canonical-spec.md"
    if not _ordinary_file(candidate):
        raise SpecArchiveError("缺少 archive/canonical-spec.md 候选长期 Spec")
    try:
        metadata = frontmatter(candidate)
    except (OSError, TicketError) as exc:
        raise SpecArchiveError(f"候选长期 Spec frontmatter 无效：{exc}") from exc
    if metadata.get("spec_id") != spec_id or metadata.get("status") != "current":
        raise SpecArchiveError("候选长期 Spec 的 spec_id/status 不匹配")
    if metadata.get("source_topic") != topic or str(metadata.get("source_spec_revision")) != str(sources[0]["revision"]):
        raise SpecArchiveError("候选长期 Spec 的来源 Topic/Spec revision 不匹配")
    if metadata.get("source_spec_sha256") != source_digest:
        raise SpecArchiveError("来源 Spec 已改变，须重新合并与审查")
    candidate_lines = candidate.read_text(encoding="utf-8").splitlines()
    frontmatter_end = candidate_lines.index("---", 1)
    if not "\n".join(candidate_lines[frontmatter_end + 1:]).strip():
        raise SpecArchiveError("候选长期 Spec 正文不能为空")
    canonical_root = agent / "specs"
    if canonical_root.is_symlink() or (canonical_root.exists() and not canonical_root.is_dir()):
        raise SpecArchiveError("长期 Spec 目标必须是普通目录")
    canonical = identifier.with_suffix(".md")
    if canonical.is_symlink() or (canonical.exists() and not canonical.is_file()):
        raise SpecArchiveError("长期 Spec 目标不是普通文件")
    previous_payload = canonical.read_bytes() if canonical.exists() else None
    try:
        previous = frontmatter(canonical) if previous_payload is not None else None
    except (OSError, TicketError) as exc:
        raise SpecArchiveError(f"现有长期 Spec frontmatter 无效：{exc}") from exc
    old_revision = 0
    if previous is not None:
        if previous.get("spec_id") != spec_id or previous.get("status") != "current":
            raise SpecArchiveError("现有长期 Spec 元数据无效")
        try:
            old_revision = int(str(previous["revision"]))
        except (KeyError, ValueError) as exc:
            raise SpecArchiveError("现有长期 Spec revision 无效") from exc
    already_current = previous is not None and previous.get("source_topic") == topic
    history_root = canonical_root / "history"
    if history_root.is_symlink() or (history_root.exists() and not history_root.is_dir()):
        raise SpecArchiveError("长期 Spec 历史目标必须是普通目录")
    history_dir = _safe_child(history_root, spec_id)
    if history_dir.is_symlink() or (history_dir.exists() and not history_dir.is_dir()):
        raise SpecArchiveError("长期 Spec 历史主题必须是普通目录")
    if history_dir.is_dir():
        for old_path in history_dir.glob("*.md"):
            if not _ordinary_file(old_path):
                raise SpecArchiveError("长期 Spec 历史含非普通文件")
            try:
                old_meta = frontmatter(old_path)
            except (OSError, TicketError) as exc:
                raise SpecArchiveError(f"长期 Spec 历史无效：{old_path}：{exc}") from exc
            if old_meta.get("source_topic") == topic:
                raise SpecArchiveError("该 Topic 已发布到这个长期 Spec，不能重复发布")
    try:
        candidate_revision = int(str(metadata["revision"]))
    except (KeyError, ValueError) as exc:
        raise SpecArchiveError("候选长期 Spec revision 无效") from exc
    if candidate_revision != old_revision + (0 if already_current else 1):
        raise SpecArchiveError(
            f"候选长期 Spec revision 必须为 {old_revision + (0 if already_current else 1)}"
        )
    prior_revision = old_revision - 1 if already_current else old_revision
    history_ref = f".agent/specs/history/{spec_id}/{prior_revision}.md"
    if prior_revision and metadata.get("supersedes") != history_ref:
        raise SpecArchiveError("候选长期 Spec 必须用 supersedes 指向即将保存的不可变旧版")
    if not prior_revision and metadata.get("supersedes") not in {"", None}:
        raise SpecArchiveError("首次长期 Spec 的 supersedes 必须为空")
    payload = candidate.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    seal = draft_dir / "publication.json"
    if seal.is_symlink():
        raise SpecArchiveError("Topic 发布记录不能是符号链接")
    seal_record = None
    if seal.exists():
        try:
            seal_record = json.loads(seal.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise SpecArchiveError("Topic 发布记录无效") from exc
    previous_digest = (
        str(seal_record.get("previous_sha256")) if isinstance(seal_record, dict)
        else hashlib.sha256(previous_payload).hexdigest() if previous_payload else "none"
    )
    seal_base = {
        "schema_version": 1, "topic": topic, "spec_id": spec_id,
        "source_sha256": source_digest, "candidate_sha256": digest,
        "previous_sha256": previous_digest, "revision": candidate_revision,
        "ticket_definitions": {
            ticket_id: source_info["ticket_definition_sha256"]
            for ticket_id, source_info in sorted(implementation_sources.items())
        },
        "completed_journals": {
            ticket_id: {
                "path": completed_evidence[ticket_id],
                "sha256": hashlib.sha256((repo / completed_evidence[ticket_id]).read_bytes()).hexdigest(),
            }
            for ticket_id in sorted(completed_evidence)
        },
    }
    if seal_record is not None and (
        not isinstance(seal_record, dict)
        or {key: value for key, value in seal_record.items() if key != "status"} != seal_base
        or seal_record.get("status") not in {"publishing", "published"}
    ):
        raise SpecArchiveError("Topic 发布记录与当前来源或候选不匹配")
    if already_current and (
        seal_record is None or hashlib.sha256(previous_payload or b"").hexdigest() != digest
    ):
        raise SpecArchiveError("该 Topic 已发布到这个长期 Spec，不能重复发布")
    if seal_record is not None and not already_current and previous_digest != (
        hashlib.sha256(previous_payload).hexdigest() if previous_payload else "none"
    ):
        raise SpecArchiveError("长期 Spec 与封存中的旧版哈希不一致")
    if seal_record is not None and seal_record["status"] == "published" and not already_current:
        raise SpecArchiveError("Topic 标记已发布，但长期 Spec 不匹配")
    review_record = draft_dir / "spec-review.json"
    review_report = draft_dir / "spec-review.md"
    review_ready = False
    if review_record.is_symlink() or review_report.is_symlink():
        raise SpecArchiveError("Spec 审查记录不能是符号链接")
    if _ordinary_file(review_record) and _ordinary_file(review_report):
        try:
            review = json.loads(review_record.read_text(encoding="utf-8"))
            review_ready = (
                isinstance(review, dict)
                and review.get("schema_version") == 1
                and isinstance(review.get("reviewer"), str)
                and bool(review["reviewer"].strip())
                and review.get("verdict") == "No findings."
                and review.get("source_sha256") == source_digest
                and review.get("previous_sha256") == previous_digest
                and review.get("candidate_sha256") == digest
                and review.get("report_sha256") == hashlib.sha256(review_report.read_bytes()).hexdigest()
                and "No findings." in review_report.read_text(encoding="utf-8")
            )
        except (OSError, ValueError, UnicodeError):
            review_ready = False
    publishing_payload = json.dumps({**seal_base, "status": "publishing"}, ensure_ascii=False, sort_keys=True).encode("utf-8") + b"\n"
    published_payload = json.dumps({**seal_base, "status": "published"}, ensure_ascii=False, sort_keys=True).encode("utf-8") + b"\n"
    report: dict[str, object] = {
        "status": "ready" if review_ready else "needs-review",
        "topic": topic, "spec_id": spec_id,
        "source_spec": str(sources[0]["path"]), "source_sha256": source_digest,
        "completed_evidence": completed_evidence,
        "candidate": str(candidate.relative_to(repo)), "candidate_sha256": digest,
        "canonical": str(canonical.relative_to(repo)), "revision": candidate_revision,
        "previous_revision": prior_revision,
        "previous_sha256": previous_digest,
        "topic_seal": str(seal.relative_to(repo)),
        "review_record": str(review_record.relative_to(repo)),
        "applied": False,
    }
    try:
        if _tree_digest(topic_dir) != initial_topic_digest:
            raise SpecArchiveError("Topic 在准入检查期间发生变化，请重新预览")
    except FilesystemSafetyError as exc:
        raise SpecArchiveError(str(exc)) from exc
    if not apply:
        if already_current:
            report["status"] = "published" if seal_record and seal_record["status"] == "published" else "recoverable"
        return report
    if already_current and seal_record and seal_record["status"] == "published":
        raise SpecArchiveError("该 Topic 已发布，不能重复发布")
    if not review_ready:
        raise SpecArchiveError("发布前需要绑定当前候选、来源和旧版哈希的独立审查记录")
    if expected_sha256 != digest:
        raise SpecArchiveError("--apply 需要与预览一致的 --expected-sha256")
    if expected_previous_sha256 != previous_digest:
        raise SpecArchiveError("--apply 需要与预览一致的 --expected-previous-sha256（首次为 none）")
    try:
        with topic_lifecycle_lock(repo, topic, exclusive=True):
            with exclusive_lock(agent, "canonical-spec"):
                if work_overview(repo, topic=topic) != overview:
                    raise SpecArchiveError("Topic 状态在预览后发生变化，请重新预览")
                if _tree_digest(topic_dir) != initial_topic_digest:
                    raise SpecArchiveError("Topic 文件在预览后发生变化，请重新预览")
                if (canonical.read_bytes() if canonical.exists() else None) != previous_payload:
                    raise SpecArchiveError("长期 Spec 在写入前发生变化")
                if hashlib.sha256(source.read_bytes()).hexdigest() != source_digest:
                    raise SpecArchiveError("来源 Spec 在写入前发生变化")
                if candidate.read_bytes() != payload:
                    raise SpecArchiveError("候选长期 Spec 在写入前发生变化")
                if not _ordinary_file(review_record) or not _ordinary_file(review_report):
                    raise SpecArchiveError("Spec 审查记录在写入前消失")
                if json.loads(review_record.read_text(encoding="utf-8")) != review:
                    raise SpecArchiveError("Spec 审查记录在写入前发生变化")
                if hashlib.sha256(review_report.read_bytes()).hexdigest() != review["report_sha256"]:
                    raise SpecArchiveError("Spec 审查报告在写入前发生变化")
                if seal.is_symlink() or (seal.exists() and seal.read_bytes() != publishing_payload):
                    raise SpecArchiveError("Topic 封存记录在写入前发生变化")
                if already_current:
                    if prior_revision:
                        history = history_dir / f"{prior_revision}.md"
                        if not _ordinary_file(history) or hashlib.sha256(history.read_bytes()).hexdigest() != previous_digest:
                            raise SpecArchiveError("旧长期 Spec 历史版本缺失或不匹配，不能恢复发布")
                    if not seal.exists():
                        raise SpecArchiveError("缺少封存中记录，不能恢复发布")
                    _atomic_bytes(seal, published_payload)
                    report["status"] = "published"
                    report["applied"] = True
                    report["recovered"] = True
                    return report
                if previous_payload is not None:
                    history = history_dir / f"{old_revision}.md"
                    if history.is_symlink() or (history.exists() and history.read_bytes() != previous_payload):
                        raise SpecArchiveError("长期 Spec 历史 revision 已有不同内容")
                if not seal.exists():
                    _atomic_bytes(seal, publishing_payload)
                canonical_root.mkdir(exist_ok=True)
                if previous_payload is not None:
                    history_dir.mkdir(parents=True, exist_ok=True)
                    if not history.exists():
                        _atomic_bytes(history, previous_payload)
                _atomic_bytes(canonical, payload)
                _atomic_bytes(seal, published_payload)
    except (OSError, FilesystemSafetyError, LifecycleError, WorkOverviewError) as exc:
        raise SpecArchiveError(str(exc)) from exc
    report["status"] = "published"
    report["applied"] = True
    return report
