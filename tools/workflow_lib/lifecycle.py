"""Recoverable coordination for mutable Ticket projections and run journals.

The filesystem cannot atomically replace two independent files.  This module
therefore persists a write-ahead log and deterministically rolls each prepared
transaction forward.  Recovery accepts only the recorded before or after bytes;
unrelated drift fails closed.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .fs_safety import (
    FilesystemSafetyError,
    REGISTRY_NAME,
    quarantine_and_remove,
    register_owned_directory,
    verify_owned_directory,
)


class LifecycleError(ValueError):
    """Raised when lifecycle state cannot be safely coordinated or recovered."""


_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_WAL_PURPOSE = "ticket-lifecycle-transaction"


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=f".{path.name}.", delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def _atomic_json(path: Path, value: dict[str, object]) -> None:
    _atomic_text(
        path,
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    )


def _repo_path(repo: Path, raw: object, *, label: str) -> Path:
    if not isinstance(raw, str) or not raw:
        raise LifecycleError(f"WAL {label} 路径无效")
    candidate = Path(raw)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise LifecycleError(f"WAL {label} 必须是仓库内相对路径")
    resolved = (repo / candidate).resolve()
    try:
        resolved.relative_to(repo)
    except ValueError as exc:
        raise LifecycleError(f"WAL {label} 路径越界") from exc
    return resolved


@contextmanager
def ticket_lock(repo: Path, topic: str, ticket_id: str) -> Iterator[None]:
    """Serialize claim/recovery/update for one Ticket without stale lock files."""
    if not _SAFE_ID.fullmatch(topic) or not _SAFE_ID.fullmatch(ticket_id):
        raise LifecycleError("Ticket topic 或 id 不能用于生命周期锁")
    path = repo / ".agent" / "work" / topic / "runs" / "locks" / f"{ticket_id}.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def project_ticket(
    text: str, *, status: str, claimed_by: str, complete_acceptance: bool = False
) -> str:
    """Update only mutable Ticket projection fields while preserving definition."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---":
        raise LifecycleError("Ticket 缺少 YAML frontmatter")
    try:
        end = next(
            index for index, line in enumerate(lines[1:], 1)
            if line.rstrip("\r\n") == "---"
        )
    except StopIteration as exc:
        raise LifecycleError("Ticket frontmatter 未结束") from exc
    found: set[str] = set()
    for index in range(1, end):
        line = lines[index]
        key = line.split(":", 1)[0].strip() if ":" in line else ""
        if key == "status":
            ending = "\n" if line.endswith("\n") else ""
            lines[index] = f"status: {status}{ending}"
            found.add(key)
        elif key == "claimed_by":
            ending = "\n" if line.endswith("\n") else ""
            lines[index] = f"claimed_by: {claimed_by}{ending}"
            found.add(key)
    if found != {"status", "claimed_by"}:
        raise LifecycleError("Ticket 必须显式声明 status 与 claimed_by")
    if complete_acceptance:
        checkbox = re.compile(r"^(\s*- \[)[ xX](\])")
        for index in range(end + 1, len(lines)):
            lines[index] = checkbox.sub(r"\1x\2", lines[index])
    return "".join(lines)


def _transaction_root(repo: Path, topic: str) -> Path:
    return repo / ".agent" / "work" / topic / "runs" / "lifecycle-transactions"


def _transaction_dir(
    repo: Path, topic: str, ticket_id: str, attempt_id: str, operation: str
) -> Path:
    for value in (topic, ticket_id, attempt_id, operation):
        if not _SAFE_ID.fullmatch(value):
            raise LifecycleError("生命周期 WAL 标识无效")
    return _transaction_root(repo, topic) / f"{ticket_id}-{attempt_id}-{operation}"


def coordinate_lifecycle_update(
    repo: Path,
    *,
    topic: str,
    ticket_id: str,
    attempt_id: str,
    operation: str,
    updates: list[tuple[Path, str, str]],
    fail_after_writes: int | None = None,
) -> None:
    """Persist a WAL and roll multiple file replacements forward recoverably.

    Each update is ``(path, expected_before_text, after_text)``.  The optional
    failure hook exists only for deterministic fault-injection tests.
    """
    root = repo.resolve()
    entries: list[dict[str, object]] = []
    seen: set[Path] = set()
    for path, before, after in updates:
        resolved = path.resolve()
        try:
            relative = resolved.relative_to(root)
        except ValueError as exc:
            raise LifecycleError("生命周期更新目标必须位于仓库") from exc
        if resolved in seen:
            raise LifecycleError("生命周期事务包含重复目标")
        seen.add(resolved)
        current = resolved.read_text(encoding="utf-8") if resolved.exists() else ""
        if current != before:
            raise LifecycleError(f"生命周期 CAS 失败：{relative.as_posix()}")
        entries.append(
            {
                "path": relative.as_posix(),
                "before_sha256": _sha256(before),
                "after_sha256": _sha256(after),
                "after_text": after,
            }
        )
    wal = {
        "schema_version": 1,
        "kind": "ticket-lifecycle-wal",
        "status": "prepared",
        "topic": topic,
        "ticket_id": ticket_id,
        "attempt_id": attempt_id,
        "operation": operation,
        "entries": entries,
    }
    transaction_root = _transaction_root(root, topic)
    transaction_dir = _transaction_dir(root, topic, ticket_id, attempt_id, operation)
    wal_path = transaction_dir / "wal.json"
    transaction_root.mkdir(parents=True, exist_ok=True)
    try:
        transaction_dir.mkdir()
    except FileExistsError as exc:
        raise LifecycleError(f"生命周期 WAL 已存在：{transaction_dir}") from exc
    try:
        _atomic_json(wal_path, wal)
        register_owned_directory(
            transaction_root, transaction_dir, purpose=_WAL_PURPOSE
        )
    except Exception:
        if wal_path.exists():
            wal_path.unlink()
        transaction_dir.rmdir()
        raise
    writes = 0
    for entry in entries:
        target = _repo_path(root, entry["path"], label="entry")
        _atomic_text(target, str(entry["after_text"]))
        writes += 1
        if fail_after_writes == writes:
            raise LifecycleError("fault-injection: lifecycle write interrupted")
    try:
        quarantine_and_remove(
            transaction_root, transaction_dir, purpose=_WAL_PURPOSE
        )
    except FilesystemSafetyError as exc:
        raise LifecycleError("已写入生命周期事务无法安全清理") from exc


def _recover_wal(repo: Path, transaction_dir: Path) -> None:
    transaction_root = transaction_dir.parent
    try:
        verify_owned_directory(
            transaction_root, transaction_dir, purpose=_WAL_PURPOSE
        )
    except FilesystemSafetyError as exc:
        raise LifecycleError(
            f"生命周期事务缺少可信 ownership capability：{transaction_dir}"
        ) from exc
    wal_path = transaction_dir / "wal.json"
    try:
        wal = json.loads(wal_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LifecycleError(f"生命周期 WAL 损坏，已保留现场：{wal_path}") from exc
    if not isinstance(wal, dict) or set(wal) != {
        "schema_version", "kind", "status", "topic", "ticket_id",
        "attempt_id", "operation", "entries",
    }:
        raise LifecycleError(f"生命周期 WAL schema 无效，已保留现场：{wal_path}")
    if wal["schema_version"] != 1 or wal["kind"] != "ticket-lifecycle-wal":
        raise LifecycleError(f"生命周期 WAL 版本或类型无效：{wal_path}")
    expected_dir = _transaction_dir(
        repo, str(wal["topic"]), str(wal["ticket_id"]),
        str(wal["attempt_id"]), str(wal["operation"]),
    )
    if expected_dir != transaction_dir.resolve():
        raise LifecycleError("生命周期 WAL 路径与内容不匹配")
    entries = wal.get("entries")
    if wal.get("status") != "prepared" or not isinstance(entries, list) or not entries:
        raise LifecycleError(f"生命周期 WAL 状态无效：{wal_path}")
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {
            "path", "before_sha256", "after_sha256", "after_text"
        }:
            raise LifecycleError(f"生命周期 WAL entry 无效：{wal_path}")
        if (
            not isinstance(entry["after_text"], str)
            or not isinstance(entry["before_sha256"], str)
            or not isinstance(entry["after_sha256"], str)
            or not _SHA256.fullmatch(entry["before_sha256"])
            or not _SHA256.fullmatch(entry["after_sha256"])
            or _sha256(entry["after_text"]) != entry["after_sha256"]
        ):
            raise LifecycleError(f"生命周期 WAL entry digest 无效：{wal_path}")
        target = _repo_path(repo, entry["path"], label="entry")
        current = target.read_text(encoding="utf-8") if target.exists() else ""
        digest = _sha256(current)
        if digest == entry["after_sha256"]:
            continue
        if digest != entry["before_sha256"]:
            raise LifecycleError(f"生命周期恢复发现目标漂移，已保留 WAL：{target}")
        _atomic_text(target, str(entry["after_text"]))
    try:
        quarantine_and_remove(
            transaction_root, transaction_dir, purpose=_WAL_PURPOSE
        )
    except FilesystemSafetyError as exc:
        raise LifecycleError("生命周期事务恢复后无法安全清理") from exc


def recover_lifecycle_transactions(
    repo: Path, *, topic: str | None = None, ticket_id: str | None = None
) -> list[str]:
    """Roll prepared transactions forward; reject corrupt or unrelated drift."""
    root = repo.resolve()
    work = root / ".agent" / "work"
    if ticket_id is not None and (topic is None or not _SAFE_ID.fullmatch(ticket_id)):
        raise LifecycleError("按 Ticket 恢复时必须提供合法 topic 与 ticket_id")
    filename = f"{ticket_id}-*" if ticket_id else "*"
    pattern = (
        f"{topic}/runs/lifecycle-transactions/{filename}"
        if topic else "*/runs/lifecycle-transactions/*"
    )
    recovered: list[str] = []
    for transaction_dir in sorted(work.glob(pattern)) if work.is_dir() else []:
        if transaction_dir.name == REGISTRY_NAME:
            continue
        if not transaction_dir.is_dir() or transaction_dir.is_symlink():
            raise LifecycleError(f"生命周期事务路径类型无效：{transaction_dir}")
        _recover_wal(root, transaction_dir.resolve())
        recovered.append(str(transaction_dir))
    return recovered
