import hashlib
import json
import tempfile
import unittest
from unittest import mock
from datetime import datetime, timezone
from pathlib import Path

from tools.workflow_lib.artifact_review import (
    ArtifactReviewError,
    build_artifact_review_snapshot,
    finalize_artifact_review_snapshot,
)
from tools.workflow_lib.fs_safety import register_owned_directory
from tools.workflow_lib.installer import (
    InstallError,
    install_release,
    recover_interrupted_install,
    remove_verified_release,
    verify_installed_state,
    verify_release,
)
from tools.workflow_lib.release import (
    ReleaseError,
    build_release,
    source_manifest,
    validate_skills,
)
from tools.workflow_lib.work_artifacts import (
    WorkArtifactError,
    apply_work_artifact_migration,
)


class SecurityHardeningTests(unittest.TestCase):
    def _release(self, root: Path, release_id: str, body: str = "managed") -> Path:
        release = root / release_id
        skill_file = release / "skills/my-demo/SKILL.md"
        skill_file.parent.mkdir(parents=True)
        skill_file.write_text(body, encoding="utf-8")
        runtime = release / "runtime/tools/workflow.py"
        runtime.parent.mkdir(parents=True)
        runtime.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
        (release / "manifest.json").write_text(json.dumps({
            "release_id": release_id,
            "skills": {"my-demo": {"SKILL.md": hashlib.sha256(skill_file.read_bytes()).hexdigest()}},
            "runtime": {"tools/workflow.py": hashlib.sha256(runtime.read_bytes()).hexdigest()},
        }), encoding="utf-8")
        return release

    def _source_skill(self, root: Path) -> Path:
        skill = root / "skills/my-demo"
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            "---\nname: my-demo\ndescription: demo\n"
            "disable-model-invocation: true\n---\n"
            "Run {{skill-call:my-next}}.\n",
            encoding="utf-8",
        )
        metadata = skill / "agents/openai.yaml"
        metadata.parent.mkdir()
        metadata.write_text(
            "policy:\n  allow_implicit_invocation: false\n", encoding="utf-8"
        )
        return skill

    def test_corrupt_install_state_fails_before_foreign_skill_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            release = self._release(root / "sources", "v2")
            home = root / "home"
            foreign = home / "skills/my-demo"
            foreign.mkdir(parents=True)
            sentinel = foreign / "SKILL.md"
            sentinel.write_text("foreign", encoding="utf-8")
            state_dir = home / "my-matt-workflow"
            state_dir.mkdir(parents=True)
            (state_dir / "install-state.json").write_text(
                json.dumps({"skills": ["../victim"]}), encoding="utf-8"
            )

            with self.assertRaises(InstallError):
                install_release(release, home)

            self.assertEqual("foreign", sentinel.read_text(encoding="utf-8"))
            self.assertFalse((state_dir / "transaction").exists())

    def test_legacy_state_cannot_claim_foreign_bytes_via_valid_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old_release = self._release(root / "sources", "v1", "expected-old")
            new_release = self._release(root / "sources", "v2", "new")
            home = root / "home"
            foreign = home / "skills/my-demo"
            foreign.mkdir(parents=True)
            sentinel = foreign / "SKILL.md"
            sentinel.write_text("foreign", encoding="utf-8")
            state_dir = home / "my-matt-workflow"
            state_dir.mkdir(parents=True)
            runtime_entry = state_dir / "runtime/v1/tools/workflow.py"
            runtime_entry.parent.mkdir(parents=True)
            runtime_entry.write_text("runtime", encoding="utf-8")
            (state_dir / "install-state.json").write_text(json.dumps({
                "release_id": "v1",
                "source": str(old_release.resolve()),
                "skills": ["my-demo"],
                "installed_at": datetime.now(timezone.utc).isoformat(),
                "transaction_id": "forged",
                "installed_agent": None,
                "metadata_projection": "portable",
                "skills_home": str((home / "skills").resolve()),
                "runtime_entry": str(runtime_entry.resolve()),
            }), encoding="utf-8")

            with self.assertRaisesRegex(InstallError, "ownership"):
                install_release(new_release, home)

            self.assertEqual("foreign", sentinel.read_text(encoding="utf-8"))
            self.assertFalse((state_dir / "transaction").exists())

    def test_verified_legacy_journal_can_restore_matching_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            release = self._release(root / "sources", "v1", "stable")
            home = root / "home"
            target = home / "skills/my-demo"
            target.mkdir(parents=True)
            (target / "SKILL.md").write_text("partial", encoding="utf-8")
            state_dir = home / "my-matt-workflow"
            transaction = state_dir / "transaction"
            backup = transaction / "backup/my-demo"
            backup.mkdir(parents=True)
            (backup / "SKILL.md").write_text("stable", encoding="utf-8")
            (transaction / "journal.json").write_text(json.dumps({
                "version": 2,
                "skills_home": str((home / "skills").resolve()),
                "skills": ["my-demo"],
                "old_present": ["my-demo"],
                "new_release_id": "v2",
                "transaction_id": "tx-v2",
            }), encoding="utf-8")
            runtime_entry = state_dir / "runtime/v1/tools/workflow.py"
            runtime_entry.parent.mkdir(parents=True)
            runtime_entry.write_text("runtime", encoding="utf-8")
            (state_dir / "install-state.json").write_text(json.dumps({
                "release_id": "v1",
                "source": str(release.resolve()),
                "skills": ["my-demo"],
                "installed_at": datetime.now(timezone.utc).isoformat(),
                "transaction_id": "tx-v1",
                "installed_agent": None,
                "metadata_projection": "portable",
                "skills_home": str((home / "skills").resolve()),
                "runtime_entry": str(runtime_entry.resolve()),
            }), encoding="utf-8")

            recover_interrupted_install(home)

            self.assertEqual("stable", (target / "SKILL.md").read_text())
            self.assertFalse(transaction.exists())

    def test_v4_recovery_accepts_legitimate_transaction_content_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = self._release(root / "sources", "v1", "expected-old")
            second = self._release(root / "sources", "v2", "expected-new")
            home = root / "home"
            install_release(first, home)
            original_rename = Path.rename

            def hard_exit_after_stage_move(path: Path, destination: Path):
                result = original_rename(path, destination)
                if path.parent.name == "staged" and path.name == "my-demo":
                    raise SystemExit("simulated hard exit")
                return result

            with mock.patch.object(Path, "rename", hard_exit_after_stage_move):
                with self.assertRaisesRegex(SystemExit, "hard exit"):
                    install_release(second, home)

            recover_interrupted_install(home)

            self.assertEqual(
                "expected-old",
                (home / "skills/my-demo/SKILL.md").read_text(),
            )
            self.assertFalse((home / "my-matt-workflow/transaction").exists())

    def test_installer_projects_portable_skill_call_macro(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            body = (
                "---\nname: my-demo\ndescription: demo\n"
                "disable-model-invocation: true\n---\n"
                "Run {{skill-call:my-next}}.\n"
            )
            release = self._release(root / "sources", "v1", body)
            metadata = release / "skills/my-demo/agents/openai.yaml"
            metadata.parent.mkdir()
            metadata.write_text(
                "policy:\n  allow_implicit_invocation: false\n", encoding="utf-8"
            )
            manifest_path = release / "manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["skills"]["my-demo"]["agents/openai.yaml"] = hashlib.sha256(
                metadata.read_bytes()
            ).hexdigest()
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

            install_release(release, root / "cursor", target="cursor")
            install_release(release, root / "codex", target="codex")

            self.assertIn(
                "/my-next", (root / "cursor/skills/my-demo/SKILL.md").read_text()
            )
            self.assertIn(
                "$my-next", (root / "codex/skills/my-demo/SKILL.md").read_text()
            )

    def test_work_artifact_traversal_journal_keeps_repo_victim(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            victim = repo / "victim"
            victim.write_text("sentinel", encoding="utf-8")
            transaction = repo / ".agent/.work-artifact-transaction"
            transaction.mkdir(parents=True)
            (transaction / "journal.json").write_text(json.dumps({
                "version": 1,
                "moves": [{"from": ".agent/work/topic/spec.md", "to": ".agent/../victim"}],
            }), encoding="utf-8")
            register_owned_directory(
                repo / ".agent", transaction, purpose="work-artifact-transaction"
            )

            with self.assertRaises(WorkArtifactError):
                apply_work_artifact_migration(repo)

            self.assertEqual("sentinel", victim.read_text(encoding="utf-8"))
            self.assertTrue(transaction.exists())

    def test_forged_review_marker_cannot_authorize_recursive_delete(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / "artifact.md"
            artifact.write_text("source", encoding="utf-8")
            forged = root / "my-matt-review-forged"
            forged.mkdir()
            (forged / ".review-unit.json").write_text(
                json.dumps({"content_id": "forged"}), encoding="utf-8"
            )
            sentinel = forged / "sentinel"
            sentinel.write_text("keep", encoding="utf-8")

            with self.assertRaisesRegex(ArtifactReviewError, "ownership"):
                finalize_artifact_review_snapshot([artifact], "forged", forged)

            self.assertEqual("keep", sentinel.read_text(encoding="utf-8"))

    def test_snapshot_byte_drift_is_rejected_without_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / "artifact.md"
            artifact.write_text("source", encoding="utf-8")
            opened = build_artifact_review_snapshot(
                [artifact], snapshot_root=root / "snapshots"
            )
            snapshot = Path(opened["artifacts"][0]["snapshot_path"])
            snapshot.chmod(0o600)
            snapshot.write_text("tampered", encoding="utf-8")

            with self.assertRaises(ArtifactReviewError):
                finalize_artifact_review_snapshot(
                    [artifact], opened["content_id"], Path(opened["snapshot_dir"])
                )

            self.assertTrue(Path(opened["snapshot_dir"]).exists())

    def test_release_verifier_rejects_id_sibling_and_root_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            release = self._release(root, "v1")
            (release / "skills/my-extra").mkdir()
            with self.assertRaisesRegex(InstallError, "Skill 目录"):
                verify_release(release)
            (release / "skills/my-extra").rmdir()
            (release / "EXTRA").write_text("extra", encoding="utf-8")
            with self.assertRaisesRegex(InstallError, "根目录"):
                verify_release(release)
            (release / "EXTRA").unlink()
            manifest = json.loads((release / "manifest.json").read_text())
            manifest["release_id"] = "v2"
            (release / "manifest.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(InstallError, "目录名"):
                verify_release(release)

    def test_build_preserves_unknown_staging_and_excludes_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = self._source_skill(root)
            cache = skill / "__pycache__"
            cache.mkdir()
            (cache / "local.pyc").write_bytes(b"machine-local")
            releases = root / "releases"
            staged = releases / ".v1.staging"
            staged.mkdir(parents=True)
            sentinel = staged / "sentinel"
            sentinel.write_text("keep", encoding="utf-8")
            with self.assertRaisesRegex(ReleaseError, "staging"):
                build_release(
                    root / "skills", releases, release_id="v1", upstream_id="local"
                )
            self.assertEqual("keep", sentinel.read_text(encoding="utf-8"))
            staged.rename(releases / ".preserved")
            release = build_release(
                root / "skills", releases, release_id="v1", upstream_id="local"
            )
            self.assertFalse((release / "skills/my-demo/__pycache__").exists())

    def test_build_retries_when_live_source_changes_after_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = self._source_skill(root)
            calls = 0

            def mutate_once(_: Path) -> None:
                nonlocal calls
                calls += 1
                if calls == 1:
                    skill_file = skill / "SKILL.md"
                    skill_file.write_text(
                        skill_file.read_text() + "Concurrent revision.\n",
                        encoding="utf-8",
                    )

            release = build_release(
                root / "skills",
                root / "releases",
                release_id="v1",
                upstream_id="local",
                source_gate=mutate_once,
            )

            self.assertEqual(2, calls)
            self.assertIn(
                "Concurrent revision.",
                (release / "skills/my-demo/SKILL.md").read_text(),
            )

    def test_prune_refuses_corrupt_release_without_deleting_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            releases = Path(tmp) / "releases"
            release = self._release(releases, "v1")
            sentinel = release / "sentinel"
            sentinel.write_text("keep", encoding="utf-8")
            with self.assertRaises(InstallError):
                remove_verified_release(releases, release)
            self.assertEqual("keep", sentinel.read_text(encoding="utf-8"))

    def test_prune_refuses_self_consistent_but_unregistered_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            releases = Path(tmp) / "releases"
            release = self._release(releases, "v1")

            with self.assertRaises(InstallError):
                remove_verified_release(releases, release)

            self.assertTrue((release / "skills/my-demo/SKILL.md").is_file())

    def test_prune_removes_only_build_registered_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._source_skill(root)
            release = build_release(
                root / "skills",
                root / "releases",
                release_id="v1",
                upstream_id="local",
            )

            remove_verified_release(root / "releases", release)

            self.assertFalse(release.exists())

    def test_release_persists_deterministic_target_manifests(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._source_skill(root)
            first = build_release(
                root / "skills", root / "releases", release_id="v1", upstream_id="local"
            )
            second = build_release(
                root / "skills", root / "releases", release_id="v2", upstream_id="local"
            )
            first_manifest = json.loads((first / "manifest.json").read_text())
            second_manifest = json.loads((second / "manifest.json").read_text())

            self.assertEqual(
                {"portable", "codex", "cursor", "claude"},
                set(first_manifest["target_manifests"]),
            )
            self.assertEqual(
                first_manifest["target_manifests"],
                second_manifest["target_manifests"],
            )
            self.assertEqual(
                first_manifest["skills"],
                first_manifest["target_manifests"]["portable"]["skills"],
            )

    def test_release_rejects_forged_resource_consumer_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            release = self._release(Path(tmp) / "releases", "v1")
            manifest_path = release / "manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["resource_consumers"] = {
                "direct": {"shared": ["my-demo"]},
                "effective": {"shared": ["../foreign"]},
            }
            manifest_path.write_text(json.dumps(manifest))

            with self.assertRaisesRegex(InstallError, "resource_consumers"):
                verify_release(release)

    def test_release_rejects_non_object_manifest_cleanly(self):
        with tempfile.TemporaryDirectory() as tmp:
            release = self._release(Path(tmp) / "releases", "v1")
            (release / "manifest.json").write_text("[]")

            with self.assertRaisesRegex(InstallError, "顶层必须是对象"):
                verify_release(release)

    def test_three_hosts_install_exact_declared_target_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._source_skill(root)
            release = build_release(
                root / "skills", root / "releases", release_id="v1", upstream_id="local"
            )
            manifest = json.loads((release / "manifest.json").read_text())

            for target, call in (("codex", "$my-next"), ("cursor", "/my-next"), ("claude", "/my-next")):
                with self.subTest(target=target):
                    home = root / target
                    install_release(release, home, target=target)
                    state = json.loads(
                        (home / "my-matt-workflow/install-state.json").read_text()
                    )
                    self.assertEqual(
                        manifest["target_manifests"][target]["skills"],
                        state["managed_inventory"],
                    )
                    self.assertIn(
                        call, (home / "skills/my-demo/SKILL.md").read_text()
                    )
                    verify_installed_state(state)

    def test_install_rejects_tampered_target_manifest_and_cleans_staging(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._source_skill(root)
            release = build_release(
                root / "skills", root / "releases", release_id="v1", upstream_id="local"
            )
            manifest_path = release / "manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["target_manifests"]["codex"]["skills"]["my-demo"]["SKILL.md"] = "0" * 64
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            home = root / "codex"

            with self.assertRaisesRegex(InstallError, "target manifest"):
                install_release(release, home, target="codex")

            self.assertFalse((home / "skills/my-demo").exists())
            self.assertFalse((home / "my-matt-workflow/transaction").exists())

    def test_shared_source_walker_rejects_unreferenced_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = self._source_skill(root)
            orphan = skill / "ORPHAN.md"
            orphan.write_text("not reachable", encoding="utf-8")

            with self.assertRaisesRegex(ReleaseError, "未引用.*ORPHAN.md"):
                validate_skills(root / "skills")
            with self.assertRaisesRegex(ReleaseError, "未引用.*ORPHAN.md"):
                source_manifest(root / "skills", upstream_id="local")
            with self.assertRaisesRegex(ReleaseError, "未引用.*ORPHAN.md"):
                build_release(
                    root / "skills",
                    root / "releases",
                    release_id="v1",
                    upstream_id="local",
                )

    def test_root_sidecar_script_and_asset_are_in_reachable_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = self._source_skill(root)
            skill_file = skill / "SKILL.md"
            skill_file.write_text(
                skill_file.read_text()
                + "Read [guide](GUIDE.md), then run `scripts/check.py`.\n",
                encoding="utf-8",
            )
            guide = skill / "GUIDE.md"
            guide.write_text(
                "Render from [template](assets/template.html).\n",
                encoding="utf-8",
            )
            script = skill / "scripts/check.py"
            script.parent.mkdir()
            script.write_text("print('ok')\n", encoding="utf-8")
            asset = skill / "assets/template.html"
            asset.parent.mkdir()
            asset.write_text("<main>template</main>\n", encoding="utf-8")

            release = build_release(
                root / "skills",
                root / "releases",
                release_id="v1",
                upstream_id="local",
            )
            files = json.loads((release / "manifest.json").read_text())["skills"]["my-demo"]

            self.assertEqual(
                {
                    "GUIDE.md",
                    "SKILL.md",
                    "agents/openai.yaml",
                    "assets/template.html",
                    "scripts/check.py",
                },
                set(files),
            )


if __name__ == "__main__":
    unittest.main()
