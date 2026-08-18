"""Checksum-verified, rollback-safe Skill installation."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


class InstallError(RuntimeError):
    """Raised when a release cannot be verified or installed safely."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(release: Path) -> dict:
    try:
        manifest = json.loads((release / "manifest.json").read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise InstallError("release manifest 无法读取") from exc
    release_id = manifest.get("release_id")
    if (
        not isinstance(release_id, str)
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", release_id)
        or not isinstance(manifest.get("skills"), dict)
        or not isinstance(manifest.get("runtime"), dict)
    ):
        raise InstallError("release manifest 的 release_id、skills 或 runtime 无效")
    return manifest


def verify_release(release: Path, manifest: dict | None = None) -> dict:
    manifest = manifest or load_manifest(release)
    for skill_name, files in manifest["skills"].items():
        if not skill_name.startswith("my-") or "/" in skill_name:
            raise InstallError(f"非法 Skill 名称：{skill_name}")
        expected_paths: set[str] = set()
        for relative, expected in files.items():
            relative_path = Path(relative)
            if relative_path.is_absolute() or ".." in relative_path.parts:
                raise InstallError(f"非法文件路径：{relative}")
            expected_paths.add(str(relative_path))
        skill_dir = release / "skills" / skill_name
        actual_paths = {
            str(path.relative_to(skill_dir))
            for path in skill_dir.rglob("*")
            if path.is_file()
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
    actual_runtime = {
        str(path.relative_to(runtime_dir))
        for path in runtime_dir.rglob("*")
        if path.is_file()
    } if runtime_dir.is_dir() else set()
    if actual_runtime != expected_runtime:
        raise InstallError("release runtime 文件集合不一致")
    if "tools/workflow.py" not in expected_runtime:
        raise InstallError("release runtime 缺少 tools/workflow.py")
    for relative, expected in manifest["runtime"].items():
        relative_path = Path(relative)
        if relative_path.is_absolute() or ".." in relative_path.parts:
            raise InstallError(f"非法 runtime 文件路径：{relative}")
        source = runtime_dir / relative_path
        if not source.is_file() or sha256_file(source) != expected:
            raise InstallError(f"runtime 校验失败：{relative}")
    return manifest


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


def _remove_path(path: Path) -> None:
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
            shutil.rmtree(transaction)
        return
    try:
        journal = json.loads(journal_path.read_text())
    except json.JSONDecodeError as exc:
        raise InstallError("安装事务日志损坏，需要人工检查") from exc

    skills_home = skills_home or state_home / "skills"
    state_path = state_home / "my-matt-workflow" / "install-state.json"
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text())
        except json.JSONDecodeError as exc:
            raise InstallError("安装状态损坏，需要人工检查") from exc
        transaction_id = journal.get("transaction_id")
        if transaction_id and state.get("transaction_id") == transaction_id:
            shutil.rmtree(transaction)
            return

    old_present = set(journal.get("old_present", []))
    for skill_name in journal.get("skills", []):
        target = skills_home / skill_name
        backup = transaction / "backup" / skill_name
        if backup.exists():
            _remove_path(target)
            backup.rename(target)
        elif skill_name not in old_present:
            _remove_path(target)
    shutil.rmtree(transaction)


def install_release(
    release: Path,
    state_home: Path,
    *,
    target: str | None = None,
    skills_home: Path | None = None,
) -> None:
    """Install one immutable release, restoring the old install on failure."""
    manifest = verify_release(release)
    install_target = target
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

    previous_state: dict = {}
    if state_path.exists():
        try:
            previous_state = json.loads(state_path.read_text())
        except json.JSONDecodeError:
            previous_state = {}

    previous_managed = set(previous_state.get("skills", []))
    for skill_name in manifest["skills"]:
        destination = skills_home / skill_name
        if destination.exists() and skill_name not in previous_managed:
            raise InstallError(f"发现同名非托管 Skill，拒绝覆盖：{skill_name}")

    transaction = state_dir / "transaction"
    staged = transaction / "staged"
    backup = transaction / "backup"
    staged.mkdir(parents=True)
    backup.mkdir()
    for skill_name in manifest["skills"]:
        shutil.copytree(release / "skills" / skill_name, staged / skill_name)
    staged_runtime = transaction / "staged-runtime"
    shutil.copytree(release / "runtime", staged_runtime)

    managed = previous_managed | set(manifest["skills"])
    transaction_id = str(uuid4())
    old_present = [
        skill_name for skill_name in sorted(managed) if (skills_home / skill_name).exists()
    ]
    (transaction / "journal.json").write_text(
        json.dumps(
            {
                "skills": sorted(managed),
                "old_present": old_present,
                "new_release_id": manifest["release_id"],
                "transaction_id": transaction_id,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )

    try:
        for skill_name in sorted(managed):
            destination = skills_home / skill_name
            if destination.exists():
                destination.rename(backup / skill_name)
            if skill_name in manifest["skills"]:
                (staged / skill_name).rename(destination)

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

        state = {
            "release_id": manifest["release_id"],
            "source": str(release),
            "skills": sorted(manifest["skills"]),
            "installed_at": datetime.now(timezone.utc).isoformat(),
            "transaction_id": transaction_id,
            "installed_agent": install_target,
            "skills_home": str(skills_home.resolve()),
            "runtime_entry": str(runtime_entry.resolve()),
        }
        state_temp = transaction / "install-state.json"
        state_temp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n")
        state_temp.replace(state_path)
        shutil.rmtree(transaction)
    except Exception as exc:
        recover_interrupted_install(state_home, skills_home=skills_home)
        raise InstallError("安装中断，已恢复旧版本") from exc
