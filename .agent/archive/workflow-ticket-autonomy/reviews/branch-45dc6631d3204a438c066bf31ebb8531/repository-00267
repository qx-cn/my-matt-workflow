"""Persist installation roots and serialize installation with release cleanup."""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path

from .fs_safety import FilesystemSafetyError

REFERENCE_LOCK = "release-references"
REGISTRY_FILE = ".release-references.json"
_RELEASE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")


def read_references(root: Path) -> dict:
    path = root / REGISTRY_FILE
    if path.is_symlink():
        raise FilesystemSafetyError("release 引用登记不能是 symlink")
    if not path.exists():
        return {"version": 1, "managed_releases": [], "state_homes": []}
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise FilesystemSafetyError("release 引用登记损坏，停止安装或清理") from exc
    if (not isinstance(data, dict) or set(data) != {"version", "managed_releases", "state_homes"}
            or data["version"] != 1
            or not isinstance(data["managed_releases"], list)
            or not isinstance(data["state_homes"], list)
            or any(not isinstance(x, str) or not _RELEASE_ID.fullmatch(x) for x in data["managed_releases"])
            or any(not isinstance(x, str) or not Path(x).is_absolute() for x in data["state_homes"])):
        raise FilesystemSafetyError("release 引用登记无效，停止安装或清理")
    return data


def write_references(root: Path, data: dict) -> None:
    """Caller holds REFERENCE_LOCK; publish one complete registry atomically."""
    if (root / REGISTRY_FILE).is_symlink():
        raise FilesystemSafetyError("release 引用登记不能是 symlink")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=root,
                                         prefix=".release-references-", suffix=".tmp", delete=False) as f:
            temporary = Path(f.name)
            json.dump(data, f, ensure_ascii=False, sort_keys=True)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, root / REGISTRY_FILE)
    except OSError as exc:
        raise FilesystemSafetyError("release 引用登记无法持久化，停止安装或清理") from exc
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def remember_installation(root: Path, home: Path) -> None:
    """Register before install side effects so a successful receipt is discoverable."""
    data = read_references(root)
    data["state_homes"] = sorted(set(data["state_homes"]) | {str(home.resolve())})
    write_references(root, data)
