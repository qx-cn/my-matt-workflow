"""Content-addressed review snapshots for Git working trees."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
from pathlib import Path


class ReviewSnapshotError(ValueError):
    """Raised when a review snapshot cannot be constructed."""


def _git(repo: Path, *arguments: str, input_bytes: bytes | None = None) -> bytes:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repo,
        input=input_bytes,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        raise ReviewSnapshotError(message or f"git {' '.join(arguments)} 失败")
    return result.stdout


def _paths(raw: bytes) -> list[str]:
    return [
        os.fsdecode(item)
        for item in raw.split(b"\0")
        if item
    ]


def _base_manifest(repo: Path, commit: str) -> dict[str, tuple[str, str]]:
    manifest: dict[str, tuple[str, str]] = {}
    for item in _git(repo, "ls-tree", "-rz", "--full-tree", commit).split(b"\0"):
        if not item:
            continue
        metadata, raw_path = item.split(b"\t", 1)
        mode, _kind, object_id = metadata.decode("ascii").split(" ")
        manifest[os.fsdecode(raw_path)] = (mode, object_id)
    return manifest


def _blob_id(repo: Path, content: bytes) -> str:
    return _git(repo, "hash-object", "--stdin", input_bytes=content).decode("ascii").strip()


def _current_entry(repo: Path, relative_path: str) -> tuple[str, str] | None:
    path = repo / relative_path
    if not os.path.lexists(path):
        return None
    if path.is_symlink():
        return "120000", _blob_id(repo, os.fsencode(os.readlink(path)))
    if path.is_file():
        mode = "100755" if path.stat().st_mode & stat.S_IXUSR else "100644"
        return mode, _blob_id(repo, path.read_bytes())
    if path.is_dir() and (path / ".git").exists():
        object_id = _git(path, "rev-parse", "HEAD").decode("ascii").strip()
        return "160000", object_id
    raise ReviewSnapshotError(f"无法快照非常规路径：{relative_path}")


def _source_paths(repo: Path, merge_base: str) -> dict[str, list[str]]:
    return {
        "committed": _paths(
            _git(repo, "diff", "--name-only", "-z", merge_base, "HEAD", "--")
        ),
        "staged": _paths(
            _git(repo, "diff", "--cached", "--name-only", "-z", "HEAD", "--")
        ),
        "unstaged": _paths(_git(repo, "diff", "--name-only", "-z", "--")),
        "untracked": _paths(
            _git(repo, "ls-files", "--others", "--exclude-standard", "-z")
        ),
    }


def build_review_snapshot(repo: Path, fixed_point: str) -> dict[str, object]:
    """Describe all reviewable content relative to ``fixed_point``.

    The content id deliberately ignores whether a path is committed, staged,
    unstaged, or untracked. Moving unchanged content between those states must
    not invalidate a completed review, while changing any reviewed bytes must.
    """
    repo = repo.resolve()
    inside_work_tree = _git(repo, "rev-parse", "--is-inside-work-tree").decode("ascii").strip()
    if inside_work_tree != "true":
        raise ReviewSnapshotError(f"不是 Git 工作树：{repo}")
    resolved_fixed = _git(
        repo,
        "rev-parse",
        "--verify",
        "--end-of-options",
        f"{fixed_point}^{{commit}}",
    ).decode("ascii").strip()
    head = _git(repo, "rev-parse", "HEAD").decode("ascii").strip()
    merge_base = _git(repo, "merge-base", resolved_fixed, head).decode("ascii").strip()

    base = _base_manifest(repo, merge_base)
    current_paths = set(
        _paths(_git(repo, "ls-files", "-z", "--cached", "--others", "--exclude-standard"))
    )
    changes: list[dict[str, object]] = []
    for relative_path in sorted(set(base) | current_paths):
        base_entry = base.get(relative_path)
        current_entry = _current_entry(repo, relative_path)
        if base_entry == current_entry:
            continue
        if base_entry is None:
            change = "added"
        elif current_entry is None:
            change = "deleted"
        else:
            change = "modified"
        changes.append(
            {
                "path": relative_path,
                "change": change,
                "base": (
                    {"mode": base_entry[0], "object_id": base_entry[1]}
                    if base_entry
                    else None
                ),
                "current": (
                    {"mode": current_entry[0], "object_id": current_entry[1]}
                    if current_entry
                    else None
                ),
            }
        )

    content_payload = {
        "schema_version": 1,
        "merge_base": merge_base,
        "changes": changes,
    }
    encoded = json.dumps(
        content_payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    clean = not bool(_git(repo, "status", "--porcelain=v1", "-z"))
    return {
        "status": "ready" if changes else "empty",
        "repo": str(repo),
        "fixed_point": fixed_point,
        "resolved_fixed_point": resolved_fixed,
        "merge_base": merge_base,
        "head": head,
        "content_id": hashlib.sha256(encoded).hexdigest(),
        "clean": clean,
        "change_sources": _source_paths(repo, merge_base),
        "changes": changes,
    }
