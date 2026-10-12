"""Content-addressed review snapshots for Git working trees."""

from __future__ import annotations

import hashlib
import argparse
import base64
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


def _index_manifest(repo: Path) -> dict[str, tuple[str, str]]:
    manifest: dict[str, tuple[str, str]] = {}
    for item in _git(repo, "ls-files", "--stage", "-z").split(b"\0"):
        if not item:
            continue
        metadata, raw_path = item.split(b"\t", 1)
        mode, object_id, stage = metadata.decode("ascii").split(" ")
        if stage != "0":
            raise ReviewSnapshotError(
                f"存在未解决的 index 冲突，无法快照：{os.fsdecode(raw_path)}"
            )
        manifest[os.fsdecode(raw_path)] = (mode, object_id)
    return manifest


def _blob_id(repo: Path, content: bytes) -> str:
    return _git(repo, "hash-object", "--stdin", input_bytes=content).decode("ascii").strip()


def _plain_entry(repo: Path, relative_path: str) -> tuple[str, str] | None:
    path = repo / relative_path
    if not os.path.lexists(path):
        return None
    if path.is_symlink():
        return "120000", _blob_id(repo, os.fsencode(os.readlink(path)))
    if path.is_file():
        mode = "100755" if path.stat().st_mode & stat.S_IXUSR else "100644"
        return mode, _blob_id(repo, path.read_bytes())
    raise ReviewSnapshotError(f"无法快照非常规路径：{relative_path}")


def gitlink_entry(
    repo: Path, relative_path: str, index_object_id: str
) -> tuple[str, str]:
    path = repo / relative_path
    if not (path / ".git").exists():
        return "160000", index_object_id
    try:
        object_id = _git(path, "rev-parse", "--verify", "HEAD").decode("ascii").strip()
    except ReviewSnapshotError as exc:
        raise ReviewSnapshotError(
            f"父仓 gitlink 没有可解析 HEAD：{relative_path}"
        ) from exc
    return "160000", object_id


def _prefixed(prefix: str, relative_path: str) -> str:
    return f"{prefix}/{relative_path}" if prefix else relative_path


def _nested_paths(
    repo: Path, index: dict[str, tuple[str, str]], untracked: list[str]
) -> list[str]:
    """Find nearest nested roots, including ancestors of parent-tracked files."""
    candidates: set[str] = set()
    for raw in [*index, *untracked]:
        path = Path(raw.rstrip("/"))
        for candidate in [path, *path.parents]:
            if candidate != Path("."):
                candidates.add(candidate.as_posix())
    roots: list[str] = []
    for relative in sorted(candidates, key=lambda path: (path.count("/"), path)):
        if any(relative.startswith(root + "/") for root in roots):
            continue
        target = repo / relative
        if target.is_dir() and not target.is_symlink() and (target / ".git").exists():
            roots.append(relative)
    return roots


def _inside_nested(path: str, roots: list[str]) -> bool:
    return any(path == root or path.startswith(root + "/") for root in roots)


def _worktree_manifest(
    repo: Path, *, prefix: str = "", seen: set[Path] | None = None
) -> dict[str, tuple[str, str]]:
    """Describe final bytes, expanding embedded repos with their own ignore rules."""
    resolved = repo.resolve()
    visited = seen if seen is not None else set()
    if resolved in visited:
        raise ReviewSnapshotError(f"检测到循环嵌套 Git 工作树：{repo}")
    visited.add(resolved)
    try:
        manifest: dict[str, tuple[str, str]] = {}
        index = _index_manifest(repo)
        for relative_path, (mode, object_id) in sorted(index.items()):
            display_path = _prefixed(prefix, relative_path)
            entry = (
                gitlink_entry(repo, relative_path, object_id)
                if mode == "160000"
                else _plain_entry(repo, relative_path)
            )
            if entry is not None:
                manifest[display_path] = entry

        untracked = _paths(
            _git(repo, "ls-files", "--others", "--exclude-standard", "-z")
        )
        nested = _nested_paths(repo, index, untracked)
        for raw_path in sorted(untracked):
            relative_path = raw_path.rstrip("/")
            display_path = _prefixed(prefix, relative_path)
            if _inside_nested(relative_path, nested):
                continue
            entry = _plain_entry(repo, relative_path)
            if entry is not None:
                manifest[display_path] = entry
        for relative_path in nested:
            if index.get(relative_path, (None, None))[0] == "160000":
                continue  # Gitlinks retain their identity; their own diffs are captured below.
            embedded = _worktree_manifest(
                repo / relative_path, prefix=_prefixed(prefix, relative_path), seen=visited
            )
            for path, entry in embedded.items():
                if path in manifest and manifest[path] != entry:
                    raise ReviewSnapshotError(f"嵌套 Git 路径与父仓清单冲突：{path}")
                manifest[path] = entry
        return manifest
    finally:
        visited.remove(resolved)


def _source_paths(
    repo: Path, merge_base: str, *, untracked: list[str]
) -> dict[str, list[str]]:
    return {
        "committed": _paths(
            _git(repo, "diff", "--name-only", "-z", merge_base, "HEAD", "--")
        ),
        "staged": _paths(
            _git(repo, "diff", "--cached", "--name-only", "-z", "HEAD", "--")
        ),
        "unstaged": _paths(_git(repo, "diff", "--name-only", "-z", "--")),
        "untracked": untracked,
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
    current = _worktree_manifest(repo)
    root_index_paths = set(_index_manifest(repo))
    expanded_untracked = sorted(set(current) - root_index_paths)
    changes: list[dict[str, object]] = []
    for relative_path in sorted(set(base) | set(current)):
        base_entry = base.get(relative_path)
        current_entry = current.get(relative_path)
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
        "schema_version": 2,
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
        "schema_version": 2,
        "status": "ready" if changes else "empty",
        "repo": str(repo),
        "fixed_point": fixed_point,
        "resolved_fixed_point": resolved_fixed,
        "merge_base": merge_base,
        "head": head,
        "content_id": hashlib.sha256(encoded).hexdigest(),
        "clean": clean,
        "change_sources": _source_paths(
            repo, merge_base, untracked=expanded_untracked
        ),
        "changes": changes,
    }


def _file_content(path: Path) -> dict[str, str]:
    content = os.fsencode(os.readlink(path)) if path.is_symlink() else path.read_bytes()
    try:
        return {"encoding": "utf-8", "content": content.decode("utf-8")}
    except UnicodeDecodeError:
        return {"encoding": "base64", "content": base64.b64encode(content).decode("ascii")}


def _repository_diffs(
    repo: Path, base: str | None, *, prefix: str = "", seen: set[Path] | None = None
) -> list[dict[str, object]]:
    """Capture each Git layer, recursively including dirty and unborn nested repos."""
    visited = seen if seen is not None else set()
    resolved = repo.resolve()
    if resolved in visited:
        raise ReviewSnapshotError(f"检测到循环嵌套 Git 工作树：{repo}")
    visited.add(resolved)
    try:
        head_result = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"], cwd=repo, capture_output=True
        )
        head = head_result.stdout.decode("ascii").strip() if head_result.returncode == 0 else None
        # New embedded repositories have no parent-owned baseline; review all their content.
        empty_tree = _git(repo, "hash-object", "-t", "tree", "--stdin", input_bytes=b"").decode("ascii").strip()
        baseline = base or empty_tree
        diff_args = ("diff", "--no-ext-diff", "--no-textconv", "--binary")
        def diff(*args: str) -> str:
            return _git(repo, *diff_args, *args, "--").decode("utf-8", errors="replace")
        untracked = _paths(_git(repo, "ls-files", "--others", "--exclude-standard", "-z"))
        untracked_files = []
        children: dict[str, str | None] = {}
        base_entries = _base_manifest(repo, baseline)
        index = _index_manifest(repo)
        nested = _nested_paths(repo, index, untracked)
        for path in nested:
            previous = base_entries.get(path)
            children[path] = previous[1] if previous and previous[0] == "160000" else None
        for raw in untracked:
            path = raw.rstrip("/")
            target = repo / path
            if _inside_nested(path, nested):
                continue
            if target.is_file() or target.is_symlink():
                untracked_files.append({"path": path, **_file_content(target)})
            elif os.path.lexists(target):
                raise ReviewSnapshotError(f"无法快照非常规路径：{_prefixed(prefix, path)}")
        reports: list[dict[str, object]] = [{
            "path": prefix or ".",
            "base": baseline,
            "head": head,
            "committed_diff": diff(baseline, head) if head else "",
            "staged_diff": diff("--cached", head or empty_tree),
            "unstaged_diff": diff(),
            "untracked_files": untracked_files,
        }]
        for path, child_base in sorted(children.items()):
            reports.extend(_repository_diffs(
                repo / path, child_base, prefix=_prefixed(prefix, path), seen=visited
            ))
        return reports
    finally:
        visited.remove(resolved)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--base", required=True)
    args = parser.parse_args()
    try:
        report = build_review_snapshot(args.repo, args.base)
        repo = Path(str(report["repo"]))
        report["repositories"] = _repository_diffs(repo, str(report["merge_base"]))
        # Include final bytes for embedded repositories omitted by the parent's diff.
        report["worktree_files"] = [
            {"path": change["path"], **_file_content(repo / str(change["path"]))}
            for change in report["changes"]
            if change["current"] and change["current"]["mode"] != "160000"
        ]
        report["content_id"] = hashlib.sha256(json.dumps(
            {"repositories": report["repositories"], "worktree_files": report["worktree_files"]},
            sort_keys=True, ensure_ascii=True, separators=(",", ":"),
        ).encode("utf-8")).hexdigest()
        if any(
            item["committed_diff"] or item["staged_diff"] or item["unstaged_diff"] or item["untracked_files"]
            for item in report["repositories"]
        ):
            report["status"] = "ready"
        print(json.dumps(report, ensure_ascii=True, sort_keys=True))
        return 0
    except (ReviewSnapshotError, OSError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
