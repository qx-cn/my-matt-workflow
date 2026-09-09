from __future__ import annotations

import json
import hashlib
import shlex
import subprocess
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from tools.workflow_lib.profile import render_profile
from tools.workflow_lib.lifecycle import recover_lifecycle_transactions
from tools.workflow_lib.fs_safety import register_owned_directory
from tools.workflow_lib.run_journal import (
    RunJournalError,
    build_code_receipt,
    build_run_context,
    record_run,
    record_review_evidence,
    run_test_evidence,
    open_review_evidence,
    start_run,
    submit_run_outcome,
    verify_run_sources,
)
from tools.workflow_lib.tickets import TicketError, frontmatter, validate_ready_ticket
from tools.workflow_lib.transitions import create_approved_scope, ticket_transition


REVIEW_COMMAND = (
    "python3 -c \"import json,os; print(json.dumps({"
    "'review_id': os.environ['MY_MATT_REVIEW_ID'], "
    "'status': 'pass', "
    "'code_content_id': os.environ['MY_MATT_CODE_CONTENT_ID'], "
    "'findings': []}))\""
)
REVIEW_ARGV = shlex.split(REVIEW_COMMAND)


class LifecycleHardeningTests(unittest.TestCase):
    def _repo(self, root: Path) -> tuple[Path, Path, str]:
        repo = root / "repo"
        ticket = repo / ".agent/work/topic/tickets/tickets-topic-01.md"
        ticket.parent.mkdir(parents=True)
        (repo / ".agent/matt-workflow.md").write_text(
            render_profile(
                {
                    "schema_version": 1,
                    "standards_sources": ["standards.md"],
                    "domain_sources": ["docs/domain.md"],
                    "test_commands": ["python3 -c pass"],
                    "review_commands": [REVIEW_COMMAND],
                }
            ),
            encoding="utf-8",
        )
        (repo / "docs").mkdir()
        (repo / "standards.md").write_text("standard v1\n", encoding="utf-8")
        (repo / "docs/domain.md").write_text("domain v1\n", encoding="utf-8")
        (repo / "app.py").write_text("value = 1\n", encoding="utf-8")
        spec = repo / ".agent/work/topic/specs/specs-topic-01.md"
        spec.parent.mkdir(parents=True)
        spec.write_text(
            "---\nspec_id: topic\nrevision: 1\n---\n\n# Spec\n",
            encoding="utf-8",
        )
        ticket.write_text(
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
            "rule_sources: [standards.md]\n"
            "rule_scope: [app.py]\n"
            "rule_constraints: [test]\n"
            "rule_conflicts: []\n"
            "execution_agent: codex\n"
            "sequence: 1\n"
            "---\n\n"
            "## Goal\n\nImplement the requested behavior.\n\n"
            "## Acceptance\n\n- [ ] works\n",
            encoding="utf-8",
        )
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
        subprocess.run(["git", "add", "."], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-qm", "base"], cwd=repo, check=True)
        sha = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo, text=True, capture_output=True, check=True
        ).stdout.strip()
        return repo, ticket, sha

    @staticmethod
    def _complete_result(journal: Path) -> dict[str, object]:
        code = build_code_receipt(journal)
        test = run_test_evidence(journal, ["python3", "-c", "pass"])
        review_unit = open_review_evidence(journal)
        review = record_review_evidence(
            journal,
            Path(str(review_unit["snapshot_dir"])),
            REVIEW_ARGV,
        )
        return {
            "outcome": "completed",
            "test_receipt": test,
            "review_receipt": review,
            "code_receipt": code,
            "blocker": None,
        }

    def test_ready_admission_rejects_wrong_kind_claim_and_zero_acceptance(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, ticket, _ = self._repo(Path(tmp))
            original = ticket.read_text(encoding="utf-8")
            for old, new, error in (
                ("ticket_kind: implementation", "ticket_kind: wayfinder", "implementation"),
                ("claimed_by:", "claimed_by: another-run", "已被认领"),
                ("- [ ] works", "- [x] works", "未完成验收"),
            ):
                ticket.write_text(original.replace(old, new), encoding="utf-8")
                with self.assertRaisesRegex(TicketError, error):
                    validate_ready_ticket(ticket)

    def test_ticket_spec_lineage_must_match_frontmatter_and_topic(self):
        for case in ("id", "revision", "topic"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as tmp:
                repo, ticket, _ = self._repo(Path(tmp))
                spec = repo / ".agent/work/topic/specs/specs-topic-01.md"
                if case == "id":
                    spec.write_text(
                        spec.read_text().replace(
                            "spec_id: topic", "spec_id: another"
                        )
                    )
                elif case == "revision":
                    spec.write_text(
                        spec.read_text().replace("revision: 1", "revision: 2")
                    )
                else:
                    other = repo / ".agent/work/other/specs/specs-topic-01.md"
                    other.parent.mkdir(parents=True)
                    other.write_text(spec.read_text())
                    ticket.write_text(
                        ticket.read_text().replace(
                            ".agent/work/topic/specs/specs-topic-01.md",
                            ".agent/work/other/specs/specs-topic-01.md",
                        )
                    )
                with self.assertRaisesRegex(
                    TicketError, "Spec.*不一致|同 topic"
                ):
                    validate_ready_ticket(ticket)

    def test_dependency_cycle_is_invalid_and_unavailable_scope_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, first, _ = self._repo(Path(tmp))
            second = first.with_name("tickets-topic-02.md")
            first.write_text(first.read_text().replace("blocked_by: []", "blocked_by: [topic-02]"))
            second.write_text(
                first.read_text()
                .replace("id: topic-01", "id: topic-02")
                .replace("blocked_by: [topic-02]", "blocked_by: [topic-01]")
                .replace("sequence: 1", "sequence: 2")
            )
            transition = ticket_transition(first.parent, work_scope_policy="ready-frontier")
            self.assertEqual("invalid", transition.status)
            self.assertIn("依赖环", transition.reason)

            first.unlink()
            second.write_text(second.read_text().replace("blocked_by: [topic-01]", "blocked_by: []"))
            second.write_text(second.read_text().replace("claimed_by:", "claimed_by: active"))
            transition = ticket_transition(second.parent, work_scope_policy="ready-frontier")
            self.assertEqual("blocked", transition.status)

    def test_approved_plan_requires_intact_scope_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, ticket, _ = self._repo(Path(tmp))
            missing = ticket_transition(
                ticket.parent, work_scope_policy="approved-plan", allowed_ids={"topic-01"}
            )
            self.assertEqual(("invalid", "approved-scope-missing"), (missing.status, missing.reason))
            scope = create_approved_scope(ticket.parent, {"topic-01"})
            allowed = ticket_transition(
                ticket.parent, work_scope_policy="approved-plan", approved_scope=scope
            )
            self.assertEqual("continue", allowed.status)
            ticket.write_text(ticket.read_text().replace("title: Topic", "title: Changed"))
            stale = ticket_transition(
                ticket.parent, work_scope_policy="approved-plan", approved_scope=scope
            )
            self.assertEqual("invalid", stale.status)

    def test_stable_definition_ignores_only_mutable_ticket_projection(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, ticket, sha = self._repo(Path(tmp))
            journal_path, journal = start_run(repo, ticket, sha)
            text = ticket.read_text()
            ticket.write_text(
                text.replace("status: ready-for-agent", "status: implementing")
                .replace("claimed_by:", "claimed_by: run-1")
                .replace("- [ ] works", "- [x] works")
            )
            verify_run_sources(journal)
            ticket.write_text(ticket.read_text() + "\nnew requirement\n")
            with self.assertRaisesRegex(RunJournalError, "definition 内容已变化"):
                verify_run_sources(journal)

    def test_profile_rule_standard_and_domain_drift_invalidate_run(self):
        for relative in (
            ".agent/matt-workflow.md", "standards.md", "docs/domain.md"
        ):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as tmp:
                repo, ticket, sha = self._repo(Path(tmp))
                _, journal = start_run(repo, ticket, sha)
                source = repo / relative
                source.write_text(source.read_text() + "changed\n")
                with self.assertRaisesRegex(RunJournalError, "内容已变化"):
                    verify_run_sources(journal)

    def test_completion_requires_phase_and_code_bound_structured_receipts(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, ticket, sha = self._repo(Path(tmp))
            journal, _ = start_run(repo, ticket, sha)
            legacy = {
                "outcome": "completed",
                "test_receipt": "tests pass",
                "review_receipt": "review clean",
                "code_receipt": None,
                "blocker": None,
            }
            with self.assertRaisesRegex(RunJournalError, "committing phase"):
                submit_run_outcome(journal, legacy)
            record_run(journal, "implementing")
            record_run(journal, "reviewing")
            record_run(journal, "committing")
            with self.assertRaisesRegex(RunJournalError, "结构化 code_receipt"):
                submit_run_outcome(journal, legacy)
            result = self._complete_result(journal)
            (repo / "app.py").write_text("value = 2\n")
            with self.assertRaisesRegex(RunJournalError, "当前声明范围不匹配"):
                submit_run_outcome(journal, result)

            result = self._complete_result(journal)
            accepted = submit_run_outcome(journal, result)
            self.assertEqual("complete", accepted["run"]["phase"])

    def test_completion_rejects_tampered_runtime_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, ticket, sha = self._repo(Path(tmp))
            journal, _ = start_run(repo, ticket, sha)
            record_run(journal, "implementing")
            record_run(journal, "reviewing")
            record_run(journal, "committing")
            result = self._complete_result(journal)
            evidence_id = result["test_receipt"]["evidence_id"]
            evidence = (
                journal.parent
                / f"{journal.stem}.evidence"
                / f"{evidence_id}.json"
            )
            evidence.write_text(evidence.read_text() + " ")

            with self.assertRaisesRegex(
                RunJournalError, "evidence record 已漂移"
            ):
                submit_run_outcome(journal, result)

    def test_context_exposes_all_stable_source_receipts(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, ticket, sha = self._repo(Path(tmp))
            context = build_run_context(repo, ticket, sha)
            kinds = {receipt["kind"] for receipt in context["source_receipts"]}
            self.assertTrue({"profile", "standard", "domain"}.issubset(kinds))
            for receipt in context["source_receipts"]:
                self.assertEqual({"kind", "path", "repo_path", "sha256", "size"}, set(receipt))

    def test_claim_is_cas_projected_and_concurrent_start_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, ticket, sha = self._repo(Path(tmp))
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _: start_run(repo, ticket, sha), range(2)))
            attempts = {result[1]["attempt_id"] for result in results}
            paths = {result[0] for result in results}
            self.assertEqual(1, len(attempts))
            self.assertEqual(1, len(paths))
            metadata = frontmatter(ticket)
            self.assertEqual("implementing", metadata["status"])
            self.assertEqual(next(iter(attempts)), metadata["claimed_by"])

    def test_blocked_evidence_releases_claim_and_allows_new_attempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, ticket, sha = self._repo(Path(tmp))
            first_path, first = start_run(repo, ticket, sha)
            result = submit_run_outcome(
                first_path,
                {
                    "outcome": "blocked-by-evidence",
                    "test_receipt": None,
                    "review_receipt": None,
                    "code_receipt": None,
                    "blocker": "credentials unavailable",
                },
            )
            self.assertEqual("pause", result["next_action"])
            self.assertEqual("ready-for-agent", frontmatter(ticket)["status"])
            self.assertEqual("", frontmatter(ticket)["claimed_by"])

            second_path, second = start_run(repo, ticket, sha)
            self.assertNotEqual(first_path, second_path)
            self.assertNotEqual(first["attempt_id"], second["attempt_id"])
            self.assertIn("-attempt-", second_path.name)

    def test_interrupted_completion_rolls_forward_from_wal(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, ticket, sha = self._repo(Path(tmp))
            journal_path, _ = start_run(repo, ticket, sha)
            record_run(journal_path, "implementing")
            record_run(journal_path, "reviewing")
            record_run(journal_path, "committing")
            result = self._complete_result(journal_path)
            with self.assertRaisesRegex(RunJournalError, "fault-injection"):
                submit_run_outcome(journal_path, result, fail_after_writes=1)

            self.assertEqual("complete", frontmatter(ticket)["status"])
            self.assertEqual("committing", json.loads(journal_path.read_text())["phase"])
            recovered = recover_lifecycle_transactions(repo, topic="topic")
            self.assertEqual(1, len(recovered))
            journal = json.loads(journal_path.read_text())
            self.assertEqual("complete", journal["phase"])
            self.assertEqual("", frontmatter(ticket)["claimed_by"])
            self.assertNotIn("- [ ]", ticket.read_text())
            verify_run_sources(journal)

    def test_interrupted_claim_recovers_same_attempt_instead_of_double_claiming(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, ticket, sha = self._repo(Path(tmp))
            with self.assertRaisesRegex(RunJournalError, "fault-injection"):
                start_run(
                    repo, ticket, sha, fail_after_claim_writes=1
                )
            claimed_attempt = frontmatter(ticket)["claimed_by"]
            self.assertTrue(claimed_attempt)
            self.assertFalse(list(ticket.parent.parent.joinpath("runs").glob("run-*.json")))

            journal_path, journal = start_run(repo, ticket, sha)
            self.assertEqual(claimed_attempt, journal["attempt_id"])
            self.assertTrue(journal_path.is_file())
            self.assertEqual("implementing", frontmatter(ticket)["status"])

    def test_recovery_fails_closed_when_target_drifted(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, ticket, sha = self._repo(Path(tmp))
            journal_path, _ = start_run(repo, ticket, sha)
            record_run(journal_path, "implementing")
            record_run(journal_path, "reviewing")
            record_run(journal_path, "committing")
            result = self._complete_result(journal_path)
            with self.assertRaises(RunJournalError):
                submit_run_outcome(journal_path, result, fail_after_writes=1)
            journal_path.write_text(journal_path.read_text() + "drift\n")
            with self.assertRaisesRegex(Exception, "目标漂移"):
                recover_lifecycle_transactions(repo, topic="topic")
            self.assertTrue(
                list((journal_path.parent / "lifecycle-transactions").glob("*/wal.json"))
            )

    def test_forged_unowned_wal_cannot_modify_repo_victim(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, _, _ = self._repo(Path(tmp))
            victim = repo / "victim.txt"
            victim.write_text("keep\n")
            transaction = (
                repo / ".agent/work/topic/runs/lifecycle-transactions"
                / "topic-01-forged-submit"
            )
            transaction.mkdir(parents=True)
            after = "overwrite\n"
            wal = {
                "schema_version": 1,
                "kind": "ticket-lifecycle-wal",
                "status": "prepared",
                "topic": "topic",
                "ticket_id": "topic-01",
                "attempt_id": "forged",
                "operation": "submit",
                "entries": [{
                    "path": "victim.txt",
                    "before_sha256": hashlib.sha256(b"keep\n").hexdigest(),
                    "after_sha256": hashlib.sha256(after.encode()).hexdigest(),
                    "after_text": after,
                }],
            }
            (transaction / "wal.json").write_text(json.dumps(wal))
            with self.assertRaisesRegex(Exception, "ownership capability"):
                recover_lifecycle_transactions(repo, topic="topic")
            self.assertEqual("keep\n", victim.read_text())

    def test_owned_wal_with_false_after_digest_fails_before_target_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, _, _ = self._repo(Path(tmp))
            victim = repo / "victim.txt"
            victim.write_text("keep\n")
            root = repo / ".agent/work/topic/runs/lifecycle-transactions"
            transaction = root / "topic-01-attempt-1-submit"
            transaction.mkdir(parents=True)
            wal = {
                "schema_version": 1,
                "kind": "ticket-lifecycle-wal",
                "status": "prepared",
                "topic": "topic",
                "ticket_id": "topic-01",
                "attempt_id": "attempt-1",
                "operation": "submit",
                "entries": [{
                    "path": "victim.txt",
                    "before_sha256": hashlib.sha256(b"keep\n").hexdigest(),
                    "after_sha256": "0" * 64,
                    "after_text": "overwrite\n",
                }],
            }
            (transaction / "wal.json").write_text(json.dumps(wal))
            register_owned_directory(root, transaction, purpose="ticket-lifecycle-transaction")
            with self.assertRaisesRegex(Exception, "entry digest 无效"):
                recover_lifecycle_transactions(repo, topic="topic")
            self.assertEqual("keep\n", victim.read_text())


if __name__ == "__main__":
    unittest.main()
