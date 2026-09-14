import unittest

from tools.workflow_lib.review_results import validate_review_result


class ReviewResultValidationTests(unittest.TestCase):
    def setUp(self):
        self.unit = {
            "review_id": "review-1",
            "implementation_session_id": "session-1",
            "ticket_boundary": {
                "current": {"acceptance": [{"id": "ticket-1#A1"}]},
                "successors": [
                    {"id": "ticket-2", "acceptance": [{"id": "ticket-2#A1"}]}
                ],
                "required_probes": [],
            },
        }
        self.code = {"content_id": "code-1"}

    def _result(self, status="pass"):
        return {
            "review_id": "review-1",
            "status": status,
            "code_content_id": "code-1",
            "reviewer_provenance": {"kind": "self", "session_id": "session-1"},
            "findings": [],
            "follow_ons": [],
            "design_gap": None,
            "self_review_coverage": {
                "acceptance": [
                    {"acceptance_id": "ticket-1#A1", "evidence_refs": ["test:e1"]}
                ],
                "probes": [],
            },
        }

    def test_pass_validation_is_independent_from_journal_storage(self):
        refs = []
        status, roots = validate_review_result(
            self._result(),
            self.unit,
            self.code,
            validate_evidence_refs=refs.append,
        )
        self.assertEqual("pass", status)
        self.assertEqual(set(), roots)
        self.assertEqual([["test:e1"]], refs)

    def test_finding_must_bind_current_acceptance(self):
        result = self._result("findings")
        result["findings"] = [
            {
                "id": "finding-1",
                "root_cause": "missing-boundary",
                "severity": "P1",
                "summary": "Boundary behavior is missing.",
                "baseline_reachable": True,
                "acceptance_ids": ["ticket-2#A1"],
            }
        ]
        with self.assertRaisesRegex(ValueError, "当前 Ticket 验收"):
            validate_review_result(
                result,
                self.unit,
                self.code,
                validate_evidence_refs=lambda refs: None,
            )


if __name__ == "__main__":
    unittest.main()
