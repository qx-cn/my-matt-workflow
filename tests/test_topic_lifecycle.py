"""Public CLI contracts for configuration v2 and quick/document Topics."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CLI = Path(__file__).resolve().parents[1] / "tools/workflow.py"
HEADINGS = ["改动概述", "测试结果", "审查发现与修复", "建议", "已知问题",
            "长期知识沉淀", "用户介入记录", "未验证项", "验收对照"]


class TopicLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        self.git("init", "-q", "--initial-branch=main")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.invalid")
        (self.repo / "code.txt").write_text("initial\n")
        self.git("add", "code.txt")
        self.git("commit", "-qm", "initial")

    def git(self, *args, cwd=None):
        return subprocess.check_output(["git", *args], cwd=cwd or self.repo, text=True).strip()

    def cli(self, *args, ok=True):
        if "--" in args:
            index = args.index("--")
            arguments = [*args[:index], "--repo", str(self.repo), *args[index:]]
        else:
            arguments = [*args, "--repo", str(self.repo)]
        result = subprocess.run([sys.executable, str(CLI), *arguments],
                                capture_output=True, text=True,
                                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
        if ok:
            self.assertEqual(0, result.returncode, result.stderr)
        else:
            self.assertNotEqual(0, result.returncode, result.stdout)
        return result

    def setup_config(self, mode="shared", tests=()):
        args = ["setup", "--apply", "--agent-directory-mode", mode]
        for command in tests:
            args.extend(["--test-command", command])
        self.cli(*args)
        if mode == "private":
            self.git("config", "user.name", "Test", cwd=self.repo / ".agent")
            self.git("config", "user.email", "test@example.invalid", cwd=self.repo / ".agent")

    def summary(self, topic="change", headings=HEADINGS):
        path = self.repo / f".agent/work/{topic}/deliveries/deliveries-{topic}-01.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(f"## {h}\n无\n" for h in headings))

    def test_setup_preview_and_nine_keys(self):
        self.cli("setup")
        self.assertFalse((self.repo / ".agent").exists())
        self.setup_config("private")
        text = (self.repo / ".agent/matt-workflow.md").read_text()
        keys = [line.split(":", 1)[0] for line in text.split("---")[1].splitlines() if ":" in line]
        self.assertEqual(9, len(keys))
        self.assertIn("schema_version: 2", text)
        self.assertNotIn("policy", text)
        self.assertTrue((self.repo / ".agent/.git").is_dir())

    def test_setup_preserves_string_branch_names_across_config_roundtrips(self):
        for branch in ('null', 'true', '123', '1e3', 'quote"name', 'feature/path', '{}'):
            with self.subTest(branch=branch):
                self.cli('setup', '--apply', '--agent-directory-mode', 'shared', '--base-branch', branch)
                self.cli('work-overview')
                report = json.loads(self.cli('setup').stdout)
                self.assertEqual(branch, report['config']['default_base_branch'])
                self.cli('setup', '--apply')
                if branch == '{}':
                    continue  # Only quoted JSON is a string; a bare object is not.
                # Previous v2 renderers emitted bare strings: keep these readable.
                path = self.repo / '.agent/matt-workflow.md'
                text = path.read_text().splitlines()
                path.write_text('\n'.join('default_base_branch: ' + branch if line.startswith('default_base_branch:') else line
                                          for line in text) + '\n')
                self.assertEqual(branch, json.loads(self.cli('setup').stdout)['config']['default_base_branch'])
        self.cli('setup', '--apply', '--base-branch', 'bad\\name', ok=False)
        path = self.repo / '.agent/matt-workflow.md'
        text = path.read_text()
        path.write_text(text.replace('schema_version: 2', 'schema_version: "2"'))
        self.assertIn('migrate', self.cli('work-overview', ok=False).stderr)

    def test_json_object_and_list_branch_values_are_rejected_without_writes(self):
        self.setup_config()
        path = self.repo / '.agent/matt-workflow.md'
        text = path.read_text()
        for value in ('{}', '[]', '{"name":"main"}', '["main"]'):
            with self.subTest(value=value):
                path.write_text('\n'.join('default_base_branch: ' + value if line.startswith('default_base_branch:') else line
                                          for line in text.splitlines()) + '\n')
                before = path.read_bytes()
                for args in (('setup',), ('work-overview',), ('setup', '--apply')):
                    self.assertIn('default_base_branch', self.cli(*args, ok=False).stderr)
                    self.assertEqual(before, path.read_bytes())

    def test_invalid_and_legacy_setup_is_zero_write(self):
        for flag, value, message in [("--assurance-level", "audited", "migrate"),
                                     ("--task-backend", "external", "task_backend")]:
            self.assertIn(message, self.cli("setup", flag, value, "--apply", ok=False).stderr)
            self.assertFalse((self.repo / ".agent").exists())
        self.setup_config()
        path = self.repo / ".agent/matt-workflow.md"
        path.write_text(path.read_text().replace("schema_version: 2", "schema_version: 1"))
        before = path.read_bytes()
        self.assertIn("migrate", self.cli("setup", "--apply", ok=False).stderr)
        self.assertEqual(before, path.read_bytes())

    def test_start_guards_and_branch_choices(self):
        self.setup_config()
        self.cli("topic", "start", "--level", "quick", ok=False)
        (self.repo / "code.txt").write_text("dirty")
        self.cli("topic", "start", "--topic", "change", "--level", "quick", ok=False)
        self.git("restore", "code.txt")
        self.cli("topic", "start", "--topic", "change", "--level", "quick")
        self.assertEqual("change", self.git("branch", "--show-current"))
        self.cli("topic", "start", "--topic", "change", "--level", "quick", ok=False)
        self.cli("topic", "start", "--topic", "second", "--level", "quick")
        self.assertEqual("change", self.git("branch", "--show-current"))
        self.cli("topic", "status", ok=False)
        self.cli("topic", "status", "--topic", "change")
        self.cli("topic", "start", "--topic", "standard", "--level", "standard", ok=False)

    def test_existing_branch_and_standard_wildcards(self):
        self.setup_config(tests=("python3 -m unittest *",))
        self.git("branch", "change")
        self.cli("topic", "start", "--topic", "change", "--level", "quick")
        self.assertEqual("change", self.git("branch", "--show-current"))
        self.cli("topic", "start", "--topic", "standard", "--level", "standard", ok=False)

    def test_overview_document_pending_active_and_archive_readonly(self):
        self.setup_config()
        (self.repo / ".agent/work/docs").mkdir(parents=True)
        pending = self.repo / ".agent/work/pending/tickets"
        pending.mkdir(parents=True)
        (pending / "tickets-pending-01.md").write_text('---\nid: pending-01\nstatus: ready-for-agent\ntest_commands: ["python3 -c \'pass\'"]\n---\nTicket\n')
        self.cli("topic", "start", "--topic", "change", "--level", "quick")
        result = json.loads(self.cli("work-overview", "--json").stdout)
        self.assertEqual({"docs": "document", "pending": "pending", "change": "active"},
                         {t["topic"]: t["status"] for t in result["topics"]})
        self.cli("topic", "start", "--topic", "pending", "--level", "quick", ok=False)
        self.assertIn("implement start", self.cli("topic", "complete", "--topic", "pending", ok=False).stderr)
        self.cli("topic", "complete", "--topic", "docs")
        self.cli("topic", "complete", "--topic", "docs", ok=False)
        self.cli("topic", "start", "--topic", "docs", "--level", "quick", ok=False)
        self.assertEqual("archived", json.loads(self.cli("topic", "status", "--topic", "docs").stdout)["status"])
        record = json.loads((self.repo / ".agent/metrics.jsonl").read_text())
        self.assertEqual("topic", record["kind"])
        self.assertIsNone(record["level"])
        self.assertIsNone(record["test_runs"])
        self.assertEqual("", self.git("status", "--porcelain", "--", ".agent"))

    def test_standard_without_ticket_rejects_completion(self):
        self.setup_config(tests=("python3 -c 'pass'",))
        self.cli("topic", "start", "--topic", "change", "--level", "standard")
        self.assertIn("Ticket", self.cli("topic", "complete", ok=False).stderr)

    def test_quick_summary_and_test_failure_leave_active(self):
        self.setup_config(tests=("python3 -c 'raise SystemExit(7)'",))
        self.cli("topic", "start", "--topic", "change", "--level", "quick")
        self.summary(headings=HEADINGS[:-1])
        self.assertIn("验收对照", self.cli("topic", "complete", ok=False).stderr)
        self.summary()
        result = self.cli("topic", "complete", ok=False)
        self.assertIn("7", result.stderr)
        self.assertFalse((self.repo / ".agent/archive/change").exists())
        self.assertEqual("active", json.loads(self.cli("topic", "status").stdout)["status"])

    def test_quick_complete_in_each_directory_mode(self):
        for mode in ("shared", "private"):
            with self.subTest(mode=mode):
                # Each mode is an independent repository and lifecycle.
                if mode == "private":
                    self.setUp()
                self.setup_config(mode, tests=("python3 -c 'pass'",))
                self.cli("topic", "start", "--topic", "change", "--level", "quick")
                before = int(self.git("rev-list", "--count", "HEAD"))
                self.summary()
                (self.repo / "code.txt").write_text("implemented\n")
                self.cli("topic", "complete")
                archive = self.repo / ".agent/archive/change"
                self.assertTrue(archive.is_dir())
                self.assertFalse((self.repo / ".agent/work/change").exists())
                record = json.loads((self.repo / ".agent/metrics.jsonl").read_text())
                self.assertEqual("quick", record["kind"])
                self.assertEqual(1, record["test_runs"])
                self.assertIsNone(record["ticket"])
                self.assertFalse(list(archive.rglob("*implement*")))
                self.assertEqual(1, int(self.git("rev-list", "--count", "HEAD")) - before)
                if mode == "private":
                    self.assertEqual("", self.git("ls-files", ".agent"))
                    self.assertEqual("", self.git("status", "--porcelain", cwd=self.repo / ".agent"))
                else:
                    self.assertEqual("", self.git("status", "--porcelain"))

    def test_quick_without_tests_marks_unconfigured(self):
        self.setup_config()
        self.cli("topic", "start", "--topic", "change", "--level", "quick")
        self.summary()
        self.cli("topic", "complete")
        self.assertIn("未配置测试", (self.repo / ".agent/archive/change/deliveries/deliveries-change-01.md").read_text())

    def test_failed_git_commit_can_retry_without_losing_work(self):
        self.setup_config()
        self.cli("topic", "start", "--topic", "change", "--level", "quick")
        self.summary()
        (self.repo / "code.txt").write_text("work to preserve\n")
        hook = self.repo / ".git/hooks/pre-commit"
        hook.write_text("#!/bin/sh\nexit 1\n")
        hook.chmod(0o755)
        self.cli("topic", "complete", ok=False)
        self.assertTrue((self.repo / ".agent/work/change").is_dir())
        self.assertFalse((self.repo / ".agent/archive/change").exists())
        self.assertEqual("work to preserve\n", (self.repo / "code.txt").read_text())
        hook.unlink()
        self.cli("topic", "complete")
        self.assertEqual(1, len((self.repo / ".agent/metrics.jsonl").read_text().splitlines()))

    def test_test_that_modifies_content_cannot_complete(self):
        self.setup_config(tests=("python3 -c \"open('code.txt','w').write('changed')\"",))
        self.cli("topic", "start", "--topic", "change", "--level", "quick")
        self.summary()
        self.assertIn("改变了内容", self.cli("topic", "complete", ok=False).stderr)
        self.assertFalse((self.repo / ".agent/archive/change").exists())

    def test_invalid_detection_does_not_write(self):
        (self.repo / "AGENTS.md").write_bytes(b"\xff")
        self.cli("setup", "--execution-agent", "codex", "--apply", ok=False)
        self.assertFalse((self.repo / ".agent").exists())

    def test_document_completion_preserves_staged_content(self):
        self.setup_config()
        (self.repo / ".agent/work/docs").mkdir(parents=True)
        (self.repo / "code.txt").write_text("unrelated\n")
        self.git("add", "code.txt")
        before = self.git("show", "HEAD:code.txt")
        self.cli("topic", "complete", "--topic", "docs")
        self.assertEqual(before, self.git("show", "HEAD:code.txt"))
        self.assertEqual("M  code.txt", self.git("status", "--porcelain", "--", "code.txt"))

    def test_shared_metadata_is_committed_even_when_ignored(self):
        self.setup_config()
        (self.repo / ".gitignore").write_text(".agent/\n")
        self.git("add", ".gitignore")
        self.git("commit", "-qm", "ignore metadata by default")
        (self.repo / ".agent/work/docs").mkdir(parents=True)
        self.cli("topic", "complete", "--topic", "docs")
        self.assertIn(".agent/metrics.jsonl", self.git("ls-files", ".agent"))
        self.assertEqual("", self.git("status", "--porcelain", "--", ".agent"))

    def test_private_metadata_commit_failure_does_not_duplicate_code_commit(self):
        self.setup_config("private")
        self.cli("topic", "start", "--topic", "change", "--level", "quick")
        self.summary()
        before = int(self.git("rev-list", "--count", "HEAD"))
        (self.repo / "code.txt").write_text("implementation\n")
        hook = self.repo / ".agent/.git/hooks/pre-commit"
        hook.write_text("#!/bin/sh\nexit 1\n")
        hook.chmod(0o755)
        self.cli("topic", "complete", ok=False)
        self.assertFalse((self.repo / ".agent/archive/change").exists())
        hook.unlink()
        self.cli("topic", "complete")
        self.assertEqual(1, int(self.git("rev-list", "--count", "HEAD")) - before)
        self.assertEqual(1, len((self.repo / ".agent/metrics.jsonl").read_text().splitlines()))

    def test_fenced_templates_are_not_summary_sections(self):
        self.setup_config()
        self.cli("topic", "start", "--topic", "change", "--level", "quick")
        self.summary()
        summary = self.repo / ".agent/work/change/deliveries/deliveries-change-01.md"
        template = summary.read_text()
        for opening, closing in [("```markdown", "```"), ("~~~~text", "~~~~"),
                                 ("  ````markdown", "  ````"), ("````", "```"),
                                 ("   ~~~", "   ~~~~~")]:
            with self.subTest(opening=opening, closing=closing):
                summary.write_text(opening + "\n" + template + "\n" + closing + "\n")
                self.assertIn("缺少章节", self.cli("topic", "complete", ok=False).stderr)
                self.assertFalse((self.repo / ".agent/archive/change").exists())
        summary.write_text("```markdown\n## 测试结果\n```\n" + template)
        self.cli("topic", "complete")
        archived = self.repo / ".agent/archive/change/deliveries/deliveries-change-01.md"
        text = archived.read_text()
        self.assertTrue(text.startswith("```markdown\n## 测试结果\n```\n## 改动概述"))
        self.assertEqual(1, text.count("未配置测试"))
