"""Focused tests for deterministic evals and local gates."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.workflow_lib.evals import EvalError, load_scenarios, validate_evals
from tools.workflow_lib.installer import install_release
from tools.workflow_lib.release import build_release
from tools.workflow_lib.smoke_registry import resolve_smoke_scenarios
from tools.workflow_lib.validator import (
    ValidationError,
    validate_markdown_references,
    validate_scripts,
)


ROOT = Path(__file__).resolve().parents[1]


class EvalValidationTests(unittest.TestCase):
    def test_checked_in_scenarios_and_evidence_are_strictly_valid(self):
        self.assertEqual(
            {"status": "valid", "scenarios": 8, "required_scenarios": 8},
            validate_evals(ROOT),
        )

    def test_allow_missing_does_not_allow_malformed_scenarios(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            scenarios = root / "evals" / "scenarios"
            scenarios.mkdir(parents=True)
            (scenarios / "broken.json").write_text("{}")

            with self.assertRaisesRegex(EvalError, "fields"):
                validate_evals(root, allow_missing=True)

    def test_allow_missing_only_skips_absent_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(ROOT / "evals", root / "evals")
            shutil.copytree(ROOT / "skills", root / "skills")
            scenario = root / "evals/scenarios/implement-automatic-ticket.json"
            raw = json.loads(scenario.read_text())
            del raw["evidence"]
            scenario.write_text(json.dumps(raw))

            self.assertEqual("valid", validate_evals(root, allow_missing=True)["status"])
            with self.assertRaisesRegex(EvalError, "evidence fields"):
                validate_evals(root)

    def test_stale_evidence_hash_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(ROOT / "evals", root / "evals")
            shutil.copytree(ROOT / "skills", root / "skills")
            scenario = root / "evals/scenarios/implement-automatic-ticket.json"
            raw = json.loads(scenario.read_text())
            raw["evidence"]["sources"][0]["sha256"] = "sha256:" + "0" * 64
            scenario.write_text(json.dumps(raw))

            with self.assertRaisesRegex(EvalError, "stale"):
                validate_evals(root)

    def test_smoke_registry_returns_no_entries_as_an_explicit_empty_selection(self):
        self.assertEqual((), resolve_smoke_scenarios(ROOT, ["my-no-such-skill"]))


class StaticGateTests(unittest.TestCase):
    def test_markdown_escape_and_shell_syntax_name_the_bad_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("[outside](../outside.md)\n")
            script = root / "bad.sh"
            script.write_text("if then\n")

            with self.assertRaisesRegex(ValidationError, "README.md.*escapes"):
                validate_markdown_references(root)
            with self.assertRaisesRegex(ValidationError, "bad.sh.*shell syntax"):
                validate_scripts(root)


class EvalCliTests(unittest.TestCase):
    def test_validate_evals_and_unmapped_smoke_report_machine_readable_status(self):
        valid = subprocess.run(
            [sys.executable, "tools/workflow.py", "validate-evals"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, valid.returncode, valid.stderr)
        self.assertEqual("valid", json.loads(valid.stdout)["status"])

        skipped = subprocess.run(
            [sys.executable, "tools/workflow.py", "smoke", "--skills", "my-unknown"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, skipped.returncode, skipped.stderr)
        report = json.loads(skipped.stdout)
        self.assertEqual("skipped", report["status"])
        self.assertIn("no matching", report["reason"])


class FullReleaseE2ETests(unittest.TestCase):
    def test_build_install_and_rollback_all_manual_skills_in_temporary_homes(self):
        with tempfile.TemporaryDirectory() as tmp:
            releases = Path(tmp) / "releases"
            first = build_release(
                ROOT / "skills",
                releases,
                release_id="e2e-v1",
                upstream_id="local-matt-skills",
                repo_root=ROOT,
            )
            second = build_release(
                ROOT / "skills",
                releases,
                release_id="e2e-v2",
                upstream_id="local-matt-skills",
                repo_root=ROOT,
            )
            for target in ("cursor", "claude", "codex"):
                home = Path(tmp) / target
                install_release(first, home, target=target)
                self.assertEqual(
                    29, len([path for path in (home / "skills").iterdir() if path.is_dir()])
                )

            cursor_home = Path(tmp) / "cursor"
            install_release(second, cursor_home, target="cursor")
            install_release(first, cursor_home, target="cursor")
            state = json.loads(
                (cursor_home / "my-matt-workflow" / "install-state.json").read_text()
            )
            self.assertEqual("e2e-v1", state["release_id"])
            self.assertEqual(
                29,
                len([path for path in (cursor_home / "skills").iterdir() if path.is_dir()]),
            )
