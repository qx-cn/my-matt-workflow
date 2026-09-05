from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.workflow_lib.profile import render_profile
from tools.workflow_lib.run_journal import (
    RunJournalError,
    build_run_context,
    record_run,
    start_run,
)


ROOT = Path(__file__).resolve().parents[1]


class RunJournalTests(unittest.TestCase):
    def _repo(self, directory: Path) -> tuple[Path, Path, str]:
        repo = directory / "repo"
        ticket = repo / ".agent/work/feature/tickets/tickets-feature-01.md"
        ticket.parent.mkdir(parents=True)
        (repo / ".agent/matt-workflow.md").write_text(
            render_profile(
                {
                    "schema_version": 1,
                    "commit_policy": "allow",
                    "external_write_policy": "deny",
                    "test_commands": ["python3 -m unittest"],
                }
            ),
            encoding="utf-8",
        )
        ticket.write_text(
            "---\n"
            "id: feature-01\n"
            "title: Feature\n"
            "ticket_kind: implementation\n"
            "spec_id: feature\n"
            "spec_revision: 2\n"
            "spec_ref: .agent/work/feature/specs/specs-feature-02.md\n"
            "status: ready-for-agent\n"
            "blocked_by: []\n"
            "claimed_by:\n"
            "rule_sources: [AGENTS.md]\n"
            "rule_scope: [app.py]\n"
            "rule_constraints: [test]\n"
            "rule_conflicts: []\n"
            "execution_agent: codex\n"
            "sequence: 1\n"
            "---\n\n"
            "- [ ] acceptance\n",
            encoding="utf-8",
        )
        (repo / "app.py").write_text("print('ok')\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.email", "smoke@example.com"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.name", "Smoke"], cwd=repo, check=True)
        subprocess.run(["git", "add", "."], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-qm", "baseline"], cwd=repo, check=True)
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True
        ).stdout.strip()
        return repo, ticket, sha

    def test_context_resolves_lineage_policies_gates_and_rules_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, ticket, sha = self._repo(Path(tmp))
            context = build_run_context(repo, ticket, sha, ["app.py"])
            self.assertEqual("feature-01", context["ticket"]["id"])
            self.assertEqual(2, context["spec"]["revision"])
            self.assertEqual("allow", context["write_gates"]["commit"]["status"])
            self.assertEqual("deny", context["write_gates"]["external"]["status"])
            self.assertEqual(["python3 -m unittest"], context["test_commands"])
            self.assertIn("rule_map", context)
            self.assertRegex(context["context_id"], r"^[0-9a-f]{64}$")

    def test_journal_persists_phase_receipts_and_blocker_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, ticket, sha = self._repo(Path(tmp))
            path, journal = start_run(repo, ticket, sha, ["app.py"])
            self.assertEqual("run-feature-01-spec-r2.json", path.name)
            self.assertEqual("admitted", journal["phase"])
            journal = record_run(path, "testing", test_receipt="red:test_name")
            journal = record_run(path, "implementing", test_receipt="green:all")
            journal = record_run(path, "reviewing", review_receipt="abc123")
            journal = record_run(path, "committing")
            journal = record_run(path, "complete")
            self.assertEqual("complete", journal["phase"])
            self.assertEqual("green:all", journal["receipts"]["test"])
            self.assertEqual("abc123", journal["receipts"]["review"])
            self.assertEqual(6, len(journal["events"]))
            self.assertEqual(journal, json.loads(path.read_text(encoding="utf-8")))

    def test_blocked_phase_requires_reason_and_transitions_are_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, ticket, sha = self._repo(Path(tmp))
            path, _ = start_run(repo, ticket, sha)
            with self.assertRaisesRegex(RunJournalError, "必须记录 blocker"):
                record_run(path, "blocked-by-design")
            with self.assertRaisesRegex(RunJournalError, "非法 run phase"):
                record_run(path, "complete")
            journal = record_run(path, "blocked-by-design", blocker="pause-for-revision")
            self.assertEqual("pause-for-revision", journal["blocker"])
            journal = record_run(path, "revising")
            self.assertIsNone(journal["blocker"])

    def test_run_start_cli_returns_recoverable_journal_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, ticket, sha = self._repo(Path(tmp))
            result = subprocess.run(
                [
                    sys.executable,
                    "tools/workflow.py",
                    "run-start",
                    "--repo",
                    str(repo),
                    "--ticket",
                    str(ticket),
                    "--base",
                    sha,
                    "--path",
                    "app.py",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual("ready", report["status"])
            self.assertTrue(Path(report["journal"]).is_file())


if __name__ == "__main__":
    unittest.main()
