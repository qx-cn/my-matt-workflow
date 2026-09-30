"""Behavioral checks for the saved pre-simplification migration inputs."""

import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.capture_workflow_baseline import measure_markdown


FIXTURES = Path(__file__).parent / "fixtures" / "workflow_simplification"
# AC-34: Cursor projection of old release 20260929-234249 measured 58,213
# Python characters, including my-requirement-analysis (capture baseline.json).


class BaselineMeasurementTests(unittest.TestCase):
    def test_example_links_do_not_expand_the_markdown_closure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = root / "sample"
            skill.mkdir()
            text = "示例\n```markdown\n[模板](unused.md) [占位](missing.md)\n```\n"
            (skill / "SKILL.md").write_text(text, encoding="utf-8")
            (skill / "unused.md").write_text("模板不是真实链接目标", encoding="utf-8")
            report = measure_markdown(root, ["sample"])
            self.assertEqual(len(text), report["characters"])
            self.assertEqual(1, report["reachable_files"])

    def test_transitive_markdown_is_counted_once_by_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("first", "second"):
                skill = root / name
                skill.mkdir()
                (skill / "SKILL.md").write_text("中文 [下一页](notes.md)\n", encoding="utf-8")
                (skill / "notes.md").write_text("[末页](end.md) [循环](SKILL.md)\n", encoding="utf-8")
                (skill / "end.md").write_text("终点\n", encoding="utf-8")
                (skill / "unused.md").write_text("不应被计数", encoding="utf-8")
            report = measure_markdown(root, ["first", "second"])
            expected = len("中文 [下一页](notes.md)\n") + len("[末页](end.md) [循环](SKILL.md)\n") + len("终点\n")
            self.assertEqual(expected, report["characters"])
            self.assertEqual(6, report["reachable_files"])
            self.assertEqual(3, report["unique_contents"])


class LegacyFixtureTests(unittest.TestCase):
    def test_saved_states_and_baselines_can_be_loaded_without_mutating_inputs(self):
        from tools.workflow_lib.tickets import frontmatter
        before = {str(p.relative_to(FIXTURES)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in FIXTURES.rglob("*") if p.is_file()}
        manifest = json.loads((FIXTURES / "baseline.json").read_text())
        project = FIXTURES / "legacy_project"
        expected = {"A": ["ready-for-agent", "complete", "implementing"],
                    "B": ["blocked-by-design"], "C": ["revalidated"],
                    "D": ["complete"], "E": ["implementing", "blocked-by-design"]}
        self.assertEqual(expected, manifest["legacy_states"])
        for topic, states in expected.items():
            files = sorted((project / ".agent" / "work" / f"legacy-{topic.lower()}" / "tickets").glob("*.md"))
            self.assertEqual(states, [frontmatter(p)["status"] for p in files])
            self.assertTrue(all("test_commands" not in frontmatter(p) for p in files))
        with tempfile.TemporaryDirectory() as tmp:
            loaded = Path(tmp) / "loaded"
            subprocess.run(["git", "clone", "--quiet", str(FIXTURES / "baseline.bundle"), str(loaded)],
                           check=True, capture_output=True)
            shutil.copytree(project, loaded, dirs_exist_ok=True)
            for topic, states in expected.items():
                files = sorted((loaded / ".agent" / "work" / f"legacy-{topic.lower()}" / "tickets").glob("*.md"))
                self.assertEqual(states, [frontmatter(p)["status"] for p in files])
            self.assertGreaterEqual(sum(state in {"implementing", "blocked-by-design"}
                                        for state in expected["E"]), 2)
            self.assertEqual("audited", frontmatter(loaded / ".agent" / "matt-workflow.md")["assurance_level"])
            for topic in ("a", "b", "c"):
                for journal in (project / ".agent" / "work" / f"legacy-{topic}" / "runs").glob("run-*.json"):
                    record = json.loads(journal.read_text())
                    baseline = record["context"]["base_sha"]
                    subprocess.run(["git", "cat-file", "-e", baseline + "^{commit}"],
                                   cwd=loaded, check=True, capture_output=True)
        after = {str(p.relative_to(FIXTURES)): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in FIXTURES.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_unfinished_session_was_copied_without_changing_its_files(self):
        copied = FIXTURES / "unfinished_session"
        original = Path(__file__).parents[1] / "evals" / "fixtures" / "my-implement" / "unfinished-session"
        inventory = lambda root: {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in root.rglob("*") if p.is_file()}
        # Later tickets remove evals; the retained copy remains independently usable.
        if original.is_dir():
            self.assertEqual(inventory(original), inventory(copied))
        self.assertTrue((copied / "app.py").is_file())
        self.assertTrue((copied / ".agent" / "work" / "turn-closure" / "tickets" /
                         "tickets-turn-closure-01.md").is_file())


if __name__ == "__main__":
    unittest.main()
