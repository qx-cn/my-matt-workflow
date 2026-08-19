import json
import tempfile
import unittest
from pathlib import Path

from tools.workflow_lib.resources import (
    bundle_resources_for_skill,
    load_resource_manifest,
)
from tools.workflow_lib.release import ReleaseError, validate_skills


ROOT = Path(__file__).resolve().parents[1]


class SharedResourceTests(unittest.TestCase):
    def test_humanizer_has_one_source(self):
        self.assertTrue((ROOT / "resources/humanizer.md").is_file())
        self.assertFalse((ROOT / "skills/my-to-spec/humanizer.md").exists())

    def test_humanizer_is_bundled_only_for_consumers(self):
        manifest = load_resource_manifest(ROOT / "resources/manifest.json")
        with tempfile.TemporaryDirectory() as tmp:
            for name in (
                "my-to-spec",
                "my-to-tickets",
                "my-grill-with-docs",
                "my-code-review",
                "my-humanizer",
            ):
                consumer = Path(tmp) / name
                consumer.mkdir()
                bundle_resources_for_skill(manifest, ROOT, name, consumer)
                self.assertTrue(
                    (consumer / "references/shared/humanizer.md").is_file(),
                    name,
                )

            other = Path(tmp) / "my-install"
            other.mkdir()
            bundle_resources_for_skill(manifest, ROOT, "my-install", other)
            self.assertFalse(
                (other / "references/shared/humanizer.md").exists()
            )

    def test_final_state_writing_is_bundled_only_for_consumers(self):
        manifest = load_resource_manifest(ROOT / "resources/manifest.json")
        direct_consumers = (
            "my-grilling",
            "my-grill-with-docs",
            "my-tech-design",
            "my-to-spec",
            "my-to-tickets",
            "my-codebase-design",
            "my-writing-great-skills",
        )
        consumers = direct_consumers + (
            "my-grill-me",
            "my-wayfinder",
            "my-improve-codebase-architecture",
        )
        with tempfile.TemporaryDirectory() as tmp:
            for name in consumers:
                target = Path(tmp) / name
                target.mkdir()
                bundle_resources_for_skill(manifest, ROOT, name, target)
                reference = target / "references/shared/final-state-writing.md"
                self.assertTrue(reference.is_file(), name)
                self.assertIn("最终产物只陈述当前有效", reference.read_text())
                if name in direct_consumers:
                    body = (ROOT / "skills" / name / "SKILL.md").read_text()
                    self.assertIn("references/shared/final-state-writing.md", body)

            other = Path(tmp) / "my-install"
            other.mkdir()
            bundle_resources_for_skill(manifest, ROOT, "my-install", other)
            self.assertFalse(
                (other / "references/shared/final-state-writing.md").exists()
            )

    def test_artifact_access_is_bundled_only_for_reader_consumers(self):
        manifest = load_resource_manifest(ROOT / "resources/manifest.json")
        with tempfile.TemporaryDirectory() as tmp:
            for skill in (
                "my-code-review",
                "my-wayfinder",
                "my-implement",
                "my-domain-modeling",
                "my-tdd",
                "my-diagnosing-bugs",
            ):
                with self.subTest(skill=skill):
                    reader = Path(tmp) / skill
                    reader.mkdir()
                    bundle_resources_for_skill(
                        manifest, ROOT, skill, reader
                    )
                    self.assertTrue(
                        (
                            reader
                            / "references/shared/adapters/artifact-access.md"
                        ).is_file()
                    )

            other = Path(tmp) / "my-install"
            other.mkdir()
            bundle_resources_for_skill(manifest, ROOT, "my-install", other)
            self.assertFalse(
                (
                    other
                    / "references/shared/adapters/artifact-access.md"
                ).exists()
            )

    def test_workflow_control_pointers_are_bundled_for_consumers(self):
        manifest = load_resource_manifest(ROOT / "resources/manifest.json")
        expectations = {
            "my-ask-matt": (
                "references/shared/adapters/composition.md",
                "references/policies/context-hygiene.md",
            ),
            "my-handoff": ("references/policies/context-hygiene.md",),
            "my-resolving-merge-conflicts": (
                "references/policies/merge-conflict-approval.md",
            ),
            "my-to-tickets": (
                "references/shared/adapters/ticket-selection.md",
            ),
            "my-triage": (
                "references/shared/adapters/ticket-selection.md",
            ),
            "my-wayfinder": (
                "references/shared/adapters/composition.md",
                "references/policies/decision-taxonomy.md",
            ),
        }

        with tempfile.TemporaryDirectory() as tmp:
            for skill, references in expectations.items():
                with self.subTest(skill=skill):
                    target = Path(tmp) / skill
                    target.mkdir()
                    bundle_resources_for_skill(manifest, ROOT, skill, target)
                    for reference in references:
                        self.assertTrue((target / reference).is_file())

    def test_policies_are_bundled_only_for_explicit_consumers(self):
        manifest = load_resource_manifest(ROOT / "resources/manifest.json")
        with tempfile.TemporaryDirectory() as tmp:
            for skill, policy in {
                "my-ask-matt": "context-hygiene.md",
                "my-handoff": "context-hygiene.md",
                "my-resolving-merge-conflicts": "merge-conflict-approval.md",
                "my-wayfinder": "decision-taxonomy.md",
            }.items():
                target = Path(tmp) / skill
                target.mkdir()
                bundle_resources_for_skill(manifest, ROOT, skill, target)
                self.assertTrue((target / "references/policies" / policy).is_file())

            for skill in ("my-install", "my-grilling", "my-grill-me"):
                target = Path(tmp) / skill
                target.mkdir()
                bundle_resources_for_skill(manifest, ROOT, skill, target)
                self.assertFalse((target / "references/policies").exists(), skill)

    def test_missing_resource_consumer_reports_source_and_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = root / "skills" / "my-a"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text(
                "---\n"
                "name: my-a\n"
                "description: test skill\n"
                "disable-model-invocation: true\n"
                "---\n\n"
                "[shared](references/shared/shared.md)\n"
            )
            other = root / "skills" / "my-other"
            other.mkdir()
            (other / "SKILL.md").write_text(
                "---\n"
                "name: my-other\n"
                "description: other test skill\n"
                "disable-model-invocation: true\n"
                "---\n"
            )
            resources = root / "resources"
            resources.mkdir()
            (resources / "shared.md").write_text("# Shared\n")
            (resources / "manifest.json").write_text(
                json.dumps(
                    {
                        "version": 1,
                        "resources": {
                            "shared": {
                                "source": "resources/shared.md",
                                "release_path": (
                                    "references/shared/shared.md"
                                ),
                                "consumers": ["my-other"],
                            }
                        },
                    }
                )
            )

            with self.assertRaisesRegex(
                ReleaseError,
                r"my-a.*SKILL\.md.*references/shared/shared\.md",
            ):
                validate_skills(root / "skills", repo_root=root)

    def test_static_validation_rejects_resource_symlink_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            root = workspace / "repo"
            skill = root / "skills" / "my-a"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text(
                "---\n"
                "name: my-a\n"
                "description: test skill\n"
                "disable-model-invocation: true\n"
                "---\n"
            )
            outside = workspace / "outside.md"
            outside.write_text("# Outside\n")
            resources = root / "resources"
            resources.mkdir()
            (resources / "leak.md").symlink_to(outside)
            (resources / "manifest.json").write_text(
                json.dumps(
                    {
                        "version": 1,
                        "resources": {
                            "leak": {
                                "source": "resources/leak.md",
                                "release_path": (
                                    "references/shared/leak.md"
                                ),
                                "consumers": ["my-a"],
                            }
                        },
                    }
                )
            )

            with self.assertRaisesRegex(
                ReleaseError, r"leak.*越界|越界.*leak"
            ):
                validate_skills(root / "skills", repo_root=root)

    def test_bundle_rejects_symlinked_file_outside_source_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            root = workspace / "repo"
            source = root / "resources" / "bundle"
            source.mkdir(parents=True)
            outside = workspace / "outside.md"
            outside.write_text("# Outside\n")
            (source / "leak.md").symlink_to(outside)
            (root / "resources/manifest.json").write_text(
                json.dumps(
                    {
                        "version": 1,
                        "resources": {
                            "bundle": {
                                "source_dir": "resources/bundle",
                                "release_path": "references/shared",
                                "consumers": ["my-a"],
                            }
                        },
                    }
                )
            )
            target = workspace / "target"
            target.mkdir()
            manifest = load_resource_manifest(
                root / "resources/manifest.json"
            )

            from tools.workflow_lib.resources import ResourceError

            with self.assertRaisesRegex(
                ResourceError, r"leak.*越界|越界.*leak"
            ):
                bundle_resources_for_skill(
                    manifest, root, "my-a", target
                )
