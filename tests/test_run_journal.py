from __future__ import annotations

import json
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.workflow_lib.profile import render_profile
from tools.workflow_lib.run_journal import (
    RunJournalError,
    build_code_receipt,
    build_run_context,
    close_implementation_session,
    open_repair_plan,
    open_repair_plan_review,
    open_implementation_session,
    open_review_evidence,
    record_review_evidence,
    record_run,
    run_test_evidence,
    start_run,
    submit_review_result,
    submit_repair_plan_review,
    submit_run_outcome,
)


ROOT = Path(__file__).resolve().parents[1]
REVIEW_COMMAND = (
    "python3 -c \"import json,os; b=json.loads(os.environ['MY_MATT_TICKET_BOUNDARY']); "
    "p=b['current']['acceptance']; r='spec:'+os.environ['MY_MATT_SPEC_REF']; print(json.dumps({"
    "'review_id': os.environ['MY_MATT_REVIEW_ID'], 'status': 'pass', "
    "'code_content_id': os.environ['MY_MATT_CODE_CONTENT_ID'], "
    "'reviewer_provenance': {'kind':'self','session_id':os.environ['MY_MATT_IMPLEMENTATION_SESSION_ID']}, "
    "'findings': [], 'follow_ons': [], 'design_gap': None, "
    "'self_review_coverage': {'acceptance':[{'acceptance_id':x['id'],'evidence_refs':[r]} for x in p], "
    "'probes':[{'probe':x,'summary':'checked','evidence_refs':[r]} for x in b['required_probes']]} }))\""
)
REVIEW_ARGV = shlex.split(REVIEW_COMMAND)


def self_review_result(unit: dict[str, object], status: str, findings: list[dict[str, object]] | None = None) -> dict[str, object]:
    boundary = unit["ticket_boundary"]
    assert isinstance(boundary, dict)
    current = boundary["current"]
    assert isinstance(current, dict)
    artifact = unit["artifacts"][0]
    assert isinstance(artifact, dict)
    ref = f"snapshot:{artifact['repo_path']}"
    acceptance = current["acceptance"]
    assert isinstance(acceptance, list)
    acceptance_id = acceptance[0]["id"]
    normalized = []
    for finding in findings or []:
        normalized.append({**finding, "acceptance_ids": [acceptance_id]})
    return {
        "review_id": unit["review_id"],
        "status": status,
        "code_content_id": unit["code_content_id"],
        "reviewer_provenance": {
            "kind": "self", "session_id": unit["implementation_session_id"],
        },
        "findings": normalized,
        "follow_ons": [],
        "design_gap": None,
        "self_review_coverage": {
            "acceptance": [
                {"acceptance_id": item["id"], "evidence_refs": [ref]}
                for item in acceptance
            ],
            "probes": [
                {"probe": probe, "summary": "checked", "evidence_refs": [ref]}
                for probe in boundary["required_probes"]
            ],
        },
    }


class RunJournalTests(unittest.TestCase):
    @staticmethod
    def _completed_result(path: Path) -> dict[str, object]:
        code = build_code_receipt(path)
        test = run_test_evidence(path, ["python3", "-c", "pass"])
        review_unit = open_review_evidence(path)
        review_report = record_review_evidence(
            path, Path(str(review_unit["snapshot_dir"])), REVIEW_ARGV
        )
        return {
            "outcome": "completed",
            "test_receipt": test,
            "review_receipt": review_report["review_receipt"],
            "code_receipt": code,
            "blocker": None,
        }

    @staticmethod
    def _advance_to_committing(path: Path) -> None:
        record_run(path, "implementing")
        record_run(path, "reviewing")
        record_run(path, "committing")

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
                    "test_commands": ["python3 -c pass"],
                    "review_commands": [REVIEW_COMMAND],
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
        spec = repo / ".agent/work/feature/specs/specs-feature-02.md"
        spec.parent.mkdir(parents=True)
        spec.write_text(
            "---\nspec_id: feature\nrevision: 2\n---\n\n# Feature spec\n",
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

    @staticmethod
    def _set_ticket_agent(ticket: Path, agent: str) -> None:
        text = ticket.read_text(encoding="utf-8")
        ticket.write_text(
            text.replace("execution_agent: codex", f"execution_agent: {agent}"),
            encoding="utf-8",
        )

    def test_context_resolves_lineage_policies_gates_and_rules_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, ticket, sha = self._repo(Path(tmp))
            context = build_run_context(repo, ticket, sha, ["app.py"])
            self.assertEqual("feature-01", context["ticket"]["id"])
            self.assertEqual(2, context["spec"]["revision"])
            self.assertEqual("allow", context["write_gates"]["commit"]["status"])
            self.assertEqual("deny", context["write_gates"]["external"]["status"])
            self.assertEqual(["python3 -c pass"], context["test_commands"])
            self.assertEqual([REVIEW_COMMAND], context["review_commands"])
            self.assertIn("rule_map", context)
            self.assertRegex(context["ticket"]["definition"]["sha256"], r"^[0-9a-f]{64}$")
            self.assertRegex(context["spec"]["content"]["sha256"], r"^[0-9a-f]{64}$")
            self.assertRegex(context["context_id"], r"^[0-9a-f]{64}$")
            explicit_context = build_run_context(
                repo, ticket, sha, ["app.py"], execution_agent="codex"
            )
            self.assertEqual(context["context_id"], explicit_context["context_id"])
            self.assertNotIn("requested_execution_agent", explicit_context["ticket"])

    def test_parallel_mode_is_absent_by_default_and_recorded_only_on_opt_in(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, ticket, sha = self._repo(Path(tmp))
            serial = build_run_context(repo, ticket, sha, ["app.py"])
            parallel = build_run_context(
                repo, ticket, sha, ["app.py"], parallel=True
            )
            self.assertNotIn("parallel_mode", serial)
            self.assertIs(True, parallel["parallel_mode"])
            self.assertNotEqual(serial["context_id"], parallel["context_id"])

    def test_auto_agent_binds_to_current_environment_for_rules_and_journal(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, ticket, sha = self._repo(Path(tmp))
            self._set_ticket_agent(ticket, "auto")
            (repo / "CLAUDE.md").write_text("Claude rules\n", encoding="utf-8")

            context = build_run_context(
                repo, ticket, sha, ["app.py"], execution_agent="claude"
            )

            self.assertEqual("claude", context["ticket"]["execution_agent"])
            self.assertEqual("auto", context["ticket"]["requested_execution_agent"])
            self.assertIn("CLAUDE.md", [rule["source"] for rule in context["rule_map"]])

    def test_auto_agent_requires_current_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, ticket, sha = self._repo(Path(tmp))
            self._set_ticket_agent(ticket, "auto")

            with self.assertRaisesRegex(RunJournalError, "需要传入当前执行 Agent"):
                build_run_context(repo, ticket, sha)

    def test_fixed_agent_rejects_a_different_current_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, ticket, sha = self._repo(Path(tmp))

            with self.assertRaisesRegex(RunJournalError, "当前 Agent 是 claude"):
                build_run_context(repo, ticket, sha, execution_agent="claude")

    def test_existing_auto_run_stays_bound_to_its_original_agent(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, ticket, sha = self._repo(Path(tmp))
            self._set_ticket_agent(ticket, "auto")
            start_run(repo, ticket, sha, execution_agent="codex")

            with self.assertRaisesRegex(RunJournalError, "已固定由 codex 执行"):
                start_run(repo, ticket, sha, execution_agent="claude")

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
            self.assertNotIn("parallel_mode", report["run"]["context"])
            self.assertEqual("implementation", report["work_unit"]["kind"])
            self.assertEqual("serial", report["work_unit"]["execution_mode"])
            self.assertEqual("feature-01", report["work_unit"]["ticket"]["id"])
            self.assertEqual(
                ["completed", "blocked-by-design", "blocked-by-evidence", "blocked-by-review"],
                report["work_unit"]["expected_outcomes"],
            )

    def test_run_start_cli_records_explicit_parallel_opt_in(self):
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
                    "--parallel",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            report = json.loads(result.stdout)
            context = report["run"]["context"]
            self.assertIs(True, context["parallel_mode"])
            self.assertEqual("parallel", report["work_unit"]["execution_mode"])

    def test_run_start_cli_resolves_auto_agent(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, ticket, sha = self._repo(Path(tmp))
            self._set_ticket_agent(ticket, "auto")
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
                    "--agent",
                    "claude",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            run = json.loads(result.stdout)["run"]
            self.assertEqual("claude", run["context"]["ticket"]["execution_agent"])

    def test_implementation_session_cli_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, ticket, sha = self._repo(root)
            opened = subprocess.run(
                [
                    sys.executable,
                    "tools/workflow.py",
                    "implementation-open",
                    "--repo",
                    str(repo),
                    "--ticket",
                    str(ticket),
                    "--base",
                    sha,
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(0, opened.returncode, opened.stderr)
            open_report = json.loads(opened.stdout)
            self.assertEqual("serial", open_report["execution_mode"])
            journal = open_report["lanes"][0]["work_unit"]["journal"]
            journal_path = Path(journal)
            self._advance_to_committing(journal_path)
            result_file = root / "result.json"
            result_file.write_text(
                json.dumps(self._completed_result(journal_path)),
                encoding="utf-8",
            )
            submitted = subprocess.run(
                [
                    sys.executable,
                    "tools/workflow.py",
                    "implementation-submit",
                    "--journal",
                    journal,
                    "--result-file",
                    str(result_file),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(0, submitted.returncode, submitted.stderr)
            self.assertEqual("complete", json.loads(submitted.stdout)["run"]["phase"])
            closed = subprocess.run(
                [
                    sys.executable,
                    "tools/workflow.py",
                    "implementation-close",
                    "--journal",
                    journal,
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(0, closed.returncode, closed.stderr)
            self.assertEqual("ready-for-integration", json.loads(closed.stdout)["status"])

    def test_submission_rejects_changed_ticket_or_spec_content(self):
        for changed in ("ticket", "spec"):
            with self.subTest(changed=changed), tempfile.TemporaryDirectory() as tmp:
                repo, ticket, sha = self._repo(Path(tmp))
                path, journal = start_run(repo, ticket, sha)
                source = ticket if changed == "ticket" else Path(
                    journal["context"]["spec"]["content"]["path"]
                )
                source.write_text(source.read_text(encoding="utf-8") + "\nchanged\n", encoding="utf-8")
                with self.assertRaisesRegex(RunJournalError, "内容已变化"):
                    submit_run_outcome(
                        path,
                        {
                            "outcome": "completed",
                            "test_receipt": "tests: pass",
                            "review_receipt": "review: clean",
                            "code_receipt": None,
                            "blocker": None,
                        },
                    )

    def test_completed_and_blocked_outcomes_require_their_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, ticket, sha = self._repo(Path(tmp))
            path, _ = start_run(repo, ticket, sha)
            self._advance_to_committing(path)
            with self.assertRaisesRegex(RunJournalError, "test_receipt"):
                submit_run_outcome(
                    path,
                    {
                        "outcome": "completed",
                        "test_receipt": None,
                        "review_receipt": "review: clean",
                        "code_receipt": build_code_receipt(path),
                        "blocker": None,
                    },
                )
            report = submit_run_outcome(
                path,
                {
                    "outcome": "blocked-by-design",
                    "test_receipt": None,
                    "review_receipt": None,
                    "code_receipt": None,
                    "blocker": "missing service credentials",
                },
            )
            self.assertEqual("pause", report["next_action"])

    def test_review_evidence_rejects_caller_created_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, ticket, sha = self._repo(Path(tmp))
            path, _ = start_run(repo, ticket, sha, ["app.py"])
            fake = path.parent / f"{path.stem}.evidence/review-snapshots/fake-review"
            fake.mkdir(parents=True)

            with self.assertRaisesRegex(RunJournalError, "无法验证"):
                record_review_evidence(path, fake, REVIEW_ARGV)

    def test_review_evidence_rejects_undeclared_self_asserted_pass_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, ticket, sha = self._repo(Path(tmp))
            path, _ = start_run(repo, ticket, sha, ["app.py"])
            record_run(path, "implementing")
            record_run(path, "reviewing")
            unit = open_review_evidence(path)

            with self.assertRaisesRegex(RunJournalError, "未在 work unit 中声明"):
                record_review_evidence(
                    path,
                    Path(str(unit["snapshot_dir"])),
                    ["python3", "-c", "print('pass')"],
                )

    def test_review_unit_and_receipt_bind_the_semantic_review_method(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, ticket, sha = self._repo(Path(tmp))
            path, _ = start_run(repo, ticket, sha, ["app.py"])
            record_run(path, "implementing")
            record_run(path, "reviewing")
            unit = open_review_evidence(path)
            self.assertEqual("my-code-review", unit["method"])
            marker = json.loads(
                (Path(str(unit["snapshot_dir"])) / ".review-unit.json").read_text()
            )
            self.assertEqual("my-code-review", marker["method"])
            report = record_review_evidence(
                path, Path(str(unit["snapshot_dir"])), REVIEW_ARGV
            )
            receipt = report["review_receipt"]
            self.assertIsNotNone(receipt)
            evidence = json.loads(
                (
                    path.parent
                    / f"{path.stem}.evidence"
                    / f"{receipt['evidence_id']}.json"
                ).read_text()
            )
            self.assertEqual("my-code-review", evidence["method"])

    def _approve_repair_plan(self, path: Path) -> None:
        opened = open_repair_plan(path)
        plan = Path(str(opened["path"]))
        plan.write_text(
            plan.read_text(encoding="utf-8")
            .replace("- Change: \n", "- Change: add a state fence\n")
            .replace("- Verification: \n", "- Verification: exercise abort during write\n")
            .replace("- Out of scope: \n", "- Out of scope: downstream delivery\n"),
            encoding="utf-8",
        )
        unit = open_repair_plan_review(path)
        submit_repair_plan_review(path, Path(str(unit["snapshot_dir"])), {
            "content_id": unit["content_id"],
            "checks": {"my-review-design": {"status": "pass", "reason": None}},
            "findings": [], "inconclusive": [],
        })

    def test_host_review_findings_are_persisted_then_require_an_approved_repair_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, ticket, sha = self._repo(Path(tmp))
            path, _ = start_run(repo, ticket, sha, ["app.py"])
            record_run(path, "implementing")
            record_run(path, "reviewing")
            unit = open_review_evidence(path)
            snapshot = Path(str(unit["snapshot_dir"]))
            result = self_review_result(unit, "findings", [{
                    "id": "state-fence-1",
                    "root_cause": "missing-state-fence",
                    "severity": "P1",
                    "summary": "abort can pass an in-flight write",
                    "baseline_reachable": True,
                }])
            report = submit_review_result(path, snapshot, result)
            self.assertEqual("findings", report["status"])
            self.assertEqual("create-repair-plan", report["next_action"])
            self.assertFalse(snapshot.exists())
            self.assertEqual("planning", json.loads(path.read_text())["phase"])
            self._approve_repair_plan(path)
            self.assertEqual("implementing", json.loads(path.read_text())["phase"])
            evidence = json.loads(
                (
                    path.parent
                    / f"{path.stem}.evidence"
                    / f"{report['evidence_receipt']['evidence_id']}.json"
                ).read_text()
            )
            self.assertEqual("findings", evidence["status"])

    def test_repeated_review_root_cause_escalates_design(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, ticket, sha = self._repo(Path(tmp))
            (repo / ".agent/matt-workflow.md").write_text(render_profile({
                "schema_version": 1, "commit_policy": "allow", "external_write_policy": "deny",
                "test_commands": ["python3 -c pass"], "review_commands": [REVIEW_COMMAND],
                "max_repair_rounds": 5, "decision_policy": "autonomous",
            }), encoding="utf-8")
            path, _ = start_run(repo, ticket, sha, ["app.py"])
            record_run(path, "implementing")
            for attempt in range(2):
                record_run(path, "reviewing")
                unit = open_review_evidence(path)
                report = submit_review_result(
                    path,
                    Path(str(unit["snapshot_dir"])),
                    self_review_result(unit, "findings", [{
                            "id": f"state-fence-{attempt}",
                            "root_cause": "missing-state-fence",
                            "severity": "P1",
                            "summary": "same invariant remains open",
                            "baseline_reachable": True,
                        }]),
                )
                if attempt == 0:
                    self._approve_repair_plan(path)
            self.assertEqual("blocked-by-design", report["next_action"])
            self.assertEqual(["missing-state-fence"], report["repeated_root_causes"])

    def test_default_stops_after_one_repair_round_and_releases_ticket(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, ticket, sha = self._repo(Path(tmp))
            path, _ = start_run(repo, ticket, sha, ["app.py"])
            record_run(path, "implementing")
            for attempt in range(2):
                record_run(path, "reviewing")
                unit = open_review_evidence(path)
                report = submit_review_result(path, Path(str(unit["snapshot_dir"])), self_review_result(unit, "findings", [{
                    "id": f"root-{attempt}", "root_cause": f"root-{attempt}",
                    "severity": "P1", "summary": "must repair", "baseline_reachable": True,
                }]))
                if attempt == 0:
                    self._approve_repair_plan(path)
            self.assertEqual("blocked-by-review", report["next_action"])
            self.assertEqual("blocked-by-review", json.loads(path.read_text())["submission"]["outcome"])
            self.assertEqual("ready-for-agent", ticket.read_text().split("status: ")[1].splitlines()[0])

    def test_full_auto_allows_at_most_five_repair_rounds(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, ticket, sha = self._repo(Path(tmp))
            (repo / ".agent/matt-workflow.md").write_text(render_profile({
                "schema_version": 1, "commit_policy": "allow", "external_write_policy": "deny",
                "test_commands": ["python3 -c pass"], "review_commands": [REVIEW_COMMAND],
                "max_repair_rounds": 5, "decision_policy": "autonomous",
            }), encoding="utf-8")
            path, _ = start_run(repo, ticket, sha, ["app.py"])
            record_run(path, "implementing")
            for attempt in range(6):
                record_run(path, "reviewing")
                unit = open_review_evidence(path)
                report = submit_review_result(path, Path(str(unit["snapshot_dir"])), self_review_result(unit, "findings", [{
                    "id": f"root-{attempt}", "root_cause": f"root-{attempt}",
                    "severity": "P1", "summary": "must repair", "baseline_reachable": True,
                }]))
                if attempt < 5:
                    self.assertEqual("create-repair-plan", report["next_action"])
                    self._approve_repair_plan(path)
            self.assertEqual("blocked-by-review", report["next_action"])

    def test_repair_plan_rejects_incomplete_plan_and_code_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, ticket, sha = self._repo(Path(tmp))
            path, _ = start_run(repo, ticket, sha, ["app.py"])
            record_run(path, "implementing")
            record_run(path, "reviewing")
            unit = open_review_evidence(path)
            submit_review_result(path, Path(str(unit["snapshot_dir"])), self_review_result(unit, "findings", [{
                "id": "root-1", "root_cause": "root-1", "severity": "P1",
                "summary": "must repair", "baseline_reachable": True,
            }]))
            opened = open_repair_plan(path)
            with self.assertRaisesRegex(RunJournalError, "缺少必填"):
                open_repair_plan_review(path)
            plan = Path(str(opened["path"]))
            plan.write_text(plan.read_text().replace("- Change: \n", "- Change: fix\n")
                .replace("- Verification: \n", "- Verification: test\n")
                .replace("- Out of scope: \n", "- Out of scope: none\n"), encoding="utf-8")
            (repo / "app.py").write_text("print('drift')\n", encoding="utf-8")
            with self.assertRaisesRegex(RunJournalError, "代码内容已变化"):
                open_repair_plan_review(path)

    def test_review_rejects_unreachable_blocker_and_releases_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, ticket, sha = self._repo(Path(tmp))
            path, _ = start_run(repo, ticket, sha, ["app.py"])
            record_run(path, "implementing")
            record_run(path, "reviewing")
            unit = open_review_evidence(path)
            snapshot = Path(str(unit["snapshot_dir"]))
            with self.assertRaisesRegex(RunJournalError, "固定基线"):
                submit_review_result(
                    path,
                    snapshot,
                    self_review_result(unit, "findings", [{
                            "id": "schema-8-to-9",
                            "root_cause": "unsupported-intermediate-schema",
                            "severity": "P1",
                            "summary": "assumes an unpublished schema version",
                            "baseline_reachable": False,
                        }]),
                )
            self.assertFalse(snapshot.exists())

    def test_self_review_requires_complete_coverage_and_acceptance_owner(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, ticket, sha = self._repo(Path(tmp))
            path, _ = start_run(repo, ticket, sha, ["app.py"])
            record_run(path, "implementing")
            record_run(path, "reviewing")
            unit = open_review_evidence(path)
            result = self_review_result(unit, "pass")
            result["self_review_coverage"]["acceptance"] = []

            with self.assertRaisesRegex(RunJournalError, "完整覆盖"):
                submit_review_result(path, Path(str(unit["snapshot_dir"])), result)

    def test_follow_on_is_nonblocking_and_must_target_direct_successor(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, ticket, sha = self._repo(Path(tmp))
            successor = ticket.with_name("tickets-feature-02.md")
            successor.write_text(
                ticket.read_text()
                .replace("feature-01", "feature-02")
                .replace("status: ready-for-agent", "status: revalidated")
                .replace("blocked_by: []", "blocked_by: [feature-01]")
                .replace("claimed_by:\n", "claimed_by:\n")
                .replace("sequence: 1", "sequence: 2"),
                encoding="utf-8",
            )
            path, _ = start_run(repo, ticket, sha, ["app.py"])
            record_run(path, "implementing")
            record_run(path, "reviewing")
            unit = open_review_evidence(path)
            result = self_review_result(unit, "pass")
            result["follow_ons"] = [{
                "id": "grid-receipt",
                "root_cause": "missing-grid-receipt",
                "owner_ticket_id": "feature-02",
                "acceptance_ids": ["feature-02#A1"],
                "summary": "future consumer needs durable receipt",
                "baseline_reachable": True,
            }]
            report = submit_review_result(path, Path(str(unit["snapshot_dir"])), result)
            self.assertEqual("pass", report["status"])
            self.assertEqual("reviewing", json.loads(path.read_text())["phase"])

    def test_design_gap_blocks_and_independent_session_must_differ(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, ticket, sha = self._repo(Path(tmp))
            path, _ = start_run(repo, ticket, sha, ["app.py"])
            record_run(path, "implementing")
            record_run(path, "reviewing")
            unit = open_review_evidence(path)
            result = self_review_result(unit, "blocked-by-design")
            result.update({
                "findings": [],
                "follow_ons": [],
                "design_gap": {
                    "root_cause": "missing-owner",
                    "summary": "no Ticket owns this external side effect",
                    "evidence_refs": ["spec:.agent/work/feature/specs/specs-feature-02.md"],
                },
            })
            report = submit_review_result(path, Path(str(unit["snapshot_dir"])), result)
            self.assertEqual("blocked-by-design", report["next_action"])
            self.assertEqual("blocked-by-design", json.loads(path.read_text())["phase"])


    def test_independent_session_must_differ_from_implementation_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, ticket, sha = self._repo(Path(tmp))
            path, _ = start_run(repo, ticket, sha, ["app.py"])
            record_run(path, "implementing")
            record_run(path, "reviewing")
            unit = open_review_evidence(path)
            result = self_review_result(unit, "pass")
            result["reviewer_provenance"] = {
                "kind": "independent_session",
                "session_id": unit["implementation_session_id"],
            }
            result["self_review_coverage"] = None
            with self.assertRaisesRegex(RunJournalError, "independent session"):
                submit_review_result(path, Path(str(unit["snapshot_dir"])), result)

            unit = open_review_evidence(path)
            self.assertIn("review_inputs", unit)
            self.assertIn("spec", [item["kind"] for item in unit["review_inputs"]])
            result = self_review_result(unit, "pass")
            result["reviewer_provenance"] = {
                "kind": "independent_session", "session_id": "fresh-review-session",
            }
            result["self_review_coverage"] = None
            report = submit_review_result(path, Path(str(unit["snapshot_dir"])), result)
            self.assertEqual("pass", report["status"])

    def test_glob_code_scope_matches_real_ticket_shape_and_freezes_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, ticket, sha = self._repo(Path(tmp))
            source = repo / "internal/domain/model.py"
            source.parent.mkdir(parents=True)
            source.write_text("value = 1\n")
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "add scoped source"], cwd=repo, check=True)
            sha = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True
            ).stdout.strip()
            ticket.write_text(
                ticket.read_text().replace("rule_scope: [app.py]", "rule_scope: [internal/domain/**]")
            )
            path, _ = start_run(repo, ticket, sha, ["internal/domain/**"])
            record_run(path, "implementing")
            record_run(path, "reviewing")
            unit = open_review_evidence(path)
            artifact = unit["artifacts"][0]
            self.assertEqual("internal/domain/model.py", artifact["repo_path"])
            self.assertIsNotNone(artifact["baseline_snapshot_path"])

    def test_review_evidence_rejects_tampered_owned_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, ticket, sha = self._repo(Path(tmp))
            path, _ = start_run(repo, ticket, sha, ["app.py"])
            unit = open_review_evidence(path)
            snapshot = Path(str(unit["snapshot_dir"]))
            marker = snapshot / ".review-unit.json"
            snapshot.chmod(0o700)
            marker.chmod(0o600)
            marker.write_text(marker.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            with self.assertRaisesRegex(RunJournalError, "无法验证"):
                record_review_evidence(path, snapshot, REVIEW_ARGV)

    def test_parallel_session_has_disjoint_lanes_and_aggregate_close(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, first, sha = self._repo(Path(tmp))
            second = first.with_name("tickets-feature-02.md")
            second.write_text(
                first.read_text(encoding="utf-8")
                .replace("feature-01", "feature-02")
                .replace("sequence: 1", "sequence: 2")
                .replace("rule_scope: [app.py]", "rule_scope: [lib.py]"),
                encoding="utf-8",
            )
            (repo / "lib.py").write_text("value = 1\n", encoding="utf-8")
            report = open_implementation_session(
                repo, [first, second], sha, parallel=True
            )
            self.assertEqual("parallel", report["execution_mode"])
            self.assertEqual(2, len(report["lanes"]))
            journals = []
            for lane in report["lanes"]:
                journal = Path(lane["work_unit"]["journal"])
                journals.append(journal)
                self._advance_to_committing(journal)
                submit_run_outcome(journal, self._completed_result(journal))
            closed = close_implementation_session(journals)
            self.assertEqual("ready-for-integration", closed["status"])
            self.assertEqual(report["session_id"], closed["session_id"])

    def test_parallel_session_rejects_overlapping_or_implicit_multiple_tickets(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, first, sha = self._repo(Path(tmp))
            second = first.with_name("tickets-feature-02.md")
            second.write_text(
                first.read_text(encoding="utf-8")
                .replace("feature-01", "feature-02")
                .replace("sequence: 1", "sequence: 2")
                .replace("rule_scope: [app.py]", "rule_scope: [app.py/generated]"),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RunJournalError, "串行"):
                open_implementation_session(repo, [first, second], sha)
            with self.assertRaisesRegex(RunJournalError, "写入范围重叠"):
                open_implementation_session(repo, [first, second], sha, parallel=True)
            second.write_text(
                second.read_text(encoding="utf-8")
                .replace("rule_scope: [app.py/generated]", "rule_scope: [lib.py]")
                .replace("blocked_by: []", "blocked_by: [feature-01]"),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(RunJournalError, "尚未解除阻塞"):
                open_implementation_session(repo, [first, second], sha, parallel=True)


if __name__ == "__main__":
    unittest.main()
