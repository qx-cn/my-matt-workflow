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
    def _record(self, model: str = "gpt-6-astra") -> dict[str, object]:
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
        self.assertEqual(9, len(cases))
        schema = json.loads(
            (ROOT / "evals/agent-smokes/astra-evidence.schema.json").read_text()
        )
        self.assertEqual(1, schema["properties"]["version"]["const"])

    def test_partial_real_evidence_is_valid_but_not_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / "evidence.json"
            evidence.write_text(json.dumps(self._record()))
            report = validate_behavior_evidence(SUITE, evidence)
            self.assertEqual(1, report["runs"])
            self.assertEqual(8, len(report["missing"]))
            with self.assertRaisesRegex(BehaviorEvidenceError, "缺少行为场景"):
                validate_behavior_evidence(SUITE, evidence, require_complete=True)

    def test_non_astra_run_cannot_be_marked_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            evidence = Path(tmp) / "evidence.json"
            evidence.write_text(json.dumps(self._record(model="gpt-5.6-sol")))
            with self.assertRaisesRegex(BehaviorEvidenceError, "不是 Astra"):
                validate_behavior_evidence(SUITE, evidence)

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
