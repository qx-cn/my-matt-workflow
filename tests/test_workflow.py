import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from tools.workflow_lib.installer import (
    InstallError,
    install_release,
    recover_interrupted_install,
    verify_release,
)
from tools.workflow_lib.release import ReleaseError, build_release, validate_skills
from tools.workflow_lib.fs_safety import register_owned_directory
from tools.workflow_lib.rules import inspect_rules, resolve_rules
from tools.workflow_lib.tickets import (
    TicketError,
    frontmatter,
    validate_ready_ticket,
)
from tools.workflow_lib.artifact_review import (
    ArtifactReviewError,
    REQUIRED_REVIEW_CHECKS,
    build_artifact_review_snapshot,
    finalize_artifact_review_snapshot,
    submit_artifact_review_result,
    verify_artifact_review_snapshot,
)




class ArtifactReviewWorkflowTests(unittest.TestCase):
    def test_artifact_review_content_id_is_stable_for_set_order_and_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "first.md"
            second = root / "second.md"
            first.write_text("first", encoding="utf-8")
            second.write_text("second", encoding="utf-8")

            forward = build_artifact_review_snapshot(
                [first, second], snapshot_root=root / "snapshots"
            )
            reverse = build_artifact_review_snapshot(
                [second, first, first], snapshot_root=root / "snapshots"
            )

            self.assertEqual(forward["content_id"], reverse["content_id"])
            self.assertEqual(2, len(reverse["artifacts"]))
            finalize_artifact_review_snapshot(
                [first, second], forward["content_id"], Path(forward["snapshot_dir"])
            )
            finalize_artifact_review_snapshot(
                [second, first, first],
                reverse["content_id"],
                Path(reverse["snapshot_dir"]),
            )

    def test_reviewers_consume_one_immutable_snapshot_and_detect_stale_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / "artifact.md"
            artifact.write_text("current state", encoding="utf-8")
            result = build_artifact_review_snapshot(
                [artifact], snapshot_root=root / "snapshots"
            )
            self.assertEqual("ready", result["status"])
            self.assertEqual(result["content_id"], result["review_unit"]["content_id"])
            self.assertEqual("serial", result["review_unit"]["execution_mode"])
            snapshot = Path(result["artifacts"][0]["snapshot_path"])
            snapshot_dir = Path(result["snapshot_dir"])
            self.assertEqual("current state", snapshot.read_text(encoding="utf-8"))
            self.assertEqual(0, snapshot.stat().st_mode & 0o222)
            self.assertEqual(0, snapshot_dir.stat().st_mode & 0o077)

            artifact.write_text("changed state", encoding="utf-8")
            verification = verify_artifact_review_snapshot(
                [artifact], result["content_id"]
            )
            self.assertEqual("stale", verification["status"])
            self.assertEqual("current state", snapshot.read_text(encoding="utf-8"))
            finalized = finalize_artifact_review_snapshot(
                [artifact], result["content_id"], snapshot_dir
            )
            self.assertEqual("stale", finalized["status"])
            self.assertTrue(finalized["released"])
            self.assertFalse(snapshot_dir.exists())

    def test_artifact_kinds_select_their_declared_review_methods(self):
        with tempfile.TemporaryDirectory() as tmp:
            artifact = Path(tmp) / 'design.md'
            artifact.write_text('# Design')
            for kind, checks in [('general', list(REQUIRED_REVIEW_CHECKS)),
                                 ('design', [*REQUIRED_REVIEW_CHECKS, 'review-design'])]:
                unit = build_artifact_review_snapshot([artifact], artifact_kind=kind)
                self.assertEqual(checks, unit['review_unit']['required_checks'])
                self.assertEqual('serial', unit['review_unit']['execution_mode'])
                finalize_artifact_review_snapshot([artifact], unit['content_id'], Path(unit['snapshot_dir']))
            with self.assertRaises(ArtifactReviewError):
                build_artifact_review_snapshot([artifact], artifact_kind='repair-plan')

    def test_artifact_review_submit_requires_complete_check_closure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / "artifact.md"
            artifact.write_text("current state", encoding="utf-8")
            opened = build_artifact_review_snapshot(
                [artifact], snapshot_root=root / "snapshots"
            )
            snapshot_dir = Path(opened["snapshot_dir"])
            incomplete = {
                "content_id": opened["content_id"],
                "checks": {},
                "findings": [],
                "inconclusive": [],
            }
            with self.assertRaisesRegex(ArtifactReviewError, "完整覆盖"):
                submit_artifact_review_result([artifact], snapshot_dir, incomplete)
            self.assertTrue(snapshot_dir.exists())

            checks = {
                check: {"status": "pass", "reason": None}
                for check in REQUIRED_REVIEW_CHECKS
            }
            checks["visual-communication"] = {
                "status": "not-applicable",
                "reason": "产物没有复杂关系、流程或状态",
            }
            accepted = submit_artifact_review_result(
                [artifact],
                snapshot_dir,
                {
                    "content_id": opened["content_id"],
                    "checks": checks,
                    "findings": [],
                    "inconclusive": [],
                },
            )
            self.assertEqual("accepted", accepted["status"])
            self.assertFalse(snapshot_dir.exists())

    def test_artifact_review_submit_rejects_unexplained_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / "artifact.md"
            artifact.write_text("current state", encoding="utf-8")
            opened = build_artifact_review_snapshot(
                [artifact], snapshot_root=root / "snapshots"
            )
            checks = {
                check: {"status": "pass", "reason": None}
                for check in REQUIRED_REVIEW_CHECKS
            }
            checks["humanizer"] = {"status": "inconclusive", "reason": None}
            with self.assertRaisesRegex(ArtifactReviewError, "完整解释"):
                submit_artifact_review_result(
                    [artifact],
                    Path(opened["snapshot_dir"]),
                    {
                        "content_id": opened["content_id"],
                        "checks": checks,
                        "findings": [],
                        "inconclusive": [],
                    },
                )

    def test_parallelism_is_not_a_separate_user_skill(self):
        root = Path(__file__).resolve().parents[1]
        skill_names = {
            path.name for path in (root / "skills").iterdir() if path.is_dir()
        }
        self.assertIn("my-review-artifact", skill_names)
        self.assertNotIn("my-review-in-parallel", skill_names)
        self.assertNotIn("my-implement-in-parallel", skill_names)
        manifest = json.loads((root / "composition/manifest.json").read_text())
        entries = manifest["routable_entries"]["my-ask-matt"]
        self.assertIn("my-review-artifact", entries)
        self.assertNotIn("my-review-in-parallel", entries)
        self.assertNotIn("my-implement-in-parallel", entries)














class InstallerTests(unittest.TestCase):
    def _release(self, root: Path, release_id: str, body: str) -> Path:
        release = root / release_id
        skill = release / "skills" / "my-demo"
        skill.mkdir(parents=True)
        skill_file = skill / "SKILL.md"
        skill_file.write_text(body)
        digest = hashlib.sha256(skill_file.read_bytes()).hexdigest()
        runtime_entry = release / "runtime" / "tools" / "workflow.py"
        runtime_entry.parent.mkdir(parents=True)
        runtime_entry.write_text("#!/usr/bin/env python3\n")
        runtime_digest = hashlib.sha256(runtime_entry.read_bytes()).hexdigest()
        (release / "manifest.json").write_text(
            json.dumps(
                {
                    "release_id": release_id,
                    "skills": {
                        "my-demo": {
                            "SKILL.md": digest,
                        }
                    },
                    "runtime": {"tools/workflow.py": runtime_digest},
                }
            )
        )
        return release

    def test_corrupt_release_does_not_replace_existing_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cursor_home = root / ".cursor"
            existing = cursor_home / "skills" / "my-demo"
            existing.mkdir(parents=True)
            (existing / "SKILL.md").write_text("stable")
            release = self._release(root, "v2", "new")
            (release / "skills" / "my-demo" / "SKILL.md").write_text("corrupt")

            with self.assertRaises(InstallError):
                install_release(release, cursor_home)

            self.assertEqual("stable", (existing / "SKILL.md").read_text())

    def test_verify_release_rejects_unmanifested_extra_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            release = self._release(root, "v1", "stable")
            extra = release / "skills/my-demo/EXTRA.md"
            extra.write_text("not in manifest")

            with self.assertRaisesRegex(
                InstallError, r"额外|EXTRA\.md"
            ):
                verify_release(release)

    def test_verify_release_rejects_unsafe_runtime_release_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            release = self._release(root, "v1", "stable")
            manifest = json.loads((release / "manifest.json").read_text())
            manifest["release_id"] = "../escape"
            (release / "manifest.json").write_text(json.dumps(manifest))

            with self.assertRaisesRegex(InstallError, "release_id"):
                verify_release(release)

    def test_codex_install_rejects_implicit_skill(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            release = self._release(
                root,
                "v1",
                "---\n"
                "name: my-demo\n"
                "description: demo\n"
                "disable-model-invocation: true\n"
                "---\n",
            )
            with self.assertRaisesRegex(
                InstallError, r"openai\.yaml|implicit"
            ):
                install_release(
                    release, root / ".codex", target="codex"
                )

    def test_claude_install_does_not_require_openai_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            release = self._release(
                root,
                "v1",
                "---\n"
                "name: my-demo\n"
                "description: demo\n"
                "disable-model-invocation: true\n"
                "---\n",
            )

            install_release(
                release, root / ".claude", target="claude"
            )

            self.assertTrue(
                (root / ".claude/skills/my-demo/SKILL.md").is_file()
            )
            state = json.loads(
                (root / ".claude/my-matt-workflow/install-state.json").read_text()
            )
            self.assertEqual("claude", state["installed_agent"])
            self.assertTrue(Path(state["runtime_entry"]).is_file())

    def test_codex_migrates_previously_split_skill_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            release = self._release(
                root,
                "v1",
                "---\n"
                "name: my-demo\n"
                "description: demo\n"
                "disable-model-invocation: true\n"
                "---\n",
            )
            metadata = release / "skills/my-demo/agents/openai.yaml"
            metadata.parent.mkdir()
            metadata.write_text("policy:\n  allow_implicit_invocation: false\n")
            manifest = json.loads((release / "manifest.json").read_text())
            manifest["skills"]["my-demo"]["agents/openai.yaml"] = hashlib.sha256(
                metadata.read_bytes()
            ).hexdigest()
            (release / "manifest.json").write_text(json.dumps(manifest))
            state_home = root / ".codex"
            skills_home = root / ".agents" / "skills"

            install_release(
                release,
                state_home,
                target="codex",
                skills_home=skills_home,
            )

            self.assertTrue((skills_home / "my-demo/SKILL.md").is_file())
            state = json.loads(
                (state_home / "my-matt-workflow/install-state.json").read_text()
            )
            self.assertEqual(str(skills_home.resolve()), state["skills_home"])
            self.assertTrue(Path(state["runtime_entry"]).is_file())
            installed = (skills_home / "my-demo/SKILL.md").read_text()
            self.assertNotIn("disable-model-invocation", installed)
            self.assertTrue((skills_home / "my-demo/agents/openai.yaml").is_file())
            self.assertEqual("codex", state["metadata_projection"])

            codex_skills_home = state_home / "skills"
            install_release(
                release,
                state_home,
                target="codex",
                skills_home=codex_skills_home,
            )

            self.assertFalse((skills_home / "my-demo").exists())
            self.assertTrue((codex_skills_home / "my-demo/SKILL.md").is_file())
            migrated_state = json.loads(
                (state_home / "my-matt-workflow/install-state.json").read_text()
            )
            self.assertEqual(
                str(codex_skills_home.resolve()), migrated_state["skills_home"]
            )

    def test_cursor_install_keeps_cursor_metadata_and_removes_openai_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            release = self._release(
                root,
                "v1",
                "---\n"
                "name: my-demo\n"
                "description: demo\n"
                "disable-model-invocation: true\n"
                "---\n",
            )
            metadata = release / "skills/my-demo/agents/openai.yaml"
            metadata.parent.mkdir()
            metadata.write_text("policy:\n  allow_implicit_invocation: false\n")
            manifest = json.loads((release / "manifest.json").read_text())
            manifest["skills"]["my-demo"]["agents/openai.yaml"] = hashlib.sha256(
                metadata.read_bytes()
            ).hexdigest()
            (release / "manifest.json").write_text(json.dumps(manifest))

            install_release(release, root / ".cursor", target="cursor")

            installed = root / ".cursor/skills/my-demo"
            self.assertIn(
                "disable-model-invocation: true",
                (installed / "SKILL.md").read_text(),
            )
            self.assertFalse((installed / "agents/openai.yaml").exists())

    def test_can_install_an_older_release_for_rollback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cursor_home = root / ".cursor"
            v1 = self._release(root, "v1", "old")
            v2 = self._release(root, "v2", "new")

            install_release(v2, cursor_home)
            install_release(v1, cursor_home)

            self.assertEqual(
                "old",
                (cursor_home / "skills" / "my-demo" / "SKILL.md").read_text(),
            )
            state = json.loads(
                (cursor_home / "my-matt-workflow" / "install-state.json").read_text()
            )
            self.assertEqual("v1", state["release_id"])

    def test_refuses_to_replace_unmanaged_same_name_skill(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cursor_home = root / ".cursor"
            existing = cursor_home / "skills" / "my-demo"
            existing.mkdir(parents=True)
            (existing / "SKILL.md").write_text("personal")
            release = self._release(root, "v1", "managed")

            with self.assertRaisesRegex(InstallError, "非托管"):
                install_release(release, cursor_home)

            self.assertEqual("personal", (existing / "SKILL.md").read_text())

    def test_recovers_persisted_interrupted_transaction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cursor_home = root / ".cursor"
            target = cursor_home / "skills" / "my-demo"
            target.mkdir(parents=True)
            (target / "SKILL.md").write_text("new")
            transaction = cursor_home / "my-matt-workflow" / "transaction"
            backup = transaction / "backup" / "my-demo"
            backup.mkdir(parents=True)
            (backup / "SKILL.md").write_text("old")
            (transaction / "journal.json").write_text(
                json.dumps(
                    {
                        "skills": ["my-demo"],
                        "old_present": ["my-demo"],
                    }
                )
            )

            with self.assertRaisesRegex(InstallError, "可验证 install-state"):
                recover_interrupted_install(
                    cursor_home, skills_home=cursor_home / "skills"
                )

            self.assertEqual("new", (target / "SKILL.md").read_text())
            self.assertTrue(transaction.exists())

    def test_committed_transaction_cleanup_keeps_new_install(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cursor_home = root / ".cursor"
            target = cursor_home / "skills" / "my-demo"
            target.mkdir(parents=True)
            (target / "SKILL.md").write_text("new")
            state_dir = cursor_home / "my-matt-workflow"
            transaction = state_dir / "transaction"
            backup = transaction / "backup" / "my-demo"
            backup.mkdir(parents=True)
            (backup / "SKILL.md").write_text("old")
            (transaction / "journal.json").write_text(
                json.dumps(
                    {
                        "skills": ["my-demo"],
                        "old_present": ["my-demo"],
                        "new_release_id": "v2",
                        "transaction_id": "tx-2",
                    }
                )
            )
            (state_dir / "install-state.json").write_text(
                json.dumps(
                    {
                        "release_id": "v2",
                        "skills": ["my-demo"],
                        "transaction_id": "tx-2",
                        "skills_home": str((cursor_home / "skills").resolve()),
                    }
                )
            )

            with self.assertRaisesRegex(InstallError, "schema"):
                recover_interrupted_install(cursor_home)

            self.assertEqual("new", (target / "SKILL.md").read_text())
            self.assertTrue(transaction.exists())

    def test_same_release_stale_state_does_not_fake_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cursor_home = root / ".cursor"
            target = cursor_home / "skills" / "my-demo"
            target.mkdir(parents=True)
            (target / "SKILL.md").write_text("partial-new")
            state_dir = cursor_home / "my-matt-workflow"
            transaction = state_dir / "transaction"
            backup = transaction / "backup" / "my-demo"
            backup.mkdir(parents=True)
            (backup / "SKILL.md").write_text("stable-old")
            (transaction / "journal.json").write_text(
                json.dumps(
                    {
                        "skills": ["my-demo"],
                        "old_present": ["my-demo"],
                        "new_release_id": "v2",
                        "transaction_id": "tx-2",
                    }
                )
            )
            (state_dir / "install-state.json").write_text(
                json.dumps(
                    {
                        "release_id": "v2",
                        "skills": ["my-demo"],
                        "transaction_id": "tx-1",
                        "skills_home": str((cursor_home / "skills").resolve()),
                    }
                )
            )

            with self.assertRaisesRegex(InstallError, "schema"):
                recover_interrupted_install(cursor_home)

            self.assertEqual("partial-new", (target / "SKILL.md").read_text())

    def test_v2_recovery_uses_recorded_split_skills_home_and_rejects_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_home = root / ".codex"
            skills_home = root / ".agents" / "skills"
            target = skills_home / "my-demo"
            target.mkdir(parents=True)
            (target / "SKILL.md").write_text("partial-new")
            transaction = state_home / "my-matt-workflow" / "transaction"
            backup = transaction / "backup" / "my-demo"
            backup.mkdir(parents=True)
            (backup / "SKILL.md").write_text("original")
            (transaction / "journal.json").write_text(json.dumps({
                "version": 2,
                "skills_home": str(skills_home.resolve()),
                "skills": ["my-demo"],
                "old_present": ["my-demo"],
                "new_release_id": "v2",
                "transaction_id": "tx-2",
            }))
            wrong_home = root / ".wrong" / "skills"
            wrong_target = wrong_home / "my-demo"
            wrong_target.mkdir(parents=True)
            (wrong_target / "SKILL.md").write_text("untouched")

            with self.assertRaisesRegex(InstallError, "不一致"):
                recover_interrupted_install(state_home, skills_home=wrong_home)
            self.assertEqual("partial-new", (target / "SKILL.md").read_text())
            self.assertEqual("untouched", (wrong_target / "SKILL.md").read_text())

            with self.assertRaisesRegex(InstallError, "可验证 install-state"):
                recover_interrupted_install(state_home)
            self.assertEqual("partial-new", (target / "SKILL.md").read_text())

    def test_v3_recovery_restores_legacy_skill_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_home = root / ".codex"
            skills_home = state_home / "skills"
            migrated = skills_home / "my-demo"
            migrated.mkdir(parents=True)
            (migrated / "SKILL.md").write_text("partial-new")
            previous_skills_home = root / ".agents" / "skills"
            transaction = state_home / "my-matt-workflow" / "transaction"
            legacy_backup = transaction / "legacy-backup" / "my-demo"
            legacy_backup.mkdir(parents=True)
            (legacy_backup / "SKILL.md").write_text("original")
            (transaction / "journal.json").write_text(json.dumps({
                "version": 3,
                "skills_home": str(skills_home.resolve()),
                "previous_skills_home": str(previous_skills_home.resolve()),
                "skills": ["my-demo"],
                "old_present": [],
                "legacy_old_present": ["my-demo"],
                "new_release_id": "v2",
                "transaction_id": "tx-2",
            }))
            state_dir = state_home / "my-matt-workflow"
            state_dir.mkdir(parents=True, exist_ok=True)
            (state_dir / "install-state.json").write_text(json.dumps({
                "release_id": "v1",
                "transaction_id": "tx-1",
                "skills_home": str(previous_skills_home.resolve()),
            }))

            with self.assertRaisesRegex(InstallError, "schema"):
                recover_interrupted_install(state_home)

            self.assertEqual("partial-new", (migrated / "SKILL.md").read_text())
            self.assertEqual("original", (legacy_backup / "SKILL.md").read_text())
            self.assertTrue(transaction.exists())

    def test_invalid_recovery_journal_does_not_touch_skills(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / ".cursor"
            target = home / "skills" / "my-demo"
            target.mkdir(parents=True)
            (target / "SKILL.md").write_text("new")
            transaction = home / "my-matt-workflow" / "transaction"
            backup = transaction / "backup" / "my-demo"
            backup.mkdir(parents=True)
            (backup / "SKILL.md").write_text("old")
            (transaction / "journal.json").write_text(json.dumps({
                "version": 2, "skills_home": str((home / "skills").resolve()),
                "skills": ["not-managed"], "old_present": ["not-managed"],
                "new_release_id": "v2", "transaction_id": "tx-2",
            }))
            with self.assertRaises(InstallError):
                recover_interrupted_install(home)
            self.assertEqual("new", (target / "SKILL.md").read_text())
            self.assertTrue(transaction.exists())

    def test_v1_recovery_uses_install_state_split_skills_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_home = root / ".codex"
            skills_home = root / ".agents" / "skills"
            target = skills_home / "my-demo"
            target.mkdir(parents=True)
            (target / "SKILL.md").write_text("partial")
            transaction = state_home / "my-matt-workflow" / "transaction"
            backup = transaction / "backup" / "my-demo"
            backup.mkdir(parents=True)
            (backup / "SKILL.md").write_text("old")
            (transaction / "journal.json").write_text(json.dumps({
                "skills": ["my-demo"], "old_present": ["my-demo"],
            }))
            state = state_home / "my-matt-workflow" / "install-state.json"
            state.write_text(json.dumps({"skills_home": str(skills_home.resolve())}))
            with self.assertRaisesRegex(InstallError, "schema"):
                recover_interrupted_install(state_home)
            self.assertEqual("partial", (target / "SKILL.md").read_text())


class ReleaseTests(unittest.TestCase):
    def test_all_skills_have_manifest_invocation_metadata(self):
        root = Path(__file__).resolve().parents[1] / "skills"
        from tests.test_skill_packaging_v2 import MODEL_ENTRIES
        failures = []
        for skill_dir in sorted(root.iterdir()):
            if not skill_dir.is_dir():
                continue
            metadata = skill_dir / "agents/openai.yaml"
            if not metadata.is_file():
                failures.append(f"{skill_dir.name}: missing")
                continue
            text = metadata.read_text()
            expected = "true" if skill_dir.name in MODEL_ENTRIES else "false"
            if f"allow_implicit_invocation: {expected}" not in text:
                failures.append(f"{skill_dir.name}: implicit")
        self.assertEqual([], failures)

    def test_tech_design_splits_content_and_frontend_with_dynamic_html(self):
        root = Path(__file__).resolve().parents[1]
        skill = root / "skills" / "my-tech-design"
        body = (skill / "SKILL.md").read_text()
        content = (skill / "CONTENT.md").read_text()
        frontend = (skill / "FRONTEND.md").read_text()
        template = skill / "assets" / "TEMPLATE.html"
        template_text = template.read_text()
        checker = skill / "scripts" / "check_html.py"
        composition = json.loads((root / "composition" / "manifest.json").read_text())

        self.assertIn("CONTENT.md", body)
        self.assertIn("FRONTEND.md", body)
        self.assertIn("document-rendering.md", body)
        self.assertIn("frontend <artifact>", body)
        self.assertIn("后停止", body)
        self.assertIn("不构成内容模型与前端模型已隔离的证据", body)
        self.assertRegex(content, r"不(?:得)?生成 HTML、CSS、JavaScript")
        self.assertIn("关键改动面", content)
        self.assertIn("明显降低理解成本", content)
        self.assertIn("不得默认要求总览图", content)
        self.assertIn("语义工件是内容权威来源", frontend)
        self.assertIn("blocked-by-content", frontend)
        self.assertIn("comparison-card", frontend)
        self.assertIn("实际渲染每个章节", frontend)
        self.assertTrue(template.is_file())
        self.assertTrue(checker.is_file())
        self.assertIn("{{NAV_ITEMS}}", template_text)
        self.assertIn("{{CHAPTER_SECTIONS}}", template_text)
        self.assertIn("repeat(12, minmax(0, 1fr))", template_text)
        self.assertIn("<th>方案摘要</th>", template_text)
        self.assertIn(".comparison-card", template_text)
        self.assertIn(".comparison { grid-template-columns: 1fr; }", template_text)
        self.assertNotIn("window.print", template_text)
        self.assertNotIn("@media print", template_text)
        self.assertEqual([{"skill":"my-review-design", "kind":"method", "when":"load-bearing-design"}], composition["callers"]["my-tech-design"])
        self.assertTrue(
            all(
                "my-tech-design" in entries
                for entries in composition["routable_entries"].values()
            )
        )

    def test_rendered_document_skills_have_independent_stage_contracts(self):
        root = Path(__file__).resolve().parents[1] / "skills"
        for name in ("my-tech-design", "my-improve-codebase-architecture", "my-teach"):
            with self.subTest(skill=name):
                skill = root / name
                body = (skill / "SKILL.md").read_text()
                content = (skill / "CONTENT.md").read_text()
                frontend = (skill / "FRONTEND.md").read_text()
                self.assertIn("content", body)
                self.assertIn("frontend <artifact>", body)
                self.assertIn("full", body)
                self.assertIn("document-rendering.md", body + content + frontend)
                self.assertIn("blocked-by-content", frontend)
                if name == "my-teach":
                    self.assertIn("写入 `lesson-drafts/", content)
                    self.assertIn("把通过内容校验的课程语义工件渲染", frontend)
                else:
                    self.assertRegex(content, r"不(?:得)?(?:生成|写) HTML")
                    self.assertRegex(frontend, r"不(?:得)?(?:改变|改写)")

    def test_teach_uses_one_continuous_searchable_course_template(self):
        root = Path(__file__).resolve().parents[1]
        skill = root / "skills/my-teach"
        body = (skill / "SKILL.md").read_text()
        content = (skill / "CONTENT.md").read_text()
        frontend = (skill / "FRONTEND.md").read_text()
        template = (skill / "assets/TEMPLATE.html").read_text()
        css = (skill / "assets/course.css").read_text()
        script = (skill / "assets/course.js").read_text()

        for phrase in (
            "行业通行术语作为主名称",
            "白话含义",
            "visual_intent",
            "多项精确对照",
        ):
            self.assertIn(phrase, content)
        for phrase in (
            "行业主名称",
            "同一内容表达清楚",
            "一条连续文档流",
        ):
            self.assertIn(phrase, frontend)

        self.assertIn("assets/TEMPLATE.html", frontend)
        self.assertIn("最近发展区", content)
        self.assertIn("全文搜索", frontend)
        self.assertIn("打印时直接可见的答案解释与来源", frontend)
        self.assertIn("对照学生课程", frontend)
        self.assertIn("可以调整段落、列表、表格", frontend)
        self.assertIn("data-learning-outcome", template)
        self.assertIn("{{NAV_ITEMS}}", template)
        self.assertIn("{{LESSON_SECTIONS}}", template)
        self.assertNotIn("data-page", template)
        self.assertNotIn("hidden", template)
        self.assertIn("@media print", css)
        self.assertIn("scroll-margin-top", css)
        self.assertNotRegex(css, r"\.lesson-section[^{}]*\{[^{}]*display\s*:\s*none")
        self.assertIn("IntersectionObserver", script)
        self.assertIn("beforeprint", script)
        self.assertIn("print-answer", script)
        self.assertRegex(css, r"@media print[\s\S]*\.print-answer\s*\{\s*display:\s*block")

    def test_teach_html_checker_accepts_complete_lesson_and_rejects_hidden_sections(self):
        root = Path(__file__).resolve().parents[1]
        skill = root / "skills/my-teach"
        checker = skill / "scripts/check_html.py"
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            lessons = workspace / "lessons"
            assets = workspace / "assets"
            lessons.mkdir()
            assets.mkdir()
            shutil.copy(skill / "assets/course.css", assets / "course.css")
            shutil.copy(skill / "assets/course.js", assets / "course.js")
            artifact = workspace / "lesson.content.md"
            artifact.write_text(
                """---
document_kind: lesson
content_revision: 1
status: content-ready
reader: 测试学生
purpose: 掌握一件事
output_path: lessons/0001-test.html
template_ref: assets/TEMPLATE.html
source_refs: [https://example.com/source]
render_root: 学生课程
---

# 学生课程

## 模型
正文。

## 练习
完成一道判断题并理解答案。

## 迁移
把方法用于新情境。

# 制作记录（不得渲染）

```json render-map
[
  {"section_id":"model","heading":"模型","visual_intent":"none","visual_reason":"短解释适合文字"},
  {"section_id":"practice","heading":"练习","visual_intent":"none","visual_reason":"短判断题适合文字"},
  {"section_id":"transfer","heading":"迁移","visual_intent":"none","visual_reason":"短迁移题适合文字"}
]
```
"""
            )
            lesson = lessons / "0001-test.html"
            lesson.write_text(
                '<!doctype html><html><head><link rel="stylesheet" '
                'href="../assets/course.css"></head><body>'
                '<header><h1>测试课程</h1><div data-learning-outcome>掌握一件事</div></header>'
                '<nav><a href="#model">模型</a></nav><main>'
                '<section class="lesson-section" id="model">正文</section>'
                '<section class="lesson-section quiz" id="practice" data-quiz '
                'data-answer="a"><h2>练习</h2>'
                '<button class="choice" data-value="a">A</button>'
                '<p class="feedback"></p><p class="print-answer">答案：A</p>'
                '<a href="https://example.com/source">来源</a></section>'
                '<section class="lesson-section" id="transfer" data-transfer>'
                '<h2>迁移</h2><p>把方法用于新情境。</p></section></main>'
                '<script src="../assets/course.js"></script></body></html>'
            )
            checked = subprocess.run(
                [sys.executable, checker, lesson, "--artifact", artifact],
                capture_output=True, text=True, check=False
            )
            self.assertEqual(0, checked.returncode, checked.stdout)

            lesson.write_text(lesson.read_text().replace(
                'class="lesson-section" id="model"',
                'class="lesson-section" id="model" hidden',
            ))
            checked = subprocess.run(
                [sys.executable, checker, lesson, "--artifact", artifact],
                capture_output=True, text=True, check=False
            )
            self.assertNotEqual(0, checked.returncode)
            self.assertIn("被隐藏的 lesson-section", checked.stdout)

    def test_tech_design_html_checker_rejects_table_in_narrow_card(self):
        root = Path(__file__).resolve().parents[1]
        checker = root / "skills/my-tech-design/scripts/check_html.py"
        with tempfile.TemporaryDirectory() as tmp:
            html = Path(tmp) / "design.html"
            html.write_text(
                '<nav><a data-page-link="overview"></a></nav>'
                '<section id="overview" data-page="overview">'
                '<article class="card span-4"><table><tr><td>x</td></tr></table>'
                "</article></section>"
            )
            checked = subprocess.run(
                [sys.executable, checker, html],
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertNotEqual(0, checked.returncode)
        self.assertIn("表格位于 span-4 窄栏", checked.stdout)

    def test_tech_design_html_checker_rejects_mixed_scope_and_unlisted_comparison(self):
        root = Path(__file__).resolve().parents[1]
        checker = root / "skills/my-tech-design/scripts/check_html.py"
        with tempfile.TemporaryDirectory() as tmp:
            html = Path(tmp) / "design.html"
            html.write_text(
                '<nav><a data-page-link="overview"></a></nav>'
                '<section id="overview" data-page="overview">'
                '<p>包含 task 表迁移，不包含下游系统改造。</p>'
                '<div class="comparison"><article class="comparison-card">'
                '<h3>包含</h3><p>task 表迁移</p>'
                '</article></div></section>'
            )
            checked = subprocess.run(
                [sys.executable, checker, html],
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertNotEqual(0, checked.returncode)
        self.assertIn("“包含/不包含”必须使用独立对比区块", checked.stdout)
        self.assertIn("comparison-card 未使用列表", checked.stdout)

    def test_tech_design_html_checker_warns_about_dense_paragraphs(self):
        root = Path(__file__).resolve().parents[1]
        checker = root / "skills/my-tech-design/scripts/check_html.py"
        with tempfile.TemporaryDirectory() as tmp:
            html = Path(tmp) / "design.html"
            html.write_text(
                '<nav><a data-page-link="kafka"></a></nav>'
                '<section id="kafka" data-page="kafka"><p>'
                'workflow 完成生成后向下游投递消息，消息中包含本次处理结果和执行范围；'
                '空数据时仍然发送完成通知，发送失败时由任务重试并记录状态，消费者需要按任务去重。'
                '</p></section>'
            )
            checked = subprocess.run(
                [sys.executable, checker, html],
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(0, checked.returncode)
        self.assertIn("复核可能需要拆点的长段落", checked.stdout)
        self.assertIn("复核使用分号压缩信息的文字", checked.stdout)

    def test_adopted_skills_include_metadata_and_safety_boundaries(self):
        root = Path(__file__).resolve().parents[1] / "skills"
        expected = {
            "my-resolving-merge-conflicts": [
                "批准前",
                "references/policies/merge-conflict-approval.md",
            ],
            "my-to-questionnaire": [
                "questionnaires-<topic>-<time-or-sequence>.md",
                "只就“发送”采访用户，而不要就主题采访用户",
            ],
            "my-wizard": [
                "每个阶段按顺序命名",
                "永远不要编造可能不存在的步骤",
                "不要改动 `STAGES` 标记上方的库",
            ],
            "my-edit-article": ["articles", "默认生成新稿", "原地修改"],
            "my-review-design": [
                "只评审，不改文档、不重新访谈",
                "读代码核实承重现状断言是必做项",
                "已考察但排除的风险",
                "待用户确认的需求语义假设",
            ],
            "my-review-artifact": [
                "references/shared/reader-first-writing.md",
                "references/shared/artifact-finalization.md",
                "No findings.",
            ],
        }

        for skill, required_text in expected.items():
            with self.subTest(skill=skill):
                skill_dir = root / skill
                self.assertTrue((skill_dir / "SKILL.md").is_file())
                self.assertTrue((skill_dir / "agents" / "openai.yaml").is_file())
                text = (skill_dir / "SKILL.md").read_text()
                for phrase in required_text:
                    self.assertIn(phrase, text)

        conflict_policy = (
            root.parent / "policies" / "merge-conflict-approval.md"
        ).read_text()
        self.assertIn("Force Push", conflict_policy)
        self.assertIn("回滚", conflict_policy)
        self.assertEqual(32, len(validate_skills(root)))

    def test_release_skills_do_not_repeat_project_policy_footer(self):
        source_skills = Path(__file__).parents[1] / "skills"
        for skill_file in source_skills.glob("my-*/SKILL.md"):
            self.assertNotIn(
                "项目策略优先", skill_file.read_text(), skill_file
            )

    def test_builds_manifest_for_valid_manual_skill(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = root / "skills" / "my-demo"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text(
                "---\n"
                "name: my-demo\n"
                "description: 手动测试 Skill\n"
                "disable-model-invocation: true\n"
                "---\n\n"
                "# Demo\n"
            )

            release = build_release(
                root / "skills",
                root / "releases",
                release_id="v1",
                upstream_id="upstream-1",
            )

            manifest = json.loads((release / "manifest.json").read_text())
            self.assertEqual("upstream-1", manifest["upstream_id"])
            self.assertIn("SKILL.md", manifest["skills"]["my-demo"])

    def test_build_ignores_placeholder_markdown_links_in_fenced_examples(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = root / "skills" / "my-demo"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text(
                "---\n"
                "name: my-demo\n"
                "description: 手动测试 Skill\n"
                "disable-model-invocation: true\n"
                "---\n\n"
                "```md\n[example](missing-example.md)\n```\n"
            )

            release = build_release(
                root / "skills",
                root / "releases",
                release_id="v1",
                upstream_id="upstream-1",
            )

            self.assertTrue((release / "skills/my-demo/SKILL.md").is_file())

    def test_build_materializes_shared_resources_without_body_copies(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            release = build_release(root / "skills", Path(tmp) / "releases",
                                    release_id="resources-v2", upstream_id="local-matt-skills", repo_root=root)
            self.assertFalse((release / "skills/my-implement/references/composed").exists())
            self.assertTrue((release / "skills/my-implement/references/shared/review-loop.md").is_file())
            body = (release / "skills/my-implement/SKILL.md").read_text()
            self.assertIn("{{skill-call:my-tdd}}", body)
            self.assertIn("{{skill-call:my-code-review}}", body)

    def test_release_bundles_policies_only_for_explicit_consumers(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            release = build_release(
                root / "skills",
                Path(tmp) / "releases",
                release_id="policy-consumers-v1",
                upstream_id="local-matt-skills",
                repo_root=root,
            )
            for skill in (
                "my-handoff",
                "my-resolving-merge-conflicts",
                "my-wayfinder",
            ):
                with self.subTest(consumer=skill):
                    self.assertTrue(
                        (release / "skills" / skill / "references/policies").is_dir()
                    )
            for skill in ("my-install", "my-grilling", "my-grill-me"):
                with self.subTest(non_consumer=skill):
                    self.assertFalse(
                        (release / "skills" / skill / "references/policies").exists()
                    )

    def test_build_materializes_plan_2_adapters_for_declared_consumers(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            release = build_release(
                root / "skills",
                Path(tmp) / "releases",
                release_id="plan-2-adapters",
                upstream_id="local-matt-skills",
                repo_root=root,
            )

            expected = {
                "my-implement": {
                    "work-scope.md",
                    "implementation-session.md",
                },
                "my-review-artifact": {"artifact-review-session.md"},
                "my-grill-me": set(),
                "my-grill-with-docs": {
                    "artifact-access.md",
                },
            }
            for skill, adapters in expected.items():
                for adapter in adapters:
                    with self.subTest(skill=skill, adapter=adapter):
                        self.assertTrue(
                            (
                                release
                                / "skills"
                                / skill
                                / "references/shared/adapters"
                                / adapter
                            ).is_file()
                        )
            self.assertFalse(
                (
                    release
                    / "skills/my-grill-me/references/shared/adapters"
                    / "ticket-selection.md"
                ).exists()
            )

    def test_build_does_not_materialize_routable_entries_for_router(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            release = build_release(
                root / "skills",
                Path(tmp) / "releases",
                release_id="routed-v1",
                upstream_id="local-matt-skills",
                repo_root=root,
            )

            self.assertFalse(
                (release / "skills/my-ask-matt/references/composed").exists()
            )
            manifest = json.loads((release / "manifest.json").read_text())
            self.assertNotIn("my-ask-matt", manifest["composed"])

    def test_rejects_skill_that_allows_model_invocation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = root / "skills" / "my-demo"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text(
                "---\nname: my-demo\ndescription: demo\n---\n"
            )

            with self.assertRaisesRegex(ReleaseError, "disable-model-invocation"):
                build_release(
                    root / "skills",
                    root / "releases",
                    release_id="v1",
                    upstream_id="upstream-1",
                )

    def test_rejects_release_id_path_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = root / "skills" / "my-demo"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text(
                "---\n"
                "name: my-demo\n"
                "description: 手动测试 Skill\n"
                "disable-model-invocation: true\n"
                "---\n"
            )

            with self.assertRaisesRegex(ReleaseError, "release_id"):
                build_release(
                    root / "skills",
                    root / "releases",
                    release_id="../outside",
                    upstream_id="upstream-1",
                )


class WorkflowCliTests(unittest.TestCase):
    @staticmethod
    def _load_workflow_module():
        root = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location(
            "workflow_cli_under_test", root / "tools/workflow.py"
        )
        module = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(root / "tools"))
        try:
            assert spec.loader is not None
            spec.loader.exec_module(module)
        finally:
            sys.path.pop(0)
        return module

    def _workflow(self, root: Path) -> Path:
        workflow = root / "workflow"
        source = Path(__file__).resolve().parents[1]
        shutil.copytree(source / "tools", workflow / "tools")
        skill = workflow / "skills" / "my-demo"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            "---\n"
            "name: my-demo\n"
            "description: Demo skill\n"
            "disable-model-invocation: true\n"
            "---\n\n"
            "# Demo\n"
        )
        (skill / "agents").mkdir()
        (skill / "agents" / "openai.yaml").write_text(
            "allow_implicit_invocation: false\n"
        )
        return workflow

    def _run(self, workflow: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "tools/workflow.py", *args],
            cwd=workflow,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_codex_skills_share_the_codex_home(self):
        module = self._load_workflow_module()

        self.assertEqual(
            module.AGENT_STATE_HOMES["codex"] / "skills",
            module._agent_skills_home("codex"),
        )

    def test_deploy_reuses_the_current_release_when_skills_are_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            workflow = self._workflow(Path(tmp))
            build_release(
                workflow / "skills",
                workflow / "releases",
                release_id="v1",
                upstream_id="local-matt-skills",
                repo_root=workflow,
            )
            (workflow / "current.json").write_text('{"release_id": "v1"}\n')

            module = self._load_workflow_module()
            with mock.patch.object(module, "ROOT", workflow), mock.patch.object(
                module, "_run_all_up_gate", return_value={"status": "valid"}
            ):
                module.command_deploy(argparse.Namespace(
                    release_id=None, upstream_id="local-matt-skills", target="auto",
                    agent_home=str(Path(tmp) / "agent"),
                ))
            self.assertEqual(
                ["v1"],
                sorted(
                    path.name
                    for path in (workflow / "releases").iterdir()
                    if path.is_dir() and not path.name.startswith(".")
                ),
            )
            self.assertTrue((Path(tmp) / "agent/skills/my-demo/SKILL.md").is_file())

    def test_current_release_pointer_uses_fsync_and_atomic_replace(self):
        module = self._load_workflow_module()
        self.assertTrue(hasattr(module, "_write_current_release"))
        with tempfile.TemporaryDirectory() as tmp:
            current = Path(tmp) / "current.json"
            real_replace = os.replace
            real_fsync = os.fsync
            with (
                mock.patch.object(
                    module.os,
                    "replace",
                    side_effect=real_replace,
                ) as replace,
                mock.patch.object(
                    module.os,
                    "fsync",
                    side_effect=real_fsync,
                ) as fsync,
            ):
                module._write_current_release(current, "v2")

            self.assertEqual(
                {"release_id": "v2"},
                json.loads(current.read_text()),
            )
            self.assertGreaterEqual(fsync.call_count, 1)
            source, destination = replace.call_args.args
            self.assertEqual(current, destination)
            self.assertEqual(current.parent, Path(source).parent)
            self.assertFalse(Path(source).exists())

    def test_current_release_pointer_cleans_temp_on_replace_error(self):
        module = self._load_workflow_module()
        self.assertTrue(hasattr(module, "_write_current_release"))
        with tempfile.TemporaryDirectory() as tmp:
            current = Path(tmp) / "current.json"
            current.write_text('{"release_id": "v1"}\n')
            with mock.patch.object(
                module.os,
                "replace",
                side_effect=OSError("replace failed"),
            ):
                with self.assertRaisesRegex(OSError, "replace failed"):
                    module._write_current_release(current, "v2")

            self.assertEqual(
                {"release_id": "v1"},
                json.loads(current.read_text()),
            )
            self.assertEqual(
                ["current.json"],
                sorted(path.name for path in current.parent.iterdir()),
            )

    def test_deploy_builds_an_initial_release_when_none_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            workflow = self._workflow(Path(tmp))
            module = self._load_workflow_module()
            agent_home = Path(tmp) / "agent"
            args = argparse.Namespace(
                release_id="v1",
                upstream_id="local-matt-skills",
                target="auto",
                agent_home=str(agent_home),
            )
            with mock.patch.object(module, "ROOT", workflow), mock.patch.object(
                module, "_run_all_up_gate", return_value={"status": "valid"}
            ):
                module.command_deploy(args)

            self.assertEqual(
                1,
                len([path for path in (workflow / "releases").iterdir() if path.is_dir()]),
            )
            self.assertEqual(
                {"release_id": "v1"},
                json.loads((workflow / "current.json").read_text()),
            )

    def test_deploy_does_not_reuse_a_corrupt_current_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            workflow = self._workflow(Path(tmp))
            current = build_release(
                workflow / "skills", workflow / "releases", release_id="v1",
                upstream_id="local-matt-skills", repo_root=workflow,
            )
            (workflow / "current.json").write_text('{"release_id": "v1"}\n')
            (current / "skills/my-demo/SKILL.md").write_text("tampered")
            module = self._load_workflow_module()
            with mock.patch.object(module, "ROOT", workflow), mock.patch.object(
                module, "_run_all_up_gate", return_value={"status": "valid"}
            ):
                module.command_deploy(argparse.Namespace(
                    release_id="v2", upstream_id="local-matt-skills", target="auto",
                    agent_home=str(Path(tmp) / "agent"),
                ))
            self.assertTrue((workflow / "releases/v1").is_dir())
            self.assertTrue((workflow / "releases/v2").is_dir())
            self.assertEqual({"release_id": "v2"}, json.loads((workflow / "current.json").read_text()))

    def test_prune_releases_keeps_current_and_agent_referenced_releases(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflow = self._workflow(root)
            skill_file = workflow / "skills" / "my-demo" / "SKILL.md"
            agent_home = root / "agent"
            for release_id, description in [
                ("v1", "Demo skill v1"),
                ("v2", "Demo skill v2"),
                ("v3", "Demo skill v3"),
            ]:
                skill_file.write_text(
                    "---\n"
                    "name: my-demo\n"
                    f"description: {description}\n"
                    "disable-model-invocation: true\n"
                    "---\n\n"
                    "# Demo\n"
                )
                build_release(
                    workflow / "skills",
                    workflow / "releases",
                    release_id=release_id,
                    upstream_id="local-matt-skills",
                    repo_root=workflow,
                    agent_homes=[agent_home],
                )
                if release_id == "v1":
                    install_release(workflow / "releases/v1", agent_home)
            (workflow / "current.json").write_text('{"release_id": "v3"}\n')

            agent_home = root / "agent"
            installed = self._run(
                workflow,
                "install",
                "--release",
                "v1",
                "--agent-home",
                str(agent_home),
            )
            self.assertEqual(0, installed.returncode, installed.stderr)

            pruned = self._run(
                workflow,
                "prune-releases",
                "--agent-home",
                str(agent_home),
                "--apply",
            )

            self.assertEqual(0, pruned.returncode, pruned.stderr)
            self.assertEqual(
                ["v1", "v3"],
                sorted(
                    path.name
                    for path in (workflow / "releases").iterdir()
                    if path.is_dir() and not path.name.startswith(".")
                ),
            )
