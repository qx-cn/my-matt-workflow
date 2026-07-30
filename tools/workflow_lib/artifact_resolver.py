"""Read-only, bounded access to ignored ``.agent/work`` artifacts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


MAX_ARTIFACT_BYTES = 256 * 1024
_IDENTIFIER = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")


class ArtifactResolverError(RuntimeError):
    """Raised when an artifact request is unsafe or cannot be resolved."""


@dataclass(frozen=True)
class WorkArtifact:
    """A validated artifact whose path remains inside ``.agent/work``."""

    topic: str
    artifact_type: str
    path: Path
    work_root: Path

    @property
    def relative_path(self) -> str:
        return self.path.relative_to(self.work_root.parent.parent).as_posix()

    @property
    def size_bytes(self) -> int:
        return self.path.stat().st_size

    def as_dict(self) -> dict[str, str | int]:
        return {
            "topic": self.topic,
            "type": self.artifact_type,
            "path": self.relative_path,
            "size_bytes": self.size_bytes,
        }


def _identifier(value: str, name: str) -> str:
    if not _IDENTIFIER.fullmatch(value):
        raise ArtifactResolverError(f"非法{name}：{value!r}")
    return value


def _selector(value: str) -> str:
    if value == "latest" or value.isdecimal():
        return value
    candidate = Path(value)
    if (
        not value
        or "\x00" in value
        or candidate.is_absolute()
        or len(candidate.parts) != 1
        or value in {".", ".."}
    ):
        raise ArtifactResolverError(f"非法选择器：{value!r}")
    return value


def _work_root(repo: Path) -> Path:
    return repo.resolve() / ".agent" / "work"


def _ensure_contained(path: Path, work_root: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to(work_root):
        raise ArtifactResolverError(f"工作产物路径越界：{path}")
    if not resolved.is_file():
        raise ArtifactResolverError(f"工作产物不存在：{path.name}")
    return resolved


def _candidate_paths(
    repo: Path, topic: str, artifact_type: str
) -> list[Path]:
    work_root = _work_root(repo)
    if not work_root.is_dir():
        return []
    base = work_root / topic / artifact_type
    if not base.exists():
        return []
    _ensure_contained_directory(base, work_root)

    paths = [path for path in base.glob("*") if path.is_file()]
    if artifact_type == "domain":
        adr = base / "adr"
        if adr.exists():
            _ensure_contained_directory(adr, work_root)
            paths.extend(path for path in adr.glob("*") if path.is_file())
    return sorted(paths, key=lambda path: path.relative_to(work_root).as_posix())


def _ensure_contained_directory(path: Path, work_root: Path) -> None:
    if not path.resolve().is_relative_to(work_root):
        raise ArtifactResolverError(f"工作产物路径越界：{path}")
    if not path.is_dir():
        raise ArtifactResolverError(f"工作产物目录无效：{path}")


def list_work_artifacts(
    repo: Path, *, topic: str | None = None, artifact_type: str | None = None
) -> list[WorkArtifact]:
    """List direct topic/type artifacts, plus nested domain ADRs."""

    if topic is not None:
        _identifier(topic, "topic")
    if artifact_type is not None:
        _identifier(artifact_type, "type")

    work_root = _work_root(repo)
    if not work_root.is_dir():
        return []
    topics = [topic] if topic is not None else sorted(
        path.name for path in work_root.iterdir() if path.is_dir()
    )
    result: list[WorkArtifact] = []
    for current_topic in topics:
        _identifier(current_topic, "topic")
        topic_root = work_root / current_topic
        if not topic_root.exists():
            continue
        _ensure_contained_directory(topic_root, work_root)
        types = [artifact_type] if artifact_type is not None else sorted(
            path.name for path in topic_root.iterdir() if path.is_dir()
        )
        for current_type in types:
            _identifier(current_type, "type")
            for path in _candidate_paths(repo, current_topic, current_type):
                result.append(
                    WorkArtifact(
                        current_topic,
                        current_type,
                        _ensure_contained(path, work_root),
                        work_root,
                    )
                )
    return sorted(
        result,
        key=lambda artifact: (
            artifact.topic,
            artifact.artifact_type,
            artifact.relative_path,
        ),
    )


def _sort_key(artifact: WorkArtifact) -> tuple[int, str]:
    prefix = f"{artifact.artifact_type}-{artifact.topic}-"
    suffix = artifact.path.stem.removeprefix(prefix)
    match = re.match(r"(?P<key>\d{2,}(?:-\d{6})?)", suffix)
    return (1, match["key"]) if match else (0, suffix)


def _matches_sequence(artifact: WorkArtifact, sequence: str) -> bool:
    prefix = f"{artifact.artifact_type}-{artifact.topic}-{sequence}"
    suffix = artifact.path.stem.removeprefix(prefix)
    return artifact.path.stem.startswith(prefix) and (
        not suffix or suffix.startswith("-")
    )


def resolve_work_artifact(
    repo: Path, topic: str, artifact_type: str, selector: str = "latest"
) -> WorkArtifact:
    """Resolve ``latest``, a numeric sequence, or an exact filename."""

    _identifier(topic, "topic")
    _identifier(artifact_type, "type")
    selector = _selector(selector)
    artifacts = list_work_artifacts(
        repo, topic=topic, artifact_type=artifact_type
    )
    if selector == "latest":
        if not artifacts:
            raise ArtifactResolverError("没有可读取的工作产物")
        highest = max(_sort_key(artifact) for artifact in artifacts)
        matches = [
            artifact for artifact in artifacts if _sort_key(artifact) == highest
        ]
    elif selector.isdecimal():
        matches = [
            artifact
            for artifact in artifacts
            if _matches_sequence(artifact, selector)
        ]
    else:
        matches = [
            artifact
            for artifact in artifacts
            if artifact.path.name == selector
        ]
    if not matches:
        raise ArtifactResolverError(f"找不到工作产物：{selector}")
    if len(matches) != 1:
        raise ArtifactResolverError(
            f"工作产物选择存在歧义：{selector} -> "
            f"{', '.join(artifact.relative_path for artifact in matches)}"
        )
    return matches[0]


def read_work_artifact(artifact: WorkArtifact) -> str:
    """Read one validated Markdown artifact without permitting HTML or binary."""

    _ensure_contained(artifact.path, artifact.work_root)
    if artifact.size_bytes > MAX_ARTIFACT_BYTES:
        raise ArtifactResolverError(
            f"工作产物大小超过上限：{MAX_ARTIFACT_BYTES} bytes"
        )
    if artifact.path.suffix.lower() in {".htm", ".html"}:
        raise ArtifactResolverError("不允许读取 HTML 工作产物")
    try:
        content = artifact.path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ArtifactResolverError("工作产物不是 UTF-8 文本") from exc
    if content.lstrip().lower().startswith(("<!doctype html", "<html")):
        raise ArtifactResolverError("不允许读取 HTML 工作产物")
    return content
