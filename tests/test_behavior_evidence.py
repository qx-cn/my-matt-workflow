import json
import tempfile
import unittest
from pathlib import Path

from tools.workflow_lib.behavior_evidence import (
    BehaviorEvidenceError,
    validate_behavior_evidence,
    validate_behavior_suite,
)


ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "evals/agent-smokes/astra-behavior-suite.json"


class BehaviorEvidenceTests(unittest.TestCase):
    def _record(self, model: str = "default-test-model") -> dict[str, object]:
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
                    "release_id": "test-release",
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
        self.assertEqual(15, len(cases))
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

    def test_partial_real_evidence_is_valid_but_not_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / "evidence.json"
            evidence.write_text(json.dumps(self._record()))
            report = validate_behavior_evidence(SUITE, evidence)
            self.assertEqual(1, report["runs"])
            self.assertEqual(14, len(report["missing"]))
            with self.assertRaisesRegex(BehaviorEvidenceError, "缺少行为场景"):
                validate_behavior_evidence(SUITE, evidence, require_complete=True)

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
