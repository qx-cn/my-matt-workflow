import unittest

from tools.workflow_lib.implementation_service import next_implementation_action


class ImplementationServiceTests(unittest.TestCase):
    def test_active_phases_return_one_compatible_next_action(self):
        cases = {
            "admitted": "continue-implementation",
            "reviewing": "open-review",
            "committing": "submit-completed",
            "plan-reviewing": "review-repair-plan",
        }
        for phase, expected in cases.items():
            with self.subTest(phase=phase):
                result = next_implementation_action({"phase": phase})
                self.assertEqual(expected, result["next_action"])
                self.assertEqual(expected, result["next_gate"])
                self.assertEqual("active", result["status"])

    def test_review_recovery_and_terminal_results_are_explicit(self):
        correction = next_implementation_action(
            {"phase": "reviewing", "active_review": {}, "recovery": {}}
        )
        self.assertEqual("correct-review-result", correction["next_action"])

        completed = next_implementation_action(
            {"phase": "committing", "submission": {"outcome": "completed"}}
        )
        self.assertEqual("complete", completed["status"])
        self.assertEqual("complete", completed["next_action"])

    def test_unknown_phase_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "phase 无效"):
            next_implementation_action({"phase": "invented"})


if __name__ == "__main__":
    unittest.main()
