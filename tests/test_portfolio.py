import json
import shutil
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PortfolioContractTests(unittest.TestCase):


    def test_ticket_contract_preserves_coverage_and_expand_contract_exception(self):
        text = (ROOT / "skills/my-to-tickets/SKILL.md").read_text()
        self.assertIn("acceptance coverage", text)
        self.assertIn("expand–contract", text)


    def test_artifact_storage_adapter_is_declared_for_writers(self):
        manifest = json.loads((ROOT / "resources/manifest.json").read_text())
        resource = manifest["resources"]["adapter-artifact-storage"]
        self.assertEqual(
            {
                "my-edit-article",
                "my-grill-with-docs",
                "my-to-spec",
                "my-handoff",
                "my-test-report",
                "my-to-questionnaire",
            },
            set(resource["consumers"]),
        )
        for skill in resource["consumers"]:
            body = (ROOT / "skills" / skill / "SKILL.md").read_text()
            self.assertIn(resource["release_path"], body, skill)

    def test_testing_seam_contract_is_shared(self):
        manifest = json.loads((ROOT / "resources/manifest.json").read_text())
        resource = manifest["resources"]["testing-seams"]
        self.assertEqual(
            {
                "my-codebase-design",
                "my-diagnosing-bugs",
                "my-tdd",
            },
            set(resource["consumers"]),
        )
        contract = (ROOT / resource["source"]).read_text()
        for phrase in ("公共接口", "内部 seam", "Adapter", "mock"):
            self.assertIn(phrase, contract)
        for skill in ("my-codebase-design", "my-diagnosing-bugs", "my-tdd"):
            body = (ROOT / "skills" / skill / "SKILL.md").read_text()
            self.assertIn(resource["release_path"], body, skill)

    def test_high_risk_skill_corrections_have_static_contracts(self):
        triage = (ROOT / "skills/my-triage/SKILL.md").read_text()
        self.assertNotIn("ticket_kind: implementation", triage)
        self.assertIn("confirmed-local-brief", (ROOT / "composition/manifest.json").read_text())
        self.assertIn("原请求路径或 URL", triage)

        install = (ROOT / "skills/my-install/SKILL.md").read_text()
        self.assertIn("runtime_entry", install)
        self.assertIn("workflow source root", install)
        self.assertIn("可在任意项目 cwd 执行", install)

        prototype = (ROOT / "skills/my-prototype/SKILL.md").read_text()
        self.assertIn("已批准的 implementation work unit", prototype)
        self.assertIn("{{skill-call:my-implement}}", prototype)
        for support in ("LOGIC.md", "UI.md"):
            body = (ROOT / "skills/my-prototype" / support).read_text()
            self.assertIn("获批的 implementation work unit", body)
            self.assertIn("my-implement", body)

        wizard = (ROOT / "skills/my-wizard/SKILL.md").read_text()
        for command in ("git ls-files --error-unmatch", "git check-ignore", "chmod 0600"):
            self.assertIn(command, wizard)

    def test_writing_tdd_and_design_contracts_match_runtime_model(self):
        tests_reference = (ROOT / "skills/my-tdd/tests.md").read_text()
        deepening = (ROOT / "skills/my-codebase-design/DEEPENING.md").read_text()
        self.assertIn("module boundary under test", tests_reference)
        self.assertIn("references/shared/testing-seams.md", deepening)
        self.assertNotIn("删掉它们", deepening)

        checker = (ROOT / "skills/my-tech-design/scripts/check_html.py").read_text()
        template = (ROOT / "skills/my-tech-design/assets/TEMPLATE.html").read_text()
        frontend = (ROOT / "skills/my-tech-design/FRONTEND.md").read_text()
        self.assertNotIn("REVIEW_TERMS", checker)
        self.assertIn("{{OVERVIEW_VISUAL}}", template)
        self.assertIn("删除整个可选视觉区块", frontend)

    def test_specialist_requirement_analysis_reports_independence_gap(self):
        skill = (ROOT / "resources/requirement-analysis.md").read_text()
        self.assertIn("requirement-reviewer-brief.md", skill)
        self.assertIn("independence evidence gap", skill)
        self.assertIn("简单请求", skill)
        self.assertIn("不意味着每次都要启动独立 reviewer", skill)


    def test_skill_review_requires_an_authorized_dispute_before_comparative(self):
        review = (ROOT / "skills/my-review-instructions/SKILL.md").read_text()
        self.assertIn("不自动授权 Deep Review 或 comparative", review)
        self.assertIn("争议命题", review)
        self.assertIn("预计成本", review)
        self.assertIn("用户明确授权", review)


    def test_ticket_templates_are_progressively_disclosed_by_backend(self):
        skill = (ROOT / "skills/my-to-tickets/SKILL.md").read_text()
        formats = (ROOT / "skills/my-to-tickets/TICKET-FORMATS.md").read_text()
        self.assertIn("[Ticket 格式](TICKET-FORMATS.md)", skill)
        self.assertLessEqual(len(skill.splitlines()), 90)
        for heading in ("## local", "## external", "## project-docs 与 none"):
            self.assertIn(heading, formats)

    def test_learning_mission_change_requires_confirmation(self):
        record = (
            ROOT / "skills/my-teach/LEARNING-RECORD-FORMAT.md"
        ).read_text()
        self.assertIn("用户确认后再更新 `MISSION.md`", record)


if __name__ == "__main__":
    unittest.main()
