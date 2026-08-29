"""The single local repository gate for source trees without Git."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from .evals import EvalError, validate_evals
from .installer import verify_release
from .release import release_matches_source
from .smoke_registry import SmokeRegistryError, validate_smoke_registry
from .validator import ValidationError, validate_repository


class CheckError(RuntimeError):
    """Raised when a local all-up gate fails."""


def _current_release(root: Path) -> Path | None:
    pointer = root / "current.json"
    if not pointer.exists():
        return None
    try:
        value = json.loads(pointer.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CheckError(f"{pointer}: invalid current release pointer") from exc
    identifier = value.get("release_id") if isinstance(value, dict) else None
    if not isinstance(identifier, str) or not identifier:
        raise CheckError(f"{pointer}: release_id is missing")
    release = root / "releases" / identifier
    if not release.is_dir():
        raise CheckError(f"{pointer}: referenced release is missing: {identifier}")
    return release


def verify_current_release(root: Path) -> dict[str, object]:
    """Verify source/release parity if a repository has a current release."""
    release = _current_release(root)
    if release is None:
        return {
            "status": "not-applicable",
            "reason": "release verification is not applicable: no current release",
        }
    try:
        # Verify the immutable tree before generating an expected source tree.
        # Otherwise a damaged release can be reported merely as "stale", which
        # makes corruption easy to miss and lets deploy incorrectly reuse it.
        verify_release(release)
        matches = release_matches_source(
            release,
            root / "skills",
            upstream_id="local-matt-skills",
            repo_root=root,
        )
    except Exception as exc:
        raise CheckError(f"current release validation failed: {exc}") from exc
    if not matches:
        raise CheckError(f"current release is stale: {release.relative_to(root)}")
    return {"status": "valid", "release": release.name}


def run_check(
    repo_root: Path, *, check_current_release: bool = True
) -> dict[str, object]:
    """Run static, unit, eval, registry, and optional current-release gates."""
    root = repo_root.resolve()
    try:
        static = validate_repository(root)
        evals = validate_evals(root)
        validate_smoke_registry(root)
    except (ValidationError, EvalError, SmokeRegistryError) as exc:
        raise CheckError(str(exc)) from exc
    tests = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if tests.returncode:
        output = (tests.stdout + tests.stderr).strip()
        raise CheckError("unit tests failed:\n" + output)
    report = {
        "status": "valid",
        "static": static,
        "evals": evals,
        "tests": {"status": "valid"},
    }
    if check_current_release:
        report["release"] = verify_current_release(root)
    return report
