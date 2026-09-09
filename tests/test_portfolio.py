import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.workflow_lib.portfolio import PortfolioError, validate_portfolio


ROOT = Path(__file__).resolve().parents[1]


class PortfolioContractTests(unittest.TestCase):
    def _fixture(self, target: Path) -> None:
        for directory in ("skills", "portfolio", "composition", "evals"):
            shutil.copytree(ROOT / directory, target / directory)

    def test_repository_portfolio_is_closed(self):
        manifest = validate_portfolio(ROOT)
        self.assertEqual(37, len(manifest.skills))
        self.assertEqual(
            {
                path.name
                for path in (ROOT / "skills").iterdir()
                if path.is_dir()
            },
            set(manifest.skills),
        )

    def test_router_macro_edges_are_bidirectional(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._fixture(root)
            router = root / "skills/my-ask-matt/SKILL.md"
            router.write_text(
                router.read_text().replace(
                    "`{{skill-call:my-test-report}}`",
                    "`my-test-report`",
                )
            )
            with self.assertRaisesRegex(
                PortfolioError, r"my-ask-matt.*调用宏.*my-test-report"
            ):
                validate_portfolio(root)

    def test_unknown_evidence_case_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._fixture(root)
            path = root / "portfolio/manifest.json"
            data = json.loads(path.read_text())
            data["skills"]["my-tdd"]["evidence"]["deterministic"] = {
                "cases": ["invented-green-case"]
            }
            path.write_text(json.dumps(data))
            with self.assertRaisesRegex(
                PortfolioError, r"my-tdd.*未知 deterministic case"
            ):
                validate_portfolio(root)

    def test_raw_host_call_in_portable_prose_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._fixture(root)
            skill = root / "skills/my-install/SKILL.md"
            skill.write_text(skill.read_text() + "\nRun $my-install.\n")
            with self.assertRaisesRegex(
                PortfolioError, r"my-install/SKILL.md.*宿主专属调用"
            ):
                validate_portfolio(root)

    def test_artifact_storage_adapter_is_declared_for_writers(self):
        manifest = json.loads((ROOT / "resources/manifest.json").read_text())
        resource = manifest["resources"]["adapter-artifact-storage"]
        self.assertEqual(
            {
                "my-edit-article",
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
        self.assertIn("references/composed/my-implement/COMPOSED.md", prototype)
        for support in ("LOGIC.md", "UI.md"):
            body = (ROOT / "skills/my-prototype" / support).read_text()
            self.assertIn("获批的 implementation work unit", body)
            self.assertIn("my-implement", body)

        wizard = (ROOT / "skills/my-wizard/SKILL.md").read_text()
        for command in ("git ls-files --error-unmatch", "git check-ignore", "chmod 0600"):
            self.assertIn(command, wizard)

    def test_writing_tdd_and_design_contracts_match_runtime_model(self):
        writing = (ROOT / "skills/my-writing-great-skills/SKILL.md").read_text()
        glossary = (ROOT / "skills/my-writing-great-skills/GLOSSARY.md").read_text()
        self.assertIn("调用能力由**宿主 policy**决定", writing)
        self.assertNotIn("存在本身*就是*调用轴", glossary)

        tdd = (ROOT / "skills/my-tdd/SKILL.md").read_text()
        self.assertIn("red → green → refactor", tdd)
        self.assertIn("references/shared/testing-seams.md", tdd)
        self.assertNotIn("重构不属于循环", tdd)
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
        skill = (ROOT / "skills/my-requirement-analysis/SKILL.md").read_text()
        self.assertIn("references/reviewer-brief.md", skill)
        self.assertIn("independence evidence gap", skill)
        self.assertIn("简单请求", skill)

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
