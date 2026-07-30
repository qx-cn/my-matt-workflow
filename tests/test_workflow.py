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
        # Non-navigation skills keep a slim policy footer without continue encyclopaedia.
        teach = (root / "my-teach" / "SKILL.md").read_text()
        self.assertIn("已解析生效策略", teach)
        self.assertNotIn("不升档", teach)
        self.assertNotIn("五档预设", teach)

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
        for skill_file in root.glob("my-*/SKILL.md"):
            text = skill_file.read_text()
            with self.subTest(skill=skill_file.parent.name):
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
            "my-triage": ".agent/work/<feature>/triages/",
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
            "my-teach": ".agent/work/<topic>/learning/",
            "my-domain-modeling": ".agent/work/<topic>/domain/",
            "my-improve-codebase-architecture": ".agent/work/<topic>/architecture-reports/",
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
            "my-to-questionnaire": ["questionnaires", "不得自动对外发送"],
            "my-wizard": ["wizards", "不得回显秘密", "单独确认"],
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

    def test_every_skill_declares_project_policy_precedence(self):
        source_skills = Path(__file__).parents[1] / "skills"
        for skill_file in source_skills.glob("my-*/SKILL.md"):
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


if __name__ == "__main__":
    unittest.main()
