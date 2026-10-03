"""Fail-closed filesystem capabilities for destructive workflow operations."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import shutil
import stat
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from uuid import uuid4


class FilesystemSafetyError(RuntimeError):
    """Raised before an unsafe filesystem mutation is attempted."""


REGISTRY_NAME = ".my-matt-ownership.json"
RELEASES_MUTATION_LOCK = "releases-mutation"


def strict_relative_path(
    root: Path, raw: str | Path, *, direct_child: bool = False
) -> Path:
    """Resolve an untrusted relative path and prove it remains below ``root``."""
    if isinstance(raw, Path):
        value = str(raw)
    elif isinstance(raw, str):
        value = raw
    else:
        raise FilesystemSafetyError("路径必须是字符串")
    if not value or "\x00" in value:
        raise FilesystemSafetyError("路径为空或包含 NUL")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts or relative in {Path("."), Path("")}:
        raise FilesystemSafetyError(f"路径必须是安全相对路径：{value}")
    if direct_child and len(relative.parts) != 1:
        raise FilesystemSafetyError(f"目标必须是可信根的直接子项：{value}")
    root = root.resolve()
    candidate = root / relative
    # Check every already-existing ancestor without following a symlink outside
    # the capability root.  The final resolve also covers a symlink target.
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise FilesystemSafetyError(f"路径包含 symlink：{value}")
        if not current.exists():
            break
    resolved = candidate.resolve(strict=False)
    if resolved == root or not resolved.is_relative_to(root):
        raise FilesystemSafetyError(f"路径越出可信根：{value}")
    return candidate


def _tree_digest(path: Path) -> str:
    digest = hashlib.sha256()
    root = path.resolve()
    for item in sorted(path.rglob("*"), key=lambda value: str(value.relative_to(path))):
        if item.is_symlink():
            raise FilesystemSafetyError(f"托管目录包含 symlink：{item}")
        relative = item.relative_to(path).as_posix().encode("utf-8")
        digest.update(relative)
        digest.update(b"\0")
        mode = item.lstat().st_mode
        if stat.S_ISDIR(mode):
            digest.update(b"d\0")
            continue
        if not stat.S_ISREG(mode):
            raise FilesystemSafetyError(f"托管目录包含非常规文件：{item}")
        digest.update(b"f\0")
        with item.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
        if not item.resolve().is_relative_to(root):
            raise FilesystemSafetyError(f"托管文件越界：{item}")
    return digest.hexdigest()


def _registry_path(root: Path, registry_path: Path | None = None) -> Path:
    return registry_path or root / REGISTRY_NAME


def _load_registry(
    root: Path, registry_path: Path | None = None
) -> dict[str, object]:
    path = _registry_path(root, registry_path)
    if not path.is_file() or path.is_symlink():
        return {"version": 1, "entries": {}}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FilesystemSafetyError("ownership registry 损坏") from exc
    if set(value) != {"version", "entries"} or value.get("version") != 1:
        raise FilesystemSafetyError("ownership registry schema 无效")
    entries = value.get("entries")
    if not isinstance(entries, dict):
        raise FilesystemSafetyError("ownership registry entries 无效")
    return value


def _write_registry(
    root: Path, value: dict[str, object], registry_path: Path | None = None
) -> None:
    path = _registry_path(root, registry_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.{uuid4().hex}.tmp"
    try:
        temporary.write_text(
            json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        with temporary.open("rb") as handle:
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def register_owned_directory(
    root: Path,
    target: Path,
    *,
    purpose: str,
    registry_path: Path | None = None,
    control_paths: tuple[str, ...] | None = None,
) -> None:
    """Record a direct-child directory in a registry outside that directory."""
    root = root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    candidate = strict_relative_path(root, target.name, direct_child=True)
    if candidate.resolve() != target.resolve() or not candidate.is_dir() or candidate.is_symlink():
        raise FilesystemSafetyError("只能登记可信根的现有直接子目录")
    info = candidate.stat()
    registry = _load_registry(root, registry_path)
    entries = registry["entries"]
    assert isinstance(entries, dict)
    previous = entries.get(target.name)
    if control_paths is None and isinstance(previous, dict):
        previous_controls = previous.get("controls", {})
        names = (
            tuple(previous_controls)
            if isinstance(previous_controls, dict)
            else ()
        )
    else:
        names = control_paths or ()
    controls: dict[str, str] = {}
    for relative in names:
        control = strict_relative_path(candidate, relative)
        if not control.is_file() or control.is_symlink():
            raise FilesystemSafetyError(f"ownership control 文件无效：{relative}")
        controls[relative] = hashlib.sha256(control.read_bytes()).hexdigest()
    entries[target.name] = {
        "purpose": purpose,
        "device": info.st_dev,
        "inode": info.st_ino,
        "digest": _tree_digest(candidate),
        "controls": controls,
    }
    _write_registry(root, registry, registry_path)


def verify_owned_directory_identity(
    root: Path,
    target: Path,
    *,
    purpose: str,
    registry_path: Path | None = None,
    required_controls: tuple[str, ...] = (),
) -> None:
    root = root.resolve()
    candidate = strict_relative_path(root, target.name, direct_child=True)
    if candidate.resolve() != target.resolve() or not candidate.is_dir() or candidate.is_symlink():
        raise FilesystemSafetyError("托管目录路径或类型无效")
    registry = _load_registry(root, registry_path)
    entries = registry["entries"]
    assert isinstance(entries, dict)
    entry = entries.get(target.name)
    info = candidate.stat()
    if (
        not isinstance(entry, dict)
        or set(entry) not in (
            {"purpose", "device", "inode", "digest"},
            {"purpose", "device", "inode", "digest", "controls"},
        )
        or entry.get("purpose") != purpose
        or entry.get("device") != info.st_dev
        or entry.get("inode") != info.st_ino
    ):
        raise FilesystemSafetyError("托管目录 ownership 或 identity 不匹配")
    controls = entry.get("controls", {})
    if not isinstance(controls, dict) or not set(required_controls).issubset(controls):
        raise FilesystemSafetyError("托管目录 ownership control 缺失")
    for relative, expected in controls.items():
        if (
            not isinstance(relative, str)
            or not isinstance(expected, str)
            or not re.fullmatch(r"[0-9a-f]{64}", expected)
        ):
            raise FilesystemSafetyError("托管目录 ownership control 无效")
        control = strict_relative_path(candidate, relative)
        if (
            not control.is_file()
            or control.is_symlink()
            or hashlib.sha256(control.read_bytes()).hexdigest() != expected
        ):
            raise FilesystemSafetyError("托管目录 ownership control 已漂移")


def verify_owned_directory(
    root: Path,
    target: Path,
    *,
    purpose: str,
    registry_path: Path | None = None,
) -> None:
    verify_owned_directory_identity(
        root, target, purpose=purpose, registry_path=registry_path
    )
    registry = _load_registry(root.resolve(), registry_path)
    entries = registry["entries"]
    assert isinstance(entries, dict)
    entry = entries[target.name]
    if not isinstance(entry, dict) or entry.get("digest") != _tree_digest(target):
        raise FilesystemSafetyError("托管目录 ownership 或 identity 不匹配")


def refresh_owned_directory(
    root: Path,
    target: Path,
    *,
    purpose: str,
    registry_path: Path | None = None,
    control_paths: tuple[str, ...] | None = None,
) -> None:
    """Refresh a registered directory after a controlled mutation."""
    registry = _load_registry(root.resolve(), registry_path)
    entries = registry["entries"]
    if not isinstance(entries, dict) or target.name not in entries:
        raise FilesystemSafetyError("目录未登记，不能刷新 ownership")
    register_owned_directory(
        root,
        target,
        purpose=purpose,
        registry_path=registry_path,
        control_paths=control_paths,
    )


def release_ownership(
    root: Path,
    target: Path,
    *,
    purpose: str,
    registry_path: Path | None = None,
) -> None:
    """Remove a registry entry after ownership is intentionally transferred."""
    root = root.resolve()
    verify_owned_directory(
        root, target, purpose=purpose, registry_path=registry_path
    )
    registry = _load_registry(root, registry_path)
    entries = registry["entries"]
    assert isinstance(entries, dict)
    entries.pop(target.name, None)
    _write_registry(root, registry, registry_path)


def quarantine_and_remove(
    root: Path,
    target: Path,
    *,
    purpose: str,
    registry_path: Path | None = None,
) -> None:
    """Verify, rename within one filesystem, then remove an owned directory."""
    root = root.resolve()
    verify_owned_directory(
        root, target, purpose=purpose, registry_path=registry_path
    )
    registry = _load_registry(root, registry_path)
    entries = registry["entries"]
    assert isinstance(entries, dict)
    quarantine = strict_relative_path(
        root, f".quarantine-{target.name}-{uuid4().hex}", direct_child=True
    )
    os.replace(target, quarantine)
    try:
        shutil.rmtree(quarantine)
    except Exception:
        os.replace(quarantine, target)
        raise
    entries.pop(target.name, None)
    _write_registry(root, registry, registry_path)


@contextmanager
def exclusive_lock(root: Path, name: str) -> Iterator[None]:
    """Hold a process lock for one destructive root."""
    if not name or "/" in name or ".." in name:
        raise FilesystemSafetyError("lock 名称无效")
    root.mkdir(parents=True, exist_ok=True)
    lock_path = root / f".{name}.lock"
    with lock_path.open("a+b") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise FilesystemSafetyError(f"另一个 {name} 事务仍在运行") from exc
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
