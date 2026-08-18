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
from tools.workflow_lib.release import ReleaseError, build_release, validate_skills
from tools.workflow_lib.rules import resolve_rules
from tools.workflow_lib.tickets import TicketError, validate_ready_ticket


class ProfileTests(unittest.TestCase):
    def test_ask_matt_routes_with_manual_branches_without_composed_entries(self):
        text = (
            Path(__file__).resolve().parents[1]
            / "skills/my-ask-matt/SKILL.md"
        ).read_text()
        self.assertNotIn("references/composed/", text)
        self.assertIn("Cursor / Claude", text)
        self.assertIn("Codex", text)
        self.assertIn("停止", text)
        self.assertIn("路由索引", text)
        self.assertIn("不要在本 Skill 内执行", text)

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

    def test_plan_skills_use_project_rule_adapter(self):
        root = Path(__file__).resolve().parents[1]
        adapter = root / "resources/adapters/project-rules.md"
        self.assertTrue(adapter.is_file())
        adapter_text = adapter.read_text()
        self.assertIn(".cursor/rules/**/*.mdc", adapter_text)
        self.assertIn("execution_agent", adapter_text)
        self.assertIn("不得生成 `ready-for-agent`", adapter_text)

        for skill in (
            "my-grill-with-docs",
            "my-to-spec",
            "my-to-tickets",
            "my-implement",
            "my-code-review",
        ):
            text = (root / "skills" / skill / "SKILL.md").read_text()
            with self.subTest(skill=skill):
                self.assertIn("references/shared/adapters/project-rules.md", text)

    def test_setup_discovers_cursor_rule_candidates_without_persisting_them(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "AGENTS.md").write_text("rules")
            rules_dir = repo / ".cursor" / "rules"
            rules_dir.mkdir(parents=True)
            (rules_dir / "backend.mdc").write_text("---\nglobs: src/**\n---")

            workflow = Path(__file__).resolve().parents[1] / "tools/workflow.py"
            result = subprocess.run(
                [
                    sys.executable,
                    str(workflow),
                    "setup",
                    "--repo",
                    str(repo),
                    "--execution-agent",
                    "cursor",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn(
                '"detected_standards_sources": ["AGENTS.md", '
                '".cursor/rules/backend.mdc"]',
                result.stdout,
            )

    def test_composition_callers_use_one_dispatch_channel(self):
        root = Path(__file__).resolve().parents[1]
        expectations = {
            "my-implement": {
                "core": [
                    "实施用户在 Spec 或 Ticket 中描述的工作。",
                    "在预先约定的 seam 上进入 `my-tdd` 阶段。",
                    "定期运行类型检查和单个测试文件；结束时运行一次完整测试套件。",
                    "完成后进入 `my-code-review` 阶段审查工作。",
                    "将工作提交到当前分支。",
                ],
                "adapters": [
                    "ticket-selection.md",
                    "work-scope.md",
                    "composition.md",
                ],
            },
            "my-grill-me": {"core": ["composition_policy", "随后停止"], "adapters": ["composition.md"]},
            "my-grill-with-docs": {
                "core": ["composition_policy", "随后停止"],
                "adapters": ["composition.md", "artifact-access.md"],
            },
        }

        for skill, expectation in expectations.items():
            text = (root / "skills" / skill / "SKILL.md").read_text()
            with self.subTest(skill=skill):
                for phrase in expectation["core"]:
                    self.assertIn(phrase, text)
                for adapter in expectation["adapters"]:
                    self.assertIn(
                        f"references/shared/adapters/{adapter}", text
                    )
                self.assertIn("automatic", text)
                self.assertIn("manual", text)
                self.assertNotIn("项目策略优先", text)

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
            "default_execution_agent": "auto",
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

    def test_rule_resolution_keeps_agent_specific_rules_separate(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "AGENTS.md").write_text("shared")
            cursor_rules = repo / ".cursor" / "rules"
            cursor_rules.mkdir(parents=True)
            (cursor_rules / "backend.mdc").write_text(
                "---\nglobs: src/backend/**\nalwaysApply: false\n---\nbackend"
            )
            (cursor_rules / "manual.mdc").write_text("---\n---\nmanual")
            claude_rules = repo / ".claude" / "rules"
            claude_rules.mkdir(parents=True)
            (claude_rules / "frontend.md").write_text(
                "---\npaths: src/frontend/**\n---\nfrontend"
            )

            cursor = resolve_rules(repo, "cursor", ["src/backend/api.py"])
            self.assertEqual(
                ["AGENTS.md", ".cursor/rules/backend.mdc"],
                [rule["source"] for rule in cursor],
            )
            codex = resolve_rules(repo, "codex", ["src/backend/api.py"])
            self.assertEqual(["AGENTS.md"], [rule["source"] for rule in codex])
            claude = resolve_rules(repo, "claude", ["src/backend/api.py"])
            self.assertEqual(["AGENTS.md"], [rule["source"] for rule in claude])

    def test_ready_ticket_requires_rule_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            ticket = Path(tmp) / "ticket.md"
            ticket.write_text(
                "---\nstatus: ready-for-agent\nexecution_agent: codex\n"
                "rule_sources: []\nrule_scope: []\nrule_constraints: []\n"
                "rule_conflicts: []\n---\n"
            )
            with self.assertRaisesRegex(TicketError, "规则来源"):
                validate_ready_ticket(ticket)
            ticket.write_text(
                "---\nstatus: ready-for-agent\nexecution_agent: codex\n"
                'rule_sources: ["AGENTS.md"]\nrule_scope: ["src/**"]\n'
                'rule_constraints: ["run tests"]\nrule_conflicts: []\n---\n'
            )
            self.assertEqual("ready", validate_ready_ticket(ticket)["status"])

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
        sources = {
            "my-implement": (
                root / "my-implement" / "SKILL.md",
                root.parent / "resources/adapters/work-scope.md",
            ),
            "my-ask-matt": (root / "my-ask-matt" / "SKILL.md",),
        }
        for skill, paths in sources.items():
            text = "\n".join(path.read_text() for path in paths)
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
    def test_skills_remove_repeated_project_policy_footer(self):
        root = Path(__file__).resolve().parents[1] / "skills"
        for skill_file in root.glob("my-*/SKILL.md"):
            text = skill_file.read_text()
            with self.subTest(skill=skill_file.parent.name):
                self.assertNotIn("项目策略优先", text)
                self.assertNotIn("均服从该生效策略", text)
                self.assertNotIn("绝对安全底线始终不变", text)

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
        self.assertIn("/my-humanizer", sot)
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


class GitIgnoreRepositoryTests(unittest.TestCase):
    def test_non_git_project_keeps_agent_directory_without_gitignore(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)

            added, conflicts = apply_personal_ignores(project)

            self.assertEqual([], added)
            self.assertEqual([], conflicts)
            self.assertFalse((project / ".gitignore").exists())


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
            state = json.loads(
                (root / ".claude/my-matt-workflow/install-state.json").read_text()
            )
            self.assertEqual("claude", state["installed_agent"])

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

    def test_tech_design_is_standalone_and_uses_a_fixed_html_template(self):
        root = Path(__file__).resolve().parents[1]
        skill = root / "skills" / "my-tech-design"
        body = (skill / "SKILL.md").read_text()
        template = skill / "assets" / "TEMPLATE.html"
        composition = json.loads((root / "composition" / "manifest.json").read_text())

        self.assertIn("assets/TEMPLATE.html", body)
        self.assertTrue(template.is_file())
        self.assertNotIn("my-tech-design", composition["callers"])
        self.assertTrue(
            all(
                "my-tech-design" not in entries
                for entries in composition["routable_entries"].values()
            )
        )

    def test_adopted_skills_include_metadata_and_safety_boundaries(self):
        root = Path(__file__).resolve().parents[1] / "skills"
        expected = {
            "my-resolving-merge-conflicts": [
                "批准前",
                "references/policies/merge-conflict-approval.md",
            ],
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

        conflict_policy = (
            root.parent / "policies" / "merge-conflict-approval.md"
        ).read_text()
        self.assertIn("Force Push", conflict_policy)
        self.assertIn("回滚", conflict_policy)
        self.assertEqual(28, len(validate_skills(root)))

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
                    / "skills/my-implement/references/composed/my-tdd/COMPOSED.md"
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
                    release / "skills/my-implement/references/shared/humanizer.md"
                ).is_file()
            )
            self.assertIn(
                "../../shared/humanizer.md",
                (
                    release
                    / "skills/my-implement/references/composed/my-code-review/COMPOSED.md"
                ).read_text(),
            )
            self.assertEqual(
                [],
                list(
                    release.glob(
                        "skills/*/references/composed/**/references/policies"
                    )
                )
                + list(
                    release.glob(
                        "skills/*/references/composed/**/references/shared"
                    )
                ),
            )
            manifest = json.loads((release / "manifest.json").read_text())
            self.assertEqual(
                ["my-code-review", "my-tdd"],
                manifest["composed"]["my-implement"],
            )

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
                "my-ask-matt",
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
                    "ticket-selection.md",
                    "work-scope.md",
                    "composition.md",
                },
                "my-grill-me": {"composition.md"},
                "my-grill-with-docs": {
                    "composition.md",
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
            module = self._load_workflow_module()
            agent_home = Path(tmp) / "agent"
            args = argparse.Namespace(
                release_id="v1",
                upstream_id="local-matt-skills",
                target="auto",
                agent_home=str(agent_home),
            )
            with mock.patch.object(module, "ROOT", workflow):
                module.command_deploy(args)

            self.assertEqual(
                1,
                len([path for path in (workflow / "releases").iterdir() if path.is_dir()]),
            )
            self.assertEqual(
                {"release_id": "v1"},
                json.loads((workflow / "current.json").read_text()),
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
                build_release(
                    workflow / "skills",
                    workflow / "releases",
                    release_id=release_id,
                    upstream_id="local-matt-skills",
                    repo_root=workflow,
                )
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
                sorted(path.name for path in (workflow / "releases").iterdir()),
            )
