import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.workflow_lib.resources import (
    bundle_resources_for_skill,
    load_resource_manifest,
)
from tools.workflow_lib.composition import load_composition_manifest
from tools.workflow_lib.resource_governance import (
    ResourceGovernanceError,
    validate_resource_governance,
)
from tools.workflow_lib.release import (
    ReleaseError,
    resource_consumer_maps,
    validate_skills,
)


ROOT = Path(__file__).resolve().parents[1]


class SharedResourceTests(unittest.TestCase):
    def _effective_consumers(self):
        resources = load_resource_manifest(ROOT / "resources/manifest.json")
        composition = load_composition_manifest(
            ROOT / "composition/manifest.json"
        )
        skills = {path.name for path in (ROOT / "skills").iterdir() if path.is_dir()}
        return resource_consumer_maps(resources, skills, composition, ROOT)[1]

    def test_artifact_finalization_gate_is_shared_by_spec_handoff_and_review(self):
        manifest = json.loads((ROOT / "resources/manifest.json").read_text())
        entry = manifest["resources"]["artifact-finalization"]
        self.assertEqual(
            "resources/artifact-finalization.md",
            entry["source"],
        )
        self.assertEqual(
            {
                "my-to-spec",
                "my-handoff",
                "my-final-state-writing",
                "my-artifact-finalization",
            },
            set(entry["consumers"]),
        )
        text = (ROOT / entry["source"]).read_text()
        for gate in ("来源账本", "内部一致性", "读者重建", "事实正确性"):
            self.assertIn(gate, text)

    def test_every_shared_document_has_a_reviewer_or_validation(self):
        manifest = load_resource_manifest(ROOT / "resources/manifest.json")
        validate_resource_governance(
            ROOT,
            manifest,
            ROOT / "resources/governance.json",
        )

    def test_unregistered_shared_markdown_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(ROOT / "resources", root / "resources")
            shutil.copytree(ROOT / "policies", root / "policies")
            shutil.copytree(ROOT / "skills", root / "skills")
            (root / "resources/new-rule.md").write_text("# New rule\n")
            manifest = load_resource_manifest(root / "resources/manifest.json")
            with self.assertRaisesRegex(
                ResourceGovernanceError,
                "resources/new-rule.md",
            ):
                validate_resource_governance(
                    root,
                    manifest,
                    root / "resources/governance.json",
                )

    def test_write_only_skill_cannot_satisfy_review_governance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(ROOT / "resources", root / "resources")
            shutil.copytree(ROOT / "policies", root / "policies")
            shutil.copytree(ROOT / "skills", root / "skills")
            skill = root / "skills/my-final-state-writing/SKILL.md"
            skill.write_text(skill.read_text().replace("只读", "读取"))
            manifest = load_resource_manifest(root / "resources/manifest.json")
            with self.assertRaisesRegex(
                ResourceGovernanceError,
                "未声明只读 review 能力",
            ):
                validate_resource_governance(
                    root,
                    manifest,
                    root / "resources/governance.json",
                )

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
        direct_consumers = tuple(
            manifest.resources["final-state-writing"].consumers
        )
        effective = self._effective_consumers()
        consumers = tuple(sorted(effective["final-state-writing"]))
        with tempfile.TemporaryDirectory() as tmp:
            for name in consumers:
                target = Path(tmp) / name
                target.mkdir()
                bundle_resources_for_skill(
                    manifest,
                    ROOT,
                    name,
                    target,
                    effective_consumers=effective,
                )
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


    def test_visual_communication_is_bundled_only_for_human_facing_consumers(self):
        manifest = load_resource_manifest(ROOT / "resources/manifest.json")
        consumers = (
            "my-visual-communication",
            "my-teach",
            "my-test-report",
        )
        with tempfile.TemporaryDirectory() as tmp:
            for name in consumers:
                target = Path(tmp) / name
                target.mkdir()
                bundle_resources_for_skill(manifest, ROOT, name, target)
                reference = target / "references/shared/visual-communication.md"
                self.assertTrue(reference.is_file(), name)
                self.assertIn("图只回答一个核心问题", reference.read_text())
                self.assertIn("字溢出、叠字、遮挡", reference.read_text())
                skill = ROOT / "skills" / name
                body = (skill / "SKILL.md").read_text()
                if name == "my-teach":
                    body += (skill / "CONTENT.md").read_text()
                    body += (skill / "FRONTEND.md").read_text()
                self.assertIn("references/shared/visual-communication.md", body)

            other = Path(tmp) / "my-install"
            other.mkdir()
            bundle_resources_for_skill(manifest, ROOT, "my-install", other)
            self.assertFalse(
                (other / "references/shared/visual-communication.md").exists()
            )

            design = Path(tmp) / "my-review-design"
            design.mkdir()
            bundle_resources_for_skill(manifest, ROOT, "my-review-design", design)
            self.assertFalse(
                (design / "references/shared/visual-communication.md").exists()
            )

    def test_reader_first_and_document_rendering_resources_are_scoped(self):
        manifest = load_resource_manifest(ROOT / "resources/manifest.json")
        with tempfile.TemporaryDirectory() as tmp:
            for name in ("my-edit-article", "my-research", "my-test-report"):
                target = Path(tmp) / name
                target.mkdir()
                bundle_resources_for_skill(manifest, ROOT, name, target)
                self.assertTrue((target / "references/shared/reader-first-writing.md").is_file())
                self.assertFalse((target / "references/shared/document-rendering.md").exists())
            for name in ("my-tech-design", "my-improve-codebase-architecture", "my-teach"):
                target = Path(tmp) / f"render-{name}"
                target.mkdir()
                bundle_resources_for_skill(manifest, ROOT, name, target)
                self.assertTrue((target / "references/shared/reader-first-writing.md").is_file())
                self.assertTrue((target / "references/shared/document-rendering.md").is_file())

        reader_rule = (ROOT / "resources/reader-first-writing.md").read_text()
        self.assertIn("用户与 AI 的讨论", reader_rule)
        self.assertIn("主要读者是人、Agent 还是两者", reader_rule)
        self.assertIn("不得仅为记录制作过程而原样残留", reader_rule)
        self.assertIn("面向 Agent 的工件可以保留可执行状态", reader_rule)
        self.assertIn("原始提示词只有本身就是目标 Agent 必须执行的指令", reader_rule)
        self.assertIn("结构化元数据或独立交接工件", reader_rule)

    def test_artifact_access_is_bundled_only_for_reader_consumers(self):
        manifest = load_resource_manifest(ROOT / "resources/manifest.json")
        effective = self._effective_consumers()
        with tempfile.TemporaryDirectory() as tmp:
            for skill in (
                "my-code-review",
                "my-review-design",
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
                        manifest,
                        ROOT,
                        skill,
                        reader,
                        effective_consumers=effective,
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
            "my-implement": (
                "references/shared/adapters/implementation-session.md",
            ),
            "my-review-artifact": (
                "references/shared/adapters/artifact-review-session.md",
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

    def test_instruction_authority_is_bundled_for_decision_callers(self):
        manifest = load_resource_manifest(ROOT / "resources/manifest.json")
        with tempfile.TemporaryDirectory() as tmp:
            for skill in (
                "my-code-review",
                "my-diagnosing-bugs",
                "my-domain-modeling",
                "my-edit-article",
                "my-to-tickets",
            ):
                target = Path(tmp) / skill
                target.mkdir()
                bundle_resources_for_skill(manifest, ROOT, skill, target)
                authority = target / "references/shared/instruction-authority.md"
                self.assertTrue(authority.is_file(), skill)
                self.assertIn("decision-gate", authority.read_text())

    def test_policies_are_bundled_only_for_explicit_consumers(self):
        manifest = load_resource_manifest(ROOT / "resources/manifest.json")
        effective = self._effective_consumers()
        with tempfile.TemporaryDirectory() as tmp:
            for skill, policy in {
                "my-ask-matt": "context-hygiene.md",
                "my-handoff": "context-hygiene.md",
                "my-resolving-merge-conflicts": "merge-conflict-approval.md",
                "my-wayfinder": "decision-taxonomy.md",
            }.items():
                target = Path(tmp) / skill
                target.mkdir()
                bundle_resources_for_skill(
                    manifest,
                    ROOT,
                    skill,
                    target,
                    effective_consumers=effective,
                )
                self.assertTrue((target / "references/policies" / policy).is_file())

            for skill in ("my-install", "my-grilling", "my-grill-me"):
                target = Path(tmp) / skill
                target.mkdir()
                bundle_resources_for_skill(manifest, ROOT, skill, target)
                self.assertFalse((target / "references/policies").exists(), skill)

    def test_direct_consumers_are_exact_and_effective_consumers_are_derived(self):
        manifest = load_resource_manifest(ROOT / "resources/manifest.json")
        composition = load_composition_manifest(
            ROOT / "composition/manifest.json"
        )
        skills = {path.name for path in (ROOT / "skills").iterdir() if path.is_dir()}
        direct, effective = resource_consumer_maps(
            manifest, skills, composition, ROOT
        )

        self.assertEqual({"my-tdd"}, direct["adapter-work-scope"])
        self.assertTrue(
            {"my-implement", "my-prototype", "my-wayfinder"}
            <= effective["adapter-work-scope"]
        )
        self.assertNotIn("my-triage", direct["adapter-write-actions"])
        self.assertIn("my-triage", effective["adapter-write-actions"])
        self.assertIn("my-to-spec", effective["instruction-authority"])

        validate_skills(ROOT / "skills", repo_root=ROOT)

    def test_direct_consumer_without_source_reference_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shutil.copytree(ROOT / "skills", root / "skills")
            shutil.copytree(ROOT / "resources", root / "resources")
            shutil.copytree(ROOT / "policies", root / "policies")
            shutil.copytree(ROOT / "composition", root / "composition")
            raw = json.loads((root / "resources/manifest.json").read_text())
            raw["resources"]["adapter-work-scope"]["consumers"].append(
                "my-install"
            )
            (root / "resources/manifest.json").write_text(json.dumps(raw))

            with self.assertRaisesRegex(ReleaseError, "无直接引用.*my-install"):
                validate_skills(root / "skills", repo_root=root)

    def test_resource_dependency_parser_supports_titles_angles_and_fragments(self):
        for link in ('[B](b.md "details")', '[B](<b.md#section>)'):
            with self.subTest(link=link), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                resources = root / "resources"
                resources.mkdir()
                (resources / "a.md").write_text(link + "\n")
                (resources / "b.md").write_text("# B\n")
                (resources / "manifest.json").write_text(json.dumps({
                    "version": 1,
                    "resources": {
                        "a": {
                            "source": "resources/a.md",
                            "release_path": "references/shared/a.md",
                            "consumers": ["my-a"],
                        },
                        "b": {
                            "source": "resources/b.md",
                            "release_path": "references/shared/b.md",
                            "consumers": ["my-b"],
                        },
                    },
                }))
                manifest = load_resource_manifest(resources / "manifest.json")
                _, effective = resource_consumer_maps(
                    manifest, {"my-a", "my-b"}, None, root
                )
                self.assertIn("my-a", effective["b"])

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
                r"shared.*未声明.*my-a.*无直接引用.*my-other",
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
