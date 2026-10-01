import json
import re
import tempfile
import unittest
from pathlib import Path

from tools.workflow_lib.composition import (
    CompositionError,
    CompositionManifest,
    DependencyEdge,
    load_composition_manifest,
    resolve_transitive_closure,
    validate_composition_manifest,
)
from tools.workflow_lib.release import (
    ReleaseError,
    _validate_staged_references,
    build_release,
    validate_skills,
)


ROOT = Path(__file__).resolve().parents[1]


class CompositionManifestTests(unittest.TestCase):
    def test_manifest_declares_implement_dependencies(self):
        manifest = load_composition_manifest(ROOT / "composition/manifest.json")
        self.assertEqual(
            {"my-tdd", "my-code-review"},
            {edge.skill for edge in manifest.callers["my-implement"]},
        )
        self.assertEqual(
            {"method"},
            {edge.kind for edge in manifest.callers["my-implement"]},
        )
        self.assertEqual(
            "handoff",
            next(
                edge.kind
                for edge in manifest.callers["my-wayfinder"]
                if edge.skill == "my-to-spec"
            ),
        )
        design_edge = next(
            edge
            for edge in manifest.callers["my-review-artifact"]
            if edge.skill == "my-review-design"
        )
        self.assertEqual("method", design_edge.kind)
        self.assertEqual("design-artifact", design_edge.when)

    def test_cycle_is_rejected_with_path(self):
        manifest = CompositionManifest(
            version=2,
            callers={
                "my-a": (DependencyEdge("my-b", "always", "method"),),
                "my-b": (DependencyEdge("my-a", "always", "method"),),
            },
            routable_entries={},
        )
        with tempfile.TemporaryDirectory() as tmp:
            skills = Path(tmp)
            for name in ("my-a", "my-b"):
                (skills / name).mkdir()
            with self.assertRaisesRegex(
                CompositionError, r"my-a.*my-b|my-b.*my-a"
            ):
                validate_composition_manifest(manifest, skills)

    def test_routing_is_not_a_call_edge(self):
        """Router A → entry B via routable_entries, B → A via callers."""
        manifest = CompositionManifest(
            version=2,
            callers={
                "my-b": (DependencyEdge("my-a", "always", "method"),),
            },
            routable_entries={
                "my-a": ("my-b",),
            },
        )
        with tempfile.TemporaryDirectory() as tmp:
            skills = Path(tmp)
            for name in ("my-a", "my-b"):
                (skills / name).mkdir()
            validate_composition_manifest(manifest, skills)

    def test_unknown_dependency_reports_caller_and_target(self):
        manifest = CompositionManifest(
            version=2,
            callers={
                "my-a": (DependencyEdge("my-missing", "always", "method"),),
            },
            routable_entries={},
        )
        with tempfile.TemporaryDirectory() as tmp:
            skills = Path(tmp)
            (skills / "my-a").mkdir()
            with self.assertRaisesRegex(
                CompositionError, r"my-a.*my-missing"
            ):
                validate_composition_manifest(manifest, skills)

    def test_transitive_closure_is_deterministic(self):
        manifest = load_composition_manifest(ROOT / "composition/manifest.json")
        self.assertEqual(
            [
                "my-codebase-design",
                "my-domain-modeling",
                "my-grilling",
                    ],
            resolve_transitive_closure(
                manifest, "my-improve-codebase-architecture"
            ),
        )

    def test_manifest_rejects_unknown_dependency_kind(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.json"
            path.write_text(
                json.dumps(
                    {
                        "version": 2,
                        "callers": {
                            "my-a": [
                                {"skill": "my-b", "when": "always", "kind": "magic"}
                            ]
                        },
                        "routable_entries": {},
                    }
                )
            )
            with self.assertRaisesRegex(CompositionError, "kind"):
                load_composition_manifest(path)




class CompositionValidationTests(unittest.TestCase):
    @staticmethod
    def _skill(root: Path, name: str, body: str = "") -> Path:
        skill = root / "skills" / name
        skill.mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            "---\n"
            f"name: {name}\n"
            "description: test skill\n"
            "disable-model-invocation: true\n"
            "---\n\n"
            f"{body}"
        )
        return skill

    def test_undeclared_generated_pointer_reports_source_and_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._skill(
                root,
                "my-a",
                "[dependency](references/composed/my-b/SKILL.md)\n",
            )
            self._skill(root, "my-b")
            composition = root / "composition"
            composition.mkdir()
            (composition / "manifest.json").write_text(
                json.dumps(
                    {
                        "version": 2,
                        "callers": {},
                        "routable_entries": {},
                    }
                )
            )

            with self.assertRaisesRegex(
                ReleaseError,
                r"my-a.*SKILL\.md.*references/composed/my-b/SKILL\.md",
            ):
                validate_skills(root / "skills", repo_root=root)

    def test_staged_tree_rejects_broken_markdown_link_with_fragment(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._skill(root, "my-a", "[support](support.md#usage)\n")

            with self.assertRaisesRegex(
                ReleaseError, r"my-a.*SKILL\.md.*support\.md#usage"
            ):
                build_release(
                    root / "skills",
                    root / "releases",
                    release_id="v1",
                    upstream_id="test",
                )


    def test_source_validation_scans_support_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = self._skill(root, "my-a")
            (skill / "SUPPORT.md").write_text(
                "[undeclared](references/composed/my-b/SKILL.md)\n"
            )
            (skill / "SKILL.md").write_text(
                (skill / "SKILL.md").read_text() + "[support](SUPPORT.md)\n"
            )
            self._skill(root, "my-b")
            composition = root / "composition"
            composition.mkdir()
            (composition / "manifest.json").write_text(
                json.dumps(
                    {
                        "version": 2,
                        "callers": {},
                        "routable_entries": {},
                    }
                )
            )

            with self.assertRaisesRegex(
                ReleaseError,
                r"my-a.*SUPPORT\.md.*references/composed/my-b/SKILL\.md",
            ):
                validate_skills(root / "skills", repo_root=root)




    def test_build_rejects_source_skill_symlink_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            root = workspace / "repo"
            skill = self._skill(root, "my-a")
            outside = workspace / "outside.txt"
            outside.write_text("outside")
            (skill / "leak.txt").symlink_to(outside)

            with self.assertRaisesRegex(
                ReleaseError, r"my-a.*leak\.txt.*越界|my-a.*越界.*leak"
            ):
                build_release(
                    root / "skills",
                    root / "releases",
                    release_id="v1",
                    upstream_id="test",
                )
