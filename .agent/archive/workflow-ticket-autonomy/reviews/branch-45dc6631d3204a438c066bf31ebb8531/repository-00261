"""Checksum-verified, rollback-safe Skill installation."""

from __future__ import annotations

import hashlib
import copy
import json
import os
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .fs_safety import (
    FilesystemSafetyError,
    RELEASES_MUTATION_LOCK,
    exclusive_lock,
    quarantine_and_remove,
    refresh_owned_directory,
    register_owned_directory,
    strict_relative_path,
    verify_owned_directory,
    verify_owned_directory_identity,
)
from .release_references import REFERENCE_LOCK, remember_installation
from .projection import (
    TARGETS,
    directory_inventory,
    project_skill_directory,
    skills_inventory,
    projected_skills_inventory,
)


class InstallError(RuntimeError):
    """Raised when a release cannot be verified or installed safely."""


_MANAGED_SKILL = re.compile(r"my-[a-z0-9-]+")
_RELEASE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
_MANIFEST_FIELDS = {
    "release_id", "upstream_id", "skills", "runtime", "composed",
    "shared_resources", "resource_consumers", "target_manifests", "invocable_skills",
    "source_input_digest",
}


def _atomic_json_write(path: Path, value: dict) -> None:
    """Persist a recovery record before any user Skill is moved."""
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as handle:
            temporary = Path(handle.name)
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def _validated_journal(journal: object) -> tuple[int, list[str], set[str]]:
    if not isinstance(journal, dict):
        raise InstallError("安装事务日志损坏，需要人工检查")
    version = journal.get("version", 1)
    if version not in {1, 2, 3, 4}:
        raise InstallError("安装事务日志版本无效，需要人工检查")
    if version == 4:
        base_fields = {
            "version", "skills_home", "skills", "old_present",
            "new_release_id", "transaction_id",
        }
        migration_fields = {"previous_skills_home", "legacy_old_present"}
        recovery_fields = {"previous_state_sha256"}
        allowed_fields = {frozenset(base_fields | extra)
                          for extra in (set(), migration_fields, recovery_fields,
                                        migration_fields | recovery_fields)}
        if set(journal) not in allowed_fields:
            raise InstallError("安装事务日志 v4 schema 无效，需要人工检查")
        if "previous_state_sha256" in journal and journal["previous_state_sha256"] is not None:
            digest = journal["previous_state_sha256"]
            if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise InstallError("安装事务日志旧状态摘要无效，需要人工检查")
    skills = journal.get("skills")
    old_present = journal.get("old_present")
    if (
        not isinstance(skills, list)
        or not isinstance(old_present, list)
        or any(not isinstance(name, str) or not _MANAGED_SKILL.fullmatch(name) for name in skills)
        or len(set(skills)) != len(skills)
        or any(not isinstance(name, str) for name in old_present)
        or not set(old_present).issubset(skills)
    ):
        raise InstallError("安装事务日志包含非法 Skill，需要人工检查")
    return version, sorted(skills), set(old_present)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _skill_inventory(skill_dir: Path) -> dict[str, str]:
    if not skill_dir.is_dir() or skill_dir.is_symlink():
        raise InstallError(f"托管 Skill 目录无效：{skill_dir.name}")
    for path in sorted(skill_dir.rglob("*")):
        if path.is_symlink() or not (path.is_file() or path.is_dir()):
            raise InstallError(f"托管 Skill 包含 symlink 或非常规路径：{skill_dir.name}")
    return directory_inventory(skill_dir)




def _canonical_host_layout(state_home: Path, *, skills_home: Path | None = None,
                           release_id: str | None = None,
                           validate_default_skills: bool = True) -> tuple[Path, Path | None]:
    """Trust the explicitly selected root alias, never links inside that root."""
    selected = state_home.absolute()
    home = selected.resolve()
    if home.exists() and not home.is_dir():
        raise InstallError("安装宿主根目录无效")
    try:
        for relative in ("my-matt-workflow", "my-matt-workflow/runtime",
                         "my-matt-workflow/transaction"):
            path = strict_relative_path(home, relative)
            if path.exists() and not path.is_dir():
                raise InstallError("安装内部目录类型无效")
        for relative in ("my-matt-workflow/install-state.json",
                         "my-matt-workflow/.install.lock",
                         "my-matt-workflow/.my-matt-ownership.json"):
            path = strict_relative_path(home, relative)
            if path.exists() and not path.is_file():
                raise InstallError("安装内部状态路径类型无效")
        if release_id is not None:
            strict_relative_path(home, f"my-matt-workflow/runtime/{release_id}")
        if skills_home is None:
            if validate_default_skills:
                strict_relative_path(home, "skills")
            return home, None
        skills = skills_home.absolute()
        relative = None
        for selected_root in (selected, home):
            try:
                relative = skills.relative_to(selected_root)
                break
            except ValueError:
                pass
        if relative == Path("."):
            skills = home
        elif relative is not None:
            skills = strict_relative_path(home, relative)
        else:
            skills = skills.resolve()
        return home, skills
    except (FilesystemSafetyError, OSError, RuntimeError) as exc:
        raise InstallError("安装内部路径包含 symlink 或越出宿主根目录") from exc


def _recorded_directory(raw: str | Path, *, label: str) -> Path:
    """Validate a persisted canonical identity before resolution loses links.

    A newly selected user root may be canonicalized by the selection adapter;
    a persisted root already records that result and must not silently redirect.
    Missing directories can be legitimate during recovery of verified backups.
    """
    path = Path(raw)
    if not path.is_absolute() or any(part in {".", ".."} for part in path.parts):
        raise InstallError(f"{label}不是 canonical 绝对路径")
    if any(ancestor.is_symlink() for ancestor in (path, *path.parents)):
        raise InstallError(f"{label}的记录路径发生 symlink 漂移")
    if path != path.resolve():
        raise InstallError(f"{label}的记录路径身份已漂移")
    if path.exists() and not path.is_dir():
        raise InstallError(f"{label}不是目录")
    return path


def _verify_recorded_receipt_roots(state: dict[str, object]) -> None:
    _recorded_directory(str(state["skills_home"]), label="旧 Skill 根")
    _recorded_directory(Path(str(state["runtime_entry"])).parent.parent,
                        label="旧 runtime 根")

def _runtime_inventory(runtime_root: Path) -> dict[str, str]:
    """Reject path/link drift before ignoring defined execution by-products."""
    if not runtime_root.is_dir() or runtime_root.is_symlink():
        raise InstallError("托管 runtime 目录或路径无效")
    if any(path.is_symlink() or not (path.is_file() or path.is_dir())
           for path in runtime_root.rglob("*")):
        raise InstallError("托管 runtime 包含 symlink 或非常规路径")
    return directory_inventory(runtime_root)


def _verify_runtime_state(state: dict[str, object], expected: dict[str, str],
                          *, state_home: Path | None = None) -> None:
    runtime_entry = Path(str(state["runtime_entry"]))
    runtime_root = _recorded_directory(runtime_entry.parent.parent, label="托管 runtime 根")
    if runtime_entry != runtime_root / "tools/workflow.py":
        raise InstallError("托管 runtime 入口路径无效")
    if state_home is not None:
        expected_root = state_home.resolve() / "my-matt-workflow/runtime" / str(state["release_id"])
        if runtime_root != expected_root:
            raise InstallError("托管 runtime 入口不属于安装目录")
    if _runtime_inventory(runtime_root) != expected:
        raise InstallError("已安装 runtime 与 release 内容不一致")

def load_install_state(path: Path) -> dict[str, object] | None:
    """Load and strictly validate a persisted installer ownership receipt."""
    if not path.exists():
        return None
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InstallError("安装状态损坏，需要人工检查") from exc
    if not isinstance(state, dict):
        raise InstallError("安装状态损坏，需要人工检查")
    version = state.get("version", 1)
    common = {
        "release_id", "source", "skills", "installed_at", "transaction_id",
        "installed_agent", "metadata_projection", "skills_home", "runtime_entry",
    }
    allowed = common if version == 1 else common | {"version", "managed_inventory", "manifest_sha256"}
    if version not in {1, 2} or set(state) != allowed:
        raise InstallError("安装状态 schema 或版本无效，需要人工检查")
    release_id = state.get("release_id")
    skills = state.get("skills")
    source = state.get("source")
    skills_home = state.get("skills_home")
    runtime_entry = state.get("runtime_entry")
    installed_agent = state.get("installed_agent")
    projection = state.get("metadata_projection")
    if (
        not isinstance(release_id, str)
        or not _RELEASE_ID.fullmatch(release_id)
        or not isinstance(skills, list)
        or len(set(skills)) != len(skills)
        or any(not isinstance(name, str) or not _MANAGED_SKILL.fullmatch(name) for name in skills)
        or not isinstance(source, str)
        or not Path(source).is_absolute()
        or not isinstance(skills_home, str)
        or not Path(skills_home).is_absolute()
        or not isinstance(runtime_entry, str)
        or not Path(runtime_entry).is_absolute()
        or not isinstance(state.get("transaction_id"), str)
        or not isinstance(state.get("installed_at"), str)
        or not state["installed_at"].strip()
        or installed_agent not in {None, "cursor", "claude", "codex"}
        or projection not in {"portable", "cursor", "claude", "codex"}
        or (projection == "portable" and installed_agent is not None)
        or (projection != "portable" and installed_agent != projection)
    ):
        raise InstallError("安装状态字段无效，需要人工检查")
    if version == 2:
        inventory = state.get("managed_inventory")
        if (
            not isinstance(inventory, dict)
            or set(inventory) != set(skills)
            or any(not isinstance(files, dict) for files in inventory.values())
            or not isinstance(state.get("manifest_sha256"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", str(state.get("manifest_sha256")))
        ):
            raise InstallError("安装状态 ownership inventory 无效")
        validation_root = Path(tempfile.gettempdir()).resolve()
        for files in inventory.values():
            assert isinstance(files, dict)
            for relative, digest in files.items():
                if not isinstance(relative, str) or not isinstance(digest, str):
                    raise InstallError("安装状态 ownership inventory 条目无效")
                try:
                    strict_relative_path(validation_root, relative)
                except FilesystemSafetyError as exc:
                    raise InstallError("安装状态 ownership inventory 路径无效") from exc
                if not re.fullmatch(r"[0-9a-f]{64}", digest):
                    raise InstallError("安装状态 ownership inventory digest 无效")
    return state


def verify_installed_state(state: dict[str, object], *,
                           validation_context: ReleaseValidationContext | None = None,
                           state_home: Path | None = None) -> None:
    """Verify that a state receipt still owns the installed Skill bytes."""
    verify = validation_context.verify if validation_context else verify_release
    skills_home = _recorded_directory(str(state["skills_home"]), label="托管 Skill 根")
    skills = list(state["skills"])
    if state.get("version", 1) == 2:
        inventory = state["managed_inventory"]
        assert isinstance(inventory, dict)
        source = Path(str(state["source"]))
        source_release = verify(source)
        if (
            source_release.get("release_id") != state["release_id"]
            or set(source_release["skills"]) != set(skills)
        ):
            raise InstallError("安装状态与 source release 不一致")
        target_manifests = source_release.get("target_manifests")
        expected_target = (
            target_manifests[str(state["metadata_projection"])]
            if isinstance(target_manifests, dict)
            else {"skills": projected_skills_inventory(source / "skills", str(state["metadata_projection"])),
                  "runtime": source_release["runtime"]}
        )
        if inventory != expected_target["skills"]:
            raise InstallError("安装状态 inventory 与 release target manifest 不一致")
        for name in skills:
            target = strict_relative_path(skills_home, name, direct_child=True)
            if _skill_inventory(target) != inventory[name]:
                raise InstallError(f"托管 Skill ownership 已漂移：{name}")
        source_manifest = source / "manifest.json"
        if not source_manifest.is_file() or sha256_file(source_manifest) != state["manifest_sha256"]:
            raise InstallError("安装状态引用的 release manifest 已漂移")
        _verify_runtime_state(state, expected_target["runtime"], state_home=state_home)
        return
    # Legacy receipts are accepted only when their immutable source release is
    # still available and proves the exact managed name set.
    source = Path(str(state["source"]))
    previous = verify(source)
    if previous.get("release_id") != state["release_id"] or set(previous["skills"]) != set(skills):
        raise InstallError("旧安装状态与 source release 不一致")
    projection = str(state["metadata_projection"])
    with tempfile.TemporaryDirectory(prefix="my-matt-legacy-install-state-") as tmp:
        staging = Path(tmp)
        for name in skills:
            staged = staging / name
            shutil.copytree(source / "skills" / name, staged)
            _project_skill_metadata_for_target(
                staged, None if projection == "portable" else projection
            )
            target = strict_relative_path(skills_home, name, direct_child=True)
            if _skill_inventory(target) != _skill_inventory(staged):
                raise InstallError(f"旧安装状态无法证明托管 Skill ownership：{name}")

    _verify_runtime_state(state, previous["runtime"], state_home=state_home)


def _projected_release_inventories(state: dict[str, object]) -> dict[str, dict[str, str]]:
    """Derive byte inventories for a legacy host projection."""
    source = Path(str(state["source"]))
    manifest = verify_release(source)
    skills = list(state["skills"])
    if manifest.get("release_id") != state["release_id"] or set(manifest["skills"]) != set(skills):
        raise InstallError("旧安装状态与 source release 不一致")
    projection = str(state["metadata_projection"])
    result = projected_skills_inventory(source / "skills", projection)
    if state.get("version", 1) == 2 and (
        sha256_file(source / "manifest.json") != state["manifest_sha256"]
        or result != state["managed_inventory"]
    ):
        raise InstallError("旧安装状态与 source release ownership 已漂移")
    return result


def load_manifest(release: Path) -> dict:
    try:
        manifest = json.loads((release / "manifest.json").read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise InstallError("release manifest 无法读取") from exc
    if not isinstance(manifest, dict):
        raise InstallError("release manifest 顶层必须是对象")
    release_id = manifest.get("release_id")
    if (
        not isinstance(release_id, str)
        or not _RELEASE_ID.fullmatch(release_id)
        or not isinstance(manifest.get("skills"), dict)
        or not isinstance(manifest.get("runtime"), dict)
    ):
        raise InstallError("release manifest 的 release_id、skills 或 runtime 无效")
    if release.name != release_id:
        raise InstallError("release manifest 的 release_id 与目录名不一致")
    invocable = manifest.get("invocable_skills", [])
    if (not isinstance(invocable, list) or any(not isinstance(n, str) for n in invocable)
            or len(invocable) != len(set(invocable)) or not set(invocable) <= set(manifest["skills"])):
        raise InstallError("release invocable_skills 与 Skill 集合不一致")
    if set(manifest) - _MANIFEST_FIELDS:
        raise InstallError("release manifest 包含未知字段")
    if "source_input_digest" in manifest and (
        not isinstance(manifest["source_input_digest"], str) or
        not re.fullmatch(r"[0-9a-f]{64}", manifest["source_input_digest"])
    ):
        raise InstallError("release source_input_digest 无效")
    return manifest


class ReleaseValidationContext:
    """One operation only; a fresh byte identity guards every cached use.

    Callers performing mutations hold the release-reference lock. Read-only
    callers get drift detection before and after full validation instead.
    """
    def __init__(self):
        self._validated = {}

    def verify(self, release: Path) -> dict:
        identity = self._identity(release)
        key = str(release.resolve())
        cached = self._validated.get(key)
        if cached is not None and cached[0] == identity:
            return copy.deepcopy(cached[1])
        manifest = verify_release(release)
        if self._identity(release) != identity:
            raise InstallError("release 在验证期间发生漂移")
        self._validated[key] = (identity, copy.deepcopy(manifest))
        return manifest

    @staticmethod
    def _identity(release):
        if not release.is_dir() or release.is_symlink():
            raise InstallError("release 目录无效或为 symlink")
        paths = sorted(release.rglob("*"))
        if any(path.is_symlink() for path in paths):
            raise InstallError("release 不能包含 symlink")
        stat = release.stat()
        return (stat.st_dev, stat.st_ino,
                tuple((str(path.relative_to(release)),
                       sha256_file(path) if path.is_file() else "directory")
                      for path in paths))


def verify_release(release: Path, manifest: dict | None = None) -> dict:
    if not release.is_dir() or release.is_symlink():
        raise InstallError("release 目录无效或为 symlink")
    if any(path.is_symlink() for path in release.rglob("*")):
        raise InstallError("release 不能包含 symlink")
    manifest = manifest or load_manifest(release)
    if manifest.get("release_id") != release.name:
        raise InstallError("release manifest 的 release_id 与目录名不一致")
    expected_root = {"manifest.json", "skills", "runtime"}
    actual_root = {path.name for path in release.iterdir()} if release.is_dir() else set()
    if actual_root != expected_root:
        raise InstallError("release 根目录文件集合不一致")
    skills_root = release / "skills"
    actual_skills = (
        {path.name for path in skills_root.iterdir()}
        if skills_root.is_dir() and not skills_root.is_symlink()
        else set()
    )
    if actual_skills != set(manifest["skills"]):
        raise InstallError("release Skill 目录集合不一致")
    for skill_name, files in manifest["skills"].items():
        if not isinstance(skill_name, str) or not _MANAGED_SKILL.fullmatch(skill_name):
            raise InstallError(f"非法 Skill 名称：{skill_name}")
        if not isinstance(files, dict):
            raise InstallError(f"{skill_name}: manifest 文件清单无效")
        expected_paths: set[str] = set()
        for relative, expected in files.items():
            if (
                not isinstance(relative, str)
                or not isinstance(expected, str)
                or not re.fullmatch(r"[0-9a-f]{64}", expected)
            ):
                raise InstallError(f"{skill_name}: manifest 文件条目无效")
            try:
                validation_root = Path(tempfile.gettempdir()).resolve()
                relative_path = strict_relative_path(
                    validation_root, relative
                ).relative_to(validation_root)
            except (FilesystemSafetyError, ValueError) as exc:
                raise InstallError(f"非法文件路径：{relative}")
            expected_paths.add(str(relative_path))
        skill_dir = release / "skills" / skill_name
        actual_paths = {
            str(path.relative_to(skill_dir))
            for path in skill_dir.rglob("*")
            if path.is_file() and not path.is_symlink()
        } if skill_dir.is_dir() else set()
        if actual_paths != expected_paths:
            extra = sorted(actual_paths - expected_paths)
            missing = sorted(expected_paths - actual_paths)
            details = []
            if extra:
                details.append(f"额外文件：{', '.join(extra)}")
            if missing:
                details.append(f"缺少文件：{', '.join(missing)}")
            raise InstallError(
                f"{skill_name}: release 文件集合不一致；"
                + "；".join(details)
            )
        for relative, expected in files.items():
            relative_path = Path(relative)
            source = release / "skills" / skill_name / relative_path
            if not source.is_file() or sha256_file(source) != expected:
                raise InstallError(f"校验失败：{skill_name}/{relative}")
    runtime_dir = release / "runtime"
    expected_runtime = set(manifest["runtime"])
    if runtime_dir.is_symlink():
        raise InstallError("release runtime 不能是 symlink")
    actual_runtime = {
        str(path.relative_to(runtime_dir))
        for path in runtime_dir.rglob("*")
        if path.is_file() and not path.is_symlink()
    } if runtime_dir.is_dir() else set()
    if actual_runtime != expected_runtime:
        raise InstallError("release runtime 文件集合不一致")
    if "tools/workflow.py" not in expected_runtime:
        raise InstallError("release runtime 缺少 tools/workflow.py")
    for relative, expected in manifest["runtime"].items():
        if (
            not isinstance(relative, str)
            or not isinstance(expected, str)
            or not re.fullmatch(r"[0-9a-f]{64}", expected)
        ):
            raise InstallError("runtime manifest 条目无效")
        try:
            validation_root = Path(tempfile.gettempdir()).resolve()
            relative_path = strict_relative_path(
                validation_root, relative
            ).relative_to(validation_root)
        except (FilesystemSafetyError, ValueError) as exc:
            raise InstallError(f"非法 runtime 文件路径：{relative}")
        source = runtime_dir / relative_path
        if not source.is_file() or sha256_file(source) != expected:
            raise InstallError(f"runtime 校验失败：{relative}")
    resource_consumers = manifest.get("resource_consumers")
    if resource_consumers is not None:
        if (
            not isinstance(resource_consumers, dict)
            or set(resource_consumers) != {"direct", "effective"}
            or not all(
                isinstance(resource_consumers[layer], dict)
                for layer in ("direct", "effective")
            )
            or set(resource_consumers["direct"])
            != set(resource_consumers["effective"])
        ):
            raise InstallError("release resource_consumers schema 无效")
        known_skills = set(manifest["skills"])
        for resource_name, direct in resource_consumers["direct"].items():
            effective = resource_consumers["effective"][resource_name]
            if (
                not isinstance(resource_name, str)
                or not resource_name
                or not isinstance(direct, list)
                or not isinstance(effective, list)
                or any(
                    not isinstance(skill, str)
                    or not _MANAGED_SKILL.fullmatch(skill)
                    for skill in [*direct, *effective]
                )
                or direct != sorted(set(direct))
                or effective != sorted(set(effective))
                or not set(direct).issubset(effective)
                or not set(effective).issubset(known_skills)
            ):
                raise InstallError(
                    f"release resource_consumers 条目无效：{resource_name}"
                )
    target_manifests = manifest.get("target_manifests")
    if target_manifests is not None:
        if not isinstance(target_manifests, dict) or set(target_manifests) != set(TARGETS):
            raise InstallError("release target_manifests 目标集合无效")
        validation_root = Path(tempfile.gettempdir()).resolve()
        for target in TARGETS:
            target_manifest = target_manifests[target]
            if not isinstance(target_manifest, dict) or set(target_manifest) != {"skills", "runtime"}:
                raise InstallError(f"release {target} target manifest schema 无效")
            projected_skills = target_manifest["skills"]
            projected_runtime = target_manifest["runtime"]
            if (
                not isinstance(projected_skills, dict)
                or set(projected_skills) != set(manifest["skills"])
                or not isinstance(projected_runtime, dict)
            ):
                raise InstallError(f"release {target} target manifest inventory 无效")
            for files in projected_skills.values():
                if not isinstance(files, dict):
                    raise InstallError(f"release {target} Skill inventory 无效")
                for relative, digest in files.items():
                    if not isinstance(relative, str) or not isinstance(digest, str):
                        raise InstallError(f"release {target} Skill entry 无效")
                    try:
                        strict_relative_path(validation_root, relative)
                    except FilesystemSafetyError as exc:
                        raise InstallError(f"release {target} Skill path 无效") from exc
                    if not re.fullmatch(r"[0-9a-f]{64}", digest):
                        raise InstallError(f"release {target} Skill digest 无效")
            for relative, digest in projected_runtime.items():
                if not isinstance(relative, str) or not isinstance(digest, str):
                    raise InstallError(f"release {target} runtime entry 无效")
                try:
                    strict_relative_path(validation_root, relative)
                except FilesystemSafetyError as exc:
                    raise InstallError(f"release {target} runtime path 无效") from exc
                if not re.fullmatch(r"[0-9a-f]{64}", digest):
                    raise InstallError(f"release {target} runtime digest 无效")
        portable = target_manifests["portable"]
        if portable["skills"] != manifest["skills"] or portable["runtime"] != manifest["runtime"]:
            raise InstallError("portable target manifest 与 release 内容不一致")
        for target in TARGETS:
            projected_skills = (manifest["skills"] if target == "portable" else
                                projected_skills_inventory(skills_root, target))
            if (
                target_manifests[target]["skills"] != projected_skills
                or target_manifests[target]["runtime"] != manifest["runtime"]
            ):
                raise InstallError(
                    f"release {target} target manifest 与确定性投影不一致"
                )
    return manifest


def remove_verified_release(releases_dir: Path, release: Path) -> None:
    """Delete only a complete, direct-child immutable release."""
    releases_dir = releases_dir.resolve()
    try:
        candidate = strict_relative_path(
            releases_dir, release.name, direct_child=True
        )
    except FilesystemSafetyError as exc:
        raise InstallError("release prune 目标越界") from exc
    if candidate.resolve() != release.resolve():
        raise InstallError("release prune 目标不属于 releases root")
    verify_release(candidate)
    try:
        with exclusive_lock(releases_dir, RELEASES_MUTATION_LOCK):
            quarantine_and_remove(
                releases_dir,
                candidate,
                purpose="release",
            )
    except FilesystemSafetyError as exc:
        raise InstallError(str(exc)) from exc


def validate_skill_metadata_for_target(
    skill_dir: Path, target: str, *, invocable: bool = False
) -> None:
    """Enforce target-specific manual invocation metadata."""
    if target not in {"cursor", "claude", "codex"}:
        raise InstallError(f"未知安装目标：{target}")
    if target in {"cursor", "claude"}:
        skill_file = skill_dir / "SKILL.md"
        text = skill_file.read_text() if skill_file.is_file() else ""
        text = text.split("---", 2)[1] if text.startswith("---") and len(text.split("---", 2)) == 3 else ""
        disabled = re.search(r"(?m)^disable-model-invocation:\s*(\S+)\s*$", text)
        if (disabled is not None if invocable else disabled is None or disabled.group(1) != "true"):
            raise InstallError(
                f"{skill_dir.name}: {target} 目标要求 "
                "disable-model-invocation: true"
            )
        return
    metadata = skill_dir / "agents" / "openai.yaml"
    text = metadata.read_text() if metadata.is_file() else ""
    expected = "true" if invocable else "false"
    if not re.search(
        rf"(?m)^\s*allow_implicit_invocation:\s*{expected}\s*$", text
    ):
        raise InstallError(
            f"{skill_dir.name}: agents/openai.yaml 缺少 "
            f"allow_implicit_invocation: {expected}"
        )


def _project_skill_metadata_for_target(skill_dir: Path, target: str | None) -> None:
    """Project host metadata and portable explicit-invocation macros."""
    projection = target or "portable"
    if projection not in TARGETS:
        raise InstallError(f"未知安装目标：{projection}")
    project_skill_directory(skill_dir, projection)


def _remove_path(path: Path) -> None:
    if path.is_symlink():
        raise InstallError(f"拒绝删除 symlink 目标：{path}")
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()



def _verify_rollback_materials(transaction: Path, skills_home: Path,
                               skills: list[str], old_present: set[str],
                               previous_skills_home: Path | None,
                               legacy_old_present: list[str],
                               previous: dict[str, object] | None,
                               *, state_home: Path) -> None:
    """Prove each old byte source, allowing interruption between any moves.

    Whole transaction digests cannot establish this: staging and move phases
    legitimately change it before its ownership registration is refreshed.
    """
    if any(path.is_symlink() or not (path.is_file() or path.is_dir())
           for path in transaction.rglob("*")):
        raise InstallError("安装事务包含不允许的链接或非常规恢复路径")
    inventories = _projected_release_inventories(previous) if previous else {}
    if previous is not None:
        source = Path(str(previous["source"]))
        manifest = load_manifest(source)
        _verify_runtime_state(previous, manifest["runtime"], state_home=state_home)
    names = set(inventories)
    if not names.issubset(skills):
        raise InstallError("恢复材料与旧 install-state Skill 集合不一致")
    old_home = previous_skills_home or skills_home
    if previous is not None and _recorded_directory(
        str(previous["skills_home"]), label="旧恢复 Skill 根") != old_home:
        raise InstallError("恢复材料与旧 install-state home 不一致")
    if previous_skills_home is None:
        if old_present != names or legacy_old_present:
            raise InstallError("恢复材料无法证明旧目标所有权")
    elif old_present or set(legacy_old_present) != names:
        raise InstallError("恢复材料无法证明迁移目标所有权")
    backup_root = transaction / ("legacy-backup" if previous_skills_home else "backup")
    for folder in (transaction / "backup", transaction / "legacy-backup"):
        allowed = names if folder == backup_root else set()
        if folder.is_symlink() or (folder.exists() and not folder.is_dir()):
            raise InstallError("恢复 backup 路径无效")
        if folder.exists():
            for backup in folder.iterdir():
                if backup.name not in allowed or _skill_inventory(backup) != inventories[backup.name]:
                    raise InstallError(f"恢复无法证明 backup ownership：{backup.name}")
    for name in names:
        backup = backup_root / name
        if not backup.exists():
            target = strict_relative_path(old_home, name, direct_child=True)
            if _skill_inventory(target) != inventories[name]:
                raise InstallError(f"恢复无法证明尚未移动的旧目标：{name}")

def recover_interrupted_install(
    state_home: Path, *, skills_home: Path | None = None
) -> None:
    """Restore the previous install from a persisted transaction journal."""
    state_home, skills_home = _canonical_host_layout(
        state_home, skills_home=skills_home, validate_default_skills=False)
    transaction = state_home / "my-matt-workflow" / "transaction"
    journal_path = transaction / "journal.json"
    if not journal_path.exists():
        if transaction.exists():
            raise InstallError("安装事务日志缺失，需要人工检查")
        return
    try:
        journal = json.loads(journal_path.read_text())
    except json.JSONDecodeError as exc:
        raise InstallError("安装事务日志损坏，需要人工检查") from exc

    state_path = state_home / "my-matt-workflow" / "install-state.json"
    state: dict = {}
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text())
        except json.JSONDecodeError as exc:
            raise InstallError("安装状态损坏，需要人工检查") from exc
        if not isinstance(state, dict):
            raise InstallError("安装状态损坏，需要人工检查")
    version, skills, old_present = _validated_journal(journal)
    if version == 4:
        try:
            verify_owned_directory_identity(
                state_path.parent,
                transaction,
                purpose="install-transaction",
                required_controls=("journal.json",),
            )
        except FilesystemSafetyError as exc:
            raise InstallError(
                "安装事务缺少可信 ownership capability，需要人工检查"
            ) from exc
    if version in {2, 3, 4}:
        recorded = journal.get("skills_home")
        if (
            not isinstance(recorded, str)
            or not Path(recorded).is_absolute()
            or not isinstance(journal.get("new_release_id"), str)
            or not isinstance(journal.get("transaction_id"), str)
        ):
            raise InstallError(f"安装事务日志 v{version} 无效，需要人工检查")
        recorded_home = _recorded_directory(recorded, label="恢复 Skill 根")
        if skills_home is not None and skills_home.resolve() != recorded_home:
            raise InstallError("恢复目录与安装事务不一致，拒绝操作")
        skills_home = recorded_home
    else:
        recorded = state.get("skills_home")
        if isinstance(recorded, str) and Path(recorded).is_absolute():
            recorded_home = _recorded_directory(recorded, label="旧恢复 Skill 根")
            if skills_home is not None and skills_home.resolve() != recorded_home:
                raise InstallError("恢复目录与安装状态不一致，拒绝操作")
            skills_home = recorded_home
        elif skills_home is None:
            raise InstallError("旧安装事务缺少 skills_home；请明确指定恢复目录")

    assert skills_home is not None
    previous_skills_home: Path | None = None
    legacy_old_present: list[str] = []
    if version == 3 or (
        version == 4 and "previous_skills_home" in journal
    ):
        recorded_previous = journal.get("previous_skills_home")
        legacy_old_present = journal.get("legacy_old_present")
        if (
            not isinstance(recorded_previous, str)
            or not Path(recorded_previous).is_absolute()
            or not isinstance(legacy_old_present, list)
            or any(not isinstance(name, str) for name in legacy_old_present)
            or not set(legacy_old_present).issubset(skills)
        ):
            raise InstallError("安装事务日志 v3 迁移信息无效，需要人工检查")
        previous_skills_home = _recorded_directory(recorded_previous, label="旧迁移 Skill 根")
    elif version == 4 and "legacy_old_present" in journal:
        raise InstallError("安装事务日志 v4 迁移信息无效，需要人工检查")
    transaction_id = journal.get("transaction_id")
    if version < 4:
        trusted_state = load_install_state(state_path)
        if trusted_state is None:
            raise InstallError(
                "旧安装事务没有可验证 install-state，需要人工检查"
            )
        inventories = _projected_release_inventories(trusted_state)
        previous_names = set(trusted_state["skills"])
        if not previous_names.issubset(skills):
            raise InstallError("旧安装事务与 install-state Skill 集合不一致")
        trusted_home = _recorded_directory(str(trusted_state["skills_home"]),
                                           label="旧安装状态 Skill 根")
        if previous_skills_home is None and trusted_home != skills_home.resolve():
            raise InstallError("旧安装事务与 install-state home 不一致")
        if previous_skills_home is not None and trusted_home != previous_skills_home:
            raise InstallError("旧迁移事务与 install-state home 不一致")
        for skill_name in sorted(previous_names):
            backup_root = (
                transaction / "legacy-backup"
                if previous_skills_home is not None
                else transaction / "backup"
            )
            backup = backup_root / skill_name
            if not backup.is_dir() or _skill_inventory(backup) != inventories[skill_name]:
                raise InstallError(
                    f"旧安装事务无法证明 backup ownership：{skill_name}"
                )
        for skill_name in sorted(set(skills) - previous_names):
            target = strict_relative_path(skills_home, skill_name, direct_child=True)
            if target.exists():
                raise InstallError(
                    f"旧安装事务无法证明新增 Skill ownership：{skill_name}"
                )
    if version == 4:
        if transaction_id and state.get("transaction_id") == transaction_id:
            committed = load_install_state(state_path)
            if committed is None:
                raise InstallError("已提交事务缺少可验证安装状态")
            verify_installed_state(committed, state_home=state_home)
        else:
            if "previous_state_sha256" in journal:
                expected_state = journal["previous_state_sha256"]
                actual_state = sha256_file(state_path) if state_path.is_file() else None
                if actual_state != expected_state:
                    raise InstallError("安装事务的旧 install-state 已漂移，保留恢复材料")
            previous = load_install_state(state_path)
            _verify_rollback_materials(transaction, skills_home, skills, old_present,
                                       previous_skills_home, legacy_old_present, previous,
                                       state_home=state_home)
    if transaction_id and state.get("transaction_id") == transaction_id:
        if version == 4:
            refresh_owned_directory(
                state_path.parent, transaction, purpose="install-transaction"
            )
            quarantine_and_remove(
                state_path.parent, transaction, purpose="install-transaction"
            )
        else:
            shutil.rmtree(transaction)
        return

    for skill_name in skills:
        target = strict_relative_path(skills_home, skill_name, direct_child=True)
        backup = transaction / "backup" / skill_name
        if backup.exists():
            _remove_path(target)
            backup.rename(target)
        elif skill_name not in old_present:
            _remove_path(target)
    if previous_skills_home is not None:
        legacy_backup = transaction / "legacy-backup"
        for skill_name in legacy_old_present:
            backup = legacy_backup / skill_name
            if backup.exists():
                target = strict_relative_path(
                    previous_skills_home, skill_name, direct_child=True
                )
                _remove_path(target)
                target.parent.mkdir(parents=True, exist_ok=True)
                backup.rename(target)
    if version == 4:
        refresh_owned_directory(
            state_path.parent, transaction, purpose="install-transaction"
        )
        quarantine_and_remove(
            state_path.parent, transaction, purpose="install-transaction"
        )
    else:
        shutil.rmtree(transaction)


def _install_release(
    release: Path,
    state_home: Path,
    *,
    target: str | None = None,
    skills_home: Path | None = None,
    validation_context: ReleaseValidationContext | None = None,
) -> str:
    """Install one immutable release, restoring the old install on failure."""
    state_home, skills_home = _canonical_host_layout(
        state_home, skills_home=skills_home, release_id=release.name)
    context = validation_context or ReleaseValidationContext()
    manifest = context.verify(release)
    install_target = target
    projection_name = install_target or "portable"
    target_manifests = manifest.get("target_manifests")
    expected_target = (
        target_manifests[projection_name]
        if isinstance(target_manifests, dict)
        else {"skills": projected_skills_inventory(release / "skills", projection_name),
              "runtime": manifest["runtime"]}
    )
    if install_target is not None:
        for skill_name in sorted(manifest["skills"]):
            validate_skill_metadata_for_target(
                release / "skills" / skill_name, install_target,
                invocable=skill_name in manifest.get("invocable_skills", [])
            )
    state_dir = state_home / "my-matt-workflow"
    state_path = state_dir / "install-state.json"
    existing = load_install_state(state_path)
    if existing is not None:
        _verify_recorded_receipt_roots(existing)
    state_home.mkdir(parents=True, exist_ok=True)
    skills_home = skills_home or state_home / "skills"
    skills_home.mkdir(parents=True, exist_ok=True)
    state_dir.mkdir(parents=True, exist_ok=True)
    recover_interrupted_install(state_home, skills_home=skills_home)

    loaded_previous = load_install_state(state_path)
    previous_state: dict[str, object] = loaded_previous or {}
    if previous_state:
        verify_installed_state(previous_state, validation_context=context, state_home=state_home)
        if (previous_state.get("version") == 2 and
            previous_state.get("source") == str(release.resolve()) and
            previous_state.get("manifest_sha256") == sha256_file(release / "manifest.json") and
            previous_state.get("metadata_projection") == projection_name and
            previous_state.get("skills_home") == str(skills_home.resolve())):
            return "current"

    previous_managed = set(previous_state.get("skills", []))
    previous_skills_home: Path | None = None
    recorded_previous_home = previous_state.get("skills_home")
    if isinstance(recorded_previous_home, str) and Path(recorded_previous_home).is_absolute():
        candidate = _recorded_directory(recorded_previous_home, label="旧迁移 Skill 根")
        if candidate != skills_home.resolve():
            previous_skills_home = candidate
    for skill_name in manifest["skills"]:
        destination = strict_relative_path(
            skills_home, skill_name, direct_child=True
        )
        if destination.exists() and skill_name not in previous_managed:
            raise InstallError(f"发现同名非托管 Skill，拒绝覆盖：{skill_name}")

    managed = previous_managed | set(manifest["skills"])
    transaction_id = str(uuid4())
    old_present = [
        skill_name
        for skill_name in sorted(managed)
        if strict_relative_path(skills_home, skill_name, direct_child=True).exists()
    ]
    journal = {
        "version": 4,
        "skills_home": str(skills_home.resolve()),
        "skills": sorted(managed),
        "old_present": old_present,
        "new_release_id": manifest["release_id"],
        "transaction_id": transaction_id,
        "previous_state_sha256": sha256_file(state_path) if previous_state else None,
    }
    legacy_old_present: list[str] = []
    if previous_skills_home is not None:
        legacy_old_present = [
            skill_name
            for skill_name in sorted(previous_managed)
            if (previous_skills_home / skill_name).exists()
        ]
        journal.update(
            {
                "version": 4,
                "previous_skills_home": str(previous_skills_home),
                "legacy_old_present": legacy_old_present,
            }
        )
    transaction = state_dir / "transaction"
    staged = transaction / "staged"
    backup = transaction / "backup"
    staged.mkdir(parents=True)
    backup.mkdir()
    _atomic_json_write(transaction / "journal.json", journal)
    register_owned_directory(
        state_dir,
        transaction,
        purpose="install-transaction",
        control_paths=("journal.json",),
    )
    staged_runtime = transaction / "staged-runtime"
    try:
        for skill_name in manifest["skills"]:
            shutil.copytree(release / "skills" / skill_name, staged / skill_name)
            _project_skill_metadata_for_target(staged / skill_name, install_target)
        shutil.copytree(release / "runtime", staged_runtime)
        if expected_target is not None and (
            skills_inventory(staged) != expected_target["skills"]
            or _runtime_inventory(staged_runtime) != expected_target["runtime"]
        ):
            raise InstallError(
                f"{projection_name} target manifest 与安装 staging 不一致"
            )
        refresh_owned_directory(
            state_dir, transaction, purpose="install-transaction"
        )
    except Exception:
        if transaction.exists():
            refresh_owned_directory(
                state_dir, transaction, purpose="install-transaction"
            )
            quarantine_and_remove(
                state_dir, transaction, purpose="install-transaction"
            )
        raise

    try:
        for skill_name in sorted(managed):
            destination = strict_relative_path(
                skills_home, skill_name, direct_child=True
            )
            if destination.exists():
                destination.rename(backup / skill_name)
            if skill_name in manifest["skills"]:
                (staged / skill_name).rename(destination)

        if previous_skills_home is not None:
            _recorded_directory(previous_skills_home, label="旧迁移 Skill 根")
            legacy_backup = transaction / "legacy-backup"
            legacy_backup.mkdir()
            for skill_name in legacy_old_present:
                strict_relative_path(
                    previous_skills_home, skill_name, direct_child=True
                ).rename(legacy_backup / skill_name)

        refresh_owned_directory(
            state_dir, transaction, purpose="install-transaction"
        )

        _canonical_host_layout(state_home, skills_home=skills_home,
                               release_id=str(manifest["release_id"]))
        runtime_dir = state_dir / "runtime" / manifest["release_id"]
        if runtime_dir.exists():
            for relative, expected in manifest["runtime"].items():
                installed = runtime_dir / relative
                if not installed.is_file() or sha256_file(installed) != expected:
                    raise InstallError(
                        f"已安装的同名 runtime 已损坏：{manifest['release_id']}"
                    )
            shutil.rmtree(staged_runtime)
        else:
            runtime_dir.parent.mkdir(exist_ok=True)
            staged_runtime.rename(runtime_dir)
        runtime_entry = runtime_dir / "tools" / "workflow.py"

        installed_inventory = {
            skill_name: _skill_inventory(
                strict_relative_path(
                    skills_home, skill_name, direct_child=True
                )
            )
            for skill_name in sorted(manifest["skills"])
        }
        if expected_target is not None:
            if installed_inventory != expected_target["skills"]:
                raise InstallError(
                    f"{projection_name} target manifest 与最终 Skill 安装不一致"
                )
            if _runtime_inventory(runtime_dir) != expected_target["runtime"]:
                raise InstallError(
                    f"{projection_name} target manifest 与最终 runtime 安装不一致"
                )

        state = {
            "version": 2,
            "release_id": manifest["release_id"],
            "source": str(release.resolve()),
            "skills": sorted(manifest["skills"]),
            "installed_at": datetime.now(timezone.utc).isoformat(),
            "transaction_id": transaction_id,
            "installed_agent": install_target,
            "metadata_projection": projection_name,
            "skills_home": str(skills_home.resolve()),
            "runtime_entry": str(runtime_entry),
            "manifest_sha256": sha256_file(release / "manifest.json"),
            "managed_inventory": installed_inventory,
        }
        _canonical_host_layout(state_home, skills_home=skills_home,
                               release_id=str(manifest["release_id"]))
        verify_installed_state(state, validation_context=context, state_home=state_home)
        state_temp = transaction / "install-state.json"
        state_temp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")
        state_temp.replace(state_path)
        refresh_owned_directory(
            state_dir, transaction, purpose="install-transaction"
        )
        quarantine_and_remove(
            state_dir, transaction, purpose="install-transaction"
        )
    except Exception as exc:
        if transaction.exists():
            refresh_owned_directory(
                state_dir, transaction, purpose="install-transaction"
            )
        recover_interrupted_install(state_home, skills_home=skills_home)
        raise InstallError("安装中断，已恢复旧版本") from exc
    return "installed"


def install_release(
    release: Path,
    state_home: Path,
    *,
    target: str | None = None,
    skills_home: Path | None = None,
    validation_context: ReleaseValidationContext | None = None,
) -> str:
    """Install under a single-writer lock for the selected state home."""
    state_home, skills_home = _canonical_host_layout(
        state_home, skills_home=skills_home, release_id=release.name)
    context = validation_context or ReleaseValidationContext()
    context.verify(release)
    state_dir = state_home / "my-matt-workflow"
    existing = load_install_state(state_dir / "install-state.json")
    if existing is not None:
        _verify_recorded_receipt_roots(existing)
    state_dir.mkdir(parents=True, exist_ok=True)
    try:
        # This short lock is also held while cleanup reads receipts and deletes.
        # The build/source gate uses a different lock and can run concurrently.
        with exclusive_lock(release.resolve().parent, REFERENCE_LOCK):
            with exclusive_lock(state_dir, "install"):
                context.verify(release)
                remember_installation(release.resolve().parent, state_home)
                return _install_release(
                    release,
                    state_home,
                    target=target,
                    skills_home=skills_home,
                    validation_context=context,
                )
    except FilesystemSafetyError as exc:
        raise InstallError(str(exc)) from exc
