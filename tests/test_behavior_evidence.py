import json
import hashlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.workflow_lib.behavior_evidence import (
    BehaviorEvidenceError,
    execution_evidence_release_relation,
    validate_behavior_evidence,
    validate_behavior_suite,
    validate_execution_evidence_registry,
)


ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "evals/agent-smokes/astra-behavior-suite.json"


class BehaviorEvidenceTests(unittest.TestCase):
    def _record(
        self,
        model: str = "default-test-model",
        release_id: str = "test-release",
    ) -> dict[str, object]:
        cases = validate_behavior_suite(SUITE)
        case_id = "authorized-local-no-reconfirm"
        return {
            "version": 1,
            "suite_id": "astra-instruction-following",
            "generated_at": "2026-09-05T00:00:00Z",
            "runs": [
                {
                    "case_id": case_id,
                    "model": model,
                    "host": "codex-cli 0.153.0",
                    "release_id": release_id,
                    "session_id": "session-1",
                    "status": "pass",
                    "raw_output": "done",
                    "observations": {key: True for key in cases[case_id]},
                    "artifacts": ["result.md"],
                    "commands": [],
                    "limitation": "isolated fixture",
                }
            ],
        }

    def test_checked_in_suite_and_schema_are_valid(self):
        cases = validate_behavior_suite(SUITE)
        self.assertEqual(18, len(cases))
        schema = json.loads(
            (ROOT / "evals/agent-smokes/astra-evidence.schema.json").read_text()
        )
        self.assertEqual(1, schema["properties"]["version"]["const"])

    def test_code_review_signal_fixtures_have_a_runbook(self):
        runbook = (
            ROOT / "evals/agent-smokes/code-review-signal-quality.md"
        ).read_text()
        for case in (
            "code-review-change-only-signal",
            "code-review-without-spec",
            "code-review-touched-context",
        ):
            self.assertIn(case, validate_behavior_suite(SUITE))
            self.assertIn(case, runbook)
        fixture_root = ROOT / "evals/fixtures/code-review"
        for fixture in ("change-only", "without-spec", "touched-context"):
            self.assertTrue((fixture_root / fixture / "baseline").is_dir())
            self.assertTrue((fixture_root / fixture / "candidate").is_dir())

    def test_teach_quality_fixtures_have_a_runbook(self):
        runbook = (
            ROOT / "evals/agent-smokes/teach-course-quality.md"
        ).read_text()
        for case in (
            "teach-reader-course-from-source-heavy-input",
            "teach-frontend-blocks-author-centered-draft",
        ):
            self.assertIn(case, validate_behavior_suite(SUITE))
            self.assertIn(case, runbook)
        fixture_root = ROOT / "evals/fixtures/my-teach"
        self.assertTrue((fixture_root / "source-heavy/MISSION.md").is_file())
        self.assertTrue((fixture_root / "source-heavy/RESOURCES.md").is_file())
        self.assertTrue((fixture_root / "source-heavy/source-notes.md").is_file())
        self.assertTrue((fixture_root / "bad-author-centered.content.md").is_file())

    def test_skill_review_root_cause_fixture_has_a_runbook(self):
        cases = validate_behavior_suite(SUITE)
        case = "skill-review-runtime-root-before-wording"
        runbook = (
            ROOT / "evals/agent-smokes/skill-review-root-cause.md"
        ).read_text()
        fixture = (
            ROOT
            / "evals/fixtures/skill-review/runtime-owned-safety/SKILL.md"
        )
        self.assertIn(case, cases)
        self.assertIn(case, runbook)
        self.assertTrue(fixture.is_file())

    def test_grill_spec_boundary_has_a_runbook(self):
        cases = validate_behavior_suite(SUITE)
        runbook = (
            ROOT / "evals/agent-smokes/grill-spec-boundary.md"
        ).read_text()
        self.assertIn("grill-spec-boundary", cases)
        self.assertIn("$my-to-spec", runbook)
        self.assertIn("No formal Spec", runbook)

    def test_implementation_turn_closure_has_an_isolated_runbook_and_fixture(self):
        cases = validate_behavior_suite(SUITE)
        case = "implementation-turn-closure"
        runbook = (ROOT / "evals/agent-smokes/implementation-turn-closure.md").read_text()
        fixture = ROOT / "evals/fixtures/my-implement/unfinished-session"
        self.assertIn(case, cases)
        self.assertIn("不得发送 final", runbook)
        self.assertTrue((fixture / ".agent/matt-workflow.md").is_file())
        self.assertTrue(
            (fixture / ".agent/work/turn-closure/tickets/tickets-turn-closure-01.md").is_file()
        )
        self.assertTrue((fixture / "app.py").is_file())
        self.assertTrue((fixture / "test_app.py").is_file())

    def test_implementation_turn_closure_fixture_admits_an_active_journal(self):
        fixture = ROOT / "evals/fixtures/my-implement/unfinished-session"
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            shutil.copytree(fixture, repo)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.email", "smoke@example.com"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "Smoke"], cwd=repo, check=True)
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "baseline"], cwd=repo, check=True)
            base = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
            ).stdout.strip()
            ticket = repo / ".agent/work/turn-closure/tickets/tickets-turn-closure-01.md"
            opened = subprocess.run(
                [
                    sys.executable, str(ROOT / "tools/workflow.py"), "implementation-open",
                    "--repo", str(repo), "--ticket", str(ticket), "--base", base,
                    "--path", "app.py", "--path", "review.py",
                ],
                cwd=ROOT, check=True, capture_output=True, text=True,
            )
            journal = json.loads(opened.stdout)["lanes"][0]["work_unit"]["journal"]
            recorded = subprocess.run(
                [sys.executable, str(ROOT / "tools/workflow.py"), "run-record", journal, "--phase", "implementing"],
                cwd=ROOT, check=True, capture_output=True, text=True,
            )
            self.assertEqual("implementing", json.loads(recorded.stdout)["run"]["phase"])
            focused = subprocess.run(
                [sys.executable, "-m", "unittest", "test_app.GreetingTests.test_trimmed_name"],
                cwd=repo, check=False, capture_output=True, text=True,
            )
            self.assertEqual(0, focused.returncode, focused.stderr)

    def test_partial_real_evidence_is_valid_but_not_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / "evidence.json"
            evidence.write_text(json.dumps(self._record()))
            report = validate_behavior_evidence(SUITE, evidence)
            self.assertEqual(1, report["runs"])
            self.assertEqual(17, len(report["missing"]))
            with self.assertRaisesRegex(BehaviorEvidenceError, "缺少行为场景"):
                validate_behavior_evidence(SUITE, evidence, require_complete=True)

    def test_empty_execution_registry_is_explicitly_not_recorded(self):
        report = validate_execution_evidence_registry(
            ROOT,
            ROOT / "evals/agent-smokes/execution-evidence-registry.json",
            SUITE,
        )
        self.assertEqual("not-recorded", report["status"])
        self.assertEqual("fresh-agent-execution", report["evidence_level"])
        self.assertEqual([], report["records"])

    def test_execution_registry_binds_repo_evidence_by_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = root / "evidence.json"
            evidence.write_text(json.dumps(self._record()))
            digest = hashlib.sha256(evidence.read_bytes()).hexdigest()
            registry = root / "registry.json"
            registry.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "records": [
                            {"evidence_path": "evidence.json", "sha256": digest}
                        ],
                    }
                )
            )
            report = validate_execution_evidence_registry(root, registry, SUITE)
            self.assertEqual("valid", report["status"])
            self.assertEqual(1, report["records"][0]["runs"])
            self.assertEqual(["test-release"], report["release_ids"])
            self.assertEqual("unbound", report["release_relation"])
            self.assertEqual(
                "current",
                execution_evidence_release_relation(report, "test-release"),
            )
            self.assertEqual(
                "historical",
                execution_evidence_release_relation(report, "new-release"),
            )
            mixed = report | {"release_ids": ["old-release", "test-release"]}
            self.assertEqual(
                "mixed",
                execution_evidence_release_relation(mixed, "test-release"),
            )
            evidence.write_text("{}")
            with self.assertRaisesRegex(BehaviorEvidenceError, "digest 不匹配"):
                validate_execution_evidence_registry(root, registry, SUITE)

    def test_execution_registry_rejects_evidence_without_any_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = root / "evidence.json"
            record = self._record()
            record["runs"] = []
            evidence.write_text(json.dumps(record))
            digest = hashlib.sha256(evidence.read_bytes()).hexdigest()
            registry = root / "registry.json"
            registry.write_text(json.dumps({
                "version": 1,
                "records": [{"evidence_path": "evidence.json", "sha256": digest}],
            }))
            with self.assertRaisesRegex(BehaviorEvidenceError, "不含运行记录"):
                validate_execution_evidence_registry(root, registry, SUITE)

    def test_execution_registry_rejects_paths_outside_repository(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "root"
            root.mkdir()
            registry = root / "registry.json"
            registry.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "records": [
                            {"evidence_path": "../evidence.json", "sha256": "0" * 64}
                        ],
                    }
                )
            )
            with self.assertRaisesRegex(BehaviorEvidenceError, "越出仓库"):
                validate_execution_evidence_registry(root, registry, SUITE)

    def test_execution_registry_requires_relative_path_and_hex_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            registry = root / "registry.json"
            for evidence_path, digest in (
                (str(root / "evidence.json"), "0" * 64),
                ("evidence.json", "z" * 64),
            ):
                registry.write_text(json.dumps({
                    "version": 1,
                    "records": [{"evidence_path": evidence_path, "sha256": digest}],
                }))
                with self.subTest(evidence_path=evidence_path, digest=digest):
                    with self.assertRaisesRegex(BehaviorEvidenceError, "标识无效"):
                        validate_execution_evidence_registry(root, registry, SUITE)

    def test_pass_is_not_bound_to_one_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / "evidence.json"
            evidence.write_text(json.dumps(self._record(model="another-model")))
            report = validate_behavior_evidence(SUITE, evidence)
            self.assertEqual(1, report["statuses"]["pass"])

    def test_pass_requires_every_rubric_observation(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = self._record()
            run = record["runs"][0]
            run["observations"]["asks_no_redundant_confirmation"] = "not-observed"
            evidence = Path(tmp) / "evidence.json"
            evidence.write_text(json.dumps(record))
            with self.assertRaisesRegex(BehaviorEvidenceError, "rubric 未全部通过"):
                validate_behavior_evidence(SUITE, evidence)

    def test_fail_requires_a_failed_observation(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = self._record()
            run = record["runs"][0]
            run["status"] = "fail"
            evidence = Path(tmp) / "evidence.json"
            evidence.write_text(json.dumps(record))
            with self.assertRaisesRegex(BehaviorEvidenceError, "没有失败观测"):
                validate_behavior_evidence(SUITE, evidence)


if __name__ == "__main__":
    unittest.main()
