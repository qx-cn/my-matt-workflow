"""Observe Ticket admission, briefing, and real test execution via the CLI."""
import json
from pathlib import Path
import subprocess

import unittest
import test_topic_lifecycle as topic_tests


class ImplementationTests(unittest.TestCase):
    # Inherit the temporary repository seam, not the Topic tests themselves.
    setUp = topic_tests.TopicLifecycleTests.setUp
    git = topic_tests.TopicLifecycleTests.git
    def cli(self, *args, ok=True):
        if args[:2] == ("implement", "start") and "--agent" not in args:
            args = (*args, "--agent", "codex")
        return topic_tests.TopicLifecycleTests.cli(self, *args, ok=ok)
    setup_config = topic_tests.TopicLifecycleTests.setup_config
    def ticket(self, topic="feature", number=1, commands=None, dependencies=(), status="ready-for-agent"):
        root = self.repo / f".agent/work/{topic}"
        spec = root / "specs" / f"specs-{topic}-01.md"
        spec.parent.mkdir(parents=True, exist_ok=True)
        spec.write_text(f"---\nspec_id: {topic}\nrevision: 1\n---\n# Spec\n## 验收标准\n- AC-01: marker observed\n")
        path = root / "tickets" / f"tickets-{topic}-{number:02d}.md"
        path.parent.mkdir(exist_ok=True)
        values = {"id": f"{topic}-{number:02d}", "title": "Execute tests", "ticket_kind": "implementation",
                  "spec_id": topic, "spec_revision": 1, "spec_ref": str(spec.relative_to(self.repo)),
                  "status": status, "blocked_by": list(dependencies), "sequence": number,
                  "test_commands": commands if commands is not None else ["python3 -c 'pass'"],
                  "rule_sources": [str(spec.relative_to(self.repo))], "rule_scope": ["code.txt"],
                  "rule_constraints": ["observe tests"], "rule_conflicts": [], "review_probes": ["recovery"],
                  "execution_agent": "auto", "claimed_by": "", "supersedes_ticket": [], "compensates": [], "tags": []}
        path.write_text("---\n" + "\n".join(f"{k}: {json.dumps(v)}" for k, v in values.items()) + "\n---\n\n## 要构建什么\nRun tests\n## 适用规则与影响区域\nlocal\n## 验收标准\n- [ ] marker observed\n")
        return path

    def replace(self, path, key, value):
        lines = path.read_text().splitlines()
        path.write_text("\n".join(f"{key}: {json.dumps(value)}" if l.startswith(key + ":") else l for l in lines) + "\n")

    def test_admission_matching_lineage_and_conflicts(self):
        self.setup_config(tests=("python3 -m unittest *", "python3 -c 'pass'"))
        p = self.ticket(commands=["python3 -m unittest"])
        self.cli("validate-ticket", str(p))
        self.replace(p, "test_commands", ["python3 -m unittest discover -s tests"])
        self.cli("validate-ticket", str(p))
        for value in ([], ["python3 -m unittestx"], ["python3 -c 'raise SystemExit(1)'"]):
            self.replace(p, "test_commands", value)
            self.cli("validate-ticket", str(p), ok=False)
        self.replace(p, "test_commands", ["python3 -c 'pass'"])
        self.replace(p, "spec_revision", 2)
        self.cli("validate-ticket", str(p), ok=False)
        self.replace(p, "spec_revision", 1)
        self.replace(p, "rule_conflicts", ["unresolved"])
        self.cli("validate-ticket", str(p), ok=False)

    def test_start_guards_dependencies_content_and_quick(self):
        self.setup_config(tests=("python3 -c 'pass'",))
        dep = self.ticket(number=1)
        p = self.ticket(number=2, dependencies=("feature-01",))
        self.cli("implement", "start", "--ticket", "feature-02", ok=False)
        self.replace(dep, "status", "complete")
        (self.repo / "code.txt").write_text("dirty")
        self.cli("implement", "start", "--ticket", "feature-02", ok=False)
        self.git("restore", "code.txt")
        self.cli("implement", "start", "--ticket", "feature-02")
        self.assertIn('status: implementing', p.read_text())
        self.ticket(number=3)
        self.cli("implement", "start", "--ticket", "feature-03", ok=False)
        self.ticket("quick")
        # A quick active Topic can gain a file accidentally; admission must still reject it.
        self.cli("topic", "start", "--topic", "other", "--level", "quick")
        self.ticket("other")
        self.cli("implement", "start", "--ticket", "other-01", ok=False)

    def test_start_briefing_baselines_and_pending_next_command(self):
        self.setup_config(tests=("python3 -c 'pass'",))
        p = self.ticket()
        topic = json.loads(self.cli("topic", "status", "--topic", "feature").stdout)
        self.assertIn("--ticket feature-01", topic["next_command"])
        baseline = self.git("rev-parse", "HEAD")
        out = json.loads(self.cli("implement", "start", "--ticket", "feature-01", "--agent", "codex").stdout)
        self.assertEqual("feature", self.git("branch", "--show-current"))
        self.assertEqual(baseline, out["baseline"])
        brief = Path(out["briefing"]).read_text()
        for value in ("feature-01", "AC-01", "marker observed", "python3 -c", "实施计划", "适用规则"):
            self.assertIn(value, brief)
        self.assertEqual("active", json.loads(self.cli("topic", "status").stdout)["status"])

    def test_pending_fork_baseline_nondefault_branch(self):
        self.setup_config(tests=("python3 -c 'pass'",))
        fork = self.git("rev-parse", "HEAD")
        self.git("switch", "-qc", "development")
        (self.repo / "code.txt").write_text("branch work")
        self.git("add", "code.txt")
        self.git("commit", "-qm", "branch work")
        self.ticket()
        out = json.loads(self.cli("implement", "start", "--ticket", "feature-01").stdout)
        self.assertEqual("development", self.git("branch", "--show-current"))
        self.assertEqual(self.git("rev-parse", "HEAD"), out["baseline"])
        self.assertEqual(fork, json.loads(self.cli("topic", "status").stdout)["baseline"])

    def test_pending_requires_full_tests_and_needs_user_is_busy(self):
        self.setup_config(tests=("python3 -m unittest *",))
        self.ticket(commands=["python3 -m unittest"])
        self.cli("implement", "start", "--ticket", "feature-01", ok=False)
        self.assertFalse((self.repo / ".agent/work/feature/topic-state.json").exists())
        self.setup_config(tests=("python3 -c 'pass'",))
        self.ticket(number=1, status="needs-user")
        self.ticket(number=2)
        self.cli("implement", "start", "--ticket", "feature-02", ok=False)

    def test_declared_tests_progress_failure_and_definition_change(self):
        self.setup_config(tests=("python3 -c *",))
        p = self.ticket(commands=["python3 -c 'pass'", "python3 -c 'print(\"failure marker\"); raise SystemExit(9)'"])
        # Full test entry is required independently from the argv prefix.
        self.setup_config(tests=("python3 -c *", "python3 -c 'pass'"))
        self.cli("implement", "start", "--ticket", "feature-01")
        self.cli("implement", "test", "--", "python3", "-c", "print('progress')")
        out = json.loads(self.cli("implement", "status").stdout)
        self.assertFalse(out["tests_passed"])
        result = self.cli("implement", "test", ok=False)
        self.assertIn("failure marker", result.stderr)
        self.assertIn("9", result.stderr)
        out = json.loads(self.cli("implement", "status").stdout)
        self.assertIn("implement test", out["next_command"])
        self.assertNotIn("finish", out["next_command"])
        self.replace(p, "test_commands", ["python3 -c 'pass'"])
        self.assertIn("reopen", self.cli("implement", "test", ok=False).stderr)

    def test_test_pass_is_bound_to_content_not_agent_or_ignored_files(self):
        self.setup_config(tests=("python3 -c 'pass'",))
        self.ticket()
        self.cli("implement", "start", "--ticket", "feature-01")
        self.cli("implement", "test")
        self.assertTrue(json.loads(self.cli("implement", "status").stdout)["tests_passed"])
        (self.repo / ".agent/note.md").write_text("note")
        self.assertTrue(json.loads(self.cli("implement", "status").stdout)["tests_passed"])
        (self.repo / "code.txt").write_text("new content")
        self.assertFalse(json.loads(self.cli("implement", "status").stdout)["tests_passed"])

    def test_topic_selection_and_cross_topic_ticket_rejection(self):
        self.setup_config(tests=("python3 -c 'pass'",))
        for topic in ("a", "b"):
            self.ticket(topic)
            self.cli("implement", "start", "--ticket", f"{topic}-01")
        self.cli("implement", "test", ok=False)
        self.cli("implement", "test", "--topic", "a", "--ticket", "b-01", ok=False)
        self.cli("implement", "test", "--topic", "a")
        self.assertTrue(json.loads(self.cli("implement", "status", "--topic", "a").stdout)["tests_passed"])
        self.assertFalse(json.loads(self.cli("implement", "status", "--topic", "b").stdout)["tests_passed"])

    def test_existing_branch_and_explicit_standard_topic(self):
        self.setup_config(tests=("python3 -c 'pass'",))
        self.git("branch", "feature")
        self.cli("topic", "start", "--topic", "feature", "--level", "standard")
        self.ticket()
        self.cli("implement", "start", "--ticket", "feature-01")
        self.assertEqual("feature", self.git("branch", "--show-current"))

    def test_dependency_commit_and_rules_are_in_brief(self):
        self.setup_config(tests=("python3 -c 'pass'",))
        dep = self.ticket(number=1, status="complete")
        self.ticket(number=2, dependencies=("feature-01",))
        (self.repo / "AGENTS.md").write_text("Apply the project rules.")
        (self.repo / "code.txt").write_text("predecessor")
        self.git("add", "AGENTS.md", "code.txt")
        self.git("commit", "-qm", "feature-01: predecessor")
        commit = self.git("rev-parse", "HEAD")
        out = json.loads(self.cli("implement", "start", "--ticket", "feature-02").stdout)
        brief = Path(out["briefing"]).read_text()
        for value in (commit, "code.txt", "AGENTS.md", "Apply the project rules."):
            self.assertIn(value, brief)

    def test_ignored_files_do_not_invalidate_tests(self):
        self.setup_config(tests=("python3 -c 'pass'",))
        (self.repo / ".gitignore").write_text("cache/\n")
        self.git("add", ".gitignore")
        self.git("commit", "-qm", "ignore cache")
        self.ticket()
        self.cli("implement", "start", "--ticket", "feature-01")
        self.cli("implement", "test")
        (self.repo / "cache").mkdir()
        (self.repo / "cache/item").write_text("ignored")
        self.assertTrue(json.loads(self.cli("implement", "status").stdout)["tests_passed"])

    def test_source_validation_failure_leaves_ticket_unclaimed(self):
        self.setup_config(tests=("python3 -c 'pass'",))
        p = self.ticket()
        self.replace(p, "rule_sources", ["missing.md"])
        self.cli("implement", "start", "--ticket", "feature-01", ok=False)
        self.assertIn('"ready-for-agent"', p.read_text())
        self.assertFalse((self.repo / ".agent/work/feature/implementations/feature-01.json").exists())

    def test_existing_branch_does_not_overwrite_changed_admission(self):
        self.setup_config(tests=("python3 -c 'pass'",))
        p = self.ticket()
        self.git("add", ".agent")
        self.git("commit", "-qm", "ready on main")
        self.git("switch", "-qc", "feature")
        self.replace(p, "status", "needs-user")
        self.git("add", ".agent")
        self.git("commit", "-qm", "needs user on target")
        self.git("switch", "-q", "main")
        self.cli("implement", "start", "--ticket", "feature-01", ok=False)
        self.assertIn('"needs-user"', p.read_text())
        self.assertFalse((self.repo / ".agent/work/feature/implementations/feature-01.json").exists())

    def test_each_test_is_bound_to_its_actual_content(self):
        self.setup_config(tests=("python3 -c *", "python3 -c 'pass'"))
        commands = ["python3 -c \"open('code.txt','w').write('changed')\"",
                    "python3 -c \"open('code.txt','w').write('initial\\n')\""]
        self.ticket(commands=commands)
        self.cli("implement", "start", "--ticket", "feature-01")
        out = json.loads(self.cli("implement", "test").stdout)
        self.assertEqual("initial\n", (self.repo / "code.txt").read_text())
        self.assertFalse(out["tests_passed"])
        self.assertFalse(json.loads(self.cli("implement", "status").stdout)["tests_passed"])

    def test_target_branch_rules_are_used(self):
        self.setup_config(tests=("python3 -c 'pass'",))
        self.ticket()
        (self.repo / "AGENTS.md").write_text("Rules on main.")
        self.git("add", ".agent", "AGENTS.md")
        self.git("commit", "-qm", "main inputs")
        self.git("switch", "-qc", "feature")
        (self.repo / "AGENTS.md").write_text("Rules on target.")
        self.git("add", "AGENTS.md")
        self.git("commit", "-qm", "target rules")
        self.git("switch", "-q", "main")
        out = json.loads(self.cli("implement", "start", "--ticket", "feature-01").stdout)
        text = Path(out["briefing"]).read_text()
        self.assertIn("Rules on target.", text)
        self.assertNotIn("Rules on main.", text)

    def test_target_branch_dependency_config_and_definition_changes_reject(self):
        for scenario in ("dependency", "config", "definition"):
            with self.subTest(scenario=scenario):
                if scenario != "dependency":
                    self.setUp()
                self.setup_config(tests=("python3 -c 'pass'",))
                dep = self.ticket(status="complete")
                p = self.ticket(number=2, dependencies=("feature-01",))
                self.git("add", ".agent")
                self.git("commit", "-qm", "main inputs")
                self.git("switch", "-qc", "feature")
                if scenario == "dependency":
                    self.replace(dep, "status", "ready-for-agent")
                elif scenario == "config":
                    config = self.repo / ".agent/matt-workflow.md"
                    config.write_text(config.read_text().replace("assurance_level: standard", "assurance_level: quick"))
                else:
                    p.write_text(p.read_text().replace("marker observed", "different acceptance"))
                before = p.read_bytes()
                self.git("add", ".agent")
                self.git("commit", "-qm", "target inputs")
                self.git("switch", "-q", "main")
                self.cli("implement", "start", "--ticket", "feature-02", ok=False)
                self.assertEqual(before, p.read_bytes())
                self.assertFalse((self.repo / ".agent/work/feature/implementations/feature-02.json").exists())

    def test_failure_with_non_utf8_output_still_records_exit_code(self):
        self.setup_config(tests=("python3 -c *", "python3 -c 'pass'"))
        self.ticket(commands=["python3 -c \"import sys; sys.stdout.buffer.write(b'binary\\xff'); raise SystemExit(7)\""])
        self.cli("implement", "start", "--ticket", "feature-01")
        result = self.cli("implement", "test", ok=False)
        self.assertIn("退出码：7", result.stderr)
        self.assertIn("binary", result.stderr)
        self.assertIn("implement test", json.loads(self.cli("implement", "status").stdout)["next_command"])
