"""Focused tests for deterministic evals and local gates."""

from __future__ import annotations

import argparse
import json
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.workflow_lib.check import CheckError, run_check, verify_current_release
from tools.workflow_lib.evals import (
    EvalError,
    load_scenarios,
    run_scenario,
    validate_evals,
)
from tools.workflow_lib.installer import install_release
from tools.workflow_lib.release import build_release
from tools.workflow_lib.smoke_registry import (
    SmokeRegistryError,
    resolve_smoke_scenarios,
    validate_smoke_registry,
)
from tools.workflow_lib.validator import (
    ValidationError,
    validate_markdown_references,
    validate_scripts,
)


ROOT = Path(__file__).resolve().parents[1]


class EvalValidationTests(unittest.TestCase):
    def test_checked_in_scenarios_and_evidence_are_strictly_valid(self):
        self.assertEqual(
            {"status": "valid", "scenarios": 5, "required_scenarios": 4},
            validate_evals(ROOT),
        )

    def test_checked_in_scenarios_dispatch_deterministic_behavior(self):
        scenarios = load_scenarios(ROOT / "evals")
        self.assertEqual(
            [scenario.identifier for scenario in scenarios],
            sorted(scenario.identifier for scenario in scenarios),
        )
        for scenario in scenarios:
            self.assertEqual(
                scenario.expected,
                run_scenario(ROOT, scenario),
                scenario.identifier,
            )

    def test_tampered_structured_expected_outcome_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(ROOT / "evals", root / "evals")
            shutil.copytree(ROOT / "skills", root / "skills")
            scenario = root / "evals/scenarios/grilling-one-question-hitl.json"
            raw = json.loads(scenario.read_text())
            raw["expected"]["stop"] = "continue-questioning"
            scenario.write_text(json.dumps(raw))

            with self.assertRaisesRegex(EvalError, "outcome mismatch"):
                validate_evals(root)

    def test_tampered_structured_input_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(ROOT / "evals", root / "evals")
            shutil.copytree(ROOT / "skills", root / "skills")
            scenario = root / "evals/scenarios/diagnosing-bugs-no-red-loop.json"
            raw = json.loads(scenario.read_text())
            raw["input"]["policy"] = "manual"
            scenario.write_text(json.dumps(raw))

            with self.assertRaisesRegex(EvalError, "fields must be"):
                validate_evals(root)

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
            scenario = root / "evals/scenarios/tdd-seam-pressure.json"
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
            scenario = root / "evals/scenarios/tdd-seam-pressure.json"
            raw = json.loads(scenario.read_text())
            raw["evidence"]["sources"][0]["sha256"] = "sha256:" + "0" * 64
            scenario.write_text(json.dumps(raw))

            with self.assertRaisesRegex(EvalError, "stale"):
                validate_evals(root)

    def test_smoke_registry_validates_complete_registered_scenarios(self):
        scenarios = load_scenarios(ROOT / "evals")
        registry = validate_smoke_registry(ROOT, scenarios)
        registered = {identifier for identifiers in registry.values() for identifier in identifiers}
        self.assertEqual({scenario.identifier for scenario in scenarios}, registered)

    def test_smoke_registry_rejects_unknown_requested_skill(self):
        with self.assertRaisesRegex(SmokeRegistryError, "not registered"):
            resolve_smoke_scenarios(ROOT, ["my-no-such-skill"])


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
    def test_validate_evals_and_smoke_report_machine_readable_status(self):
        valid = subprocess.run(
            [sys.executable, "tools/workflow.py", "validate-evals"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, valid.returncode, valid.stderr)
        self.assertEqual("valid", json.loads(valid.stdout)["status"])

        unknown = subprocess.run(
            [sys.executable, "tools/workflow.py", "smoke", "--skills", "my-unknown"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(0, unknown.returncode)
        report = json.loads(unknown.stdout)
        self.assertEqual("invalid", report["status"])
        self.assertIn("not registered", report["error"])

        registry = subprocess.run(
            [sys.executable, "tools/workflow.py", "smoke"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, registry.returncode, registry.stderr)
        self.assertEqual("valid", json.loads(registry.stdout)["status"])


class CheckGateTests(unittest.TestCase):
    @staticmethod
    def _load_workflow_module():
        spec = importlib.util.spec_from_file_location(
            "workflow_gate_under_test", ROOT / "tools/workflow.py"
        )
        module = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(ROOT / "tools"))
        try:
            assert spec.loader is not None
            spec.loader.exec_module(module)
        finally:
            sys.path.pop(0)
        return module

    def _source_copy(self, destination: Path) -> None:
        shutil.copytree(
            ROOT,
            destination,
            ignore=shutil.ignore_patterns(
                ".git", ".worktrees", "releases", "current.json", "__pycache__"
            ),
        )

    def test_release_verification_is_not_applicable_without_current_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                {
                    "status": "not-applicable",
                    "reason": "release verification is not applicable: no current release",
                },
                verify_current_release(Path(tmp)),
            )

    def test_check_rejects_stale_current_release_and_accepts_matching_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repository"
            self._source_copy(root)
            release = build_release(
                root / "skills",
                root / "releases",
                release_id="check-v1",
                upstream_id="local-matt-skills",
                repo_root=root,
            )
            (root / "current.json").write_text('{"release_id": "check-v1"}\n')
            completed = subprocess.CompletedProcess([], 0, "", "")
            with mock.patch(
                "tools.workflow_lib.check.subprocess.run", return_value=completed
            ):
                self.assertEqual("valid", run_check(root)["status"])
            (root / "skills" / "my-humanizer" / "SKILL.md").write_text(
                (root / "skills" / "my-humanizer" / "SKILL.md").read_text()
                + "\nChanged after release.\n"
            )
            with mock.patch(
                "tools.workflow_lib.check.subprocess.run", return_value=completed
            ):
                with self.assertRaisesRegex(CheckError, "current release is stale"):
                    run_check(root)
            with mock.patch(
                "tools.workflow_lib.check.subprocess.run", return_value=completed
            ):
                replacement_gate = run_check(root, check_current_release=False)
            self.assertEqual("valid", replacement_gate["status"])
            self.assertEqual({"status": "valid"}, replacement_gate["tests"])
            self.assertNotIn("release", replacement_gate)
            self.assertTrue(release.is_dir())

    def test_canonical_build_rejects_missing_eval_and_smoke_inputs(self):
        def remove_evidence(root: Path) -> None:
            scenario = (
                root / "evals" / "scenarios" / "tdd-seam-pressure.json"
            )
            raw = json.loads(scenario.read_text())
            del raw["evidence"]
            scenario.write_text(json.dumps(raw))

        cases = (
            (
                "evals",
                lambda root: shutil.rmtree(root / "evals"),
                "scenario directory is missing",
            ),
            (
                "scenarios",
                lambda root: shutil.rmtree(root / "evals" / "scenarios"),
                "scenario directory is missing",
            ),
            (
                "evidence",
                remove_evidence,
                "evidence fields are invalid",
            ),
            (
                "smoke-registry",
                lambda root: (root / "evals" / "smoke-registry.json").unlink(),
                "invalid smoke registry JSON",
            ),
        )
        for name, remove_input, error in cases:
            with self.subTest(input=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp) / "repository"
                self._source_copy(root)
                remove_input(root)

                with self.assertRaisesRegex(ValidationError, error):
                    build_release(
                        root / "skills",
                        root / "releases",
                        release_id=f"missing-{name}",
                        upstream_id="local-matt-skills",
                        repo_root=root,
                    )
                self.assertFalse((root / "releases" / f"missing-{name}").exists())

    def test_workflow_build_stops_before_writing_release_when_unit_gate_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repository"
            self._source_copy(root)
            (root / "tests" / "test_intentional_gate_failure.py").write_text(
                "import unittest\n\n"
                "class IntentionalGateFailure(unittest.TestCase):\n"
                "    def test_failure(self):\n"
                "        self.fail('intentional unit gate failure')\n"
            )

            module = self._load_workflow_module()
            with mock.patch.object(module, "ROOT", root), mock.patch.object(
                module, "_run_all_up_gate", side_effect=SystemExit(1)
            ):
                with self.assertRaises(SystemExit):
                    module.command_build(
                        argparse.Namespace(release_id="blocked-v1", upstream_id="local-matt-skills")
                    )
            self.assertFalse((root / "releases" / "blocked-v1").exists())
            self.assertFalse((root / "current.json").exists())

    def test_workflow_build_can_replace_a_stale_current_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repository"
            self._source_copy(root)
            build_release(
                root / "skills",
                root / "releases",
                release_id="stale-v1",
                upstream_id="local-matt-skills",
                repo_root=root,
            )
            (root / "current.json").write_text('{"release_id": "stale-v1"}\n')
            skill = root / "skills" / "my-humanizer" / "SKILL.md"
            skill.write_text(skill.read_text() + "\nReplacement release fixture.\n")

            module = self._load_workflow_module()
            with mock.patch.object(module, "ROOT", root), mock.patch.object(
                module, "_run_all_up_gate", return_value={"status": "valid"}
            ):
                module.command_build(
                    argparse.Namespace(release_id="replacement-v2", upstream_id="local-matt-skills")
                )
            self.assertTrue((root / "releases" / "stale-v1").is_dir())
            self.assertTrue((root / "releases" / "replacement-v2").is_dir())
            self.assertEqual(
                {"release_id": "replacement-v2"},
                json.loads((root / "current.json").read_text()),
            )
            self.assertEqual("valid", verify_current_release(root)["status"])

    def test_check_rejects_corrupt_or_extra_current_release_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repository"
            self._source_copy(root)
            release = build_release(
                root / "skills", root / "releases", release_id="intact-v1",
                upstream_id="local-matt-skills", repo_root=root,
            )
            (root / "current.json").write_text('{"release_id": "intact-v1"}\n')
            completed = subprocess.CompletedProcess([], 0, "", "")
            skill_file = next((release / "skills").rglob("SKILL.md"))
            skill_file.write_text("tampered")
            with mock.patch("tools.workflow_lib.check.subprocess.run", return_value=completed):
                with self.assertRaisesRegex(CheckError, "current release validation failed"):
                    run_check(root)

            # Repair the tree from a fresh release, then add an undeclared file.
            shutil.rmtree(release)
            release = build_release(
                root / "skills", root / "releases", release_id="intact-v1",
                upstream_id="local-matt-skills", repo_root=root,
            )
            (release / "skills" / "my-humanizer" / "EXTRA.md").write_text("extra")
            with mock.patch("tools.workflow_lib.check.subprocess.run", return_value=completed):
                with self.assertRaisesRegex(CheckError, "current release validation failed"):
                    run_check(root)

    def test_workflow_check_succeeds_from_complete_non_git_copy(self):
        if os.environ.get("MY_MATT_NESTED_CHECK"):
            self.skipTest("avoids recursively checking the copied repository")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repository"
            self._source_copy(root)
            self.assertFalse((root / ".git").exists())
            environment = os.environ | {"MY_MATT_NESTED_CHECK": "1"}
            result = subprocess.run(
                [sys.executable, "tools/workflow.py", "check"],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
                env=environment,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual("valid", json.loads(result.stdout)["status"])


class FullReleaseE2ETests(unittest.TestCase):
    def test_build_install_and_rollback_all_manual_skills_in_temporary_homes(self):
        with tempfile.TemporaryDirectory() as tmp:
            source_v2 = Path(tmp) / "source-v2"
            shutil.copytree(
                ROOT,
                source_v2,
                ignore=shutil.ignore_patterns(
                    ".git", ".worktrees", "releases", "current.json", "__pycache__"
                ),
            )
            v2_skill = source_v2 / "skills" / "my-humanizer" / "SKILL.md"
            v2_skill.write_text(v2_skill.read_text() + "\nVersion two fixture.\n")
            releases = Path(tmp) / "releases"
            first = build_release(
                ROOT / "skills",
                releases,
                release_id="e2e-v1",
                upstream_id="local-matt-skills",
                repo_root=ROOT,
            )
            second = build_release(
                source_v2 / "skills",
                releases,
                release_id="e2e-v2",
                upstream_id="local-matt-skills",
                repo_root=source_v2,
            )
            for target in ("cursor", "claude", "codex"):
                home = Path(tmp) / target
                install_release(first, home, target=target)
                self.assertEqual(
                    32, len([path for path in (home / "skills").iterdir() if path.is_dir()])
                )
                original = (home / "skills" / "my-humanizer" / "SKILL.md").read_bytes()
                install_release(second, home, target=target)
                self.assertEqual(
                    "e2e-v2",
                    json.loads(
                        (home / "my-matt-workflow" / "install-state.json").read_text()
                    )["release_id"],
                )
                self.assertNotEqual(
                    original, (home / "skills" / "my-humanizer" / "SKILL.md").read_bytes()
                )
                install_release(first, home, target=target)
                self.assertEqual(
                    "e2e-v1",
                    json.loads(
                        (home / "my-matt-workflow" / "install-state.json").read_text()
                    )["release_id"],
                )
                self.assertEqual(
                    original, (home / "skills" / "my-humanizer" / "SKILL.md").read_bytes()
                )
                self.assertEqual(
                    32, len([path for path in (home / "skills").iterdir() if path.is_dir()])
                )
