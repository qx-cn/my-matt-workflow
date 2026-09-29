"""Move completed local Topics into a verifiable read-only history area."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
from pathlib import Path

from .fs_safety import FilesystemSafetyError, exclusive_lock, strict_relative_path
from .lifecycle import LifecycleError, topic_lifecycle_lock
from .run_journal import RunJournalError, validate_completed_run_history
from .profile import ProfileError, effective_profile, parse_profile
from .tickets import TicketError, _unchecked_acceptance, frontmatter, ticket_definition_receipt
from .work_overview import WorkOverviewError, work_overview


class TopicArchiveError(ValueError):
    """The requested Topic cannot be archived or read reliably."""


_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")


def _child(root: Path, name: str) -> Path:
    if not _NAME.fullmatch(name):
        raise TopicArchiveError("Topic 必须是小写 kebab-case")
    try:
        return strict_relative_path(root, name, direct_child=True)
    except FilesystemSafetyError as exc:
        raise TopicArchiveError(str(exc)) from exc


def _file_sha256(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _inventory(topic_dir: Path) -> tuple[list[dict[str, object]], str]:
    files: list[dict[str, object]] = []
    for path in sorted(topic_dir.rglob("*"), key=lambda item: item.relative_to(topic_dir).as_posix()):
        relative = path.relative_to(topic_dir).as_posix()
        if path.is_symlink():
            raise TopicArchiveError(f"Topic 包含符号链接：{relative}")
        mode = path.lstat().st_mode
        if stat.S_ISDIR(mode):
            continue
        if not stat.S_ISREG(mode):
            raise TopicArchiveError(f"Topic 包含非普通文件：{relative}")
        if relative == "archive/manifest.json":
            continue
        sha256, size = _file_sha256(path)
        files.append({
            "path": relative, "sha256": sha256, "size": size,
        })
    encoded = json.dumps(files, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return files, hashlib.sha256(encoded).hexdigest()


def _atomic_json(path: Path, value: dict[str, object]) -> None:
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=f".{path.name}.", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(value, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def _publication(repo: Path, topic_dir: Path, item: dict[str, object]) -> dict[str, object]:
    marker = topic_dir / "archive" / "publication.json"
    if not marker.is_file() or marker.is_symlink():
        raise TopicArchiveError("行为 Topic 尚未发布长期 Spec")
    try:
        published = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise TopicArchiveError("长期 Spec 发布记录无效") from exc
    specs = item["specs"]
    if (
        not isinstance(published, dict)
        or published.get("status") != "published"
        or published.get("topic") != topic_dir.name
        or len(specs) != 1
        or published.get("spec_id") != specs[0]["spec_id"]
    ):
        raise TopicArchiveError("长期 Spec 发布记录与 Topic 不一致")
    source = repo / str(specs[0]["path"])
    if _file_sha256(source)[0] != published.get("source_sha256"):
        raise TopicArchiveError("来源 Spec 在发布后发生变化")
    candidate = topic_dir / "archive" / "canonical-spec.md"
    if candidate.is_symlink() or not candidate.is_file() or _file_sha256(candidate)[0] != published.get("candidate_sha256"):
        raise TopicArchiveError("长期 Spec 候选在发布后发生变化")
    definitions = published.get("ticket_definitions")
    journals = published.get("completed_journals")
    if (
        not isinstance(definitions, dict)
        or not isinstance(journals, dict)
        or set(definitions) != {str(ticket["id"]) for ticket in item["tickets"]}
        or set(journals) != set(definitions)
    ):
        raise TopicArchiveError("发布记录缺少完整 Ticket 完成证据")
    for ticket in item["tickets"]:
        ticket_id = str(ticket["id"])
        ticket_path = repo / str(ticket["path"])
        if ticket_definition_receipt(ticket_path)["sha256"] != definitions[ticket_id]:
            raise TopicArchiveError(f"Ticket 定义在发布后发生变化：{ticket_id}")
        journal_record = journals[ticket_id]
        if not isinstance(journal_record, dict) or set(journal_record) != {"path", "sha256"}:
            raise TopicArchiveError(f"完成会话记录无效：{ticket_id}")
        raw_path = journal_record["path"]
        if not isinstance(raw_path, str):
            raise TopicArchiveError(f"完成会话路径无效：{ticket_id}")
        try:
            journal_path = strict_relative_path(repo, raw_path)
        except FilesystemSafetyError as exc:
            raise TopicArchiveError(str(exc)) from exc
        if (
            not journal_path.is_file() or journal_path.is_symlink()
            or not journal_path.is_relative_to(topic_dir / "runs")
            or _file_sha256(journal_path)[0] != journal_record["sha256"]
        ):
            raise TopicArchiveError(f"完成会话在发布后发生变化：{ticket_id}")
        try:
            validate_completed_run_history(journal_path)
        except RunJournalError as exc:
            raise TopicArchiveError(f"完成会话证据在发布后发生变化：{ticket_id}：{exc}") from exc
    spec_id = str(published["spec_id"])
    current = repo / ".agent" / "specs" / f"{spec_id}.md"
    history = repo / ".agent" / "specs" / "history" / spec_id
    versions = [current]
    if history.is_dir() and not history.is_symlink():
        versions.extend(sorted(history.glob("*.md")))
    matches = []
    for path in versions:
        if path.is_symlink() or not path.is_file():
            continue
        try:
            metadata = frontmatter(path)
        except (OSError, TicketError):
            continue
        if (
            metadata.get("source_topic") == topic_dir.name
            and metadata.get("spec_id") == spec_id
            and _file_sha256(path)[0] == published.get("candidate_sha256")
        ):
            matches.append(path)
    if len(matches) != 1:
        raise TopicArchiveError("找不到与发布记录匹配的长期 Spec 版本")
    return {"kind": "behavior", "publication": str(marker.relative_to(repo)),
            "canonical_sha256": published["candidate_sha256"],
            "canonical_version_at_archive": str(matches[0].relative_to(repo))}


def _document_completion(repo: Path, topic_dir: Path, item: dict[str, object]) -> dict[str, object]:
    if item["specs"] or item["tickets"] or item["sessions"]:
        raise TopicArchiveError("无 Ticket 归档仅适用于没有 Spec 与实施会话的文档 Topic")
    record_path = topic_dir / "archive" / "completion.json"
    if not record_path.is_file() or record_path.is_symlink():
        raise TopicArchiveError("文档 Topic 缺少 archive/completion.json 完成记录")
    try:
        record = json.loads(record_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise TopicArchiveError("文档 Topic 完成记录无效") from exc
    if (
        not isinstance(record, dict)
        or record.get("schema_version") != 1
        or record.get("topic") != topic_dir.name
        or record.get("status") != "complete"
        or record.get("behavior_change") != "none"
        or not isinstance(record.get("evidence"), list)
        or not record["evidence"]
    ):
        raise TopicArchiveError("文档 Topic 完成记录字段无效")
    for raw in record["evidence"]:
        if not isinstance(raw, str):
            raise TopicArchiveError("文档 Topic 证据路径无效")
        try:
            path = strict_relative_path(topic_dir, raw)
        except FilesystemSafetyError as exc:
            raise TopicArchiveError(str(exc)) from exc
        if path.relative_to(topic_dir).parts[0] == "archive":
            raise TopicArchiveError("文档 Topic 证据必须独立于归档控制文件")
        if not path.is_file() or path.is_symlink() or path.stat().st_size == 0:
            raise TopicArchiveError(f"文档 Topic 证据不存在：{raw}")
    return {"kind": "document", "completion": str(record_path.relative_to(repo))}


def _external_references(repo: Path, topic: str) -> list[str]:
    work = repo / ".agent" / "work"
    tokens = (f".agent/work/{topic}".encode(), str(work / topic).encode())
    patterns = tuple(re.compile(re.escape(token) + rb"[^A-Za-z0-9._-]") for token in tokens)
    relative_pattern = re.compile(
        rb"(?<![A-Za-z0-9._/-])((?:\.\./)+[A-Za-z0-9._/-]*)(?=[^A-Za-z0-9._/-])"
    )
    work_relative_pattern = re.compile(
        rb"(?<![A-Za-z0-9._/-])((?:\./)?"
        + re.escape(f"work/{topic}".encode())
        + rb")(?=[^A-Za-z0-9._-])"
    )
    overlap = max(4096, max(len(token) for token in tokens))

    def relative_target(data: bytes, path: Path) -> bool:
        for pattern in (relative_pattern, work_relative_pattern):
            for match in pattern.finditer(data):
                target = Path(os.path.realpath(path.parent / os.fsdecode(match.group(1))))
                if target == work / topic or (work / topic) in target.parents:
                    return True
        return False

    def mentions(path: Path) -> bool:
        if path.is_symlink():
            target = Path(os.path.realpath(path))
            return target == work / topic or (work / topic) in target.parents
        if not path.is_file():
            return False
        try:
            with path.open("rb") as stream:
                previous = b""
                while chunk := stream.read(1024 * 1024):
                    data = previous + chunk
                    if any(pattern.search(data) for pattern in patterns) or relative_target(data, path):
                        return True
                    previous = data[-overlap:]
        except OSError as exc:
            raise TopicArchiveError(f"无法检查外部引用：{path}") from exc
        return any(previous.endswith(token) for token in tokens) or relative_target(previous + b"\n", path)

    found: list[str] = []
    for other in sorted(work.iterdir()):
        if other.name == topic:
            continue
        if other.is_symlink():
            if mentions(other):
                found.append(other.relative_to(repo).as_posix())
            continue
        if not other.is_dir():
            continue
        for path in other.rglob("*"):
            if mentions(path):
                found.append(path.relative_to(repo).as_posix())
    agent = repo / ".agent"
    for path in sorted(agent.glob("*")):
        if mentions(path):
            found.append(path.relative_to(repo).as_posix())
    canonical = agent / "specs"
    if canonical.is_symlink():
        raise TopicArchiveError("长期 Spec 目录不能是符号链接")
    if canonical.is_dir():
        for path in sorted(canonical.glob("*.md")):
            if mentions(path):
                found.append(path.relative_to(repo).as_posix())
    return found


def archive_topic(repo: Path, topic: str, *, apply: bool = False,
                  expected_digest: str | None = None) -> dict[str, object]:
    """Preview or move a completed Topic, preserving every source byte."""
    repo = repo.resolve()
    agent = repo / ".agent"
    work = agent / "work"
    archive = agent / "archive"
    if agent.is_symlink() or work.is_symlink() or not work.is_dir():
        raise TopicArchiveError("项目活动工作区无效")
    if archive.is_symlink() or (archive.exists() and not archive.is_dir()):
        raise TopicArchiveError("归档根目录无效")
    source = _child(work, topic)
    destination = _child(archive, topic)
    if destination.exists() or destination.is_symlink():
        raise TopicArchiveError("归档目标已存在，请使用 archive-show 检查")
    if not source.is_dir():
        raise TopicArchiveError("活动 Topic 不存在")
    try:
        profile, _ = parse_profile((agent / "matt-workflow.md").read_text(encoding="utf-8"))
        if effective_profile(profile)["task_backend"] != "local":
            raise TopicArchiveError("Topic 归档目前只支持 local 后端")
        overview = work_overview(repo, topic=topic)
    except (OSError, ProfileError, WorkOverviewError) as exc:
        raise TopicArchiveError(str(exc)) from exc
    if overview["status"] != "ok":
        raise TopicArchiveError("Topic 状态不一致，不能归档")
    item = overview["topics"][0]
    if any(session["active"] for session in item["sessions"]):
        raise TopicArchiveError("Topic 仍有活动实施会话")
    if any(ticket["status"] != "complete" for ticket in item["tickets"]):
        raise TopicArchiveError("Topic 仍有未完成 Ticket")
    for ticket in item["tickets"]:
        if _unchecked_acceptance(repo / str(ticket["path"])):
            raise TopicArchiveError(f"Ticket 验收项重新打开：{ticket['path']}")
    completion = (
        _publication(repo, source, item) if item["tickets"]
        else _document_completion(repo, source, item)
    )
    references = _external_references(repo, topic)
    if references:
        raise TopicArchiveError("活动文件仍引用原路径：" + ", ".join(references))
    files, digest = _inventory(source)
    manifest = {
        "schema_version": 1, "topic": topic, "status": "archived",
        "old_prefix": f".agent/work/{topic}/",
        "new_prefix": f".agent/archive/{topic}/",
        "tree_sha256": digest, "files": files, "completion": completion,
    }
    manifest_path = source / "archive" / "manifest.json"
    if manifest_path.is_symlink():
        raise TopicArchiveError("归档清单不能是符号链接")
    old_manifest_bytes = manifest_path.read_bytes() if manifest_path.exists() else None
    if old_manifest_bytes is not None:
        try:
            old_manifest = json.loads(old_manifest_bytes)
        except (OSError, ValueError) as exc:
            raise TopicArchiveError("现有归档清单无法读取") from exc
        if old_manifest != manifest:
            raise TopicArchiveError("现有归档清单与 Topic 当前内容不匹配")
    report: dict[str, object] = {
        "status": "ready", "topic": topic, "kind": completion["kind"],
        "completion": completion,
        "source": str(source.relative_to(repo)), "destination": str(destination.relative_to(repo)),
        "tree_sha256": digest, "file_count": len(files), "files": files, "applied": False,
    }
    if not apply:
        return report
    if expected_digest != digest:
        raise TopicArchiveError("--apply 需要与预览一致的 --expected-digest")
    try:
        with topic_lifecycle_lock(repo, topic, exclusive=True):
            with exclusive_lock(agent, "canonical-spec"):
                if work_overview(repo, topic=topic) != overview or _inventory(source) != (files, digest):
                    raise TopicArchiveError("Topic 在预览后发生变化，请重新预览")
                if completion != (
                    _publication(repo, source, item) if item["tickets"]
                    else _document_completion(repo, source, item)
                ):
                    raise TopicArchiveError("Topic 完成或长期 Spec 发布状态发生变化")
                if _external_references(repo, topic):
                    raise TopicArchiveError("活动文件新增了原路径引用")
                if destination.exists() or destination.is_symlink():
                    raise TopicArchiveError("归档目标在写入前已存在")
                if manifest_path.is_symlink() or (
                    manifest_path.read_bytes() if manifest_path.exists() else None
                ) != old_manifest_bytes:
                    raise TopicArchiveError("归档清单在写入前发生变化")
                archive.mkdir(exist_ok=True)
                manifest_path.parent.mkdir(exist_ok=True)
                if not manifest_path.exists():
                    _atomic_json(manifest_path, manifest)
                os.replace(source, destination)
    except (OSError, FilesystemSafetyError, LifecycleError, WorkOverviewError) as exc:
        raise TopicArchiveError(str(exc)) from exc
    report["status"] = "archived"
    report["applied"] = True
    return report


def show_archived_topic(repo: Path, topic: str) -> dict[str, object]:
    """Verify an archived Topic and resolve only its own frozen internal paths."""
    repo = repo.resolve()
    archive = repo / ".agent" / "archive"
    if archive.is_symlink() or not archive.is_dir():
        raise TopicArchiveError("归档目录不存在")
    topic_dir = _child(archive, topic)
    manifest_path = topic_dir / "archive" / "manifest.json"
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise TopicArchiveError("归档清单不存在")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise TopicArchiveError("归档清单无效") from exc
    files, digest = _inventory(topic_dir)
    if (
        not isinstance(manifest, dict)
        or manifest.get("schema_version") != 1
        or manifest.get("topic") != topic
        or manifest.get("status") != "archived"
        or manifest.get("old_prefix") != f".agent/work/{topic}/"
        or manifest.get("new_prefix") != f".agent/archive/{topic}/"
        or manifest.get("files") != files
        or manifest.get("tree_sha256") != digest
    ):
        raise TopicArchiveError("归档文件与清单不匹配")
    completion = manifest.get("completion")
    if not isinstance(completion, dict) or completion.get("kind") not in {"behavior", "document"}:
        raise TopicArchiveError("归档完成来源无效")
    issues: list[str] = []
    canonical_version: str | None = None
    completed_journal_paths: set[str] = set()
    if completion["kind"] == "behavior":
        marker = topic_dir / "archive" / "publication.json"
        try:
            published = json.loads(marker.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise TopicArchiveError("归档发布记录无法读取") from exc
        if (not isinstance(published, dict)
                or published.get("status") != "published"
                or completion.get("canonical_sha256") != published.get("candidate_sha256")):
            raise TopicArchiveError("归档发布记录与清单不匹配")
        candidate = topic_dir / "archive" / "canonical-spec.md"
        if not candidate.is_file() or _file_sha256(candidate)[0] != published["candidate_sha256"]:
            raise TopicArchiveError("归档长期 Spec 候选与发布记录不匹配")
        journals = published.get("completed_journals")
        if not isinstance(journals, dict):
            raise TopicArchiveError("归档发布记录缺少完成会话")
        for record in journals.values():
            if not isinstance(record, dict) or set(record) != {"path", "sha256"}:
                raise TopicArchiveError("归档完成会话记录无效")
            raw_path, expected_sha256 = record["path"], record["sha256"]
            old_prefix = f".agent/work/{topic}/"
            if not isinstance(raw_path, str) or not raw_path.startswith(old_prefix):
                raise TopicArchiveError("归档完成会话路径无效")
            relative = Path(raw_path.removeprefix(old_prefix))
            if (relative.parent != Path("runs") or not relative.name.startswith("run-")
                    or relative.suffix != ".json"):
                raise TopicArchiveError("归档完成会话路径无效")
            archived_journal = topic_dir / relative
            if (not archived_journal.is_file() or archived_journal.is_symlink()
                    or _file_sha256(archived_journal)[0] != expected_sha256):
                raise TopicArchiveError(f"归档完成会话与发布记录不匹配：{raw_path}")
            completed_journal_paths.add(raw_path)
        if len(completed_journal_paths) != len(journals):
            raise TopicArchiveError("归档完成会话路径重复")
        spec_id = str(published.get("spec_id", ""))
        if not _NAME.fullmatch(spec_id):
            raise TopicArchiveError("归档长期 Spec id 无效")
        current = repo / ".agent" / "specs" / f"{spec_id}.md"
        history = repo / ".agent" / "specs" / "history" / spec_id
        candidates = [current]
        if history.is_dir() and not history.is_symlink():
            candidates.extend(sorted(history.glob("*.md")))
        for path in candidates:
            if path.is_file() and not path.is_symlink() and _file_sha256(path)[0] == published["candidate_sha256"]:
                canonical_version = path.relative_to(repo).as_posix()
                break
        if canonical_version is None:
            issues.append("已发布长期 Spec 版本缺失或内容漂移")
    old_relative = str(repo / ".agent" / "work" / topic) + "/"
    new_relative = str(repo / ".agent" / "archive" / topic) + "/"
    known = {str(item["path"]) for item in files}
    indexed = {str(item["path"]): item for item in files}
    links: list[dict[str, object]] = []

    def collect(value: object) -> None:
        if isinstance(value, dict):
            for nested in value.values():
                collect(nested)
        elif isinstance(value, list):
            for nested in value:
                collect(nested)
        elif isinstance(value, str):
            if value.startswith(old_relative):
                suffix = value.removeprefix(old_relative)
                translated = new_relative + suffix
            elif value.startswith(manifest["old_prefix"]):
                suffix = value.removeprefix(manifest["old_prefix"])
                translated = manifest["new_prefix"] + suffix
            else:
                return
            if suffix not in known:
                raise TopicArchiveError(f"归档内部引用缺少目标：{value}")
            links.append({"original": value, "archived": translated})

    for item in files:
        path = topic_dir / str(item["path"])
        if path.parent == topic_dir / "runs" and path.suffix == ".json" and path.name.startswith("run-"):
            try:
                original_ref = f".agent/work/{topic}/{item['path']}"
                if original_ref in completed_journal_paths:
                    validate_completed_run_history(
                        path,
                        relocation=(repo / ".agent" / "work" / topic, topic_dir),
                    )
                journal = json.loads(path.read_text(encoding="utf-8"))
                context = journal.get("context", {})
                collect(context)
                submission = journal.get("submission", {})
                code = submission.get("code_receipt", {}) if isinstance(submission, dict) else {}
                receipts = []
                if isinstance(context, dict):
                    stable_sources = context.get("source_receipts", [])
                    if isinstance(stable_sources, list):
                        receipts.extend(stable_sources)
                if isinstance(code, dict):
                    code_sources = code.get("sources", [])
                    if isinstance(code_sources, list):
                        receipts.extend(code_sources)
                for receipt in receipts:
                    if not isinstance(receipt, dict):
                        continue
                    raw_path = receipt.get("path")
                    if not isinstance(raw_path, str):
                        continue
                    if raw_path.startswith(old_relative):
                        collect(raw_path)
                        target = indexed.get(raw_path.removeprefix(old_relative))
                        if (target is None or target["sha256"] != receipt.get("sha256")
                                or target["size"] != receipt.get("size")):
                            raise TopicArchiveError(f"归档内部来源收据不匹配：{raw_path}")
                        continue
                    external = Path(raw_path)
                    if (not external.is_file() or external.is_symlink()
                            or _file_sha256(external)[0] != receipt.get("sha256")):
                        issues.append(f"外部来源缺失或漂移：{raw_path}")
            except (OSError, ValueError, AttributeError, RunJournalError) as exc:
                raise TopicArchiveError(f"归档会话无法读取：{item['path']}") from exc
        elif path.parent == topic_dir / "tickets" and path.suffix == ".md":
            try:
                collect(frontmatter(path).get("spec_ref"))
            except (OSError, TicketError) as exc:
                raise TopicArchiveError(f"归档 Ticket 无法读取：{item['path']}") from exc
        elif (
            path.suffix == ".json"
            and path.parent.parent == topic_dir / "runs"
            and path.parent.name.startswith("run-")
            and path.parent.name.endswith(".evidence")
            and f"runs/{path.parent.name.removesuffix('.evidence')}.json" in known
        ):
            try:
                evidence = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise TopicArchiveError(f"归档证据无法读取：{item['path']}") from exc
            if isinstance(evidence, dict) and evidence.get("kind") == "review":
                result = evidence.get("result")
                raw_path = result.get("path") if isinstance(result, dict) else None
                if not isinstance(raw_path, str) or not raw_path.startswith(old_relative):
                    raise TopicArchiveError(f"归档审查结果路径无效：{item['path']}")
                suffix = raw_path.removeprefix(old_relative)
                target = indexed.get(suffix)
                if (target is None or target["sha256"] != result.get("sha256")
                        or target["size"] != result.get("size")):
                    raise TopicArchiveError(f"归档审查结果内容不匹配：{item['path']}")
                collect(raw_path)
    return {"status": "valid" if not issues else "needs-attention", "topic": topic,
            "path": str(topic_dir), "kind": completion["kind"],
            "tree_sha256": digest, "file_count": len(files),
            "canonical_version": canonical_version,
            "relocated_refs": links, "issues": sorted(set(issues))}


def list_archived_topics(repo: Path) -> dict[str, object]:
    repo = repo.resolve()
    root = repo / ".agent" / "archive"
    if root.is_symlink():
        raise TopicArchiveError("归档根目录不能是符号链接")
    if not root.is_dir():
        return {"repo": str(repo), "topics": []}
    topics = []
    for path in sorted(root.iterdir()):
        ordinary_dir = path.is_dir() and not path.is_symlink()
        manifest = path / "archive" / "manifest.json" if ordinary_dir else None
        topics.append({
            "topic": path.name,
            "path": str(path),
            "status": "unverified" if ordinary_dir else "invalid-entry",
            "manifest_present": bool(manifest and manifest.is_file() and not manifest.is_symlink()),
        })
    return {"repo": str(repo), "topics": topics}
