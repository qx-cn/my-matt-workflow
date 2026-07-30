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

from tools.workflow_lib.doctor import (
    SnapshotError,
    compare_snapshots,
    snapshot_tree,
    snapshot_mapped_tree,
    discover_unmapped_skills,
    validate_upstream_snapshot,
)
from tools.workflow_lib.installer import (
    InstallError,
    install_release,
    recover_interrupted_install,
    verify_release,
)
from tools.workflow_lib.work_artifacts import analyze_work_artifacts
from tools.workflow_lib.profile import (
    POLICY_PRESETS,
    PROFILE_FIELD_ORDER,
    ProfileError,
    apply_personal_ignores,
    effective_profile,
    format_policy_catalog,
    get_policy_preset,
    merge_profile,
    parse_profile,
    render_profile,
    resolve_preset_name,
)
from tools.workflow_lib.recommendations import build_recommendation_report
from tools.workflow_lib.release import ReleaseError, build_release, validate_skills
from tools.workflow_lib.sync import build_review_bundle


class ProfileTests(unittest.TestCase):
    def test_ask_matt_routes_with_composed_and_manual_branches(self):
        text = (
            Path(__file__).resolve().parents[1]
            / "skills/my-ask-matt/SKILL.md"
        ).read_text()
        for skill_name in (
            "my-grill-with-docs",
            "my-grill-me",
            "my-triage",
            "my-implement",
            "my-wayfinder",
            "my-diagnosing-bugs",
        ):
            with self.subTest(skill=skill_name):
                self.assertIn(
                    f"references/composed/{skill_name}/SKILL.md", text
                )
        self.assertIn("Cursor / Claude", text)
        self.assertIn("Codex", text)
        self.assertIn("停止", text)

    def test_consumers_point_to_generated_resources(self):
        root = Path(__file__).resolve().parents[1] / "skills"
        for skill in (
            "my-to-spec",
            "my-to-tickets",
            "my-grill-with-docs",
            "my-code-review",
        ):
            text = (root / skill / "SKILL.md").read_text()
            with self.subTest(skill=skill):
                self.assertIn("references/shared/humanizer.md", text)
                self.assertNotIn("../my-to-spec/humanizer.md", text)

    def test_implement_has_composed_and_manual_branches(self):
        text = (
            Path(__file__).resolve().parents[1]
            / "skills/my-implement/SKILL.md"
        ).read_text()
        self.assertIn("references/composed/my-tdd/SKILL.md", text)
        self.assertIn("Cursor / Claude", text)
        self.assertIn("Codex", text)

    def test_implement_stops_for_user_selected_inadmissible_ticket(self):
        text = (
            Path(__file__).resolve().parents[1]
            / "skills/my-implement/SKILL.md"
        ).read_text()
        self.assertIn("用户指定", text)
        self.assertIn("不满足准入", text)
        self.assertIn("停止", text)
        self.assertIn("不得静默改选", text)
        self.assertIn("明确确认", text)

    def test_round_trips_supported_profile(self):
        config = {
            "schema_version": 1,
            "task_backend": "local",
            "default_base_branch": "main",
            "branch_policy": "confirm",
            "commit_policy": "confirm",
            "external_write_policy": "confirm",
            "docs_writeback": "confirm",
            "humanizer_policy": "deny",
            "composition_policy": "manual",
            "work_scope_policy": "single-ticket",
            "decision_policy": "ask",
            "test_commands": ["python3 -m unittest"],
            "standards_sources": [],
            "domain_sources": [],
        }

        rendered = render_profile(config, "# 项目说明\n\n遵守仓库规则。")
        parsed, notes = parse_profile(rendered)

        self.assertEqual(config, parsed)
        self.assertEqual("# 项目说明\n\n遵守仓库规则。", notes)

    def test_rejects_unknown_schema_version(self):
        text = "---\nschema_version: 2\ntask_backend: local\n---\n"

        with self.assertRaisesRegex(ProfileError, "schema_version"):
            parse_profile(text)

    def test_rejects_invalid_policy(self):
        text = (
            "---\n"
            "schema_version: 1\n"
            "task_backend: local\n"
            "branch_policy: always\n"
            "---\n"
        )

        with self.assertRaisesRegex(ProfileError, "branch_policy"):
            parse_profile(text)

    def test_refresh_preserves_existing_values_without_override(self):
        existing = {
            "schema_version": 1,
            "task_backend": "external",
            "default_base_branch": "develop",
            "branch_policy": "confirm",
            "commit_policy": "confirm",
            "external_write_policy": "confirm",
            "docs_writeback": "confirm",
            "test_commands": ["make test"],
            "standards_sources": ["AGENTS.md"],
            "domain_sources": ["docs/domain.md"],
            "composition_policy": "manual",
            "work_scope_policy": "single-ticket",
            "decision_policy": "ask",
        }

        merged = merge_profile(existing, {"default_base_branch": "main"})

        self.assertEqual("external", merged["task_backend"])
        self.assertEqual(["make test"], merged["test_commands"])
        self.assertEqual(["AGENTS.md"], merged["standards_sources"])
        self.assertEqual("main", merged["default_base_branch"])

    def test_refresh_can_switch_composition_without_losing_other_settings(self):
        existing = {
            "schema_version": 1,
            "task_backend": "local",
            "composition_policy": "manual",
            "branch_policy": "confirm",
        }
        refreshed = merge_profile(existing, {"composition_policy": "automatic"})
        self.assertEqual("automatic", refreshed["composition_policy"])
        self.assertEqual("local", refreshed["task_backend"])

    def test_profile_accepts_autonomous_plan_scope(self):
        config = {
            "schema_version": 1,
            "task_backend": "local",
            "composition_policy": "automatic",
            "work_scope_policy": "approved-plan",
            "decision_policy": "autonomous",
        }
        parsed, _ = parse_profile(render_profile(config))
        self.assertEqual("automatic", parsed["composition_policy"])
        self.assertEqual("approved-plan", parsed["work_scope_policy"])
        self.assertEqual("autonomous", parsed["decision_policy"])
        self.assertEqual(effective_profile(config), parsed)

    def test_missing_autonomy_policies_resolve_to_strict_control(self):
        text = "---\nschema_version: 1\ntask_backend: local\n---\n"
        config, _ = parse_profile(text)
        effective = effective_profile(config)

        self.assertEqual("manual", effective["composition_policy"])
        self.assertEqual("single-ticket", effective["work_scope_policy"])
        self.assertEqual("ask", effective["decision_policy"])
        self.assertEqual("deny", effective["humanizer_policy"])
        self.assertEqual("confirm", effective["branch_policy"])
        self.assertEqual("confirm", effective["commit_policy"])
        self.assertNotEqual("approved-plan", effective["work_scope_policy"])
        self.assertNotEqual("autonomous", effective["decision_policy"])

    def test_empty_autonomy_policies_resolve_to_strict_control(self):
        text = (
            "---\n"
            "schema_version: 1\n"
            "task_backend: local\n"
            "composition_policy:\n"
            'work_scope_policy: ""\n'
            "decision_policy: ''\n"
            "---\n"
        )
        config, _ = parse_profile(text)
        effective = effective_profile(config)

        self.assertEqual(POLICY_PRESETS["strict-control"]["composition_policy"], effective["composition_policy"])
        self.assertEqual("single-ticket", effective["work_scope_policy"])
        self.assertEqual("deny", effective["humanizer_policy"])

    def test_continue_semantics_do_not_widen_work_scope_in_skills(self):
        root = Path(__file__).resolve().parents[1] / "skills"
        for skill in ("my-implement", "my-ask-matt"):
            text = (root / skill / "SKILL.md").read_text()
            with self.subTest(skill=skill):
                self.assertIn("继续", text)
                self.assertIn("不升档", text)
                self.assertIn("work_scope_policy", text)
        # Restored upstream skills preserve their source method without a local policy footer.
        teach = (root / "my-teach" / "SKILL.md").read_text()
        self.assertNotIn("项目策略优先", teach)
        self.assertNotIn("已解析生效策略", teach)

    def test_render_makes_every_known_key_explicit_including_defaults(self):
        rendered = render_profile({"schema_version": 1, "task_backend": "local"})
        for key in PROFILE_FIELD_ORDER:
            self.assertRegex(rendered, rf"(?m)^{re.escape(key)}: ")
        self.assertIn("humanizer_policy: deny", rendered)
        self.assertIn("work_scope_policy: single-ticket", rendered)

    def test_refresh_without_overrides_keeps_explicit_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            profile = repo / ".agent" / "matt-workflow.md"
            profile.parent.mkdir(parents=True)
            profile.write_text(
                render_profile(
                    {
                        "schema_version": 1,
                        "task_backend": "local",
                        "composition_policy": "automatic",
                        "commit_policy": "allow",
                        "humanizer_policy": "confirm",
                    }
                )
            )
            before_keys = {
                line.split(":", 1)[0]
                for line in profile.read_text().splitlines()
                if ":" in line and not line.lstrip().startswith("#") and line != "---"
            }

            subprocess.run(
                [
                    "python3",
                    "tools/workflow.py",
                    "refresh-project",
                    "--repo",
                    str(repo),
                ],
                cwd=Path(__file__).resolve().parents[1],
                check=True,
                capture_output=True,
                text=True,
            )

            after = profile.read_text()
            after_keys = {
                line.split(":", 1)[0]
                for line in after.splitlines()
                if ":" in line and not line.lstrip().startswith("#") and line != "---"
            }
            self.assertTrue(set(PROFILE_FIELD_ORDER) <= after_keys)
            self.assertTrue(before_keys <= after_keys)
            self.assertIn("composition_policy: automatic", after)
            self.assertIn("commit_policy: allow", after)
            self.assertIn("humanizer_policy: confirm", after)

    def test_five_presets_match_spec_including_humanizer_defaults(self):
        expected = {
            "strict-control": {
                "composition_policy": "manual",
                "work_scope_policy": "single-ticket",
                "decision_policy": "ask",
                "commit_policy": "confirm",
                "humanizer_policy": "deny",
            },
            "light-control": {
                "composition_policy": "automatic",
                "work_scope_policy": "single-ticket",
                "decision_policy": "ask",
                "commit_policy": "confirm",
                "humanizer_policy": "confirm",
            },
            "review": {
                "composition_policy": "automatic",
                "work_scope_policy": "single-ticket",
                "decision_policy": "ask",
                "commit_policy": "allow",
                "humanizer_policy": "confirm",
            },
            "semi-auto": {
                "composition_policy": "automatic",
                "work_scope_policy": "ready-frontier",
                "decision_policy": "ask",
                "commit_policy": "allow",
                "humanizer_policy": "confirm",
            },
            "full-auto": {
                "composition_policy": "automatic",
                "work_scope_policy": "approved-plan",
                "decision_policy": "autonomous",
                "branch_policy": "allow",
                "commit_policy": "allow",
                "external_write_policy": "allow",
                "docs_writeback": "allow",
                "humanizer_policy": "allow",
            },
        }
        self.assertEqual(set(expected), set(POLICY_PRESETS))
        for name, fields in expected.items():
            with self.subTest(preset=name):
                for key, value in fields.items():
                    self.assertEqual(value, POLICY_PRESETS[name][key])

        self.assertEqual("strict-control", resolve_preset_name("supervised"))
        self.assertEqual("full-auto", resolve_preset_name("unattended"))
        self.assertEqual(
            POLICY_PRESETS["strict-control"], get_policy_preset("supervised")
        )
        self.assertEqual(POLICY_PRESETS["full-auto"], get_policy_preset("unattended"))
        self.assertNotIn("guided", POLICY_PRESETS)

        light = POLICY_PRESETS["light-control"]
        strict = POLICY_PRESETS["strict-control"]
        review = POLICY_PRESETS["review"]
        self.assertEqual(strict["work_scope_policy"], light["work_scope_policy"])
        self.assertNotEqual(strict["composition_policy"], light["composition_policy"])
        self.assertEqual(light["composition_policy"], review["composition_policy"])
        self.assertEqual("allow", review["commit_policy"])
        self.assertEqual("confirm", light["commit_policy"])

    def test_setup_can_apply_each_canonical_preset(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            first = True
            for preset in POLICY_PRESETS:
                command = [
                    "python3",
                    "tools/workflow.py",
                    "setup",
                    "--repo",
                    str(repo),
                    "--preset",
                    preset,
                    "--apply",
                ]
                if not first:
                    command.append("--refresh")
                result = subprocess.run(
                    command,
                    cwd=Path(__file__).resolve().parents[1],
                    capture_output=True,
                    text=True,
                    check=True,
                )
                first = False
                written = (repo / ".agent" / "matt-workflow.md").read_text()
                for key, value in POLICY_PRESETS[preset].items():
                    self.assertIn(f"{key}: {value}", written)
                self.assertIn("strict-control", result.stdout)
                self.assertIn("light-control", result.stdout)
                self.assertIn("semi-auto", result.stdout)
                self.assertIn("full-auto", result.stdout)

    def test_rendered_profile_documents_five_presets_not_only_old_poles(self):
        rendered = render_profile(get_policy_preset("strict-control") | {
            "schema_version": 1,
            "task_backend": "local",
        })
        for name in (
            "strict-control",
            "light-control",
            "review",
            "semi-auto",
            "full-auto",
        ):
            self.assertIn(name, rendered)
        self.assertIn("strict-control（默认）", rendered)
        self.assertIn("supervised→strict-control", rendered)
        self.assertIn("unattended→full-auto", rendered)
        self.assertIn("不升档", rendered)

    def test_policy_catalog_covers_keys_and_matches_validation_rejects(self):
        catalog = format_policy_catalog()
        for key in PROFILE_FIELD_ORDER:
            self.assertIn(key, catalog)
        for name in POLICY_PRESETS:
            self.assertIn(name, catalog)
        self.assertIn("高级用法", catalog)
        self.assertIn("ready-frontier", catalog)

        with self.assertRaisesRegex(ProfileError, "humanizer_policy"):
            parse_profile(
                "---\n"
                "schema_version: 1\n"
                "task_backend: local\n"
                "humanizer_policy: rewrite\n"
                "---\n"
            )
        with self.assertRaisesRegex(ProfileError, "work_scope_policy"):
            parse_profile(
                "---\n"
                "schema_version: 1\n"
                "task_backend: local\n"
                "work_scope_policy: everything\n"
                "---\n"
            )

    def test_skills_keep_slim_policy_footer_and_local_preset_docs(self):
        root = Path(__file__).resolve().parents[1] / "skills"
        restored_without_policy_footer = {
            "my-to-questionnaire",
            "my-writing-great-skills",
            "my-triage",
            "my-teach",
            "my-improve-codebase-architecture",
            "my-wizard",
        }
        for skill_file in root.glob("my-*/SKILL.md"):
            text = skill_file.read_text()
            with self.subTest(skill=skill_file.parent.name):
                if skill_file.parent.name in restored_without_policy_footer:
                    self.assertNotIn("项目策略优先", text)
                    continue
                self.assertIn("已解析生效策略", text)
                self.assertIn("strict-control", text)
                self.assertNotRegex(
                    text,
                    r"均是 `supervised` 默认行为；`unattended` 项目",
                )

        setup = (root / "my-setup" / "SKILL.md").read_text()
        for name in (
            "strict-control",
            "light-control",
            "review",
            "semi-auto",
            "full-auto",
        ):
            self.assertIn(name, setup)
        self.assertIn("format_policy_catalog()", setup)

        diagnosing = (root / "my-diagnosing-bugs" / "SKILL.md").read_text()
        self.assertIn("decision_policy", diagnosing)
        self.assertNotIn("在 `supervised` 项目中", diagnosing)
        self.assertNotIn("在 `unattended` 项目中", diagnosing)

    def test_humanizer_policy_source_of_truth_freezes_contracts(self):
        sot = (
            Path(__file__).resolve().parents[1]
            / "resources"
            / "humanizer.md"
        ).read_text()
        self.assertIn("humanizer_policy", sot)
        self.assertIn("`deny`", sot)
        self.assertIn("`confirm`", sot)
        self.assertIn("`allow`", sot)
        self.assertIn("/humanizer", sot)
        self.assertIn("叙述段", sot)
        self.assertIn("契约段", sot)
        self.assertIn("必须 / 不得", sot)
        self.assertIn("验收条目", sot)
        self.assertIn("未确认不得", sot)
        self.assertRegex(sot, r"不主动|跳过主动")
        self.assertIn("Agent 执行偏离", sot)

    def test_doc_generation_skills_point_to_humanizer_at_write_step(self):
        root = Path(__file__).resolve().parents[1] / "skills"
        expectations = {
            "my-to-spec": (
                "[humanizer](references/shared/humanizer.md)",
                "写入前",
            ),
            "my-to-tickets": (
                "[humanizer](references/shared/humanizer.md)",
                "写入前",
            ),
            "my-grill-with-docs": (
                "[humanizer](references/shared/humanizer.md)",
                "最终确认后",
            ),
        }
        for skill, (pointer, timing) in expectations.items():
            text = (root / skill / "SKILL.md").read_text()
            with self.subTest(skill=skill):
                self.assertIn("humanizer_policy", text)
                self.assertIn(pointer, text)
                self.assertIn(timing, text)
                self.assertNotIn("## humanizer", text)

    def test_code_review_skill_covers_comments_naming_and_humanizer_policy(self):
        text = (
            Path(__file__).resolve().parents[1]
            / "skills"
            / "my-code-review"
            / "SKILL.md"
        ).read_text()
        self.assertIn("### 注释", text)
        self.assertIn("### 命名", text)
        self.assertIn("代码行为", text)
        self.assertIn("Spec", text)
        self.assertRegex(text, r"ADR|相关文档")
        self.assertIn("humanizer_policy", text)
        self.assertIn(
            "[humanizer](references/shared/humanizer.md)", text
        )
        self.assertRegex(text, r"领域用语|简短")
        self.assertIn("函数", text)
        self.assertIn("变量", text)
        self.assertIn("Mysterious Name", text)


class GitIgnoreTests(unittest.TestCase):
    def test_non_git_project_keeps_agent_directory_without_gitignore(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)

            added, conflicts = apply_personal_ignores(project)

            self.assertEqual([], added)
            self.assertEqual([], conflicts)
            self.assertFalse((project / ".gitignore").exists())


class WorkArtifactTests(unittest.TestCase):
    def test_main_workflow_skills_use_the_canonical_work_artifact_layout(self):
        root = Path(__file__).resolve().parents[1] / "skills"
        expectations = {
            "my-grill-with-docs": ".agent/work/<topic>/grills/",
            "my-to-spec": ".agent/work/<feature-slug>/specs/",
            "my-to-tickets": ".agent/work/<feature-slug>/tickets/tickets-",
            "my-wayfinder": ".agent/work/<initiative>/wayfinders/",
            "my-prototype": ".agent/work/<feature>/prototypes/",
            "my-ask-matt": ".agent/work/<feature>/tickets/tickets-",
        }

        for skill, canonical_path in expectations.items():
            with self.subTest(skill=skill):
                self.assertIn(canonical_path, (root / skill / "SKILL.md").read_text())

    def test_supporting_workflow_skills_use_topic_type_artifact_layouts(self):
        root = Path(__file__).resolve().parents[1] / "skills"
        expectations = {
            "my-handoff": ".agent/work/<topic>/handoffs/",
            "my-research": ".agent/work/<topic>/researches/",
            "my-domain-modeling": ".agent/work/<topic>/domain/",
        }

        for skill, canonical_path in expectations.items():
            with self.subTest(skill=skill):
                self.assertIn(canonical_path, (root / skill / "SKILL.md").read_text())

    def test_setup_reports_a_dry_run_for_an_existing_configuration(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            profile = repo / ".agent" / "matt-workflow.md"
            legacy = repo / ".agent" / "work" / "checkout" / "spec.md"
            profile.parent.mkdir(parents=True)
            profile.write_text(
                render_profile(
                    {
                        "schema_version": 1,
                        "task_backend": "local",
                    }
                )
            )
            legacy.parent.mkdir(parents=True)
            legacy.write_text("# Old spec\n")
            before = legacy.read_bytes()

            result = subprocess.run(
                [
                    "python3",
                    "tools/workflow.py",
                    "setup",
                    "--repo",
                    str(repo),
                ],
                cwd=Path(__file__).resolve().parents[1],
                capture_output=True,
                text=True,
                check=True,
            )

            self.assertIn('"from": ".agent/work/checkout/spec.md"', result.stdout)
            self.assertEqual(before, legacy.read_bytes())
            self.assertFalse(
                (repo / ".agent/work/checkout/specs/specs-checkout-01.md").exists()
            )

    def test_confirmed_setup_migrates_artifacts_and_only_rewrites_confirmed_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            profile = repo / ".agent" / "matt-workflow.md"
            spec = repo / ".agent" / "work" / "checkout" / "spec.md"
            ticket = repo / ".agent" / "work" / "checkout" / "ticket.md"
            profile.parent.mkdir(parents=True)
            profile.write_text(
                render_profile(
                    {
                        "schema_version": 1,
                        "task_backend": "local",
                    }
                )
            )
            spec.parent.mkdir(parents=True)
            ticket.write_text("# Ticket\n")
            spec.write_text(
                "[ticket](ticket.md)\n"
                "[workflow](../../tools/workflow.py)\n"
            )
            tool = repo / "tools" / "workflow.py"
            tool.parent.mkdir()
            tool.write_text("#!/usr/bin/env python3\n")

            subprocess.run(
                [
                    "python3",
                    "tools/workflow.py",
                    "setup",
                    "--repo",
                    str(repo),
                    "--apply",
                    "--refresh",
                    "--migrate-work-artifacts",
                ],
                cwd=Path(__file__).resolve().parents[1],
                check=True,
            )

            migrated_spec = (
                repo / ".agent/work/checkout/specs/specs-checkout-01.md"
            )
            migrated_ticket = (
                repo / ".agent/work/checkout/tickets/tickets-checkout-01.md"
            )
            self.assertFalse(spec.exists())
            self.assertFalse(ticket.exists())
            self.assertTrue(migrated_ticket.exists())
            self.assertEqual(
                "[ticket](../tickets/tickets-checkout-01.md)\n"
                "[workflow](../../tools/workflow.py)\n",
                migrated_spec.read_text(),
            )

    def test_candidate_link_repair_needs_its_own_confirmation(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            profile = repo / ".agent" / "matt-workflow.md"
            handoff = repo / ".agent" / "handoffs" / "checkout" / "2026-07-29.md"
            profile.parent.mkdir(parents=True)
            profile.write_text(
                render_profile(
                    {
                        "schema_version": 1,
                        "task_backend": "local",
                    }
                )
            )
            handoff.parent.mkdir(parents=True)
            handoff.write_text(
                "[workflow](../../tools/workflow.py)\n"
                "[recommendations](../../tools/workflow_lib/recommendations.py)\n"
            )
            tool = repo / "tools" / "workflow.py"
            tool.parent.mkdir()
            tool.write_text("#!/usr/bin/env python3\n")
            recommendations = repo / "tools" / "workflow_lib" / "recommendations.py"
            recommendations.parent.mkdir()
            recommendations.write_text("# Recommendations\n")

            subprocess.run(
                [
                    "python3",
                    "tools/workflow.py",
                    "setup",
                    "--repo",
                    str(repo),
                    "--apply",
                    "--refresh",
                    "--migrate-work-artifacts",
                    "--confirm-candidate-link-repair",
                    ".agent/handoffs/checkout/2026-07-29.md",
                    "../../tools/workflow.py",
                ],
                cwd=Path(__file__).resolve().parents[1],
                check=True,
            )

            migrated_handoff = (
                repo / ".agent/work/checkout/handoffs/handoffs-checkout-20260729.md"
            )
            self.assertFalse(handoff.exists())
            self.assertEqual(
                "[workflow](../../../../tools/workflow.py)\n"
                "[recommendations](../../tools/workflow_lib/recommendations.py)\n",
                migrated_handoff.read_text(),
            )

    def test_confirmed_migration_leaves_unclassified_files_in_place(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            profile = repo / ".agent" / "matt-workflow.md"
            legacy = repo / ".agent" / "work" / "checkout" / "spec.md"
            unclassified = repo / ".agent" / "handoffs" / "old-handoff.md"
            profile.parent.mkdir(parents=True)
            profile.write_text(
                render_profile(
                    {
                        "schema_version": 1,
                        "task_backend": "local",
                    }
                )
            )
            legacy.parent.mkdir(parents=True)
            legacy.write_text("# Old spec\n")
            unclassified.parent.mkdir(parents=True)
            unclassified.write_text("# Unclassified\n")

            subprocess.run(
                [
                    "python3",
                    "tools/workflow.py",
                    "setup",
                    "--repo",
                    str(repo),
                    "--apply",
                    "--refresh",
                    "--migrate-work-artifacts",
                ],
                cwd=Path(__file__).resolve().parents[1],
                check=True,
            )

            self.assertFalse(legacy.exists())
            self.assertTrue(
                (repo / ".agent/work/checkout/specs/specs-checkout-01.md").exists()
            )
            self.assertEqual("# Unclassified\n", unclassified.read_text())

    def test_compliant_work_artifacts_need_no_migration(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            artifact = (
                repo
                / ".agent"
                / "work"
                / "align-upstream-skills"
                / "specs"
                / "specs-align-upstream-skills-20260729-131210.md"
            )
            artifact.parent.mkdir(parents=True)
            artifact.write_text("# Spec\n")

            report = analyze_work_artifacts(repo)

            self.assertTrue(report["compliant"])
            self.assertEqual([], report["moves"])
            self.assertEqual([], report["deletions"])

    def test_reports_legacy_paths_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            legacy = repo / ".agent" / "work" / "checkout" / "spec.md"
            legacy.parent.mkdir(parents=True)
            legacy.write_text("# Old spec\n")
            before = legacy.read_bytes()

            report = analyze_work_artifacts(repo)

            self.assertFalse(report["compliant"])
            self.assertEqual(
                [
                    {
                        "from": ".agent/work/checkout/spec.md",
                        "to": ".agent/work/checkout/specs/specs-checkout-01.md",
                    }
                ],
                report["moves"],
            )
            self.assertEqual([".agent/work/checkout/spec.md"], report["deletions"])
            self.assertEqual(before, legacy.read_bytes())
            self.assertFalse((repo / report["moves"][0]["to"]).exists())

    def test_reports_an_existing_destination_as_a_conflict(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            legacy = repo / ".agent" / "work" / "checkout" / "spec.md"
            destination = (
                repo
                / ".agent"
                / "work"
                / "checkout"
                / "specs"
                / "specs-checkout-01.md"
            )
            legacy.parent.mkdir(parents=True)
            destination.parent.mkdir()
            legacy.write_text("# Old spec\n")
            destination.write_text("# Existing spec\n")

            report = analyze_work_artifacts(repo)

            self.assertEqual(
                [
                    {
                        "destination": ".agent/work/checkout/specs/specs-checkout-01.md",
                        "sources": [".agent/work/checkout/spec.md"],
                        "existing": True,
                    }
                ],
                report["conflicts"],
            )

    def test_reports_rewrites_for_valid_relative_links_when_files_move(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            source = repo / ".agent" / "work" / "checkout" / "spec.md"
            target = repo / ".agent" / "work" / "checkout" / "ticket.md"
            source.parent.mkdir(parents=True)
            target.write_text("# Ticket\n")
            source.write_text("[ticket](ticket.md)\n")

            report = analyze_work_artifacts(repo)

            self.assertEqual(
                [
                    {
                        "source": ".agent/work/checkout/spec.md",
                        "new_source": ".agent/work/checkout/specs/specs-checkout-01.md",
                        "link": "ticket.md",
                        "old_target": ".agent/work/checkout/ticket.md",
                        "new_target": ".agent/work/checkout/tickets/tickets-checkout-01.md",
                        "replacement": "../tickets/tickets-checkout-01.md",
                    }
                ],
                report["link_rewrites"],
            )

    def test_reports_broken_tools_link_as_unconfirmed_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            source = repo / ".agent" / "handoffs" / "checkout" / "2026-07-29.md"
            source.parent.mkdir(parents=True)
            source.write_text("[workflow](../../tools/workflow.py)\n")
            tool = repo / "tools" / "workflow.py"
            tool.parent.mkdir()
            tool.write_text("#!/usr/bin/env python3\n")

            report = analyze_work_artifacts(repo)

            self.assertEqual(
                [
                    {
                        "source": ".agent/handoffs/checkout/2026-07-29.md",
                        "new_source": ".agent/work/checkout/handoffs/handoffs-checkout-20260729.md",
                        "link": "../../tools/workflow.py",
                        "candidate_target": "tools/workflow.py",
                        "replacement": "../../../../tools/workflow.py",
                    }
                ],
                report["candidate_link_repairs"],
            )
            self.assertEqual([], report["link_rewrites"])


class GitIgnoreTests(unittest.TestCase):
    def test_adds_personal_directories_when_untracked(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)

            added, conflicts = apply_personal_ignores(repo)

            self.assertEqual([".agent/"], added)
            self.assertEqual([], conflicts)
            self.assertEqual(
                ".agent/\n",
                (repo / ".gitignore").read_text(),
            )

    def test_does_not_ignore_directory_with_tracked_team_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            (repo / ".cursor").mkdir()
            (repo / ".cursor" / "rules.md").write_text("team rules")
            subprocess.run(["git", "add", ".cursor/rules.md"], cwd=repo, check=True)

            added, conflicts = apply_personal_ignores(repo)

            self.assertEqual([".agent/"], added)
            self.assertEqual([], conflicts)


class InstallerTests(unittest.TestCase):
    def _release(self, root: Path, release_id: str, body: str) -> Path:
        release = root / release_id
        skill = release / "skills" / "my-demo"
        skill.mkdir(parents=True)
        skill_file = skill / "SKILL.md"
        skill_file.write_text(body)
        digest = hashlib.sha256(skill_file.read_bytes()).hexdigest()
        (release / "manifest.json").write_text(
            json.dumps(
                {
                    "release_id": release_id,
                    "skills": {
                        "my-demo": {
                            "SKILL.md": digest,
                        }
                    },
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

            recover_interrupted_install(cursor_home)

            self.assertEqual("old", (target / "SKILL.md").read_text())
            self.assertFalse(transaction.exists())

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
                    }
                )
            )

            recover_interrupted_install(cursor_home)

            self.assertEqual("new", (target / "SKILL.md").read_text())
            self.assertFalse(transaction.exists())

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
                    }
                )
            )

            recover_interrupted_install(cursor_home)

            self.assertEqual("stable-old", (target / "SKILL.md").read_text())


class DoctorTests(unittest.TestCase):
    def test_adopted_upstream_skills_are_mapped_and_not_recommended(self):
        adopted = {
            "engineering/resolving-merge-conflicts": "my-resolving-merge-conflicts",
            "in-progress/to-questionnaire": "my-to-questionnaire",
            "in-progress/wizard": "my-wizard",
            "personal/edit-article": "my-edit-article",
        }
        workflow_source = (Path(__file__).resolve().parents[1] / "tools" / "workflow.py").read_text()
        for upstream_path, skill in adopted.items():
            with self.subTest(upstream_path=upstream_path):
                self.assertIn(f'"{skill}"', workflow_source)
                self.assertIn(f'"{upstream_path}"', workflow_source)

        report = build_recommendation_report(list(adopted))
        self.assertEqual([], [item for item in report["items"] if item["status"] != "covered"])
        pre_commit = build_recommendation_report(["misc/setup-pre-commit"])["items"][0]
        self.assertEqual("consider", pre_commit["status"])
        self.assertFalse((Path(__file__).resolve().parents[1] / "skills" / "my-setup-pre-commit").exists())

    def test_snapshots_mapped_category_tree_and_reports_unmapped_skills(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            (root / "skills" / "engineering" / "implement").mkdir(parents=True)
            (root / "skills" / "productivity" / "teach").mkdir(parents=True)
            (root / "skills" / "engineering" / "implement" / "SKILL.md").write_text("impl")
            (root / "skills" / "productivity" / "teach" / "SKILL.md").write_text("teach")
            paths = {"implement": "engineering/implement"}
            snapshot = snapshot_mapped_tree(root, paths)
            self.assertEqual({"implement"}, set(snapshot))
            self.assertEqual(["productivity/teach"], discover_unmapped_skills(root, paths))
    def test_reports_only_changed_upstream_skill(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "first"
            second = root / "second"
            for directory in (first, second):
                (directory / "implement").mkdir(parents=True)
                (directory / "tdd").mkdir(parents=True)
                (directory / "implement" / "SKILL.md").write_text("same")
                (directory / "tdd" / "SKILL.md").write_text("same")
            (second / "implement" / "SKILL.md").write_text("changed")

            changes = compare_snapshots(snapshot_tree(first), snapshot_tree(second))

            self.assertEqual({"implement": ["SKILL.md"]}, changes)

    def test_rejects_empty_or_incomplete_upstream_snapshot(self):
        with self.assertRaises(SnapshotError):
            validate_upstream_snapshot({}, {"implement", "tdd"})
        with self.assertRaisesRegex(SnapshotError, "tdd"):
            validate_upstream_snapshot({"implement": {"SKILL.md": "hash"}}, {"implement", "tdd"})

    def test_doctor_mode_allows_single_upstream_skill_deletion(self):
        snapshot = {"implement": {"SKILL.md": "hash"}}

        validate_upstream_snapshot(
            snapshot,
            {"implement", "tdd"},
            allow_missing=True,
        )

    def test_upstream_manifest_wrapper_preserves_skill_hashes(self):
        root = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location(
            "workflow_cli_manifest_wrapper", root / "tools/workflow.py"
        )
        module = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(root / "tools"))
        try:
            assert spec.loader is not None
            spec.loader.exec_module(module)
        finally:
            sys.path.pop(0)

        skills = module._load_upstream_skills_snapshot(
            root / "upstream" / "manifest.json"
        )
        raw = json.loads((root / "upstream" / "manifest.json").read_text())
        self.assertEqual(
            {
                "repo": "https://github.com/mattpocock/skills.git",
                "commit": "2ab958093e83e0ec752e6c1c5932da465bf23e0c",
            },
            raw["source"],
        )
        self.assertEqual(raw["skills"], skills)
        self.assertIn("ask-matt", skills)
        self.assertEqual(
            {"ask-matt": skills["ask-matt"]},
            module._upstream_skills_from_manifest(
                {"ask-matt": skills["ask-matt"]}
            ),
        )

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.json"
            module._write_upstream_manifest(
                path,
                {"implement": {"SKILL.md": "abc"}},
                source={
                    "repo": "https://github.com/mattpocock/skills.git",
                    "commit": "deadbeef",
                },
            )
            rewritten = json.loads(path.read_text())
            self.assertEqual("deadbeef", rewritten["source"]["commit"])
            self.assertEqual(
                {"implement": {"SKILL.md": "abc"}},
                module._load_upstream_skills_snapshot(path),
            )
            module._write_upstream_manifest(
                path, {"implement": {"SKILL.md": "def"}}
            )
            preserved = json.loads(path.read_text())
            self.assertEqual("deadbeef", preserved["source"]["commit"])
            self.assertEqual("def", preserved["skills"]["implement"]["SKILL.md"])

    def test_snapshot_records_commit_of_tree_that_produced_hashes(self):
        root = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location(
            "workflow_cli_snapshot_provenance", root / "tools/workflow.py"
        )
        module = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(root / "tools"))
        try:
            assert spec.loader is not None
            spec.loader.exec_module(module)
        finally:
            sys.path.pop(0)

        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            upstream = workspace / "upstream-source"
            for upstream_path in module.UPSTREAM_PATHS.values():
                skill = upstream / "skills" / upstream_path
                skill.mkdir(parents=True, exist_ok=True)
                (skill / "SKILL.md").write_text(f"# {upstream_path}\n")
            subprocess.run(["git", "init", "-q"], cwd=upstream, check=True)
            subprocess.run(["git", "add", "."], cwd=upstream, check=True)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.name=Test",
                    "-c",
                    "user.email=test@example.com",
                    "commit",
                    "-qm",
                    "snapshot source",
                ],
                cwd=upstream,
                check=True,
            )
            source_commit = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=upstream,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            workflow_root = workspace / "workflow"
            manifest_path = workflow_root / "upstream" / "manifest.json"
            manifest_path.parent.mkdir(parents=True)
            manifest_path.write_text(
                json.dumps({"implement": {"SKILL.md": "old-hash"}})
            )
            original_root = module.ROOT
            module.ROOT = workflow_root
            try:
                module.command_snapshot(
                    argparse.Namespace(
                        upstream=str(upstream),
                        allow_deletions=False,
                    )
                )
            finally:
                module.ROOT = original_root

            manifest = json.loads(manifest_path.read_text())
            self.assertEqual(
                {"repo": str(upstream.resolve()), "commit": source_commit},
                manifest["source"],
            )
            self.assertEqual(
                module._adapted_snapshot(upstream),
                manifest["skills"],
            )

    def test_fidelity_ledger_covers_upstream_derived_skills(self):
        root = Path(__file__).resolve().parents[1]
        fidelity = json.loads((root / "upstream" / "fidelity.json").read_text())
        manifest = json.loads((root / "upstream" / "manifest.json").read_text())
        by_upstream = {entry["upstream_skill"]: entry for entry in fidelity["skills"]}
        self.assertEqual(set(manifest["skills"]), set(by_upstream))
        self.assertTrue(
            set(fidelity["conclusions"])
            >= {
                "faithful",
                "restore-required",
                "adapter-rework-required",
                "unreviewed",
            }
        )
        for entry in fidelity["skills"]:
            self.assertEqual(
                manifest["skills"][entry["upstream_skill"]],
                entry["support_files"],
            )
            self.assertIn(entry["conclusion"], fidelity["conclusions"])
            if entry["conclusion"] == "faithful":
                self.assertTrue(entry["sections"]["complete"])
                self.assertTrue(entry["sections"]["translated"])
                self.assertEqual([], entry["sections"]["missing"])
                self.assertTrue(entry["evidence_path"])
                evidence_path = Path(entry["evidence_path"])
                with self.subTest(skill=entry["local_skill"]):
                    self.assertEqual(
                        ("upstream", "evidence"),
                        evidence_path.parts[:2],
                    )
                    self.assertTrue(
                        (root / evidence_path).is_file(),
                        "faithful evidence must resolve in source",
                    )
                    tracked = subprocess.run(
                        ["git", "ls-files", "--error-unmatch", "--", str(evidence_path)],
                        cwd=root,
                        check=False,
                        capture_output=True,
                        text=True,
                    )
                    self.assertEqual(
                        0,
                        tracked.returncode,
                        f"faithful evidence must be committed: {evidence_path}",
                    )

    def test_fidelity_ledger_populates_upstream_grilling_as_24th_skill(self):
        root = Path(__file__).resolve().parents[1]
        fidelity = json.loads((root / "upstream" / "fidelity.json").read_text())
        manifest = json.loads((root / "upstream" / "manifest.json").read_text())
        spec = importlib.util.spec_from_file_location(
            "workflow_cli_grilling_registration", root / "tools/workflow.py"
        )
        module = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(root / "tools"))
        try:
            assert spec.loader is not None
            spec.loader.exec_module(module)
        finally:
            sys.path.pop(0)
        entries = fidelity["skills"]
        grilling = next(
            (
                entry
                for entry in entries
                if entry["upstream_skill"] == "grilling"
            ),
            None,
        )

        self.assertEqual(24, len(entries))
        self.assertEqual(24, len(manifest["skills"]))
        self.assertEqual(24, len(module.ADAPTATION_MAP))
        self.assertEqual(24, len(module.UPSTREAM_PATHS))
        self.assertEqual(set(manifest["skills"]), set(module.ADAPTATION_MAP))
        self.assertEqual(set(manifest["skills"]), set(module.UPSTREAM_PATHS))
        self.assertIsNotNone(grilling)
        assert grilling is not None
        self.assertEqual("productivity/grilling", grilling["upstream_path"])
        self.assertEqual("my-grilling", grilling["local_skill"])
        self.assertNotIn("my-grilling", fidelity["local_only_skills"])
        self.assertEqual(["my-grilling"], module.ADAPTATION_MAP["grilling"])
        self.assertEqual("productivity/grilling", module.UPSTREAM_PATHS["grilling"])
        self.assertIn("grilling", manifest["skills"])
        self.assertEqual(
            "upstream/evidence/grilling-audit.md", grilling["evidence_path"]
        )
        self.assertTrue((root / grilling["evidence_path"]).is_file())

    def test_codebase_design_restoration_records_parity_and_usable_method(self):
        root = Path(__file__).resolve().parents[1]
        fidelity = json.loads((root / "upstream" / "fidelity.json").read_text())
        entry = next(
            item
            for item in fidelity["skills"]
            if item["local_skill"] == "my-codebase-design"
        )
        self.assertEqual(
            "skills/engineering/codebase-design",
            entry["upstream_path"],
        )
        metadata_hash = hashlib.sha256(
            (
                root
                / "skills"
                / "my-codebase-design"
                / "agents"
                / "openai.yaml"
            ).read_bytes()
        ).hexdigest()
        self.assertEqual(
            entry.get("local_support_files", {}).get("agents/openai.yaml"),
            metadata_hash,
        )

        expected_sections = {
            "Glossary",
            "Deep vs shallow",
            "Principles",
            "Designing for testability",
            "Relationships",
            "Rejected framings",
            "Going deeper",
            "DEEPENING.md#Dependency categories",
            "DEEPENING.md#Seam discipline",
            "DEEPENING.md#Testing strategy: replace, don't layer",
            "DESIGN-IT-TWICE.md#Process",
            "DESIGN-IT-TWICE.md#Frame the problem space",
            "DESIGN-IT-TWICE.md#Spawn sub-agents",
            "DESIGN-IT-TWICE.md#Present and compare",
        }
        self.assertEqual(
            expected_sections,
            {item["upstream"] for item in entry["sections"]["complete"]},
        )
        self.assertEqual(
            expected_sections,
            {item["upstream"] for item in entry["sections"]["translated"]},
        )
        for item in entry["sections"]["complete"]:
            with self.subTest(section=item["upstream"]):
                self.assertTrue(item["local"])
                self.assertRegex(
                    item["evidence"],
                    r"(SKILL|DEEPENING|DESIGN-IT-TWICE)\.md#",
                )
        self.assertEqual([], entry["sections"]["missing"])
        for support_file in ("SKILL.md", "DEEPENING.md", "DESIGN-IT-TWICE.md"):
            with self.subTest(support_file=support_file):
                self.assertRegex(
                    entry["support_files"][support_file],
                    r"^[0-9a-f]{64}$",
                )
        self.assertEqual(
            [
                {
                    "path": "SKILL.md",
                    "adaptation": (
                        "保留本地名称、手动调用元数据，以及仓库要求的简短"
                        "“项目策略优先”提示；不改变上游方法。"
                    ),
                }
            ],
            entry["allowed_local_adaptations"],
        )
        self.assertEqual("faithful", entry["conclusion"])
        self.assertTrue(entry["evidence_path"])

        skill_dir = root / "skills" / "my-codebase-design"
        skill = (skill_dir / "SKILL.md").read_text()
        deepening = (skill_dir / "DEEPENING.md").read_text()
        design_twice = (skill_dir / "DESIGN-IT-TWICE.md").read_text()

        # The retrieved method must guide a real deepening decision, not only
        # preserve vocabulary labels.
        for instruction in (
            "接受依赖，而不是创建依赖",
            "删除测试",
            "Interface 就是测试面",
            "两个 Adapter 才意味着真实的 Seam",
        ):
            with self.subTest(instruction=instruction):
                self.assertIn(instruction, skill)
        for dependency_category in (
            "进程内",
            "可本地替代",
            "远程但自有",
            "真正外部",
        ):
            with self.subTest(dependency_category=dependency_category):
                self.assertIn(dependency_category, deepening)
        self.assertIn("替换，而不是叠加", deepening)
        self.assertIn("3 个以上", design_twice)
        self.assertIn("根本不同", design_twice)
        self.assertIn("深度", design_twice)
        self.assertIn("局部性", design_twice)

        # Apply the retrieved method to a concrete shallow-module input.  The
        # fixture is deliberately structured so this test validates the
        # constraint-to-consequence recommendation, not report prose.
        application_path = (
            root / "tests" / "fixtures" / "codebase_design_order_submission.json"
        )
        self.assertTrue(
            application_path.is_file(),
            "missing OrderSubmission retrieval/application fixture",
        )
        application = json.loads(application_path.read_text())

        self.assertEqual("OrderSubmissionService", application["input"]["module"])
        self.assertEqual(
            [
                "validateOrder(order)",
                "calculateTax(order)",
                "chargeCard(order)",
                "saveOrder(order)",
            ],
            application["input"]["public_methods"],
        )
        self.assertEqual(
            "new StripeGateway()",
            application["input"]["created_dependency"],
        )
        self.assertEqual(
            ["per-method shallow tests"],
            application["input"]["obsolete_tests"],
        )

        source_documents = {
            "SKILL.md": skill,
            "DEEPENING.md": deepening,
        }
        retrieved = {
            item["id"]: item
            for item in application["retrieved_constraints"]
        }
        expected_constraints = {
            "accept-dependencies": (
                "SKILL.md",
                "接受依赖，而不是创建依赖",
                "inject-payment-gateway",
            ),
            "external-dependency": (
                "DEEPENING.md",
                "真正外部",
                "inject-payment-gateway",
            ),
            "real-seam": (
                "DEEPENING.md",
                "两个 Adapter 才意味着真实的 Seam",
                "separate-production-and-test-adapters",
            ),
            "interface-test-surface": (
                "DEEPENING.md",
                "Interface 就是测试面",
                "test-public-interface-only",
            ),
            "replace-shallow-tests": (
                "DEEPENING.md",
                "替换，而不是叠加",
                "remove-obsolete-shallow-tests",
            ),
            "small-surface": (
                "SKILL.md",
                "小的表面积",
                "one-deep-submit-interface",
            ),
        }
        self.assertEqual(set(expected_constraints), set(retrieved))
        for constraint_id, (document, text, consequence) in expected_constraints.items():
            with self.subTest(constraint=constraint_id):
                constraint = retrieved[constraint_id]
                self.assertEqual(document, constraint["document"])
                self.assertEqual(text, constraint["text"])
                self.assertEqual(consequence, constraint["consequence"])
                self.assertIn(text, source_documents[document])

        recommendation = application["recommendation"]
        self.assertEqual(
            {"module": "OrderSubmission", "public_methods": ["submit(order)"]},
            recommendation["interface"],
        )
        self.assertEqual(
            {"port": "PaymentGateway", "injected_into": "OrderSubmission"},
            recommendation["dependency_injection"],
        )
        self.assertEqual(
            {
                "production": "StripePaymentGateway",
                "test": "InMemoryPaymentGateway",
            },
            recommendation["adapters"],
        )
        self.assertEqual(
            [
                "validateOrder(order)",
                "calculateTax(order)",
                "paymentGateway.charge(order)",
                "persistOrder(order)",
            ],
            recommendation["internalized_workflow"],
        )
        self.assertEqual(
            "translatePaymentError(error) before exposing the submit result",
            recommendation["error_ordering"],
        )
        self.assertEqual(
            {"surface": "OrderSubmission.submit(order)", "internal_state": False},
            recommendation["tests"],
        )
        self.assertEqual(
            ["per-method shallow tests"],
            recommendation["removed_tests"],
        )
        self.assertEqual(
            {
                constraint_id: consequence
                for constraint_id, (_, _, consequence) in expected_constraints.items()
            },
            recommendation["consequence_by_constraint"],
        )

    def test_recommendations_rank_general_candidates_and_defer_specialized_ones(self):
        report = build_recommendation_report(
            [
                "engineering/resolving-merge-conflicts",
                "in-progress/to-questionnaire",
                "misc/migrate-to-shoehorn",
                "unknown/new-skill",
            ]
        )

        self.assertEqual(
            {"recommend": 0, "consider": 0, "covered": 2, "defer": 2},
            report["summary"],
        )
        by_path = {item["upstream_skill"]: item for item in report["items"]}
        self.assertEqual("my-resolving-merge-conflicts", by_path["engineering/resolving-merge-conflicts"]["suggested_name"])
        self.assertEqual("covered", by_path["in-progress/to-questionnaire"]["status"])
        self.assertEqual("defer", by_path["misc/migrate-to-shoehorn"]["status"])
        self.assertIn("尚未人工评估", by_path["unknown/new-skill"]["reason"])


class ReleaseTests(unittest.TestCase):
    def test_all_skills_have_manual_only_openai_metadata(self):
        root = Path(__file__).resolve().parents[1] / "skills"
        failures = []
        for skill_dir in sorted(root.iterdir()):
            if not skill_dir.is_dir():
                continue
            metadata = skill_dir / "agents/openai.yaml"
            if not metadata.is_file():
                failures.append(f"{skill_dir.name}: missing")
                continue
            text = metadata.read_text()
            if "allow_implicit_invocation: false" not in text:
                failures.append(f"{skill_dir.name}: implicit")
        self.assertEqual([], failures)

    def test_adopted_skills_include_metadata_and_safety_boundaries(self):
        root = Path(__file__).resolve().parents[1] / "skills"
        expected = {
            "my-resolving-merge-conflicts": ["批准前", "Force Push", "回滚"],
            "my-to-questionnaire": [
                "to-questionnaire-<slug>.md",
                "只就“发送”采访用户，而不要就主题采访用户",
            ],
            "my-wizard": [
                "每个阶段按顺序命名",
                "永远不要编造可能不存在的步骤",
                "不要改动 `STAGES` 标记上方的库",
            ],
            "my-edit-article": ["articles", "默认生成新稿", "原地修改"],
        }

        for skill, required_text in expected.items():
            with self.subTest(skill=skill):
                skill_dir = root / skill
                self.assertTrue((skill_dir / "SKILL.md").is_file())
                self.assertTrue((skill_dir / "agents" / "openai.yaml").is_file())
                text = (skill_dir / "SKILL.md").read_text()
                for phrase in required_text:
                    self.assertIn(phrase, text)

        self.assertEqual(28, len(validate_skills(root)))

    def test_legacy_skills_keep_project_policy_precedence(self):
        source_skills = Path(__file__).parents[1] / "skills"
        for skill_file in source_skills.glob("my-*/SKILL.md"):
            if skill_file.parent.name in {
                "my-to-questionnaire",
                "my-writing-great-skills",
                "my-triage",
                "my-teach",
                "my-improve-codebase-architecture",
                "my-wizard",
            }:
                continue
            self.assertIn("项目策略优先", skill_file.read_text(), skill_file)

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

    def test_build_materializes_composition_and_shared_resources(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            release = build_release(
                root / "skills",
                Path(tmp) / "releases",
                release_id="composed-v1",
                upstream_id="local-matt-skills",
                repo_root=root,
            )
            self.assertTrue(
                (
                    release
                    / "skills/my-implement/references/composed/my-tdd/SKILL.md"
                ).is_file()
            )
            self.assertTrue(
                (
                    release
                    / "skills/my-to-spec/references/shared/humanizer.md"
                ).is_file()
            )
            self.assertTrue(
                (
                    release
                    / "skills/my-implement/references/composed/my-code-review"
                    / "references/shared/humanizer.md"
                ).is_file()
            )
            manifest = json.loads((release / "manifest.json").read_text())
            self.assertEqual(
                ["my-code-review", "my-tdd"],
                manifest["composed"]["my-implement"],
            )

    def test_build_materializes_routable_entries_for_router(self):
        root = Path(__file__).resolve().parents[1]
        expected = [
            "my-diagnosing-bugs",
            "my-grill-me",
            "my-grill-with-docs",
            "my-implement",
            "my-triage",
            "my-wayfinder",
        ]
        with tempfile.TemporaryDirectory() as tmp:
            release = build_release(
                root / "skills",
                Path(tmp) / "releases",
                release_id="routed-v1",
                upstream_id="local-matt-skills",
                repo_root=root,
            )

            for skill_name in expected:
                with self.subTest(skill=skill_name):
                    self.assertTrue(
                        (
                            release
                            / "skills/my-ask-matt/references/composed"
                            / skill_name
                            / "SKILL.md"
                        ).is_file()
                    )
            manifest = json.loads((release / "manifest.json").read_text())
            self.assertEqual(
                expected, manifest["composed"]["my-ask-matt"]
            )

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
        return workflow

    def _run(self, workflow: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "tools/workflow.py", *args],
            cwd=workflow,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_deploy_reuses_the_current_release_when_skills_are_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            workflow = self._workflow(Path(tmp))
            first = self._run(workflow, "build", "--release-id", "v1")
            self.assertEqual(0, first.returncode, first.stderr)

            deployed = self._run(
                workflow,
                "deploy",
                "--agent-home",
                str(Path(tmp) / "agent"),
            )

            self.assertEqual(0, deployed.returncode, deployed.stderr)
            self.assertEqual(
                ["v1"],
                sorted(path.name for path in (workflow / "releases").iterdir()),
            )
            self.assertIn("INSTALLED v1", deployed.stdout)

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

            deployed = self._run(
                workflow,
                "deploy",
                "--agent-home",
                str(Path(tmp) / "agent"),
            )

            self.assertEqual(0, deployed.returncode, deployed.stderr)
            self.assertEqual(
                1,
                len([path for path in (workflow / "releases").iterdir() if path.is_dir()]),
            )

    def test_prune_releases_keeps_current_and_agent_referenced_releases(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workflow = self._workflow(root)
            skill_file = workflow / "skills" / "my-demo" / "SKILL.md"
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
                built = self._run(workflow, "build", "--release-id", release_id)
                self.assertEqual(0, built.returncode, built.stderr)

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
                sorted(path.name for path in (workflow / "releases").iterdir()),
            )


class SyncTests(unittest.TestCase):
    def test_review_bundle_maps_upstream_changes_to_personal_skills(self):
        bundle = build_review_bundle(
            {"implement": ["SKILL.md"], "tdd": ["tests.md"]},
            {"implement": ["my-implement"], "tdd": ["my-tdd", "my-implement"]},
        )

        self.assertEqual(
            {
                "implement": {
                    "files": ["SKILL.md"],
                    "affected_skills": ["my-implement"],
                    "decision": None,
                },
                "tdd": {
                    "files": ["tests.md"],
                    "affected_skills": ["my-implement", "my-tdd"],
                    "decision": None,
                },
            },
            bundle,
        )


class WritingGreatSkillsParityTests(unittest.TestCase):
    @staticmethod
    def _apply_writing_great_skills_mapping(case):
        decisions = {
            mapping["decision"]
            for mapping in case["constraint_mapping"]
            if all(
                case["input"].get(field) == expected
                for field, expected in mapping["when"].items()
            )
        }
        if len(decisions) != 1:
            return None
        return decisions.pop()

    def test_restored_skill_has_no_project_policy_footer(self):
        root = Path(__file__).resolve().parents[1]
        skill = (
            root / "skills" / "my-writing-great-skills" / "SKILL.md"
        ).read_text()

        self.assertNotIn("项目策略优先", skill)
        self.assertNotIn("读取 `.agent/matt-workflow.md`", skill)
        self.assertNotIn("本 Skill 中要求询问、确认、停止或限制后续工作的表述", skill)
        self.assertNotIn("均服从该生效策略", skill)
        self.assertNotIn("绝对安全底线始终不变", skill)

    def test_restoration_records_full_parity_and_applies_guidance(self):
        root = Path(__file__).resolve().parents[1]
        skill_dir = root / "skills" / "my-writing-great-skills"
        skill = (skill_dir / "SKILL.md").read_text()
        glossary = (skill_dir / "GLOSSARY.md").read_text()
        documents = {"SKILL.md": skill, "GLOSSARY.md": glossary}

        fidelity = json.loads((root / "upstream" / "fidelity.json").read_text())
        entry = next(
            item
            for item in fidelity["skills"]
            if item["local_skill"] == "my-writing-great-skills"
        )
        self.assertEqual(
            "skills/productivity/writing-great-skills",
            entry["upstream_path"],
        )
        expected_sections = {
            "SKILL.md#Invocation",
            "SKILL.md#Writing the description",
            "SKILL.md#Information hierarchy",
            "SKILL.md#When to split",
            "SKILL.md#Pruning",
            "SKILL.md#Leading words",
            "SKILL.md#Failure modes",
            "GLOSSARY.md#Predictability",
            "GLOSSARY.md#Invocation",
            "GLOSSARY.md#Model-Invoked",
            "GLOSSARY.md#User-Invoked",
            "GLOSSARY.md#Description",
            "GLOSSARY.md#Context Pointer",
            "GLOSSARY.md#Context Load",
            "GLOSSARY.md#Cognitive Load",
            "GLOSSARY.md#Router Skill",
            "GLOSSARY.md#Granularity",
            "GLOSSARY.md#Information Hierarchy",
            "GLOSSARY.md#Steps",
            "GLOSSARY.md#Reference",
            "GLOSSARY.md#External Reference",
            "GLOSSARY.md#Progressive Disclosure",
            "GLOSSARY.md#Co-location",
            "GLOSSARY.md#Sprawl",
            "GLOSSARY.md#Steering",
            "GLOSSARY.md#Branch",
            "GLOSSARY.md#Leading Word",
            "GLOSSARY.md#Completion Criterion",
            "GLOSSARY.md#Legwork",
            "GLOSSARY.md#Post-Completion Steps",
            "GLOSSARY.md#Premature Completion",
            "GLOSSARY.md#Negation",
            "GLOSSARY.md#Pruning",
            "GLOSSARY.md#Single Source of Truth",
            "GLOSSARY.md#Duplication",
            "GLOSSARY.md#Relevance",
            "GLOSSARY.md#Sediment",
            "GLOSSARY.md#No-Op",
        }
        for field in ("complete", "translated"):
            mappings = entry["sections"][field]
            self.assertEqual(expected_sections, {item["upstream"] for item in mappings})
            for mapping in mappings:
                with self.subTest(field=field, section=mapping["upstream"]):
                    self.assertTrue(mapping["local"])
                    self.assertRegex(mapping["evidence"], r"(SKILL|GLOSSARY)\.md#")
        self.assertEqual([], entry["sections"]["missing"])
        self.assertEqual("faithful", entry["conclusion"])
        self.assertEqual(
            "upstream/evidence/writing-great-skills-restoration.md",
            entry["evidence_path"],
        )
        self.assertEqual(
            ["GLOSSARY.md", "SKILL.md", "agents/openai.yaml"],
            sorted(entry["support_files"]),
        )
        self.assertEqual(
            hashlib.sha256(
                (skill_dir / "agents" / "openai.yaml").read_bytes()
            ).hexdigest(),
            entry["local_support_files"]["agents/openai.yaml"],
        )
        self.assertEqual(
            [
                {
                    "path": "SKILL.md",
                    "adaptation": (
                        "保留本地名称和手动调用元数据；不改变上游方法。"
                    ),
                }
            ],
            entry["allowed_local_adaptations"],
        )

        for phrase in (
            "上下文负荷",
            "一个分支只保留一个触发条件",
            "完成条件",
            "渐进式披露",
            "按调用拆分",
            "单一事实来源",
            "提前完成",
            "正向",
        ):
            with self.subTest(translation=phrase):
                self.assertIn(phrase, skill + glossary)

        fixture_path = root / "tests" / "fixtures" / "writing_great_skills_wording.json"
        self.assertTrue(fixture_path.is_file(), "missing wording application fixture")
        fixture = json.loads(fixture_path.read_text())
        self.assertEqual(
            {"baseline", "fixed", "stress"},
            set(fixture["groups"]),
        )
        for group, cases in fixture["groups"].items():
            with self.subTest(group=group):
                self.assertGreaterEqual(len(cases), 5)
                for case in cases:
                    self.assertIsInstance(case["input"], dict)
                    self.assertIn(
                        case["expected"]["decision"],
                        {"accept", "reject", "rewrite"},
                    )
                    self.assertTrue(case["expected"]["observable"])
                    self.assertTrue(case["retrieved_guidance"])
                    guidance_by_text = {
                        guidance["text"]: guidance
                        for guidance in case["retrieved_guidance"]
                    }
                    self.assertEqual(
                        len(case["retrieved_guidance"]), len(guidance_by_text)
                    )
                    for guidance in guidance_by_text.values():
                        self.assertIn(guidance["document"], documents)
                        self.assertIn(
                            guidance["text"],
                            documents[guidance["document"]],
                        )
                    self.assertTrue(case["constraint_mapping"])
                    for mapping in case["constraint_mapping"]:
                        self.assertTrue(mapping["when"])
                        self.assertEqual(
                            case["expected"]["decision"], mapping["decision"]
                        )
                        self.assertEqual(
                            case["expected"]["observable"], mapping["observable"]
                        )
                        for guidance_text in mapping["guidance"]:
                            self.assertIn(guidance_text, guidance_by_text)
                    self.assertEqual(
                        case["expected"]["decision"],
                        self._apply_writing_great_skills_mapping(case),
                    )


class TriageParityTests(unittest.TestCase):
    @staticmethod
    def _apply_triage_constraint_mapping(case):
        outcomes = [
            mapping["outcome"]
            for mapping in case["constraint_mapping"]
            if all(
                case["input"].get(field) == expected
                for field, expected in mapping["when"].items()
            )
            and set(mapping["constraints"])
            <= {constraint["id"] for constraint in case["retrieved_constraints"]}
        ]
        if len(outcomes) != 1:
            return None
        return outcomes[0]

    def test_triage_restoration_records_complete_translated_parity(self):
        root = Path(__file__).resolve().parents[1]
        skill_dir = root / "skills" / "my-triage"
        self.assertTrue(skill_dir.is_dir(), "missing restored my-triage Skill")

        documents = {
            "SKILL.md": (skill_dir / "SKILL.md").read_text(),
            "AGENT-BRIEF.md": (skill_dir / "AGENT-BRIEF.md").read_text(),
            "OUT-OF-SCOPE.md": (skill_dir / "OUT-OF-SCOPE.md").read_text(),
        }
        fidelity = json.loads((root / "upstream" / "fidelity.json").read_text())
        entry = next(
            item
            for item in fidelity["skills"]
            if item["local_skill"] == "my-triage"
        )

        self.assertEqual("skills/engineering/triage", entry["upstream_path"])
        expected_mappings = {
            "SKILL.md#Triage": ("SKILL.md", "分诊"),
            "SKILL.md#Reference docs": ("SKILL.md", "参考文档"),
            "SKILL.md#Roles": ("SKILL.md", "角色"),
            "SKILL.md#Invocation": ("SKILL.md", "调用"),
            "SKILL.md#Show what needs attention": ("SKILL.md", "显示需要关注的事项"),
            "SKILL.md#Triage a specific issue or PR": ("SKILL.md", "分诊特定 Issue 或 PR"),
            "SKILL.md#Quick state override": ("SKILL.md", "快速状态覆盖"),
            "SKILL.md#Needs-info template": ("SKILL.md", "需要更多信息模板"),
            "SKILL.md#Resuming a previous session": ("SKILL.md", "恢复之前的会话"),
            "AGENT-BRIEF.md#Writing Agent Briefs": ("AGENT-BRIEF.md", "编写 Agent 简报"),
            "AGENT-BRIEF.md#Principles": ("AGENT-BRIEF.md", "原则"),
            "AGENT-BRIEF.md#Durability over precision": ("AGENT-BRIEF.md", "持久性优先于精确性"),
            "AGENT-BRIEF.md#Behavioral, not procedural": ("AGENT-BRIEF.md", "描述行为，而非过程"),
            "AGENT-BRIEF.md#Complete acceptance criteria": ("AGENT-BRIEF.md", "完整的验收标准"),
            "AGENT-BRIEF.md#Explicit scope boundaries": ("AGENT-BRIEF.md", "明确的范围边界"),
            "AGENT-BRIEF.md#Template": ("AGENT-BRIEF.md", "模板"),
            "AGENT-BRIEF.md#Examples": ("AGENT-BRIEF.md", "示例"),
            "AGENT-BRIEF.md#Good agent brief (bug)": ("AGENT-BRIEF.md", "好的 Agent 简报（Bug）"),
            "AGENT-BRIEF.md#Good agent brief (enhancement)": ("AGENT-BRIEF.md", "好的 Agent 简报（增强）"),
            "AGENT-BRIEF.md#Good agent brief (PR)": ("AGENT-BRIEF.md", "好的 Agent 简报（PR）"),
            "AGENT-BRIEF.md#Bad agent brief": ("AGENT-BRIEF.md", "不好的 Agent 简报"),
            "OUT-OF-SCOPE.md#Out-of-Scope Knowledge Base": ("OUT-OF-SCOPE.md", "超出范围知识库"),
            "OUT-OF-SCOPE.md#Directory structure": ("OUT-OF-SCOPE.md", "目录结构"),
            "OUT-OF-SCOPE.md#File format": ("OUT-OF-SCOPE.md", "文件格式"),
            "OUT-OF-SCOPE.md#Naming the file": ("OUT-OF-SCOPE.md", "文件命名"),
            "OUT-OF-SCOPE.md#Writing the reason": ("OUT-OF-SCOPE.md", "编写理由"),
            "OUT-OF-SCOPE.md#When to check `.out-of-scope/`": ("OUT-OF-SCOPE.md", "何时检查 `.out-of-scope/`"),
            "OUT-OF-SCOPE.md#When to write to `.out-of-scope/`": ("OUT-OF-SCOPE.md", "何时写入 `.out-of-scope/`"),
            "OUT-OF-SCOPE.md#Updating or removing out-of-scope files": ("OUT-OF-SCOPE.md", "更新或移除超出范围文件"),
        }
        for field in ("complete", "translated"):
            mappings = entry["sections"][field]
            self.assertEqual(expected_mappings.keys(), {item["upstream"] for item in mappings})
            for mapping in mappings:
                with self.subTest(field=field, section=mapping["upstream"]):
                    document, heading = expected_mappings[mapping["upstream"]]
                    self.assertEqual(heading, mapping["local"])
                    self.assertIn(heading, documents[document])
                    self.assertRegex(mapping["evidence"], r"\.md#")
        self.assertEqual([], entry["sections"]["missing"])
        self.assertEqual([], entry["sections"]["local_added"])
        self.assertEqual(
            {
                "AGENT-BRIEF.md": "5b78d347cc53f6bcf7b875106005ccf5315055fa4cf75eb28d41e96ee426d27b",
                "OUT-OF-SCOPE.md": "2526f998fd7ca5e956d3f6f234bcc2431a5971ee769f1148ddc60b92f04d5914",
                "SKILL.md": "d45827c299c021f77b0f146fefa3ee679b13f99e9a2ffdf48e8de2347adeefe1",
                "agents/openai.yaml": "2e683717720cf456d165d0bb1a68bb600d0b6a8ccb61841c172e50d26f95351c",
            },
            entry["support_files"],
        )
        metadata = skill_dir / "agents" / "openai.yaml"
        self.assertTrue(metadata.is_file(), "missing local manual-only metadata")
        self.assertEqual(
            hashlib.sha256(metadata.read_bytes()).hexdigest(),
            entry["local_support_files"]["agents/openai.yaml"],
        )
        self.assertIn("allow_implicit_invocation: false", metadata.read_text())
        self.assertEqual(
            [
                {
                    "path": "SKILL.md",
                    "adaptation": "保留本地名称和手动调用元数据；不改变上游方法。",
                }
            ],
            entry["allowed_local_adaptations"],
        )
        self.assertEqual("faithful", entry["conclusion"])
        self.assertEqual(
            "upstream/evidence/triage-restoration.md",
            entry["evidence_path"],
        )

    def test_triage_scenarios_apply_retrieved_constraints(self):
        root = Path(__file__).resolve().parents[1]
        skill_dir = root / "skills" / "my-triage"
        fixture_path = root / "tests" / "fixtures" / "triage_workflow_application.json"
        self.assertTrue(fixture_path.is_file(), "missing triage workflow fixture")
        self.assertTrue(skill_dir.is_dir(), "missing restored my-triage Skill")

        fixture = json.loads(fixture_path.read_text())
        self.assertEqual("skills/engineering/triage", fixture["source_path"])
        self.assertEqual(
            {
                "state-transition",
                "deterministic-ordering",
                "needs-info",
                "validation-failure",
                "recovery",
            },
            {case["id"] for case in fixture["scenarios"]},
        )
        documents = {
            "SKILL.md": (skill_dir / "SKILL.md").read_text(),
            "AGENT-BRIEF.md": (skill_dir / "AGENT-BRIEF.md").read_text(),
            "OUT-OF-SCOPE.md": (skill_dir / "OUT-OF-SCOPE.md").read_text(),
        }
        for case in fixture["scenarios"]:
            with self.subTest(scenario=case["id"]):
                self.assertIsInstance(case["input"], dict)
                self.assertTrue(case["retrieved_constraints"])
                constraint_ids = set()
                for constraint in case["retrieved_constraints"]:
                    self.assertNotIn(constraint["id"], constraint_ids)
                    constraint_ids.add(constraint["id"])
                    self.assertIn(constraint["document"], documents)
                    self.assertIn(
                        constraint["text"], documents[constraint["document"]]
                    )
                self.assertTrue(case["constraint_mapping"])
                for mapping in case["constraint_mapping"]:
                    self.assertTrue(mapping["when"])
                    self.assertTrue(mapping["constraints"])
                    self.assertTrue(set(mapping["constraints"]) <= constraint_ids)
                    self.assertEqual(case["expected"], mapping["outcome"])
                self.assertEqual(
                    case["expected"],
                    self._apply_triage_constraint_mapping(case),
                )


class TeachParityTests(unittest.TestCase):
    @staticmethod
    def _apply_teach_constraint_mapping(case):
        outcomes = [
            mapping["outcome"]
            for mapping in case["constraint_mapping"]
            if all(
                case["input"].get(field) == expected
                for field, expected in mapping["when"].items()
            )
            and set(mapping["constraints"])
            <= {constraint["id"] for constraint in case["retrieved_constraints"]}
        ]
        if len(outcomes) != 1:
            return None
        return outcomes[0]

    def test_teach_lesson_scope_allows_knowledge_or_skill(self):
        root = Path(__file__).resolve().parents[1]
        skill = (root / "skills" / "my-teach" / "SKILL.md").read_text()
        lesson_definition = next(
            line for line in skill.splitlines() if "`./lessons/*.html`" in line
        )

        self.assertIn("一项范围明确的内容", lesson_definition)
        self.assertIn("与任务紧密关联", lesson_definition)

    def test_teach_restoration_records_complete_translated_parity(self):
        root = Path(__file__).resolve().parents[1]
        skill_dir = root / "skills" / "my-teach"
        documents = {
            "SKILL.md": (skill_dir / "SKILL.md").read_text(),
            "GLOSSARY-FORMAT.md": (
                skill_dir / "GLOSSARY-FORMAT.md"
            ).read_text(),
            "LEARNING-RECORD-FORMAT.md": (
                skill_dir / "LEARNING-RECORD-FORMAT.md"
            ).read_text(),
            "MISSION-FORMAT.md": (
                skill_dir / "MISSION-FORMAT.md"
            ).read_text(),
            "RESOURCES-FORMAT.md": (
                skill_dir / "RESOURCES-FORMAT.md"
            ).read_text(),
        }
        fidelity = json.loads((root / "upstream" / "fidelity.json").read_text())
        entry = next(
            item
            for item in fidelity["skills"]
            if item["local_skill"] == "my-teach"
        )

        self.assertEqual("skills/productivity/teach", entry["upstream_path"])
        expected_mappings = {
            "SKILL.md#Teaching Workspace": ("SKILL.md", "教学工作区"),
            "SKILL.md#Philosophy": ("SKILL.md", "教学理念"),
            "SKILL.md#Fluency vs Storage Strength": (
                "SKILL.md",
                "流畅度与存储强度",
            ),
            "SKILL.md#Lessons": ("SKILL.md", "课程"),
            "SKILL.md#Assets": ("SKILL.md", "资源组件"),
            "SKILL.md#The Mission": ("SKILL.md", "学习任务"),
            "SKILL.md#Zone Of Proximal Development": (
                "SKILL.md",
                "最近发展区",
            ),
            "SKILL.md#Knowledge": ("SKILL.md", "知识"),
            "SKILL.md#Skills": ("SKILL.md", "技能"),
            "SKILL.md#Acquiring Wisdom": ("SKILL.md", "获取智慧"),
            "SKILL.md#Reference Documents": ("SKILL.md", "参考文档"),
            "SKILL.md#`NOTES.md`": ("SKILL.md", "`NOTES.md`"),
            "GLOSSARY-FORMAT.md#GLOSSARY.md Format": (
                "GLOSSARY-FORMAT.md",
                "GLOSSARY.md 格式",
            ),
            "GLOSSARY-FORMAT.md#Structure": (
                "GLOSSARY-FORMAT.md",
                "结构",
            ),
            "GLOSSARY-FORMAT.md#Rules": ("GLOSSARY-FORMAT.md", "规则"),
            "LEARNING-RECORD-FORMAT.md#Learning Record Format": (
                "LEARNING-RECORD-FORMAT.md",
                "学习记录格式",
            ),
            "LEARNING-RECORD-FORMAT.md#Template": (
                "LEARNING-RECORD-FORMAT.md",
                "模板",
            ),
            "LEARNING-RECORD-FORMAT.md#Optional sections": (
                "LEARNING-RECORD-FORMAT.md",
                "可选章节",
            ),
            "LEARNING-RECORD-FORMAT.md#Numbering": (
                "LEARNING-RECORD-FORMAT.md",
                "编号",
            ),
            "LEARNING-RECORD-FORMAT.md#When to write a learning record": (
                "LEARNING-RECORD-FORMAT.md",
                "何时编写学习记录",
            ),
            "LEARNING-RECORD-FORMAT.md#What does _not_ qualify": (
                "LEARNING-RECORD-FORMAT.md",
                "不符合条件的情形",
            ),
            "LEARNING-RECORD-FORMAT.md#Supersession": (
                "LEARNING-RECORD-FORMAT.md",
                "取代",
            ),
            "MISSION-FORMAT.md#MISSION.md Format": (
                "MISSION-FORMAT.md",
                "MISSION.md 格式",
            ),
            "MISSION-FORMAT.md#Template": ("MISSION-FORMAT.md", "模板"),
            "MISSION-FORMAT.md#Rules": ("MISSION-FORMAT.md", "规则"),
            "RESOURCES-FORMAT.md#RESOURCES.md Format": (
                "RESOURCES-FORMAT.md",
                "RESOURCES.md 格式",
            ),
            "RESOURCES-FORMAT.md#Structure": (
                "RESOURCES-FORMAT.md",
                "结构",
            ),
            "RESOURCES-FORMAT.md#Rules": ("RESOURCES-FORMAT.md", "规则"),
        }
        for field in ("complete", "translated"):
            mappings = entry["sections"][field]
            self.assertEqual(expected_mappings.keys(), {item["upstream"] for item in mappings})
            for mapping in mappings:
                with self.subTest(field=field, section=mapping["upstream"]):
                    document, heading = expected_mappings[mapping["upstream"]]
                    self.assertEqual(heading, mapping["local"])
                    self.assertIn(heading, documents[document])
                    self.assertRegex(mapping["evidence"], r"\.md#")
        self.assertEqual([], entry["sections"]["missing"])
        self.assertEqual([], entry["sections"]["local_added"])
        self.assertEqual(
            {
                "GLOSSARY-FORMAT.md": "d177def491519d97873291f2e860d8f1d60ead78feecb82eee022177958069c6",
                "LEARNING-RECORD-FORMAT.md": "855f81017625256584bbf62bd5edb9b0c86605c4cc1139c56acc36b802595d17",
                "MISSION-FORMAT.md": "8da6d3ac84eb2eb19f17c260b6acf01c560d3ac7a4501c415eea0e985602f4d7",
                "RESOURCES-FORMAT.md": "2bc634a64b0d0daa10904f9222e7aa0d361420dfacabbf092fbe3a72222edc08",
                "SKILL.md": "6d2dbe5e03084cf26fef66b535127b36cd1bcbe9478e26b0626029cd51dc2259",
                "agents/openai.yaml": "5856f3ae8aec742f1499c640aecdd5f1d6af5fa210a7c6ec794de8263a6f733f",
            },
            entry["support_files"],
        )
        metadata = skill_dir / "agents" / "openai.yaml"
        self.assertTrue(metadata.is_file(), "missing local manual-only metadata")
        self.assertEqual(
            hashlib.sha256(metadata.read_bytes()).hexdigest(),
            entry["local_support_files"]["agents/openai.yaml"],
        )
        self.assertIn("allow_implicit_invocation: false", metadata.read_text())
        self.assertEqual(
            [
                {
                    "path": "SKILL.md",
                    "adaptation": "保留本地名称和手动调用元数据；不改变上游方法。",
                }
            ],
            entry["allowed_local_adaptations"],
        )
        self.assertEqual("faithful", entry["conclusion"])
        self.assertEqual(
            "upstream/evidence/teach-restoration.md",
            entry["evidence_path"],
        )

    def test_teach_scenarios_apply_retrieved_constraints(self):
        root = Path(__file__).resolve().parents[1]
        skill_dir = root / "skills" / "my-teach"
        fixture_path = root / "tests" / "fixtures" / "teach_application.json"
        self.assertTrue(fixture_path.is_file(), "missing teach application fixture")
        fixture = json.loads(fixture_path.read_text())
        self.assertEqual("skills/productivity/teach", fixture["source_path"])
        self.assertEqual(
            {
                "zpd-selection",
                "storage-strength",
                "mission-revision",
                "learning-record",
                "glossary-promotion",
                "resources-curation",
            },
            {case["id"] for case in fixture["scenarios"]},
        )
        documents = {
            "SKILL.md": (skill_dir / "SKILL.md").read_text(),
            "GLOSSARY-FORMAT.md": (
                skill_dir / "GLOSSARY-FORMAT.md"
            ).read_text(),
            "LEARNING-RECORD-FORMAT.md": (
                skill_dir / "LEARNING-RECORD-FORMAT.md"
            ).read_text(),
            "MISSION-FORMAT.md": (
                skill_dir / "MISSION-FORMAT.md"
            ).read_text(),
            "RESOURCES-FORMAT.md": (
                skill_dir / "RESOURCES-FORMAT.md"
            ).read_text(),
        }
        for case in fixture["scenarios"]:
            with self.subTest(scenario=case["id"]):
                self.assertIsInstance(case["input"], dict)
                self.assertTrue(case["retrieved_constraints"])
                constraint_ids = set()
                for constraint in case["retrieved_constraints"]:
                    self.assertNotIn(constraint["id"], constraint_ids)
                    constraint_ids.add(constraint["id"])
                    self.assertIn(constraint["document"], documents)
                    self.assertIn(
                        constraint["text"], documents[constraint["document"]]
                    )
                self.assertTrue(case["constraint_mapping"])
                for mapping in case["constraint_mapping"]:
                    self.assertTrue(mapping["when"])
                    self.assertTrue(mapping["constraints"])
                    self.assertTrue(set(mapping["constraints"]) <= constraint_ids)
                    self.assertEqual(case["expected"], mapping["outcome"])
                self.assertEqual(
                    case["expected"],
                    self._apply_teach_constraint_mapping(case),
                )


class ImproveCodebaseArchitectureParityTests(unittest.TestCase):
    @staticmethod
    def _section_contents(document, source_section):
        _, separator, heading = source_section.partition("#")
        if not separator or not heading:
            return None
        heading_match = re.search(
            rf"^(?P<markers>#+)\s+{re.escape(heading)}\s*$",
            document,
            re.MULTILINE,
        )
        if heading_match is None:
            return None
        next_heading = re.search(
            rf"^#{{1,{len(heading_match['markers'])}}}\s+",
            document[heading_match.end() :],
            re.MULTILINE,
        )
        section_end = (
            heading_match.end() + next_heading.start()
            if next_heading is not None
            else len(document)
        )
        return document[heading_match.end() : section_end]

    @staticmethod
    def _apply_architecture_rules(input_facts, retrieved_constraints, rules):
        outcomes = [
            rule["outcome"]
            for rule in rules
            if all(
                input_facts.get(field) == expected
                for field, expected in rule["when"].items()
            )
            and set(rule["requires_constraints"])
            <= {constraint["id"] for constraint in retrieved_constraints}
        ]
        if len(outcomes) != 1:
            return None
        return outcomes[0]

    def test_architecture_restoration_records_translated_parity(self):
        root = Path(__file__).resolve().parents[1]
        skill_dir = root / "skills" / "my-improve-codebase-architecture"
        documents = {
            "SKILL.md": (skill_dir / "SKILL.md").read_text(),
            "HTML-REPORT.md": (skill_dir / "HTML-REPORT.md").read_text(),
        }
        fidelity = json.loads((root / "upstream" / "fidelity.json").read_text())
        entry = next(
            item
            for item in fidelity["skills"]
            if item["local_skill"] == "my-improve-codebase-architecture"
        )

        self.assertEqual(
            "skills/engineering/improve-codebase-architecture",
            entry["upstream_path"],
        )
        expected_mappings = {
            "SKILL.md#Improve Codebase Architecture": ("SKILL.md", "改进代码库架构"),
            "SKILL.md#Process": ("SKILL.md", "流程"),
            "SKILL.md#1. Explore": ("SKILL.md", "1. 探索"),
            "SKILL.md#2. Present candidates as an HTML report": (
                "SKILL.md",
                "2. 将候选项呈现为 HTML 报告",
            ),
            "SKILL.md#3. Grilling loop": ("SKILL.md", "3. 深挖循环"),
            "HTML-REPORT.md#HTML Report Format": ("HTML-REPORT.md", "HTML 报告格式"),
            "HTML-REPORT.md#Scaffold": ("HTML-REPORT.md", "骨架"),
            "HTML-REPORT.md#Header": ("HTML-REPORT.md", "页首"),
            "HTML-REPORT.md#Candidate card": ("HTML-REPORT.md", "候选项卡片"),
            "HTML-REPORT.md#Diagram patterns": ("HTML-REPORT.md", "图示模式"),
            "HTML-REPORT.md#Mermaid graph (the workhorse for dependencies / call flow)": (
                "HTML-REPORT.md",
                "Mermaid 图（依赖关系与调用流程的主力）",
            ),
            "HTML-REPORT.md#Hand-built boxes-and-arrows (when Mermaid's layout fights you)": (
                "HTML-REPORT.md",
                "手工绘制的方框与箭头（当 Mermaid 布局不适用时）",
            ),
            "HTML-REPORT.md#Cross-section (good for layered shallowness)": (
                "HTML-REPORT.md",
                "横截面图（适合分层的浅薄性）",
            ),
            "HTML-REPORT.md#Mass diagram (good for \"interface as wide as implementation\")": (
                "HTML-REPORT.md",
                "面积图（适合“接口与实现一样宽”）",
            ),
            "HTML-REPORT.md#Call-graph collapse": (
                "HTML-REPORT.md",
                "调用图折叠",
            ),
            "HTML-REPORT.md#Style guidance": ("HTML-REPORT.md", "样式指南"),
            "HTML-REPORT.md#Top recommendation section": (
                "HTML-REPORT.md",
                "首要推荐部分",
            ),
            "HTML-REPORT.md#Tone": ("HTML-REPORT.md", "语气"),
        }
        for field in ("complete", "translated"):
            mappings = entry["sections"][field]
            self.assertEqual(expected_mappings.keys(), {item["upstream"] for item in mappings})
            for mapping in mappings:
                with self.subTest(field=field, section=mapping["upstream"]):
                    document, heading = expected_mappings[mapping["upstream"]]
                    self.assertEqual(heading, mapping["local"])
                    self.assertIn(heading, documents[document])
                    self.assertRegex(mapping["evidence"], r"(SKILL|HTML-REPORT)\.md#")
        self.assertEqual([], entry["sections"]["missing"])
        self.assertEqual([], entry["sections"]["local_added"])
        self.assertEqual(
            {
                "HTML-REPORT.md": (
                    "0b0936104158abeef7246ff6cbabefa4dc055f17589f2833f2d93001421910a1"
                ),
                "SKILL.md": (
                    "4b4cb798c3863d5b6f5c0b4604af1ecb5beb6df82553c972898a91ba38bcf289"
                ),
                "agents/openai.yaml": (
                    "c8cb20f68ebf0edb4e497bc11ae5fcaa196004e661cd189015b04f4109ced7f1"
                ),
            },
            entry["support_files"],
        )
        metadata = skill_dir / "agents" / "openai.yaml"
        self.assertEqual(
            hashlib.sha256(metadata.read_bytes()).hexdigest(),
            entry["local_support_files"]["agents/openai.yaml"],
        )
        self.assertEqual(
            [
                {
                    "path": "SKILL.md",
                    "adaptation": "保留本地名称和手动调用元数据；不改变上游方法。",
                },
                {
                    "path": "SKILL.md#2. 将候选项呈现为 HTML 报告, HTML-REPORT.md",
                    "adaptation": (
                        "单一离线报告适配：为满足本地离线报告要求，保留所有上游"
                        "语义，同时将 Tailwind/Mermaid 的远程依赖改为内联 CSS/SVG "
                        "与本地可用的静态图示。"
                    ),
                },
            ],
            entry["allowed_local_adaptations"],
        )
        self.assertEqual("faithful", entry["conclusion"])
        self.assertEqual(
            "upstream/evidence/improve-codebase-architecture-restoration.md",
            entry["evidence_path"],
        )

        skill = documents["SKILL.md"]
        report = documents["HTML-REPORT.md"]
        report_instructions = self._section_contents(
            skill,
            "SKILL.md#2. 将候选项呈现为 HTML 报告",
        )
        self.assertIsNotNone(report_instructions)
        self.assertNotRegex(
            report_instructions,
            r"(?i)tailwind|mermaid|cdn|远程(?:依赖|脚本)",
        )
        for offline_instruction in ("内联 CSS", "内联 SVG", "静态图示"):
            with self.subTest(offline_instruction=offline_instruction):
                self.assertIn(offline_instruction, report_instructions)
        for instruction in (
            "范围先于扫描——YAGNI",
            "删除测试",
            "不要先提出接口",
            "用户选择候选项后",
            "添加该术语到 `CONTEXT.md`",
            "未来的架构审查不再重新建议它",
        ):
            with self.subTest(instruction=instruction):
                self.assertIn(instruction, skill)
        self.assertNotIn("https://cdn.tailwindcss.com", report)
        self.assertNotIn("https://cdn.jsdelivr.net", report)
        for report_requirement in (
            "每个候选项都要有前后对比图",
            "首要推荐",
            "模块",
            "接口",
            "局部性",
            "杠杆",
        ):
            with self.subTest(report_requirement=report_requirement):
                self.assertIn(report_requirement, report)

    def test_architecture_scenarios_apply_retrieved_constraints(self):
        root = Path(__file__).resolve().parents[1]
        skill_dir = root / "skills" / "my-improve-codebase-architecture"
        fixture_path = root / "tests" / "fixtures" / "architecture_application.json"
        self.assertTrue(
            fixture_path.is_file(),
            "missing architecture retrieval/application fixture",
        )
        fixture = json.loads(fixture_path.read_text())
        self.assertEqual(
            "skills/engineering/improve-codebase-architecture",
            fixture["source_path"],
        )
        self.assertEqual(2, fixture["version"])
        self.assertEqual(
            {
                "exploration-before-recommendation",
                "yagni-rejection",
                "report-recommendation",
                "grilling-domain-modeling-loop",
            },
            {case["id"] for case in fixture["scenarios"]},
        )
        self.assertTrue(fixture["rules"])
        rules = fixture["rules"]
        rule_ids = set()
        for rule in rules:
            self.assertNotIn(rule["id"], rule_ids)
            rule_ids.add(rule["id"])
            self.assertTrue(rule["when"])
            self.assertTrue(rule["requires_constraints"])
            self.assertNotIn("id", rule["when"])
            self.assertIsInstance(rule["outcome"], dict)
        documents = {
            "SKILL.md": (skill_dir / "SKILL.md").read_text(),
            "HTML-REPORT.md": (skill_dir / "HTML-REPORT.md").read_text(),
        }
        for case in fixture["scenarios"]:
            with self.subTest(scenario=case["id"]):
                self.assertIsInstance(case["input"], dict)
                self.assertTrue(case["retrieved_constraints"])
                constraint_ids = set()
                for constraint in case["retrieved_constraints"]:
                    self.assertNotIn(constraint["id"], constraint_ids)
                    constraint_ids.add(constraint["id"])
                    self.assertIn(constraint["document"], documents)
                    self.assertTrue(constraint["source_section"])
                    self.assertEqual(
                        constraint["document"],
                        constraint["source_section"].split("#", 1)[0],
                    )
                    section_contents = self._section_contents(
                        documents[constraint["document"]],
                        constraint["source_section"],
                    )
                    self.assertIsNotNone(section_contents)
                    self.assertIn(
                        constraint["text"],
                        section_contents,
                    )
                self.assertEqual(
                    case["expected"],
                    self._apply_architecture_rules(
                        case["input"],
                        case["retrieved_constraints"],
                        rules,
                    ),
                )


class ToQuestionnaireParityTests(unittest.TestCase):
    @staticmethod
    def _section_contents(document, source_section):
        _, separator, heading = source_section.partition("#")
        if not separator or not heading:
            return None
        heading_match = re.search(
            rf"^(?P<markers>#+)\s+{re.escape(heading)}\s*$",
            document,
            re.MULTILINE,
        )
        if heading_match is None:
            return None
        next_heading = re.search(
            rf"^#{{1,{len(heading_match['markers'])}}}\s+",
            document[heading_match.end() :],
            re.MULTILINE,
        )
        section_end = (
            heading_match.end() + next_heading.start()
            if next_heading is not None
            else len(document)
        )
        return document[heading_match.end() : section_end]

    @staticmethod
    def _apply_questionnaire_rules(input_facts, retrieved_constraints, rules):
        outcomes = [
            rule["outcome"]
            for rule in rules
            if all(
                input_facts.get(field) == expected
                for field, expected in rule["when"].items()
            )
            and set(rule["requires_constraints"])
            <= {constraint["id"] for constraint in retrieved_constraints}
        ]
        if len(outcomes) != 1:
            return None
        return outcomes[0]

    def test_questionnaire_restoration_records_complete_translated_parity(self):
        root = Path(__file__).resolve().parents[1]
        skill_dir = root / "skills" / "my-to-questionnaire"
        skill = (skill_dir / "SKILL.md").read_text()
        fidelity = json.loads((root / "upstream" / "fidelity.json").read_text())
        entry = next(
            item
            for item in fidelity["skills"]
            if item["local_skill"] == "my-to-questionnaire"
        )

        self.assertEqual(
            "skills/in-progress/to-questionnaire", entry["upstream_path"]
        )
        upstream_metadata = (
            root
            / ".superpowers/sdd/mattpocock-skills-pinned"
            / entry["upstream_path"]
            / "agents/openai.yaml"
        ).read_text()
        self.assertIn('display_name: "To Questionnaire"', upstream_metadata)
        expected_mappings = {
            "agents/openai.yaml#interface.display_name": (
                "SKILL.md",
                "生成发现问卷",
            ),
            "SKILL.md#Questionnaire workflow": (
                "SKILL.md",
                "生成发现问卷",
            ),
            "SKILL.md#Document structure": ("SKILL.md", "文档结构"),
        }
        for field in ("complete", "translated"):
            mappings = entry["sections"][field]
            self.assertEqual(
                expected_mappings.keys(), {item["upstream"] for item in mappings}
            )
            for mapping in mappings:
                with self.subTest(field=field, section=mapping["upstream"]):
                    document, heading = expected_mappings[mapping["upstream"]]
                    self.assertEqual(heading, mapping["local"])
                    self.assertIn(heading, skill)
                    self.assertRegex(mapping["evidence"], r"SKILL\.md#")
                    if mapping["upstream"] == "agents/openai.yaml#interface.display_name":
                        self.assertIn(
                            "metadata-to-local-title translation/adaptation",
                            mapping["evidence"],
                        )
        self.assertEqual([], entry["sections"]["missing"])
        self.assertEqual([], entry["sections"]["local_added"])
        self.assertEqual(
            {
                "SKILL.md": (
                    "8e7f9ed8d7b2e66babf1a54aee9b94319bf38c32619cffe78819df6518ead5fc"
                ),
                "agents/openai.yaml": (
                    "9e8a06c38c8842eea8d4922cb9d1ead8e3ace647bab259b943c994a1b4742bc2"
                ),
            },
            entry["support_files"],
        )
        metadata = skill_dir / "agents" / "openai.yaml"
        self.assertEqual(
            hashlib.sha256(metadata.read_bytes()).hexdigest(),
            entry["local_support_files"]["agents/openai.yaml"],
        )
        self.assertEqual(
            [
                {
                    "path": "SKILL.md",
                    "adaptation": (
                        "将上游 agents/openai.yaml#interface.display_name（"
                        "“To Questionnaire”）翻译/适配为本地文档标题 "
                        "SKILL.md#生成发现问卷；保留本地手动调用元数据；"
                        "不改变上游方法。"
                    ),
                }
            ],
            entry["allowed_local_adaptations"],
        )
        self.assertEqual("faithful", entry["conclusion"])
        self.assertEqual(
            "upstream/evidence/to-questionnaire-restoration.md",
            entry["evidence_path"],
        )

        for instruction in (
            "只就“发送”采访用户，而不要就主题采访用户",
            "收件人的角色、专长以及与用户的关系",
            "用户必须在拿到答案后能够做出或决定什么",
            "当前目录中的 `to-questionnaire-<slug>.md`",
            "步骤 2 中用户列出的每一项都由一个问题覆盖",
            "异步意味着你可能只能获得一次回复",
            "每个问题只问一个概念",
            "答案留白",
            "还有什么遗漏？",
            "部分答案和“我不知道”同样有用",
        ):
            with self.subTest(instruction=instruction):
                self.assertIn(instruction, skill)
        self.assertNotIn("项目策略优先", skill)

    def test_questionnaire_scenarios_apply_section_bounded_constraints(self):
        root = Path(__file__).resolve().parents[1]
        skill_dir = root / "skills" / "my-to-questionnaire"
        fixture_path = (
            root / "tests" / "fixtures" / "questionnaire_application.json"
        )
        self.assertTrue(
            fixture_path.is_file(),
            "missing questionnaire retrieval/application fixture",
        )
        fixture = json.loads(fixture_path.read_text())
        self.assertEqual(
            "skills/in-progress/to-questionnaire", fixture["source_path"]
        )
        self.assertEqual(
            {
                "questionnaire-structure",
                "asking-one-useful-question",
                "scope-and-ambiguity",
                "done-when",
            },
            {case["id"] for case in fixture["scenarios"]},
        )
        self.assertTrue(fixture["rules"])
        for rule in fixture["rules"]:
            self.assertTrue(rule["when"])
            self.assertTrue(rule["requires_constraints"])
            self.assertIsInstance(rule["outcome"], dict)

        documents = {"SKILL.md": (skill_dir / "SKILL.md").read_text()}
        for case in fixture["scenarios"]:
            with self.subTest(scenario=case["id"]):
                self.assertIsInstance(case["input"], dict)
                self.assertTrue(case["retrieved_constraints"])
                constraint_ids = set()
                for constraint in case["retrieved_constraints"]:
                    self.assertNotIn(constraint["id"], constraint_ids)
                    constraint_ids.add(constraint["id"])
                    self.assertIn(constraint["document"], documents)
                    section_contents = self._section_contents(
                        documents[constraint["document"]],
                        constraint["source_section"],
                    )
                    self.assertIsNotNone(section_contents)
                    self.assertIn(constraint["text"], section_contents)
                self.assertEqual(
                    case["expected"],
                    self._apply_questionnaire_rules(
                        case["input"],
                        case["retrieved_constraints"],
                        fixture["rules"],
                    ),
                )


class TddParityTests(unittest.TestCase):
    @staticmethod
    def _apply_tdd_rules(input_facts, retrieved_constraints, rules):
        outcomes = [
            rule["outcome"]
            for rule in rules
            if all(
                input_facts.get(field) == expected
                for field, expected in rule["when"].items()
            )
            and set(rule["requires_constraints"])
            <= {constraint["id"] for constraint in retrieved_constraints}
        ]
        if len(outcomes) != 1:
            return None
        return outcomes[0]

    def test_tdd_audit_records_source_local_deltas_and_application_scenarios(self):
        root = Path(__file__).resolve().parents[1]
        skill_dir = root / "skills" / "my-tdd"
        source_dir = (
            root
            / ".superpowers/sdd/mattpocock-skills-pinned"
            / "skills/engineering/tdd"
        )
        source_files = {
            "SKILL.md": source_dir / "SKILL.md",
            "mocking.md": source_dir / "mocking.md",
            "tests.md": source_dir / "tests.md",
            "agents/openai.yaml": source_dir / "agents/openai.yaml",
        }
        fidelity = json.loads((root / "upstream" / "fidelity.json").read_text())
        entry = next(
            (
                item
                for item in fidelity["skills"]
                if item["local_skill"] == "my-tdd"
            ),
            None,
        )
        evidence_path = root / "upstream/evidence/tdd-audit.md"
        fixture_path = root / "tests/fixtures/tdd_application.json"

        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual("engineering/tdd", entry["upstream_path"])
        self.assertEqual(
            {
                name: hashlib.sha256(path.read_bytes()).hexdigest()
                for name, path in source_files.items()
            },
            entry["support_files"],
        )
        self.assertIn("local_support_files", entry)
        self.assertEqual(
            {
                name: hashlib.sha256((skill_dir / name).read_bytes()).hexdigest()
                for name in source_files
            },
            entry["local_support_files"],
        )
        self.assertIn(
            entry["conclusion"],
            {"faithful", "restore-required", "adapter-rework-required"},
        )
        self.assertEqual("upstream/evidence/tdd-audit.md", entry["evidence_path"])
        self.assertTrue(evidence_path.is_file())
        evidence = evidence_path.read_text()
        for text in (
            "2ab958093e83e0ec752e6c1c5932da465bf23e0c",
            "skills/engineering/tdd",
            "SKILL.md",
            "mocking.md",
            "tests.md",
            "agents/openai.yaml",
            "Source files and SHA-256",
            "Local files and SHA-256",
            f"Conclusion: **{entry['conclusion']}**",
        ):
            with self.subTest(evidence=text):
                self.assertIn(text, evidence)

        self.assertTrue(fixture_path.is_file())
        fixture = json.loads(fixture_path.read_text())
        self.assertEqual("engineering/tdd", fixture["source_path"])
        self.assertEqual(
            {"red-green-slice", "mock-only-system-boundary"},
            {scenario["id"] for scenario in fixture["scenarios"]},
        )
        local_documents = {
            name: (skill_dir / name).read_text()
            for name in ("SKILL.md", "mocking.md", "tests.md")
        }
        for constraint in fixture["constraints"]:
            with self.subTest(constraint=constraint["id"]):
                self.assertIn(constraint["document"], local_documents)
                self.assertIn(
                    constraint["text"],
                    local_documents[constraint["document"]],
                )
                self.assertIn("#", constraint["source_section"])

        for scenario in fixture["scenarios"]:
            with self.subTest(scenario=scenario["id"]):
                self.assertTrue(scenario["retrieved_constraints"])
                self.assertEqual(
                    scenario["expected"],
                    self._apply_tdd_rules(
                        scenario["input"],
                        scenario["retrieved_constraints"],
                        fixture["rules"],
                    ),
                )


class GrillingParityTests(unittest.TestCase):
    @staticmethod
    def _apply_grilling_rules(input_facts, retrieved_constraints, rules):
        outcomes = [
            rule["outcome"]
            for rule in rules
            if all(
                input_facts.get(field) == expected
                for field, expected in rule["when"].items()
            )
            and set(rule["requires_constraints"])
            <= {constraint["id"] for constraint in retrieved_constraints}
        ]
        if len(outcomes) != 1:
            return None
        return outcomes[0]

    def test_grilling_audit_records_source_local_delta_and_retrieval_scenarios(self):
        root = Path(__file__).resolve().parents[1]
        skill_dir = root / "skills" / "my-grilling"
        source_dir = (
            root
            / ".superpowers/sdd/mattpocock-skills-pinned"
            / "skills/productivity/grilling"
        )
        fidelity = json.loads((root / "upstream" / "fidelity.json").read_text())
        entry = next(
            (
                item
                for item in fidelity["skills"]
                if item["local_skill"] == "my-grilling"
            ),
            None,
        )
        evidence_path = root / "upstream/evidence/grilling-audit.md"
        fixture_path = root / "tests/fixtures/grilling_application.json"
        source_skill = (source_dir / "SKILL.md").read_text()
        source_metadata = (source_dir / "agents/openai.yaml").read_text()
        local_skill = (skill_dir / "SKILL.md").read_text()
        local_metadata = (skill_dir / "agents/openai.yaml").read_text()

        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual("productivity/grilling", entry["upstream_path"])
        self.assertEqual(
            {
                "SKILL.md": hashlib.sha256(
                    (source_dir / "SKILL.md").read_bytes()
                ).hexdigest(),
                "agents/openai.yaml": hashlib.sha256(
                    (source_dir / "agents/openai.yaml").read_bytes()
                ).hexdigest(),
            },
            entry["support_files"],
        )
        self.assertEqual(
            hashlib.sha256((skill_dir / "agents/openai.yaml").read_bytes()).hexdigest(),
            entry["local_support_files"]["agents/openai.yaml"],
        )
        self.assertEqual(
            [
                "SKILL.md#document-body",
                "agents/openai.yaml#interface.display_name",
                "agents/openai.yaml#interface.short_description",
            ],
            entry["sections"]["upstream"],
        )
        self.assertEqual(
            {
                "SKILL.md#document-body",
                "agents/openai.yaml#interface.display_name",
            },
            {mapping["upstream"] for mapping in entry["sections"]["complete"]},
        )
        self.assertEqual(
            {
                "SKILL.md#document-body",
                "agents/openai.yaml#interface.display_name",
            },
            {mapping["upstream"] for mapping in entry["sections"]["translated"]},
        )
        self.assertEqual([], entry["sections"]["missing"])
        self.assertEqual(
            [
                "SKILL.md#项目策略优先",
                "agents/openai.yaml#policy",
            ],
            entry["sections"]["local_added"],
        )
        short_description_delta = next(
            (
                adaptation
                for adaptation in entry["allowed_local_adaptations"]
                if adaptation["path"] == "agents/openai.yaml#interface.short_description"
            ),
            None,
        )
        self.assertIsNotNone(short_description_delta)
        assert short_description_delta is not None
        self.assertIn("缩窄", short_description_delta["adaptation"])
        self.assertIn("Plan 2", short_description_delta["adaptation"])
        self.assertEqual("adapter-rework-required", entry["conclusion"])
        self.assertEqual("upstream/evidence/grilling-audit.md", entry["evidence_path"])
        self.assertTrue(evidence_path.is_file())
        evidence = evidence_path.read_text()
        for text in (
            "2ab958093e83e0ec752e6c1c5932da465bf23e0c",
            "SKILL.md",
            "agents/openai.yaml",
            "项目策略优先",
            "Plan 2",
        ):
            with self.subTest(evidence=text):
                self.assertIn(text, evidence)
        self.assertIn("Interview me relentlessly", source_skill)
        self.assertIn("持续就此事的每个方面高强度访谈", local_skill)
        self.assertIn('display_name: "Grilling"', source_metadata)
        self.assertIn('display_name: "Grilling"', local_metadata)
        self.assertTrue(fixture_path.is_file())

        fixture = json.loads(fixture_path.read_text())
        self.assertEqual("productivity/grilling", fixture["source_path"])
        self.assertEqual(
            {
                "look-up-facts",
                "interview-decisions",
                "wait-for-shared-understanding",
            },
            {scenario["id"] for scenario in fixture["scenarios"]},
        )
        constraint_ids = set()
        for constraint in fixture["constraints"]:
            self.assertNotIn(constraint["id"], constraint_ids)
            constraint_ids.add(constraint["id"])
            self.assertEqual("SKILL.md", constraint["document"])
            self.assertEqual("SKILL.md#document-body", constraint["source_section"])
            self.assertIn(constraint["text"], local_skill)

        rules = fixture["rules"]
        self.assertTrue(rules)
        for scenario in fixture["scenarios"]:
            with self.subTest(scenario=scenario["id"]):
                retrieved_constraints = scenario["retrieved_constraints"]
                self.assertTrue(retrieved_constraints)
                self.assertEqual(
                    scenario["expected"],
                    self._apply_grilling_rules(
                        scenario["input"], retrieved_constraints, rules
                    ),
                )


class DomainModelingParityTests(unittest.TestCase):
    @staticmethod
    def _apply_domain_modeling_rules(
        input_facts, retrieved_constraints, rules, policy=None
    ):
        outcomes = [
            rule["outcome"]
            for rule in rules
            if (policy is None or rule.get("policy") == policy)
            and all(
                input_facts.get(field) == expected
                for field, expected in rule["when"].items()
            )
            and set(rule["requires_constraints"])
            <= {constraint["id"] for constraint in retrieved_constraints}
        ]
        if len(outcomes) != 1:
            return None
        return outcomes[0]

    def test_domain_modeling_audit_records_parity_deltas_and_scenarios(self):
        root = Path(__file__).resolve().parents[1]
        skill_dir = root / "skills" / "my-domain-modeling"
        source_dir = (
            root
            / ".superpowers/sdd/mattpocock-skills-pinned"
            / "skills/engineering/domain-modeling"
        )
        fidelity = json.loads((root / "upstream" / "fidelity.json").read_text())
        entry = next(
            (
                item
                for item in fidelity["skills"]
                if item["local_skill"] == "my-domain-modeling"
            ),
            None,
        )
        evidence_path = root / "upstream/evidence/domain-modeling-audit.md"
        fixture_path = root / "tests/fixtures/domain_modeling_application.json"
        source_files = {
            "SKILL.md": source_dir / "SKILL.md",
            "CONTEXT-FORMAT.md": source_dir / "CONTEXT-FORMAT.md",
            "ADR-FORMAT.md": source_dir / "ADR-FORMAT.md",
            "agents/openai.yaml": source_dir / "agents/openai.yaml",
        }
        source_sections = {
            "SKILL.md#frontmatter.name",
            "SKILL.md#frontmatter.description",
            "SKILL.md#File structure",
            "SKILL.md#Challenge against the glossary",
            "SKILL.md#Sharpen fuzzy language",
            "SKILL.md#Discuss concrete scenarios",
            "SKILL.md#Cross-reference with code",
            "SKILL.md#Update CONTEXT.md inline",
            "SKILL.md#Offer ADRs sparingly",
            "CONTEXT-FORMAT.md#Structure",
            "CONTEXT-FORMAT.md#Rules",
            "CONTEXT-FORMAT.md#Single vs multi-context repos",
            "ADR-FORMAT.md#Template",
            "ADR-FORMAT.md#Optional sections",
            "ADR-FORMAT.md#Numbering",
            "ADR-FORMAT.md#When to offer an ADR",
            "ADR-FORMAT.md#What qualifies",
            "agents/openai.yaml#interface.display_name",
            "agents/openai.yaml#interface.short_description",
        }

        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual("engineering/domain-modeling", entry["upstream_path"])
        self.assertEqual(
            {
                name: hashlib.sha256(path.read_bytes()).hexdigest()
                for name, path in source_files.items()
            },
            entry["support_files"],
        )
        self.assertEqual(source_sections, set(entry["sections"]["upstream"]))
        translated = {
            mapping["upstream"]
            for bucket in ("complete", "translated")
            for mapping in entry["sections"][bucket]
        }
        changed_upstream_sections = {
            "SKILL.md#frontmatter.name",
            "SKILL.md#frontmatter.description",
            "SKILL.md#File structure",
            "SKILL.md#Update CONTEXT.md inline",
            "CONTEXT-FORMAT.md#Single vs multi-context repos",
        }
        adaptation_sections = {
            section
            for adaptation in entry["allowed_local_adaptations"]
            for section in adaptation.get("upstream_sections", [])
        }
        self.assertEqual(
            source_sections - changed_upstream_sections,
            translated,
        )
        self.assertEqual(changed_upstream_sections, adaptation_sections)
        self.assertEqual([], entry["sections"]["missing"])
        self.assertIn("SKILL.md#项目策略优先", entry["sections"]["local_added"])
        self.assertIn(
            "SKILL.md#frontmatter.disable-model-invocation",
            entry["sections"]["local_added"],
        )
        self.assertIn("agents/openai.yaml#policy", entry["sections"]["local_added"])
        frontmatter_adaptations = {
            adaptation["path"]: adaptation
            for adaptation in entry["allowed_local_adaptations"]
            if adaptation["path"].startswith("SKILL.md#frontmatter.")
        }
        self.assertEqual(
            {
                "SKILL.md#frontmatter.name",
                "SKILL.md#frontmatter.description",
                "SKILL.md#frontmatter.disable-model-invocation",
            },
            set(frontmatter_adaptations),
        )
        self.assertEqual(
            "changed-local-adaptation",
            frontmatter_adaptations["SKILL.md#frontmatter.name"]["classification"],
        )
        self.assertEqual(
            "changed-local-adaptation",
            frontmatter_adaptations["SKILL.md#frontmatter.description"][
                "classification"
            ],
        )
        self.assertEqual(
            "local-only-adaptation",
            frontmatter_adaptations[
                "SKILL.md#frontmatter.disable-model-invocation"
            ]["classification"],
        )
        self.assertIn(
            "manual-only",
            frontmatter_adaptations[
                "SKILL.md#frontmatter.disable-model-invocation"
            ]["adaptation"],
        )
        self.assertEqual(
            hashlib.sha256(
                (skill_dir / "agents/openai.yaml").read_bytes()
            ).hexdigest(),
            entry["local_support_files"]["agents/openai.yaml"],
        )
        self.assertEqual("adapter-rework-required", entry["conclusion"])
        self.assertEqual(
            "upstream/evidence/domain-modeling-audit.md",
            entry["evidence_path"],
        )
        self.assertTrue(evidence_path.is_file())
        evidence = evidence_path.read_text()
        for text in (
            "2ab958093e83e0ec752e6c1c5932da465bf23e0c",
            "skills/engineering/domain-modeling",
            "CONTEXT-FORMAT.md",
            "ADR-FORMAT.md",
            "agents/openai.yaml",
            "项目策略优先",
            "frontmatter",
            "disable-model-invocation",
            "Plan 2",
        ):
            with self.subTest(evidence=text):
                self.assertIn(text, evidence)

        source_skill = source_files["SKILL.md"].read_text()
        local_skill = (skill_dir / "SKILL.md").read_text()
        self.assertIn("If unclear, ask.", source_files["CONTEXT-FORMAT.md"].read_text())
        self.assertIn("按 `decision_policy` 询问", local_skill)
        self.assertIn("均服从该生效策略", local_skill)
        self.assertIn("name: domain-modeling", source_skill)
        self.assertIn("name: my-domain-modeling", local_skill)
        self.assertIn(
            "description: Build and sharpen a project's domain model.",
            source_skill,
        )
        self.assertIn("description: 澄清领域术语、关系、边界和难以逆转的设计决策", local_skill)
        self.assertIn("disable-model-invocation: true", local_skill)
        self.assertIn("only when you have something to write", source_skill)
        self.assertIn("只有内容可写时才创建", local_skill)
        self.assertTrue(fixture_path.is_file())

        fixture = json.loads(fixture_path.read_text())
        self.assertEqual("engineering/domain-modeling", fixture["source_path"])
        self.assertEqual(
            {
                "route-multiple-contexts",
                "clarify-unclear-multiple-contexts",
                "record-resolved-term",
                "offer-adr-only-for-real-tradeoff",
            },
            {scenario["id"] for scenario in fixture["scenarios"]},
        )
        local_documents = {
            "SKILL.md": local_skill,
            "CONTEXT-FORMAT.md": (
                skill_dir / "CONTEXT-FORMAT.md"
            ).read_text(),
            "ADR-FORMAT.md": (skill_dir / "ADR-FORMAT.md").read_text(),
        }
        for constraint in fixture["constraints"]:
            with self.subTest(constraint=constraint["id"]):
                self.assertIn(constraint["document"], local_documents)
                self.assertIn(
                    constraint["text"],
                    local_documents[constraint["document"]],
                )

        for scenario in fixture["scenarios"]:
            with self.subTest(scenario=scenario["id"]):
                if isinstance(scenario["expected"], dict):
                    self.assertEqual(
                        "ask-for-clarification",
                        scenario["expected"]["upstream"],
                    )
                    self.assertEqual(
                        "record-routing-assumption",
                        scenario["expected"]["local"],
                    )
                    for policy, expected in scenario["expected"].items():
                        self.assertEqual(
                            expected,
                            self._apply_domain_modeling_rules(
                                scenario["input"],
                                scenario["retrieved_constraints"],
                                fixture["rules"],
                                policy,
                            ),
                        )
                else:
                    self.assertEqual(
                        scenario["expected"],
                        self._apply_domain_modeling_rules(
                            scenario["input"],
                            scenario["retrieved_constraints"],
                            fixture["rules"],
                        ),
                    )


class WizardParityTests(unittest.TestCase):
    @staticmethod
    def _section_contents(document, source_section):
        _, separator, heading = source_section.partition("#")
        if not separator or not heading:
            return None
        heading_match = re.search(
            rf"^(?P<markers>#+)\s+{re.escape(heading)}\s*$",
            document,
            re.MULTILINE,
        )
        if heading_match is None:
            return None
        next_heading = re.search(
            rf"^#{{1,{len(heading_match['markers'])}}}\s+",
            document[heading_match.end() :],
            re.MULTILINE,
        )
        section_end = (
            heading_match.end() + next_heading.start()
            if next_heading is not None
            else len(document)
        )
        return document[heading_match.end() : section_end]

    @staticmethod
    def _apply_wizard_rules(input_facts, retrieved_constraints, rules):
        outcomes = [
            rule["outcome"]
            for rule in rules
            if all(
                input_facts.get(field) == expected
                for field, expected in rule["when"].items()
            )
            and set(rule["requires_constraints"])
            <= {constraint["id"] for constraint in retrieved_constraints}
        ]
        if len(outcomes) != 1:
            return None
        return outcomes[0]

    def test_wizard_restoration_records_complete_translated_parity(self):
        root = Path(__file__).resolve().parents[1]
        skill_dir = root / "skills" / "my-wizard"
        skill = (skill_dir / "SKILL.md").read_text()
        template = skill_dir / "template.sh"
        metadata = skill_dir / "agents" / "openai.yaml"
        fidelity = json.loads((root / "upstream" / "fidelity.json").read_text())
        entry = next(
            item for item in fidelity["skills"] if item["local_skill"] == "my-wizard"
        )

        self.assertIn('short_description: "交互式设置向导"', metadata.read_text())
        self.assertEqual("skills/in-progress/wizard", entry["upstream_path"])
        source_dir = (
            root / ".superpowers/sdd/mattpocock-skills-pinned" / entry["upstream_path"]
        )
        source_metadata = (source_dir / "agents/openai.yaml").read_text()
        self.assertIn('display_name: "Wizard"', source_metadata)
        expected_mappings = {
            "agents/openai.yaml#interface.display_name": ("SKILL.md", "向导"),
            "SKILL.md#Wizard": ("SKILL.md", "向导"),
            "SKILL.md#Process": ("SKILL.md", "流程"),
            "SKILL.md#1. Scope the procedure": ("SKILL.md", "1. 界定流程范围"),
            "SKILL.md#2. Map each stage's journey": (
                "SKILL.md",
                "2. 绘制每个阶段的路径",
            ),
            "SKILL.md#3. Author the wizard": ("SKILL.md", "3. 编写向导"),
            "SKILL.md#4. Verify and hand off": ("SKILL.md", "4. 验证并交付"),
        }
        for field in ("complete", "translated"):
            mappings = entry["sections"][field]
            self.assertEqual(
                expected_mappings.keys(), {item["upstream"] for item in mappings}
            )
            for mapping in mappings:
                with self.subTest(field=field, section=mapping["upstream"]):
                    document, heading = expected_mappings[mapping["upstream"]]
                    self.assertEqual(heading, mapping["local"])
                    self.assertIn(heading, skill)
                    self.assertRegex(mapping["evidence"], r"SKILL\.md#")
                    if mapping["upstream"] == "agents/openai.yaml#interface.display_name":
                        self.assertIn(
                            "metadata-to-local-title translation/adaptation",
                            mapping["evidence"],
                        )
        self.assertEqual([], entry["sections"]["missing"])
        self.assertEqual([], entry["sections"]["local_added"])
        self.assertEqual(
            {
                "SKILL.md": (
                    "e113612095b14178e680022153f2409fb14ea8b992e55d59ad8ce94071ffaf49"
                ),
                "agents/openai.yaml": (
                    "b7f38980ab3ac03275edeae3209bd80de2592bd4b50b851fcf4cd57c22fff8eb"
                ),
                "template.sh": (
                    "4ebf795271ea5be1326e42de60608ab5f01dd6e070ee6d16168e618dca70a14f"
                ),
            },
            entry["support_files"],
        )
        self.assertEqual(
            hashlib.sha256(metadata.read_bytes()).hexdigest(),
            entry["local_support_files"]["agents/openai.yaml"],
        )
        self.assertEqual(
            hashlib.sha256(template.read_bytes()).hexdigest(),
            entry["local_support_files"]["template.sh"],
        )
        self.assertEqual(
            {
                "template.sh": {
                    "sha256": hashlib.sha256(template.read_bytes()).hexdigest(),
                    "mode": "0644",
                    "source_mode": "0644",
                    "library_unchanged": True,
                }
            },
            entry["local_file_metadata"],
        )
        self.assertEqual(
            (source_dir / "template.sh").read_bytes(),
            template.read_bytes(),
            "the reusable library and example stages must be restored faithfully",
        )
        self.assertEqual(0o644, template.stat().st_mode & 0o777)
        self.assertEqual(0, subprocess.run(["bash", "-n", template]).returncode)
        self.assertEqual(
            [
                {
                    "path": "SKILL.md",
                    "adaptation": (
                        "将上游 agents/openai.yaml#interface.display_name（“Wizard”）"
                        "翻译/适配为本地文档标题 SKILL.md#向导；保留本地手动调用元数据；"
                        "不改变上游方法。"
                    ),
                }
            ],
            entry["allowed_local_adaptations"],
        )
        self.assertEqual("faithful", entry["conclusion"])
        self.assertEqual(
            "upstream/evidence/wizard-restoration.md", entry["evidence_path"]
        )
        self.assertTrue(
            (root / entry["evidence_path"]).is_file(),
            "wizard evidence must resolve in committed source",
        )

        for instruction in (
            "每个阶段按顺序命名",
            "若你并不知道当前 UI 或确切命令",
            "永远不要编造可能不存在的步骤",
            "不要改动 `STAGES` 标记上方的库",
            "`bash -n <script>`",
            "不要自行端到端运行",
        ):
            with self.subTest(instruction=instruction):
                self.assertIn(instruction, skill)
        self.assertNotIn("项目策略优先", skill)

    def test_wizard_scenarios_apply_section_bounded_constraints(self):
        root = Path(__file__).resolve().parents[1]
        skill_dir = root / "skills" / "my-wizard"
        fixture_path = root / "tests" / "fixtures" / "wizard_application.json"
        self.assertTrue(
            fixture_path.is_file(), "missing wizard retrieval/application fixture"
        )
        fixture = json.loads(fixture_path.read_text())
        self.assertEqual("skills/in-progress/wizard", fixture["source_path"])
        self.assertEqual(
            {
                "wizard-discovery",
                "prompt-process-progression",
                "invalid-or-unsafe-input-stop",
                "template-use",
                "completion",
            },
            {case["id"] for case in fixture["scenarios"]},
        )
        rules = fixture["rules"]
        self.assertTrue(rules)
        rule_ids = set()
        for rule in rules:
            self.assertNotIn(rule["id"], rule_ids)
            rule_ids.add(rule["id"])
            self.assertTrue(rule["when"])
            self.assertTrue(rule["requires_constraints"])
            self.assertIsInstance(rule["outcome"], dict)

        documents = {"SKILL.md": (skill_dir / "SKILL.md").read_text()}
        for case in fixture["scenarios"]:
            with self.subTest(scenario=case["id"]):
                self.assertIsInstance(case["input"], dict)
                self.assertTrue(case["retrieved_constraints"])
                constraint_ids = set()
                for constraint in case["retrieved_constraints"]:
                    self.assertNotIn(constraint["id"], constraint_ids)
                    constraint_ids.add(constraint["id"])
                    self.assertIn(constraint["document"], documents)
                    self.assertEqual(
                        constraint["document"],
                        constraint["source_section"].split("#", 1)[0],
                    )
                    section_contents = self._section_contents(
                        documents[constraint["document"]],
                        constraint["source_section"],
                    )
                    self.assertIsNotNone(section_contents)
                    self.assertIn(constraint["text"], section_contents)
                self.assertEqual(
                    case["expected"],
                    self._apply_wizard_rules(
                        case["input"],
                        case["retrieved_constraints"],
                        rules,
                    ),
                )


if __name__ == "__main__":
    unittest.main()
