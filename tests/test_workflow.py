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
from tools.workflow_lib.decision_gates import resolve_decision_gate
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
from tools.workflow_lib.tickets import (
    TicketError,
    frontmatter,
    validate_ready_ticket,
    validate_ticket_transition,
)
from tools.workflow_lib.transitions import ticket_transition
from tools.workflow_lib.write_gates import resolve_write_gate
from tools.workflow_lib.work_artifacts import WorkArtifactError, apply_work_artifact_migration


class TicketTransitionTests(unittest.TestCase):
    def _ticket(
        self,
        directory: Path,
        identifier: str,
        sequence: int,
        *,
        status: str = "ready-for-agent",
        blocked_by: str = "[]",
        spec_revision: int = 1,
        accepted: bool = False,
    ) -> Path:
        path = directory / f"tickets-feature-{sequence:02d}-{identifier}.md"
        path.write_text(
            "---\n"
            f"id: {identifier}\n"
            "title: Test ticket\n"
            "ticket_kind: implementation\n"
            "spec_id: feature\n"
            f"spec_revision: {spec_revision}\n"
            "spec_ref: specs/specs-feature-01.md\n"
            f"status: {status}\n"
            f"blocked_by: {blocked_by}\n"
            "claimed_by:\n"
            "rule_sources: [AGENTS.md]\n"
            "rule_scope: [src]\n"
            "rule_constraints: [test]\n"
            "rule_conflicts: []\n"
            "execution_agent: codex\n"
            f"sequence: {sequence}\n"
            "---\n\n## 验收标准\n\n"
            f"- [{'x' if accepted else ' '}] works\n"
        )
        return path

    def test_semi_auto_selects_stable_ready_frontier(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            self._ticket(directory, "feature-b", 2)
            self._ticket(directory, "feature-a", 2)
            result = ticket_transition(directory, work_scope_policy="ready-frontier")
            self.assertEqual("continue", result.status)
            self.assertEqual("feature-a", result.next_ticket.identifier)

    def test_semi_auto_pauses_at_critical_decision(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = ticket_transition(
                Path(tmp), work_scope_policy="ready-frontier", blocker="critical-tdd-seam"
            )
            self.assertEqual(("pause", "critical-tdd-seam"), (result.status, result.reason))

    def test_full_auto_uses_initial_scope_and_dependency_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            self._ticket(directory, "feature-a", 1, status="complete")
            self._ticket(directory, "feature-b", 2, blocked_by='["feature-a"]')
            self._ticket(directory, "feature-later", 3)
            result = ticket_transition(
                directory,
                work_scope_policy="approved-plan",
                allowed_ids={"feature-a", "feature-b"},
            )
            self.assertEqual("continue", result.status)
            self.assertEqual("feature-b", result.next_ticket.identifier)

    def test_full_auto_reports_hard_blocker(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = ticket_transition(
                Path(tmp), work_scope_policy="approved-plan", blocker="new-external-authorization"
            )
            self.assertEqual(("pause", "new-external-authorization"), (result.status, result.reason))

    def test_single_ticket_stops_even_with_ready_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            self._ticket(directory, "feature-b", 2)
            result = ticket_transition(directory, work_scope_policy="single-ticket")
            self.assertEqual(("complete", "single-ticket"), (result.status, result.reason))

    def test_revalidated_ticket_can_reenter_implementation(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            ticket = self._ticket(
                directory,
                "feature-a",
                1,
                status="revalidated",
                spec_revision=2,
            )
            self.assertEqual("ready", validate_ready_ticket(ticket)["status"])
            result = ticket_transition(directory, work_scope_policy="ready-frontier")
            self.assertEqual("feature-a", result.next_ticket.identifier)

    def test_design_revision_state_machine_is_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            states = (
                ("ready-for-agent", "implementing"),
                ("implementing", "blocked-by-design"),
                ("blocked-by-design", "revising"),
                ("revising", "revalidated"),
                ("revalidated", "implementing"),
                ("implementing", "complete"),
            )
            for current, target in states:
                ticket = self._ticket(
                    directory,
                    f"{current}-{target}",
                    1,
                    status=current,
                    accepted=target == "complete",
                )
                report = validate_ticket_transition(ticket, target)
                self.assertEqual("allow", report["status"])
            completed = self._ticket(directory, "done", 2, status="complete")
            with self.assertRaisesRegex(TicketError, "complete"):
                validate_ticket_transition(completed, "revising")

    def test_complete_transition_requires_checked_acceptance(self):
        with tempfile.TemporaryDirectory() as tmp:
            ticket = self._ticket(Path(tmp), "feature-a", 1, status="implementing")
            with self.assertRaisesRegex(TicketError, "验收标准"):
                validate_ticket_transition(ticket, "complete")

    def test_frontmatter_accepts_yaml_block_lists(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ticket.md"
            path.write_text(
                "---\n"
                "id: feature-a\n"
                "rule_sources:\n"
                "  - requirements.md\n"
                "  - AGENTS.md\n"
                "rule_scope:\n"
                "  - app.py\n"
                "claimed_by:\n"
                "---\n",
                encoding="utf-8",
            )
            ticket = frontmatter(path)
            self.assertEqual(["requirements.md", "AGENTS.md"], ticket["rule_sources"])
            self.assertEqual(["app.py"], ticket["rule_scope"])
            self.assertEqual("", ticket["claimed_by"])

    def test_ticket_transition_cli_is_a_read_only_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            ticket = self._ticket(Path(tmp), "feature-a", 1)
            result = subprocess.run(
                [
                    sys.executable,
                    "tools/workflow.py",
                    "ticket-transition",
                    str(ticket),
                    "--to",
                    "implementing",
                ],
                cwd=Path(__file__).resolve().parents[1],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual("allow", json.loads(result.stdout)["status"])
            self.assertEqual("ready-for-agent", frontmatter(ticket)["status"])

    def test_next_ticket_cli_reads_project_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            tickets = repo / ".agent" / "work" / "feature" / "tickets"
            tickets.mkdir(parents=True)
            (repo / ".agent" / "matt-workflow.md").write_text(
                render_profile({"schema_version": 1, "task_backend": "local", "work_scope_policy": "ready-frontier"})
            )
            self._ticket(tickets, "feature-b", 2)
            result = subprocess.run(
                [sys.executable, "tools/workflow.py", "next-ticket", "--repo", str(repo), "--feature", "feature"],
                cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, check=False,
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual("feature-b", json.loads(result.stdout)["next_ticket"]["id"])
            scope = subprocess.run(
                [sys.executable, "tools/workflow.py", "ticket-scope", "--repo", str(repo), "--feature", "feature"],
                cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, check=False,
            )
            self.assertEqual(0, scope.returncode, scope.stderr)
            self.assertEqual(["feature-b"], json.loads(scope.stdout)["ticket_ids"])


class WriteGateTests(unittest.TestCase):
    def test_every_configured_write_policy_has_a_runtime_gate(self):
        profile = {
            "branch_policy": "allow",
            "commit_policy": "confirm",
            "external_write_policy": "allow",
            "docs_writeback": "deny",
        }
        self.assertEqual("allow", resolve_write_gate(profile, kind="branch").status)
        self.assertEqual("confirm", resolve_write_gate(profile, kind="commit").status)
        self.assertEqual("pause", resolve_write_gate(profile, kind="external").status)
        self.assertEqual("allow", resolve_write_gate(profile, kind="external", approved_scope=True).status)
        self.assertEqual("deny", resolve_write_gate(profile, kind="docs").status)


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
        self.assertIn(".agent/rules/**/*", adapter_text)
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

    def test_setup_discovers_codex_agent_rule_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "AGENTS.md").write_text("rules")
            rules_dir = repo / ".agent" / "rules" / "backend"
            rules_dir.mkdir(parents=True)
            (rules_dir / "coding.mdc").write_text("coding rules")

            workflow = Path(__file__).resolve().parents[1] / "tools/workflow.py"
            result = subprocess.run(
                [
                    sys.executable,
                    str(workflow),
                    "setup",
                    "--repo",
                    str(repo),
                    "--execution-agent",
                    "codex",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn('"detected_standards_sources": ["AGENTS.md"]', result.stdout)

    def test_composition_callers_use_one_dispatch_channel(self):
        root = Path(__file__).resolve().parents[1]
        expectations = {
            "my-implement": {
                "core": [
                    "实施用户在 Spec 或 Ticket 中描述的工作。",
                    "在计划、Ticket 或代码可推断的 seam 上进入 `my-tdd` 阶段",
                    "改动中运行能最快证明当前行为的最小针对性测试",
                    "只有整份计划完成、发布或合并前",
                    "再进入 `my-code-review` 阶段审查该 `content_id` 的完整工作树。",
                    "按[写操作 Gate]",
                ],
                "adapters": [
                    "ticket-selection.md",
                    "work-scope.md",
                    "composition.md",
                ],
            },
            "my-grill-me": {
                "core": [
                    "composition_policy",
                    "执行后返回宿主",
                    "立即提出第一个问题",
                ],
                "adapters": ["composition.md"],
            },
            "my-grill-with-docs": {
                "core": ["composition_policy", "执行后返回宿主"],
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

    def test_internal_composition_methods_return_in_manual_mode(self):
        root = Path(__file__).resolve().parents[1] / "skills"
        for skill in (
            "my-grill-me",
            "my-grill-with-docs",
            "my-implement",
            "my-improve-codebase-architecture",
        ):
            text = (root / skill / "SKILL.md").read_text()
            with self.subTest(skill=skill):
                self.assertIn("执行后返回宿主", text)
                self.assertNotRegex(text, r"manual`：输出对应的.*随后停止")

        wayfinder = (root / "my-wayfinder/SKILL.md").read_text()
        self.assertIn("内部方法", wayfinder)
        self.assertIn("阶段交接", wayfinder)
        self.assertIn("my-to-spec", wayfinder)

    def test_grill_me_manual_entry_executes_composed_interview_in_same_turn(self):
        root = Path(__file__).resolve().parents[1]
        text = (root / "skills/my-grill-me/SKILL.md").read_text()

        self.assertIn("references/composed/my-grilling/COMPOSED.md", text)
        self.assertIn("立即提出第一个问题", text)
        self.assertNotIn("输出 `/my-grilling`", text)
        self.assertNotIn("输出 `$my-grilling`", text)

    def test_round_trips_supported_profile(self):
        config = {
            "schema_version": 1,
            "task_backend": "local",
            "agent_directory_mode": "private",
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
            codex_rules = repo / ".agent" / "rules" / "backend"
            codex_rules.mkdir(parents=True)
            (codex_rules / "coding.mdc").write_text("codex")
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
            self.assertEqual("codex-native", codex[0]["applies_by"])
            claude = resolve_rules(repo, "claude", ["src/backend/api.py"])
            self.assertEqual(["AGENTS.md"], [rule["source"] for rule in claude])

    def test_codex_rules_follow_directory_override_and_precedence(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "AGENTS.md").write_text("root")
            (repo / "AGENTS.override.md").write_text("root override")
            nested = repo / "src" / "backend"
            nested.mkdir(parents=True)
            (repo / "src" / "AGENTS.md").write_text("src")
            (nested / "AGENTS.md").write_text("backend")

            rules = resolve_rules(repo, "codex", ["src/backend/api.py"])

            self.assertEqual(
                ["AGENTS.override.md", "src/AGENTS.md", "src/backend/AGENTS.md"],
                [rule["source"] for rule in rules],
            )
            self.assertEqual([0, 1, 2], [rule["precedence_index"] for rule in rules])
            self.assertEqual("override", rules[0]["selected_by"])
            self.assertEqual(["src/backend/api.py"], rules[-1]["scope"])

    def test_codex_rules_support_configured_fallback_and_reject_escaping_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / "TEAM.md").write_text("fallback")
            rules = resolve_rules(
                repo,
                "codex",
                ["src/api.py"],
                codex_fallback_filenames=["TEAM.md"],
            )
            self.assertEqual(["TEAM.md"], [rule["source"] for rule in rules])
            self.assertEqual("fallback", rules[0]["selected_by"])
            with self.assertRaisesRegex(ValueError, "相对路径"):
                resolve_rules(repo, "codex", ["../outside.py"])

    def test_decision_gate_maps_each_class_to_one_action(self):
        expected = {
            "ask": ("allow", "confirm", "confirm"),
            "autonomous": ("allow", "allow", "confirm"),
            "halt": ("allow", "pause", "pause"),
        }
        classes = ("routine", "consequential", "user-exclusive")
        for policy, statuses in expected.items():
            for decision_class, status in zip(classes, statuses):
                with self.subTest(policy=policy, decision_class=decision_class):
                    gate = resolve_decision_gate(
                        {"decision_policy": policy}, decision_class=decision_class
                    )
                    self.assertEqual(status, gate.status)

    def test_policy_catalog_does_not_restore_legacy_manual_or_ask_meanings(self):
        catalog = format_policy_catalog()
        self.assertIn("内部 method 同轮执行", catalog)
        self.assertIn("普通可逆细节继续", catalog)
        self.assertNotIn("提示用户手动启动依赖 Skill", catalog)
        self.assertNotIn("ask（遇到决策时询问）", catalog)

    def test_high_frequency_skills_do_not_block_on_routine_decisions(self):
        root = Path(__file__).resolve().parents[1] / "skills"
        tickets = (root / "my-to-tickets/SKILL.md").read_text()
        article = (root / "my-edit-article/SKILL.md").read_text()
        diagnosing = (root / "my-diagnosing-bugs/SKILL.md").read_text()
        domain = (root / "my-domain-modeling/SKILL.md").read_text()
        prototype = (root / "my-prototype/LOGIC.md").read_text()
        wayfinder = (root / "my-wayfinder/SKILL.md").read_text()

        self.assertIn("分类为 `routine`", tickets)
        self.assertNotIn("反复迭代直至用户批准", tickets)
        self.assertIn("不为普通、可逆的重排单独等待确认", article)
        self.assertIn("继续穷尽当前授权范围内的只读证据", diagnosing)
        self.assertIn("不因 `decision_policy: ask` 重复确认", diagnosing)
        self.assertIn("执行 `allow | confirm | pause` 的唯一结果", domain)
        self.assertIn("视为 `routine`", prototype)
        self.assertNotIn("按 `decision_policy` 询问后续方式", wayfinder)

    def test_testing_and_delegation_are_risk_and_capability_aware(self):
        root = Path(__file__).resolve().parents[1] / "skills"
        implement = (root / "my-implement/SKILL.md").read_text()
        design_twice = (root / "my-codebase-design/DESIGN-IT-TWICE.md").read_text()

        self.assertIn("最小针对性测试", implement)
        self.assertIn("受影响模块或链路", implement)
        self.assertIn("只有整份计划完成、发布或合并前", implement)
        self.assertNotIn("结束时运行一次完整测试套件", implement)
        self.assertIn("用户未禁止", design_twice)
        self.assertIn("不设固定下限", design_twice)
        self.assertIn("串行生成独立方案", design_twice)
        self.assertNotIn("3 个以上子代理", design_twice)

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
                'rule_constraints: ["run tests"]\nrule_conflicts: []\n'
                "spec_id: feature\nspec_revision: 1\n"
                "spec_ref: specs/specs-feature-01.md\n---\n"
            )
            self.assertEqual("ready", validate_ready_ticket(ticket)["status"])

    def test_ready_ticket_requires_spec_lineage(self):
        with tempfile.TemporaryDirectory() as tmp:
            ticket = Path(tmp) / "ticket.md"
            ticket.write_text(
                "---\nstatus: ready-for-agent\nexecution_agent: codex\n"
                'rule_sources: ["AGENTS.md"]\nrule_scope: ["src/**"]\n'
                'rule_constraints: ["run tests"]\nrule_conflicts: []\n---\n'
            )
            with self.assertRaisesRegex(TicketError, "Spec 血缘"):
                validate_ready_ticket(ticket)

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
        self.assertIn("发现契约", text)
        self.assertIn("P0", text)
        self.assertIn("失败场景/不变量", text)
        self.assertIn("证据与置信度", text)
        self.assertIn("影响与验证", text)
        self.assertIn("低风险变更不为并行而增加 reviewer", text)
        self.assertIn("manual` 或 `automatic` 都必须", text)
        self.assertNotIn("少于 400 字", text)
        self.assertNotIn("提示用户分别启动审查", text)

    def test_humanizer_avoids_neologisms_without_banning_normal_grammar(self):
        text = (
            Path(__file__).resolve().parents[1]
            / "skills/my-humanizer/SKILL.md"
        ).read_text()
        self.assertIn("不用造词换风格", text)
        self.assertIn("专业术语首次出现时用白话解释", text)
        self.assertIn("不能仅因“动词＋宾语”形式", text)

    def test_implement_review_uses_content_snapshot_and_commit_equivalence(self):
        root = Path(__file__).resolve().parents[1]
        review = (root / "skills/my-code-review/SKILL.md").read_text()
        implement = (root / "skills/my-implement/SKILL.md").read_text()

        for source in ("committed", "staged", "unstaged", "untracked"):
            self.assertIn(source, review)
        self.assertIn("Review-Snapshot: <content_id>", review)
        self.assertIn("旧 receipt 立即失效", review)
        self.assertIn("review-snapshot --repo <repo> --base", implement)
        self.assertIn("--expect-content-id", implement)
        self.assertIn("--require-clean", implement)
        self.assertIn("run-start --repo <repo>", implement)
        self.assertIn("run-record <journal>", implement)
        self.assertIn("context receipt", implement)
        self.assertIn("run-<ticket-id>-spec-r<revision>.json", implement)
        self.assertIn("Commit 与已审查内容等价", implement)

    def test_spec_handoff_and_design_review_apply_finalization_gate(self):
        root = Path(__file__).resolve().parents[1] / "skills"
        for skill in ("my-to-spec", "my-handoff", "my-review-design"):
            text = (root / skill / "SKILL.md").read_text()
            with self.subTest(skill=skill):
                self.assertIn(
                    "references/shared/artifact-finalization.md",
                    text,
                )
                self.assertIn("最终校验", text)

        spec = (root / "my-to-spec/SKILL.md").read_text()
        self.assertIn("依据与未知", spec)
        handoff = (root / "my-handoff/SKILL.md").read_text()
        self.assertIn("fresh-context", handoff)

    def test_spec_and_tickets_preserve_revision_lineage_without_overdesign(self):
        root = Path(__file__).resolve().parents[1] / "skills"
        spec = (root / "my-to-spec/SKILL.md").read_text()
        tickets = (root / "my-to-tickets/SKILL.md").read_text()
        implement = (root / "my-implement/SKILL.md").read_text()

        for field in ("spec_id", "revision", "supersedes"):
            self.assertIn(field, spec)
        for field in ("spec_id", "spec_revision", "spec_ref"):
            self.assertIn(field, tickets)
        self.assertNotIn("很长、带编号", spec)
        self.assertNotIn("理想数量是一个", spec)
        self.assertIn("pause-for-revision", implement)
        self.assertIn("blocked-by-design", implement)
        self.assertIn("补偿", implement)


class GitIgnoreRepositoryTests(unittest.TestCase):
    def test_non_git_project_keeps_agent_directory_without_gitignore(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)

            added, conflicts = apply_personal_ignores(project)

            self.assertEqual([], added)
            self.assertEqual([], conflicts)
            self.assertFalse((project / ".gitignore").exists())


class RefreshProjectTests(unittest.TestCase):
    def _run(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve().parents[1] / "tools/workflow.py"),
                *arguments,
            ],
            cwd=Path(__file__).resolve().parents[1],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_setup_previews_and_refresh_migrates_artifacts_without_gitignore_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            gitignore = repo / ".gitignore"
            gitignore.write_text(".cache/\n")
            profile = repo / ".agent" / "matt-workflow.md"
            legacy = repo / ".agent" / "work" / "checkout" / "spec.md"
            profile.parent.mkdir(parents=True)
            profile.write_text(render_profile({"schema_version": 1, "task_backend": "local"}))
            legacy.parent.mkdir(parents=True)
            legacy.write_text("# Old spec\n")

            preview = self._run("setup", "--repo", str(repo))

            self.assertEqual(0, preview.returncode, preview.stderr)
            self.assertIn('"from": ".agent/work/checkout/spec.md"', preview.stdout)
            self.assertTrue(legacy.exists())
            self.assertEqual(".cache/\n", gitignore.read_text())

            refreshed = self._run(
                "refresh-project",
                "--repo",
                str(repo),
                "--migrate-work-artifacts",
            )

            self.assertEqual(0, refreshed.returncode, refreshed.stderr)
            self.assertFalse(legacy.exists())
            self.assertTrue(
                (repo / ".agent/work/checkout/specs/specs-checkout-01.md").is_file()
            )
            self.assertEqual(".cache/\n", gitignore.read_text())
            nested_git = repo / ".agent" / ".git"
            self.assertTrue(nested_git.exists())
            remote = subprocess.run(
                ["git", "remote"], cwd=repo / ".agent", capture_output=True, text=True, check=True
            )
            self.assertEqual("", remote.stdout)

    def test_refresh_refuses_tracked_agent_directory_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            profile = repo / ".agent" / "matt-workflow.md"
            profile.parent.mkdir(parents=True)
            profile.write_text("tracked profile\n")
            subprocess.run(["git", "add", ".agent/matt-workflow.md"], cwd=repo, check=True)

            result = self._run("refresh-project", "--repo", str(repo))

            self.assertNotEqual(0, result.returncode)
            self.assertIn("已跟踪", result.stderr)
            self.assertEqual("tracked profile\n", profile.read_text())
            self.assertFalse((repo / ".agent/.git").exists())

    def test_shared_mode_allows_parent_repository_to_track_agent_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)

            result = self._run(
                "setup",
                "--repo",
                str(repo),
                "--agent-directory-mode",
                "shared",
                "--apply",
            )

            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn('"mode": "shared"', result.stdout)
            self.assertFalse((repo / ".agent/.git").exists())
            subprocess.run(["git", "add", ".agent/matt-workflow.md"], cwd=repo, check=True)
            refreshed = self._run("refresh-project", "--repo", str(repo))
            self.assertEqual(0, refreshed.returncode, refreshed.stderr)

    def test_shared_mode_requires_explicit_migration_before_removing_nested_git(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            private = self._run("setup", "--repo", str(repo), "--apply")
            self.assertEqual(0, private.returncode, private.stderr)
            self.assertTrue((repo / ".agent/.git").exists())

            preview = self._run(
                "setup", "--repo", str(repo), "--refresh", "--agent-directory-mode", "shared"
            )
            self.assertEqual(0, preview.returncode, preview.stderr)
            self.assertIn("remove_nested_git_requires_migrate_agent_directory_mode", preview.stdout)

            refused = self._run(
                "refresh-project", "--repo", str(repo), "--agent-directory-mode", "shared"
            )
            self.assertNotEqual(0, refused.returncode)
            self.assertIn("--migrate-agent-directory-mode", refused.stderr)
            self.assertTrue((repo / ".agent/.git").exists())

            migrated = self._run(
                "refresh-project",
                "--repo",
                str(repo),
                "--agent-directory-mode",
                "shared",
                "--migrate-agent-directory-mode",
            )
            self.assertEqual(0, migrated.returncode, migrated.stderr)
            self.assertFalse((repo / ".agent/.git").exists())
            profile, _ = parse_profile((repo / ".agent/matt-workflow.md").read_text())
            self.assertEqual("shared", profile["agent_directory_mode"])

    def test_refresh_rewrites_only_explicitly_confirmed_candidate_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            profile = repo / ".agent" / "matt-workflow.md"
            handoff = repo / ".agent" / "handoffs" / "checkout" / "2026-07-29.md"
            profile.parent.mkdir(parents=True)
            profile.write_text(render_profile({"schema_version": 1, "task_backend": "local"}))
            handoff.parent.mkdir(parents=True)
            handoff.write_text("[workflow](../../tools/workflow.py)\n")
            tool = repo / "tools" / "workflow.py"
            tool.parent.mkdir()
            tool.write_text("#!/usr/bin/env python3\n")

            result = self._run(
                "refresh-project",
                "--repo",
                str(repo),
                "--migrate-work-artifacts",
                "--confirm-candidate-link-repair",
                ".agent/handoffs/checkout/2026-07-29.md",
                "../../tools/workflow.py",
            )

            self.assertEqual(0, result.returncode, result.stderr)
            migrated = repo / ".agent/work/checkout/handoffs/handoffs-checkout-20260729.md"
            self.assertEqual("[workflow](../../../../tools/workflow.py)\n", migrated.read_text())


class WorkArtifactTransactionTests(unittest.TestCase):
    def _legacy(self, repo: Path) -> Path:
        legacy = repo / ".agent/work/topic/spec.md"
        legacy.parent.mkdir(parents=True)
        legacy.write_text("# legacy\n")
        return legacy

    def test_preflight_conflict_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            legacy = self._legacy(repo)
            target = repo / ".agent/work/topic/specs/specs-topic-01.md"
            target.parent.mkdir()
            target.write_text("existing")
            with self.assertRaises(WorkArtifactError):
                apply_work_artifact_migration(repo)
            self.assertEqual("# legacy\n", legacy.read_text())
            self.assertEqual("existing", target.read_text())
            self.assertFalse((repo / ".agent/.work-artifact-transaction").exists())

    def test_commit_failure_rolls_back_first_moved_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            legacy = self._legacy(repo)
            original_rename = Path.rename

            def fail_staged_rename(path: Path, destination: Path):
                if path.name == "0" and path.parent.name == "staged":
                    raise OSError("injected destination failure")
                return original_rename(path, destination)

            with mock.patch.object(Path, "rename", fail_staged_rename):
                with self.assertRaisesRegex(WorkArtifactError, "已恢复"):
                    apply_work_artifact_migration(repo)
            self.assertEqual("# legacy\n", legacy.read_text())
            self.assertFalse((repo / ".agent/work/topic/specs/specs-topic-01.md").exists())
            self.assertFalse((repo / ".agent/.work-artifact-transaction").exists())

    def test_leftover_transaction_is_rolled_back_before_next_migration(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            legacy = self._legacy(repo)
            target = repo / ".agent/work/topic/specs/specs-topic-01.md"
            target.parent.mkdir()
            target.write_text("partial")
            transaction = repo / ".agent/.work-artifact-transaction"
            backup = transaction / "backup/0"
            backup.parent.mkdir(parents=True)
            backup.write_text("# legacy\n")
            (transaction / "journal.json").write_text(json.dumps({
                "version": 1,
                "moves": [{"from": ".agent/work/topic/spec.md", "to": ".agent/work/topic/specs/specs-topic-01.md"}],
            }))
            apply_work_artifact_migration(repo)
            self.assertFalse(legacy.exists())
            self.assertEqual("# legacy\n", target.read_text())
            self.assertFalse(transaction.exists())


class GitIgnoreTests(unittest.TestCase):
    def test_never_modifies_gitignore_when_agent_directory_is_untracked(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)

            (repo / ".gitignore").write_text(".cache/\n")

            added, conflicts = apply_personal_ignores(repo)

            self.assertEqual([], added)
            self.assertEqual([], conflicts)
            self.assertEqual(".cache/\n", (repo / ".gitignore").read_text())

    def test_does_not_ignore_directory_with_tracked_team_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            (repo / ".cursor").mkdir()
            (repo / ".cursor" / "rules.md").write_text("team rules")
            subprocess.run(["git", "add", ".cursor/rules.md"], cwd=repo, check=True)

            added, conflicts = apply_personal_ignores(repo)

            self.assertEqual([], added)
            self.assertEqual([], conflicts)


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

    def test_codex_can_split_state_and_skill_roots(self):
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

            recover_interrupted_install(cursor_home, skills_home=cursor_home / "skills")

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
                        "skills_home": str((cursor_home / "skills").resolve()),
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
                        "skills_home": str((cursor_home / "skills").resolve()),
                    }
                )
            )

            recover_interrupted_install(cursor_home)

            self.assertEqual("stable-old", (target / "SKILL.md").read_text())

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

            recover_interrupted_install(state_home)
            self.assertEqual("original", (target / "SKILL.md").read_text())

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
            recover_interrupted_install(state_home)
            self.assertEqual("old", (target / "SKILL.md").read_text())


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
        self.assertNotIn("my-tech-design", composition["callers"])
        self.assertTrue(
            all(
                "my-tech-design" not in entries
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
                self.assertIn("document-rendering.md", body)
                self.assertRegex(content, r"不(?:得)?(?:生成|写) HTML")
                self.assertIn("blocked-by-content", frontend)
                self.assertRegex(frontend, r"不(?:得)?(?:改变|改写)")

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
                "to-questionnaire-<slug>.md",
                "只就“发送”采访用户，而不要就主题采访用户",
            ],
            "my-wizard": [
                "每个阶段按顺序命名",
                "永远不要编造可能不存在的步骤",
                "不要改动 `STAGES` 标记上方的库",
            ],
            "my-edit-article": ["articles", "默认生成新稿", "原地修改"],
            "my-review-design": [
                "只评审，不修改文档，不重新展开访谈",
                "references/shared/final-state-writing.md",
                "未发现影响方案成立或实施的实质问题",
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
                sorted(path.name for path in (workflow / "releases").iterdir()),
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
