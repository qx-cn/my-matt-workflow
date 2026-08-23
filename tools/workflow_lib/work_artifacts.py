"""Plan and apply personal work-artifact layout migrations."""

from __future__ import annotations

import posixpath
import re
from pathlib import Path


_NAME_PART = r"[a-z0-9]+(?:-[a-z0-9]+)*"
_SORT_KEY = r"(?:\d{8}(?:-\d{6})?|\d{2,})(?:-[a-z0-9]+(?:-[a-z0-9]+)*)?"
_DATE = re.compile(r"(?P<date>\d{4})-?(?P<month>\d{2})-?(?P<day>\d{2})(?:-?(?P<time>\d{6}))?")
_SEQUENCE = re.compile(r"^(?P<sequence>\d{2,})(?:-|$)")
_MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\((?P<target><[^>]+>|[^)\s]+)(?:\s+[^)]*)?\)")
_LEGACY_FILE_TYPES = {
    "spec": "specs",
    "ticket": "tickets",
    "triage-brief": "triages",
    "prototype-findings": "prototypes",
}


class WorkArtifactError(RuntimeError):
    """Raised when a requested artifact migration cannot be applied safely."""


def _relative(repo: Path, path: Path) -> str:
    return path.relative_to(repo).as_posix()


def _canonical_path(repo: Path, path: Path) -> bool:
    try:
        parts = path.relative_to(repo).parts
    except ValueError:
        return False
    if len(parts) != 5 or parts[:2] != (".agent", "work"):
        return False
    topic, artifact_type, filename = parts[2:]
    stem = Path(filename).stem
    prefix = f"{artifact_type}-{topic}-"
    return bool(
        re.fullmatch(_NAME_PART, topic)
        and re.fullmatch(_NAME_PART, artifact_type)
        and stem.startswith(prefix)
        and re.fullmatch(_SORT_KEY, stem.removeprefix(prefix))
    )


def _sort_key(stem: str) -> str:
    date = _DATE.search(stem)
    if date:
        suffix = f"{date['date']}{date['month']}{date['day']}"
        return f"{suffix}-{date['time']}" if date["time"] else suffix
    sequence = _SEQUENCE.match(stem)
    return sequence["sequence"] if sequence else "01"


def _destination(repo: Path, path: Path) -> Path | None:
    """Return the canonical destination for a recognized legacy artifact."""
    parts = path.relative_to(repo).parts
    stem = path.stem
    extension = path.suffix
    if len(parts) == 5 and parts[:2] == (".agent", "work"):
        topic, artifact_type, _ = parts[2:]
        return repo / ".agent" / "work" / topic / artifact_type / f"{artifact_type}-{topic}-{_sort_key(stem)}{extension}"
    if len(parts) == 4 and parts[:2] == (".agent", "handoffs"):
        topic = parts[2]
        return repo / ".agent" / "work" / topic / "handoffs" / f"handoffs-{topic}-{_sort_key(stem)}{extension}"
    if len(parts) == 4 and parts[:2] == (".agent", "work"):
        topic, filename = parts[2:]
        artifact_type = _LEGACY_FILE_TYPES.get(Path(filename).stem)
        if artifact_type:
            return repo / ".agent" / "work" / topic / artifact_type / f"{artifact_type}-{topic}-{_sort_key(stem)}{extension}"
    return None


def _replacement_link(source: Path, target: Path) -> str:
    return posixpath.relpath(target, start=source.parent)


def _link_target(source: Path, link: str) -> tuple[Path, str] | None:
    if link.startswith(("#", "/")) or "://" in link or link.startswith("mailto:"):
        return None
    raw_target, separator, fragment = link.partition("#")
    if not raw_target:
        return None
    return (source.parent / raw_target).resolve(), f"{separator}{fragment}" if separator else ""


def _tools_candidate(repo: Path, link: str) -> Path | None:
    parts = Path(link.partition("#")[0]).parts
    if "tools" not in parts:
        return None
    candidate = repo.joinpath(*parts[parts.index("tools"):])
    return candidate if candidate.is_file() else None


def _rewrite_markdown_links(text: str, replacements: dict[str, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        target = match["target"]
        replacement = replacements.get(target.strip("<>"))
        return match[0] if replacement is None else match[0].replace(target, replacement, 1)

    return _MARKDOWN_LINK.sub(replace, text)


def _remove_empty_ancestors(path: Path, stop: Path) -> None:
    while path != stop:
        try:
            path.rmdir()
        except OSError:
            return
        path = path.parent


def _validate_rewritten_links(repo: Path, rewrites: list[dict[str, str]]) -> None:
    for rewrite in rewrites:
        source = repo / rewrite["new_source"]
        parsed = _link_target(source, rewrite["replacement"])
        if parsed is None or not parsed[0].is_file():
            raise WorkArtifactError(
                f"迁移后的链接目标不存在：{rewrite['new_source']} -> {rewrite['replacement']}"
            )


def analyze_work_artifacts(repo: Path) -> dict[str, object]:
    """Plan a migration without changing files."""
    repo = repo.resolve()
    agent_dir = repo / ".agent"
    if not agent_dir.is_dir():
        return {"compliant": True, "moves": [], "deletions": [], "link_rewrites": [], "candidate_link_repairs": [], "conflicts": [], "unclassified": []}

    moves_by_source: dict[Path, Path] = {}
    unclassified: list[str] = []
    for path in sorted(item for item in agent_dir.rglob("*") if item.is_file()):
        if path == agent_dir / "matt-workflow.md" or ".git" in path.parts:
            continue
        if _canonical_path(repo, path):
            continue
        destination = _destination(repo, path)
        if destination is None:
            unclassified.append(_relative(repo, path))
        else:
            moves_by_source[path.resolve()] = destination.resolve()

    moves = [{"from": _relative(repo, source), "to": _relative(repo, destination)} for source, destination in sorted(moves_by_source.items(), key=lambda item: _relative(repo, item[0]))]
    sources_by_destination: dict[Path, list[Path]] = {}
    for source, destination in moves_by_source.items():
        sources_by_destination.setdefault(destination, []).append(source)
    conflicts = [
        {"destination": _relative(repo, destination), "sources": sorted(_relative(repo, source) for source in sources), "existing": destination.is_file() and destination not in moves_by_source}
        for destination, sources in sorted(sources_by_destination.items(), key=lambda item: _relative(repo, item[0]))
        if len(sources) > 1 or (destination.is_file() and destination not in moves_by_source)
    ]

    link_rewrites: list[dict[str, str]] = []
    candidate_repairs: list[dict[str, str]] = []
    for source, new_source in sorted(moves_by_source.items(), key=lambda item: _relative(repo, item[0])):
        if source.suffix.lower() != ".md":
            continue
        for match in _MARKDOWN_LINK.finditer(source.read_text()):
            link = match["target"].strip("<>")
            parsed = _link_target(source, link)
            if parsed is not None:
                old_target, fragment = parsed
                if old_target.is_file():
                    new_target = moves_by_source.get(old_target, old_target)
                    link_rewrites.append({"source": _relative(repo, source), "new_source": _relative(repo, new_source), "link": link, "old_target": _relative(repo, old_target), "new_target": _relative(repo, new_target), "replacement": _replacement_link(new_source, new_target) + fragment})
                    continue
            candidate = _tools_candidate(repo, link)
            if candidate is not None:
                candidate_repairs.append({"source": _relative(repo, source), "new_source": _relative(repo, new_source), "link": link, "candidate_target": _relative(repo, candidate), "replacement": _replacement_link(new_source, candidate)})

    return {"compliant": not moves and not conflicts and not unclassified, "moves": moves, "deletions": [move["from"] for move in moves], "link_rewrites": link_rewrites, "candidate_link_repairs": candidate_repairs, "conflicts": conflicts, "unclassified": unclassified}


def apply_work_artifact_migration(repo: Path, *, confirmed_candidate_link_repairs: set[tuple[str, str]] | None = None) -> dict[str, object]:
    """Apply a reviewed layout plan, preserving unconfirmed broken links."""
    repo = repo.resolve()
    report = analyze_work_artifacts(repo)
    if report["conflicts"]:
        raise WorkArtifactError(f"迁移目标冲突：{report['conflicts']}")
    move_paths = [(repo / move["from"], repo / move["to"]) for move in report["moves"]]
    for source, destination in move_paths:
        if not source.is_file():
            raise WorkArtifactError(f"迁移源不存在：{_relative(repo, source)}")
        if destination.exists():
            raise WorkArtifactError(f"迁移目标已存在：{_relative(repo, destination)}")

    confirmed = confirmed_candidate_link_repairs or set()
    candidates_by_key = {(candidate["source"], candidate["link"]): candidate for candidate in report["candidate_link_repairs"]}
    unknown = confirmed - candidates_by_key.keys()
    if unknown:
        raise WorkArtifactError(f"不存在的候选链接修复：{sorted(unknown)}")
    rewrites = list(report["link_rewrites"]) + [candidates_by_key[key] for key in sorted(confirmed)]
    replacements_by_source: dict[str, dict[str, str]] = {}
    for rewrite in rewrites:
        replacements_by_source.setdefault(rewrite["new_source"], {})[rewrite["link"]] = rewrite["replacement"]
    for source, destination in move_paths:
        destination.parent.mkdir(parents=True, exist_ok=True)
        source.rename(destination)
        if replacements := replacements_by_source.get(_relative(repo, destination)):
            destination.write_text(_rewrite_markdown_links(destination.read_text(), replacements))
        _remove_empty_ancestors(source.parent, repo / ".agent")
    _validate_rewritten_links(repo, rewrites)
    return report
