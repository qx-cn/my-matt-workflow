"""Checksum-verified, rollback-safe Skill installation."""

from __future__ import annotations

import hashlib
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
from .projection import (
    TARGETS,
    directory_inventory,
    project_skill_directory,
    skills_inventory,
)


class InstallError(RuntimeError):
    """Raised when a release cannot be verified or installed safely."""


_MANAGED_SKILL = re.compile(r"my-[a-z0-9-]+")
_RELEASE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
_MANIFEST_FIELDS = {
    "release_id", "upstream_id", "skills", "runtime", "composed",
    "shared_resources", "resource_consumers", "target_manifests",
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
        if set(journal) not in {frozenset(base_fields), frozenset(base_fields | migration_fields)}:
            raise InstallError("安装事务日志 v4 schema 无效，需要人工检查")
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
        if path.is_symlink():
            raise InstallError(f"托管 Skill 包含 symlink：{skill_dir.name}")
    return directory_inventory(skill_dir)


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


def verify_installed_state(state: dict[str, object]) -> None:
    """Verify that a state receipt still owns the installed Skill bytes."""
    skills_home = Path(str(state["skills_home"])).resolve()
    skills = list(state["skills"])
    if state.get("version", 1) == 2:
        inventory = state["managed_inventory"]
        assert isinstance(inventory, dict)
        source = Path(str(state["source"]))
        source_release = verify_release(source)
        if (
            source_release.get("release_id") != state["release_id"]
            or set(source_release["skills"]) != set(skills)
        ):
            raise InstallError("安装状态与 source release 不一致")
        target_manifests = source_release.get("target_manifests")
        expected_target = (
            target_manifests[str(state["metadata_projection"])]
            if isinstance(target_manifests, dict)
            else None
        )
        if expected_target is not None and inventory != expected_target["skills"]:
            raise InstallError("安装状态 inventory 与 release target manifest 不一致")
        for name in skills:
            target = strict_relative_path(skills_home, name, direct_child=True)
            if _skill_inventory(target) != inventory[name]:
                raise InstallError(f"托管 Skill ownership 已漂移：{name}")
        source_manifest = source / "manifest.json"
        if not source_manifest.is_file() or sha256_file(source_manifest) != state["manifest_sha256"]:
            raise InstallError("安装状态引用的 release manifest 已漂移")
        if expected_target is not None:
            runtime_entry = Path(str(state["runtime_entry"])).resolve()
            runtime_root = runtime_entry.parent.parent
            if directory_inventory(runtime_root) != expected_target["runtime"]:
                raise InstallError("已安装 runtime 与 release target manifest 不一致")
        return
    # Legacy receipts are accepted only when their immutable source release is
    # still available and proves the exact managed name set.
    source = Path(str(state["source"]))
    previous = verify_release(source)
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


def _projected_release_inventories(state: dict[str, object]) -> dict[str, dict[str, str]]:
    """Derive byte inventories for a legacy host projection."""
    source = Path(str(state["source"]))
    manifest = verify_release(source)
    skills = list(state["skills"])
    if manifest.get("release_id") != state["release_id"] or set(manifest["skills"]) != set(skills):
        raise InstallError("旧安装状态与 source release 不一致")
    projection = str(state["metadata_projection"])
    result: dict[str, dict[str, str]] = {}
    with tempfile.TemporaryDirectory(prefix="my-matt-legacy-recovery-") as tmp:
        staging = Path(tmp)
        for name in skills:
            staged = staging / name
            shutil.copytree(source / "skills" / name, staged)
            _project_skill_metadata_for_target(
                staged, None if projection == "portable" else projection
            )
            result[name] = _skill_inventory(staged)
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
    if set(manifest) - _MANIFEST_FIELDS:
        raise InstallError("release manifest 包含未知字段")
    return manifest


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
            if target == "portable":
                projected_skills = manifest["skills"]
            else:
                with tempfile.TemporaryDirectory(
                    prefix=f"my-matt-verify-{target}-"
                ) as tmp:
                    projected_root = Path(tmp) / "skills"
                    shutil.copytree(skills_root, projected_root)
                    for skill_dir in sorted(projected_root.iterdir()):
                        project_skill_directory(skill_dir, target)
                    projected_skills = skills_inventory(projected_root)
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
    skill_dir: Path, target: str
) -> None:
    """Enforce target-specific manual invocation metadata."""
    if target not in {"cursor", "claude", "codex"}:
        raise InstallError(f"未知安装目标：{target}")
    if target in {"cursor", "claude"}:
        skill_file = skill_dir / "SKILL.md"
        text = skill_file.read_text() if skill_file.is_file() else ""
        if not re.search(
            r"(?m)^disable-model-invocation:\s*true\s*$", text
        ):
            raise InstallError(
                f"{skill_dir.name}: {target} 目标要求 "
                "disable-model-invocation: true"
            )
        return
    metadata = skill_dir / "agents" / "openai.yaml"
    text = metadata.read_text() if metadata.is_file() else ""
    if not re.search(
        r"(?m)^\s*allow_implicit_invocation:\s*false\s*$", text
    ):
        raise InstallError(
            f"{skill_dir.name}: agents/openai.yaml 缺少 "
            "allow_implicit_invocation: false"
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


def recover_interrupted_install(
    state_home: Path, *, skills_home: Path | None = None
) -> None:
    """Restore the previous install from a persisted transaction journal."""
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
        recorded_home = Path(recorded).resolve()
        if skills_home is not None and skills_home.resolve() != recorded_home:
            raise InstallError("恢复目录与安装事务不一致，拒绝操作")
        skills_home = recorded_home
    else:
        recorded = state.get("skills_home")
        if isinstance(recorded, str) and Path(recorded).is_absolute():
            recorded_home = Path(recorded).resolve()
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
        previous_skills_home = Path(recorded_previous).resolve()
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
        trusted_home = Path(str(trusted_state["skills_home"])).resolve()
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
) -> None:
    """Install one immutable release, restoring the old install on failure."""
    manifest = verify_release(release)
    install_target = target
    projection_name = install_target or "portable"
    target_manifests = manifest.get("target_manifests")
    expected_target = (
        target_manifests[projection_name]
        if isinstance(target_manifests, dict)
        else None
    )
    if install_target is not None:
        for skill_name in sorted(manifest["skills"]):
            validate_skill_metadata_for_target(
                release / "skills" / skill_name, install_target
            )
    state_home.mkdir(parents=True, exist_ok=True)
    skills_home = skills_home or state_home / "skills"
    skills_home.mkdir(parents=True, exist_ok=True)
    state_dir = state_home / "my-matt-workflow"
    state_dir.mkdir(parents=True, exist_ok=True)
    state_path = state_dir / "install-state.json"
    recover_interrupted_install(state_home, skills_home=skills_home)

    loaded_previous = load_install_state(state_path)
    previous_state: dict[str, object] = loaded_previous or {}
    if previous_state:
        verify_installed_state(previous_state)

    previous_managed = set(previous_state.get("skills", []))
    previous_skills_home: Path | None = None
    recorded_previous_home = previous_state.get("skills_home")
    if isinstance(recorded_previous_home, str) and Path(recorded_previous_home).is_absolute():
        candidate = Path(recorded_previous_home).resolve()
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
            or directory_inventory(staged_runtime) != expected_target["runtime"]
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
            legacy_backup = transaction / "legacy-backup"
            legacy_backup.mkdir()
            for skill_name in legacy_old_present:
                strict_relative_path(
                    previous_skills_home, skill_name, direct_child=True
                ).rename(legacy_backup / skill_name)

        refresh_owned_directory(
            state_dir, transaction, purpose="install-transaction"
        )

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
            if directory_inventory(runtime_dir) != expected_target["runtime"]:
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
            "runtime_entry": str(runtime_entry.resolve()),
            "manifest_sha256": sha256_file(release / "manifest.json"),
            "managed_inventory": installed_inventory,
        }
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


def install_release(
    release: Path,
    state_home: Path,
    *,
    target: str | None = None,
    skills_home: Path | None = None,
) -> None:
    """Install under a single-writer lock for the selected state home."""
    state_dir = state_home / "my-matt-workflow"
    state_dir.mkdir(parents=True, exist_ok=True)
    try:
        with exclusive_lock(state_dir, "install"):
            _install_release(
                release,
                state_home,
                target=target,
                skills_home=skills_home,
            )
    except FilesystemSafetyError as exc:
        raise InstallError(str(exc)) from exc
