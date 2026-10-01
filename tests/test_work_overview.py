"""Read-only work overview behavior across Specs, Tickets, and journals."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.workflow_lib.profile import render_profile
from tools.workflow_lib.tickets import TicketError, validate_ready_ticket
from tools.workflow_lib.work_overview import format_work_overview, work_overview


class WorkOverviewTests(unittest.TestCase):
    def _repo(self, root: Path, *, backend: str = "local") -> Path:
        agent = root / ".agent"
        agent.mkdir()
        (agent / "matt-workflow.md").write_text(
            render_profile({"schema_version": 1, "task_backend": backend}),
            encoding="utf-8",
        )
        return root

    def _spec(self, topic: Path, name: str, revision: int, *, status: str = "current") -> Path:
        directory = topic / "specs"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"specs-feature-{name}.md"
        path.write_text(
            f"---\nspec_id: feature\nrevision: {revision}\nstatus: {status}\n---\n# Feature\n",
            encoding="utf-8",
        )
        return path

    def _ticket(self, topic: Path, identifier: str, sequence: int, *, blocked_by: str = "[]", status: str = "ready-for-agent", claimed_by: str = "") -> Path:
        directory = topic / "tickets"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"tickets-feature-{sequence:02d}.md"
        path.write_text(
            "---\n"
            f"id: {identifier}\n"
            f"title: {identifier}\n"
            "ticket_kind: implementation\n"
            "spec_id: feature\n"
            "spec_revision: 2\n"
            "spec_ref: .agent/work/feature/specs/specs-feature-02.md\n"
            f"status: {status}\n"
            f"blocked_by: {blocked_by}\n"
            f"claimed_by: {claimed_by}\n"
            "rule_sources: [AGENTS.md]\n"
            "rule_scope: [src]\n"
            "rule_constraints: [test]\n"
            "rule_conflicts: []\n"
            "execution_agent: codex\n"
            f"sequence: {sequence}\n"
            "---\n\n## 验收\n- [ ] observable result\n",
            encoding="utf-8",
        )
        return path

    def test_reports_latest_spec_and_ready_frontier_without_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._repo(Path(tmp))
            topic = repo / ".agent" / "work" / "feature"
            self._spec(topic, "01", 1)
            self._spec(topic, "02", 2)
            self._ticket(topic, "first", 1)
            self._ticket(topic, "second", 2, blocked_by="[first]")
            before = {path: path.read_bytes() for path in topic.rglob("*") if path.is_file()}

            report = work_overview(repo, topic="feature")

            self.assertEqual("ok", report["status"])
            item = report["topics"][0]
            self.assertEqual(2, item["specs"][0]["revision"])
            self.assertEqual(["first"], [ticket["id"] for ticket in item["frontier"]])
            self.assertEqual(["first"], item["tickets"][1]["blocked_by"])
            self.assertEqual("start-ticket", item["next_action"]["kind"])
            self.assertEqual(before, {path: path.read_bytes() for path in topic.rglob("*") if path.is_file()})

    def test_duplicate_current_revision_does_not_select_arbitrarily(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._repo(Path(tmp))
            topic = repo / ".agent" / "work" / "feature"
            self._spec(topic, "a", 2)
            self._spec(topic, "b", 2)

            report = work_overview(repo, topic="feature")

            self.assertEqual("needs-attention", report["status"])
            self.assertEqual([], report["topics"][0]["specs"])
            self.assertEqual("inspect-inconsistent-state", report["topics"][0]["next_action"]["kind"])

    def test_historical_spec_status_is_shown_without_claiming_current(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._repo(Path(tmp))
            topic = repo / ".agent" / "work" / "feature"
            self._spec(topic, "04", 4, status="implemented-with-declared-evidence-gaps")

            report = work_overview(repo, topic="feature")

            self.assertEqual("ok", report["status"])
            spec = report["topics"][0]["specs"][0]
            self.assertFalse(spec["is_current"])
            self.assertEqual("implemented-with-declared-evidence-gaps", spec["status"])

    def test_active_journal_reuses_runtime_action_and_exposes_stale_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._repo(Path(tmp))
            topic = repo / ".agent" / "work" / "feature"
            self._spec(topic, "02", 2)
            self._ticket(topic, "first", 1, status="implementing", claimed_by="attempt-1")
            runs = topic / "runs"
            runs.mkdir()
            journal = runs / "run-first-spec-r2.json"
            journal.write_text(json.dumps({
                "phase": "implementing",
                "attempt_id": "attempt-1",
                "context": {"repo": str(repo), "topic": "feature", "ticket": {"id": "first"}},
                "receipts": {"test": None, "review": None, "code": None},
                "evidence": [],
            }), encoding="utf-8")

            with mock.patch("tools.workflow_lib.work_overview.verify_run_sources"):
                report = work_overview(repo, topic="feature")
            self.assertEqual(1, len(report["topics"][0]["sessions"]), report)
            session = report["topics"][0]["sessions"][0]
            self.assertEqual("continue-implementation", session["next_action"])
            self.assertEqual("continue-implementation", report["topics"][0]["next_action"]["action"])
            self.assertEqual("match", session["source_state"])

            report = work_overview(repo, topic="feature")
            self.assertEqual("needs-attention", report["status"])
            self.assertEqual("stale", report["topics"][0]["sessions"][0]["source_state"])
            self.assertEqual("inspect-inconsistent-state", report["topics"][0]["next_action"]["kind"])

    def test_duplicate_active_journal_for_one_claim_blocks_next_action(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._repo(Path(tmp))
            topic = repo / ".agent" / "work" / "feature"
            self._spec(topic, "02", 2)
            self._ticket(topic, "first", 1, status="implementing", claimed_by="attempt-1")
            runs = topic / "runs"
            runs.mkdir()
            journal = json.dumps({
                "phase": "implementing",
                "attempt_id": "attempt-1",
                "context": {"repo": str(repo), "topic": "feature", "ticket": {"id": "first"}},
                "receipts": {"test": None, "review": None, "code": None},
                "evidence": [],
            })
            (runs / "run-first-spec-r2.json").write_text(journal, encoding="utf-8")
            (runs / "run-first-spec-r2-attempt-attempt-1.json").write_text(journal, encoding="utf-8")

            with mock.patch("tools.workflow_lib.work_overview.verify_run_sources"):
                report = work_overview(repo, topic="feature")

            self.assertEqual("needs-attention", report["status"])
            item = report["topics"][0]
            self.assertEqual("inspect-inconsistent-state", item["next_action"]["kind"])
            self.assertTrue(any("多个活动 journal" in problem for problem in item["problems"]))

    def test_current_claim_is_visible_despite_unrelated_historical_problems(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._repo(Path(tmp))
            topic = repo / ".agent" / "work" / "feature"
            self._spec(topic, "02", 2)
            self._ticket(topic, "current", 1, status="implementing", claimed_by="current-attempt")
            runs = topic / "runs"
            runs.mkdir()
            (runs / "run-current.json").write_text(json.dumps({
                "phase": "implementing",
                "attempt_id": "current-attempt",
                "context": {"repo": str(repo), "topic": "feature", "ticket": {"id": "current"}},
                "evidence": [],
            }), encoding="utf-8")
            (runs / "run-old.json").write_text(json.dumps({
                "phase": "complete",
                "attempt_id": ["legacy"],
                "submission": {"outcome": "completed"},
                "context": {"repo": str(repo), "topic": "feature", "ticket": {"id": "old"}},
            }), encoding="utf-8")
            (runs / "run-archived.json").write_text(json.dumps({
                "phase": "complete",
                "attempt_id": "archived-attempt",
                "submission": {"outcome": "completed"},
                "context": {"repo": str(repo), "topic": "feature", "ticket": {"id": "archived"}},
                "evidence": [],
            }), encoding="utf-8")

            with mock.patch("tools.workflow_lib.work_overview.verify_run_sources"):
                report = work_overview(repo, topic="feature")

            item = report["topics"][0]
            self.assertEqual("needs-attention", report["status"])
            self.assertTrue(any("attempt_id 无效" in problem for problem in item["problems"]))
            self.assertEqual("implementation-next-action", item["next_action"]["kind"])
            self.assertEqual(".agent/work/feature/runs/run-current.json", item["next_action"]["journal"])
            rendered = format_work_overview(report)
            self.assertIn("历史实施会话：1 条", rendered)
            self.assertNotIn("实施会话：archived /", rendered)

    def test_invalid_claimed_by_is_reported_without_crashing(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._repo(Path(tmp))
            topic = repo / ".agent" / "work" / "feature"
            self._spec(topic, "02", 2)
            bad = self._ticket(topic, "bad", 1, claimed_by="[bad]")

            report = work_overview(repo, topic="feature")

            self.assertEqual("needs-attention", report["status"])
            item = report["topics"][0]
            self.assertEqual(["bad"], [ticket["id"] for ticket in item["tickets"]])
            self.assertEqual([], item["frontier"])
            self.assertEqual("inspect-inconsistent-state", item["next_action"]["kind"])
            self.assertTrue(any(str(bad.relative_to(repo)) in problem and "claimed_by" in problem for problem in item["problems"]))
            with self.assertRaisesRegex(TicketError, "claimed_by"):
                validate_ready_ticket(bad)

    def test_invalid_ready_candidate_preserves_current_ticket_and_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._repo(Path(tmp))
            topic = repo / ".agent" / "work" / "feature"
            self._spec(topic, "02", 2)
            self._ticket(topic, "current", 1, status="implementing", claimed_by="current-attempt")
            bad = self._ticket(topic, "bad", 2)
            bad.write_text(
                bad.read_text(encoding="utf-8").replace("spec_revision: 2", "spec_revision: 3"),
                encoding="utf-8",
            )
            runs = topic / "runs"
            runs.mkdir()
            journal = runs / "run-current.json"
            journal.write_text(json.dumps({
                "phase": "implementing",
                "attempt_id": "current-attempt",
                "context": {"repo": str(repo), "topic": "feature", "ticket": {"id": "current"}},
                "evidence": [],
            }), encoding="utf-8")

            with mock.patch("tools.workflow_lib.work_overview.verify_run_sources"):
                report = work_overview(repo, topic="feature")

            item = report["topics"][0]
            self.assertEqual("needs-attention", report["status"])
            self.assertEqual(["bad", "current"], [ticket["id"] for ticket in item["tickets"]])
            self.assertEqual([], item["frontier"])
            self.assertTrue(any("spec_id/spec_revision" in problem for problem in item["problems"]))
            self.assertEqual("implementation-next-action", item["next_action"]["kind"])
            self.assertEqual(str(journal.relative_to(repo)), item["next_action"]["journal"])

    def test_invalid_dependency_graph_preserves_current_ticket_and_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._repo(Path(tmp))
            topic = repo / ".agent" / "work" / "feature"
            self._spec(topic, "02", 2)
            self._ticket(topic, "current", 1, status="implementing", claimed_by="current-attempt")
            self._ticket(topic, "bad", 2, blocked_by="[missing]")
            runs = topic / "runs"
            runs.mkdir()
            journal = runs / "run-current.json"
            journal.write_text(json.dumps({
                "phase": "implementing",
                "attempt_id": "current-attempt",
                "context": {"repo": str(repo), "topic": "feature", "ticket": {"id": "current"}},
                "evidence": [],
            }), encoding="utf-8")

            with mock.patch("tools.workflow_lib.work_overview.verify_run_sources"):
                report = work_overview(repo, topic="feature")

            item = report["topics"][0]
            self.assertEqual("needs-attention", report["status"])
            self.assertEqual(["bad", "current"], [ticket["id"] for ticket in item["tickets"]])
            self.assertEqual(["missing"], item["tickets"][0]["blocked_by"])
            self.assertEqual([], item["frontier"])
            self.assertTrue(any("依赖不存在" in problem for problem in item["problems"]))
            self.assertEqual("implementation-next-action", item["next_action"]["kind"])
            self.assertEqual(str(journal.relative_to(repo)), item["next_action"]["journal"])

    def test_invalid_ready_ticket_does_not_hide_independent_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._repo(Path(tmp))
            topic = repo / ".agent" / "work" / "feature"
            self._spec(topic, "02", 2)
            bad = self._ticket(topic, "bad", 1)
            bad.write_text(
                bad.read_text(encoding="utf-8").replace("spec_revision: 2", "spec_revision: 3"),
                encoding="utf-8",
            )
            self._ticket(topic, "good", 2)

            report = work_overview(repo, topic="feature")

            self.assertEqual("needs-attention", report["status"])
            item = report["topics"][0]
            self.assertEqual(["good"], [ticket["id"] for ticket in item["frontier"]])
            self.assertFalse(item["tickets"][0]["eligible"])
            self.assertTrue(item["tickets"][1]["eligible"])
            self.assertTrue(any("spec_id/spec_revision" in problem for problem in item["problems"]))

    def test_malformed_submission_is_reported_not_hidden_as_history(self):
        for submission in ("oops", {}, {"outcome": ["completed"]}):
            with self.subTest(submission=submission), tempfile.TemporaryDirectory() as tmp:
                repo = self._repo(Path(tmp))
                topic = repo / ".agent" / "work" / "feature"
                runs = topic / "runs"
                runs.mkdir(parents=True)
                (runs / "run-bad.json").write_text(json.dumps({
                    "phase": "implementing",
                    "attempt_id": "attempt-1",
                    "submission": submission,
                    "context": {"repo": str(repo), "topic": "feature", "ticket": {"id": "bad"}},
                }), encoding="utf-8")

                report = work_overview(repo, topic="feature")

                self.assertEqual("needs-attention", report["status"])
                item = report["topics"][0]
                self.assertEqual([], item["sessions"])
                self.assertEqual("inspect-inconsistent-state", item["next_action"]["kind"])
                self.assertTrue(any("submission 无效" in problem for problem in item["problems"]))

    def test_malformed_phase_is_reported_instead_of_crashing(self):
        for phase in ([], {}):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as tmp:
                repo = self._repo(Path(tmp))
                topic = repo / ".agent" / "work" / "feature"
                runs = topic / "runs"
                runs.mkdir(parents=True)
                (runs / "run-bad.json").write_text(json.dumps({
                    "phase": phase,
                    "attempt_id": "attempt-1",
                    "context": {"repo": str(repo), "topic": "feature", "ticket": {"id": "bad"}},
                }), encoding="utf-8")

                report = work_overview(repo, topic="feature")

                self.assertEqual("needs-attention", report["status"])
                item = report["topics"][0]
                self.assertEqual([], item["sessions"])
                self.assertEqual("inspect-inconsistent-state", item["next_action"]["kind"])
                self.assertTrue(any("phase 无效" in problem for problem in item["problems"]))

    def test_submitted_outcome_must_match_terminal_phase(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._repo(Path(tmp))
            topic = repo / ".agent" / "work" / "feature"
            runs = topic / "runs"
            runs.mkdir(parents=True)
            (runs / "run-bad.json").write_text(json.dumps({
                "phase": "implementing",
                "attempt_id": "attempt-1",
                "submission": {"outcome": "completed"},
                "context": {"repo": str(repo), "topic": "feature", "ticket": {"id": "bad"}},
            }), encoding="utf-8")

            report = work_overview(repo, topic="feature")

            self.assertEqual("needs-attention", report["status"])
            item = report["topics"][0]
            self.assertEqual([], item["sessions"])
            self.assertEqual("inspect-inconsistent-state", item["next_action"]["kind"])
            self.assertTrue(any("submission 与 phase 不一致" in problem for problem in item["problems"]))

    def test_malformed_attempt_id_is_reported_instead_of_crashing(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._repo(Path(tmp))
            topic = repo / ".agent" / "work" / "feature"
            self._spec(topic, "02", 2)
            runs = topic / "runs"
            runs.mkdir()
            (runs / "run-first-spec-r2.json").write_text(json.dumps({
                "phase": "implementing",
                "attempt_id": ["invalid"],
                "context": {"repo": str(repo), "topic": "feature", "ticket": {"id": "first"}},
            }), encoding="utf-8")

            report = work_overview(repo, topic="feature")

            self.assertEqual("needs-attention", report["status"])
            self.assertEqual("inspect-inconsistent-state", report["topics"][0]["next_action"]["kind"])
            self.assertTrue(any("attempt_id 无效" in problem for problem in report["topics"][0]["problems"]))

    def test_default_overview_reports_symlink_topic(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._repo(Path(tmp))
            work = repo / ".agent" / "work"
            work.mkdir()
            other = repo / "other-topic"
            other.mkdir()
            (work / "linked").symlink_to(other, target_is_directory=True)

            report = work_overview(repo)

            self.assertEqual("needs-attention", report["status"])
            self.assertEqual([], report["topics"])
            self.assertTrue(any("linked" in problem for problem in report["problems"]))

    def test_external_backend_is_explicitly_unsupported(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._repo(Path(tmp), backend="external")
            report = work_overview(repo)
            self.assertEqual("unsupported-backend", report["status"])
            self.assertEqual([], report["topics"])

    def test_cli_has_readable_and_machine_readable_views(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._repo(Path(tmp))
            topic = repo / ".agent" / "work" / "feature"
            self._spec(topic, "02", 2)
            ticket = self._ticket(topic, "first", 1)
            ticket.write_text(ticket.read_text().replace('ticket_kind: implementation\n',
                                                         'ticket_kind: implementation\ntest_commands: []\n'))
            from tools.workflow_lib.topic_service import render_config
            (repo / ".agent/matt-workflow.md").write_text(render_config({
                "schema_version": 2, "task_backend": "local", "agent_directory_mode": "shared",
                "default_base_branch": "main", "test_commands": [], "standards_sources": [],
                "domain_sources": [], "default_execution_agent": "auto", "assurance_level": "standard",
            }))
            base = [sys.executable, "tools/workflow.py", "work-overview", "--repo", str(repo), "--topic", "feature"]
            root = Path(__file__).resolve().parents[1]

            readable = subprocess.run(base, cwd=root, capture_output=True, text=True, check=False)
            structured = subprocess.run([*base, "--json"], cwd=root, capture_output=True, text=True, check=False)

            self.assertEqual(0, readable.returncode, readable.stderr)
            self.assertIn("feature: pending", readable.stdout)
            self.assertEqual(0, structured.returncode, structured.stderr)
            self.assertEqual("pending", json.loads(structured.stdout)["topics"][0]["status"])


if __name__ == "__main__":
    unittest.main()
