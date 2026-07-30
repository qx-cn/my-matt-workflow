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
            consumer = Path(tmp) / "my-to-spec"
            consumer.mkdir()
            bundle_resources_for_skill(
                manifest, ROOT, "my-to-spec", consumer
            )
            self.assertTrue(
                (consumer / "references/shared/humanizer.md").is_file()
            )

            other = Path(tmp) / "my-install"
            other.mkdir()
            bundle_resources_for_skill(manifest, ROOT, "my-install", other)
            self.assertFalse(
                (other / "references/shared/humanizer.md").exists()
            )

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
