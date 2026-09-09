from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.workflow_lib.profile import render_profile


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / "tools/workflow.py"


class WorkflowCliHardeningTests(unittest.TestCase):
    def _repo(self, root: Path, *, scope_policy: str = "approved-plan") -> Path:
        repo = root / "repo"
        tickets = repo / ".agent/work/topic/tickets"
        tickets.mkdir(parents=True)
        (repo / ".agent/matt-workflow.md").write_text(
            render_profile(
                {
                    "schema_version": 1,
                    "work_scope_policy": scope_policy,
                    "external_write_policy": "allow",
                }
            ),
            encoding="utf-8",
        )
        spec = repo / ".agent/work/topic/specs/specs-topic-01.md"
        spec.parent.mkdir()
        spec.write_text(
            "---\nspec_id: topic\nrevision: 1\n---\n\n# Topic spec\n",
            encoding="utf-8",
        )
        (tickets / "tickets-topic-01.md").write_text(
            "---\n"
            "id: topic-01\n"
            "title: Topic\n"
            "ticket_kind: implementation\n"
            "spec_id: topic\n"
            "spec_revision: 1\n"
            "spec_ref: .agent/work/topic/specs/specs-topic-01.md\n"
            "status: ready-for-agent\n"
            "blocked_by: []\n"
            "claimed_by:\n"
            "rule_sources: [AGENTS.md]\n"
            "rule_scope: [app.py]\n"
            "rule_constraints: [test]\n"
            "rule_conflicts: []\n"
            "execution_agent: codex\n"
            "sequence: 1\n"
            "---\n\n## Acceptance\n\n- [ ] works\n",
            encoding="utf-8",
        )
        return repo

    def _run(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(WORKFLOW), *arguments],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_ticket_scope_output_is_consumable_by_next_ticket(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = self._repo(root)
            scope = self._run("ticket-scope", "--repo", str(repo), "--feature", "topic")
            self.assertEqual(0, scope.returncode, scope.stderr)
            document = json.loads(scope.stdout)
            self.assertEqual("approved-ticket-scope", document["approved_scope"]["kind"])
            scope_file = root / "scope.json"
            scope_file.write_text(scope.stdout, encoding="utf-8")

            selected = self._run(
                "next-ticket",
                "--repo",
                str(repo),
                "--feature",
                "topic",
                "--scope-file",
                str(scope_file),
            )
            self.assertEqual(0, selected.returncode, selected.stderr)
            self.assertEqual("continue", json.loads(selected.stdout)["status"])

            missing = self._run("next-ticket", "--repo", str(repo), "--feature", "topic")
            self.assertEqual("invalid", json.loads(missing.stdout)["status"])

    def test_external_write_boolean_cannot_mint_authorization(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._repo(Path(tmp))
            result = self._run(
                "write-gate",
                "--repo",
                str(repo),
                "--kind",
                "external",
                "--approved-scope",
                "--target",
                "origin",
                "--operation",
                "push",
                "--scope-id",
                "scope-1",
            )
            self.assertEqual(0, result.returncode, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual("pause", report["status"])
            self.assertEqual("boolean-approved-scope-is-not-authorization", report["reason"])


if __name__ == "__main__":
    unittest.main()
