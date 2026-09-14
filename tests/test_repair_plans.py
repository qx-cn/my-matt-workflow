import unittest

from tools.workflow_lib.repair_plans import render_repair_plan, validate_repair_plan_text


class RepairPlanTests(unittest.TestCase):
    def setUp(self):
        self.findings = [{
            "id": "finding-1",
            "acceptance_ids": ["ticket-1#A1"],
            "root_cause": "missing-boundary",
        }]

    def test_rendered_plan_requires_explicit_decisions_before_validation(self):
        draft = render_repair_plan(self.findings)
        self.assertIn("## Finding finding-1", draft)
        with self.assertRaisesRegex(ValueError, "缺少必填决策"):
            validate_repair_plan_text(draft, ["finding-1"])

        completed = draft.replace("- Change: \n", "- Change: add boundary\n")
        completed = completed.replace("- Verification: \n", "- Verification: run tests\n")
        completed = completed.replace("- Out of scope: \n", "- Out of scope: downstream\n")
        validate_repair_plan_text(completed, ["finding-1"])

    def test_plan_cannot_add_omit_or_duplicate_findings(self):
        completed = render_repair_plan(self.findings).replace(": \n", ": decided\n")
        for expected in ([], ["finding-2"]):
            with self.subTest(expected=expected):
                with self.assertRaisesRegex(ValueError, "逐项覆盖"):
                    validate_repair_plan_text(completed, expected)

        duplicated = completed + completed[completed.index("## Finding"):]
        with self.assertRaisesRegex(ValueError, "逐项覆盖"):
            validate_repair_plan_text(duplicated, ["finding-1"])


if __name__ == "__main__":
    unittest.main()
