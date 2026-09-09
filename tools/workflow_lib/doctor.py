"""Read-only source, release, and host deployment diagnostics."""

from __future__ import annotations

import json
import re
from pathlib import Path

from .installer import InstallError, load_install_state, verify_installed_state, verify_release
from .release import release_matches_source
from .validator import ValidationError, validate_repository


_RELEASE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")


def _source_skills(root: Path) -> list[str]:
    skills = root / "skills"
    return sorted(
        path.name
        for path in skills.iterdir()
        if path.is_dir() and not path.is_symlink() and path.name.startswith("my-")
    )


def _current_release(root: Path) -> tuple[dict[str, object], str | None]:
    pointer = root / "current.json"
    if not pointer.is_file():
        return {"status": "not-applicable", "reason": "current-pointer-missing"}, None
    try:
        raw = json.loads(pointer.read_text(encoding="utf-8"))
        if not isinstance(raw, dict) or set(raw) != {"release_id"}:
            raise ValueError("current pointer fields")
        identifier = raw["release_id"]
        if not isinstance(identifier, str) or not _RELEASE_ID.fullmatch(identifier):
            raise ValueError("current release id")
        release = root / "releases" / identifier
        manifest = verify_release(release)
    except (OSError, ValueError, KeyError, InstallError, RuntimeError) as exc:
        return {"status": "invalid", "reason": str(exc)}, None
    try:
        source_match = release_matches_source(
            release,
            root / "skills",
            upstream_id=str(manifest["upstream_id"]),
            repo_root=root,
        )
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        return {
            "status": "valid",
            "release_id": identifier,
            "source_match": "unavailable",
            "source_error": str(exc),
            "skills": len(manifest["skills"]),
        }, identifier
    return {
        "status": "valid" if source_match else "drift",
        "release_id": identifier,
        "source_match": source_match,
        "skills": len(manifest["skills"]),
    }, identifier


def _host_status(
    home: Path, *, current_release_id: str | None, source_skills: list[str]
) -> dict[str, object]:
    state_path = home.resolve() / "my-matt-workflow" / "install-state.json"
    try:
        state = load_install_state(state_path)
        if state is None:
            return {
                "status": "not-installed",
                "agent_home": str(home.resolve()),
                "state_path": str(state_path),
            }
        verify_installed_state(state)
    except (InstallError, OSError) as exc:
        return {
            "status": "invalid",
            "agent_home": str(home.resolve()),
            "state_path": str(state_path),
            "reason": str(exc),
        }

    reasons: list[str] = []
    release_id = str(state["release_id"])
    installed_skills = sorted(str(name) for name in state["skills"])
    if current_release_id is not None and release_id != current_release_id:
        reasons.append("release-id-drift")
    if installed_skills != source_skills:
        reasons.append("skill-set-drift")
    runtime_entry = Path(str(state["runtime_entry"]))
    if not runtime_entry.is_file():
        reasons.append("runtime-entry-missing")
    return {
        "status": "drift" if reasons else "valid",
        "agent_home": str(home.resolve()),
        "state_path": str(state_path),
        "release_id": release_id,
        "installed_agent": state["installed_agent"],
        "metadata_projection": state["metadata_projection"],
        "skills": len(installed_skills),
        "reasons": reasons,
    }


def diagnose_repository(
    root: Path, agent_homes: dict[str, Path]
) -> dict[str, object]:
    """Report independent source/current-release/deployment health layers."""
    root = root.resolve()
    skills = _source_skills(root)
    try:
        source_report: dict[str, object] = {
            "status": "valid",
            **validate_repository(root),
        }
    except (ValidationError, OSError) as exc:
        source_report = {
            "status": "invalid",
            "skills": len(skills),
            "reason": str(exc),
        }
    release, current_id = _current_release(root)
    return {
        "status": "diagnostic",
        "source": source_report,
        "current_release": release,
        "hosts": {
            label: _host_status(
                home, current_release_id=current_id, source_skills=skills
            )
            for label, home in sorted(agent_homes.items())
        },
    }
