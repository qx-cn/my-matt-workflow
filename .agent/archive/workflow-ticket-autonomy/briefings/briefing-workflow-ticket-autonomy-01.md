# workflow-ticket-autonomy-01 执行简报

## Ticket

---
id: workflow-ticket-autonomy-01
title: 实施自主权与不重置预算的技术刷新
ticket_kind: implementation
spec_id: workflow-ticket-autonomy
spec_revision: 1
spec_ref: .agent/work/workflow-ticket-autonomy/specs/specs-workflow-ticket-autonomy-01.md
supersedes_ticket: []
compensates: []
status: ready-for-agent
blocked_by: []
claimed_by:
tags: []
sequence: 1
test_commands: ["python3 -m unittest discover -s tests"]
touchpoints: ["tools/workflow_lib", "tools/workflow.py", "skills", "resources", "tests", "README.md"]
review_probes: [recovery]
execution_agent: codex
---

# 01 — 实施自主权与不重置预算的技术刷新

**要构建什么：** Agent 为已确认目标自主调整实施；技术刷新能恢复已登记技术挑战、失效旧证据，同时保留预算与真实待决事项。

## 验收标准

- [ ] AC-01、AC-02：规则一致，实施调整可追溯，验收覆盖和完成历史保留。
- [ ] AC-03：三个技术刷新入口与记录校验可通过真实 CLI 使用。
- [ ] AC-04：刷新失效证据而保留轮数、基线、发现与历史，预算耗尽仍拒绝第五轮。
- [ ] AC-05：技术/产品挑战混合时准确处置与路由，覆盖三个入口。
- [ ] AC-06：旧记录和重复恢复安全，缺证据/错误身份不解除停止。
- [ ] AC-07：回归、全量、冻结独立审查、场景演练和发布包验证有实际证据。


## Spec 验收

- AC-01：共同授权规则与实施、TDD、测试边界、项目规则、审查修复、Ticket 格式一致；touchpoints、旧 rule_scope、原计划是提示。技术事实错误、实现漏项按普通 spec/correctness 修复，不构成用户专属挑战。
- AC-02：实施调整记录原因、影响、验收归属和验证；保持 Spec 血缘与完成历史，不减少验收覆盖或隐藏实际失败。
- AC-03：提供 resolve --ticket <id> --refresh、resolve --branch --refresh、batch refresh，必填 reason 和 notes-file；Agent 判断技术/产品性质，runtime 校验身份、定义及状态。accept/reopen 保留用户裁决语义。
- AC-04：技术刷新更新定义并使旧测试、自审、审查通过失效；基线、同一 series 的全部已开轮次、剩余预算、未解发现、原始历史保留；未提交轮次仍消耗预算。预算耗尽后仍拒绝第五轮。
- AC-05：已登记技术性 spec-challenge 可凭点名证据追加处置；不得批量删除旧挑战，不解除无关产品挑战、证据不足、语义矛盾或预算停止。覆盖 Ticket、批次、整分支及 status/next_command。
- AC-06：旧记录依据现存审查历史恢复预算，不默认清零；重复恢复不丢历史、不重复计数。缺少证据、错误发现身份不能解除停止。
- AC-07：相关 CLI 生命周期、恢复、预算、资源打包回归及全量测试通过；另以固定场景新上下文 Agent 验证自主施工。源码、发布包、宿主安装和行为演练分别报告。


## 已完成前置 Ticket

## 适用规则

[
  {
    "source": "tests/fixtures/workflow_simplification/legacy_project/AGENTS.md",
    "applies_by": "codex-native",
    "scope": [
      "tests/fixtures/workflow_simplification/legacy_project/.agent/matt-workflow.md",
      "tests/fixtures/workflow_simplification/legacy_project/.agent/topic-locks/legacy-a.lock",
      "tests/fixtures/workflow_simplification/legacy_project/.agent/topic-locks/legacy-b.lock",
      "tests/fixtures/workflow_simplification/legacy_project/.agent/topic-locks/legacy-c.lock",
      "tests/fixtures/workflow_simplification/legacy_project/.agent/topic-locks/legacy-d.lock",
      "tests/fixtures/workflow_simplification/legacy_project/.agent/topic-locks/legacy-e.lock",
      "tests/fixtures/workflow_simplification/legacy_project/.agent/work/legacy-a/contexts/contexts-legacy-a-01.md",
      "tests/fixtures/workflow_simplification/legacy_project/.agent/work/legacy-a/runs/lifecycle-transactions/.my-matt-ownership.json",
      "tests/fixtures/workflow_simplification/legacy_project/.agent/work/legacy-a/runs/locks/legacy-a-02.lock",
      "tests/fixtures/workflow_simplification/legacy_project/.agent/work/legacy-a/runs/locks/legacy-a-03.lock",
      "tests/fixtures/workflow_simplification/legacy_project/.agent/work/legacy-a/runs/run-legacy-a-02-spec-r1.evidence/5acd4e4eb298f58c38e8a6cee3b41433317686a6212b613db16e38002bc246cf.json",
      "tests/fixtures/workflow_simplification/legacy_project/.agent/work/legacy-a/runs/run-legacy-a-02-spec-r1.evidence/dfdab5fd13e9b6d727d6d1a34a062268ae281f1099acc45d92bf8ac76301b913.json",
      "tests/fixtures/workflow_simplification/legacy_project/.agent/work/legacy-a/runs/run-legacy-a-02-spec-r1.evidence/review-results/d30f270e1ae5fec9b08b234e849a3908.json",
      "tests/fixtures/workflow_simplification/legacy_project/.agent/work/legacy-a/runs/run-legacy-a-02-spec-r1.evidence/review-snapshots/.my-matt-ownership.json",
      "tests/fixtures/workflow_simplification/legacy_project/.agent/work/legacy-a/runs/run-legacy-a-02-spec-r1.json",
      "tests/fixtures/workflow_simplification/legacy_project/.agent/work/legacy-a/runs/run-legacy-a-03-spec-r1.json",
      "tests/fixtures/workflow_simplification/legacy_project/.agent/work/legacy-a/specs/specs-legacy-a-01.md",
      "tests/fixtures/workflow_simplification/legacy_project/.agent/work/legacy-a/tickets/tickets-legacy-a-01.md",
      "tests/fixtures/workflow_simplification/legacy_project/.agent/work/legacy-a/tickets/tickets-legacy-a-02.md",
      "tests/fixtures/workflow_simplification/legacy_project/.agent/work/legacy-a/tickets/tickets-legacy-a-03.md",
      "tests/fixtures/workflow_simplification/legacy_project/.agent/work/legacy-b/contexts/contexts-legacy-b-01.md",
      "tests/fixtures/workflow_simplification/legacy_project/.agent/work/legacy-b/runs/lifecycle-transactions/.my-matt-ownership.json",
      "tests/fixtures/workflow_simplification/legacy_project/.agent/work/legacy-b/runs/locks/legacy-b-01.lock",
      "tests/fixtures/workflow_simplification/legacy_project/.agent/work/legacy-b/runs/run-legacy-b-01-spec-r1.json",
      "tests/fixtures/workflow_simplification/legacy_project/.agent/work/legacy-b/specs/specs-legacy-b-01.md",
      "tests/fixtures/workflow_simplification/legacy_project/.agent/work/legacy-b/tickets/tickets-legacy-b-01.md",
      "tests/fixtures/workflow_simplification/legacy_project/.agent/work/legacy-c/contexts/contexts-legacy-c-01.md",
      "tests/fixtures/workflow_simplification/legacy_project/.agent/work/legacy-c/runs/lifecycle-transactions/.my-matt-ownership.json",
      "tests/fixtures/workflow_simplification/legacy_project/.agent/work/legacy-c/runs/locks/legacy-c-01.lock",
      "tests/fixtures/workflow_simplification/legacy_project/.agent/work/legacy-c/runs/run-legacy-c-01-spec-r1.json",
      "tests/fixtures/workflow_simplification/legacy_project/.agent/work/legacy-c/specs/specs-legacy-c-01.md",
      "tests/fixtures/workflow_simplification/legacy_project/.agent/work/legacy-c/tickets/tickets-legacy-c-01.md",
      "tests/fixtures/workflow_simplification/legacy_project/.agent/work/legacy-d/contexts/contexts-legacy-d-01.md",
      "tests/fixtures/workflow_simplification/legacy_project/.agent/work/legacy-d/runs/lifecycle-transactions/.my-matt-ownership.json",
      "tests/fixtures/workflow_simplification/legacy_project/.agent/work/legacy-d/runs/locks/legacy-d-01.lock",
      "tests/fixtures/workflow_simplification/legacy_project/.agent/work/legacy-d/runs/run-legacy-d-01-spec-r1.evidence/5acd4e4eb298f58c38e8a6cee3b41433317686a6212b613db16e38002bc246cf.json",
      "tests/fixtures/workflow_simplification/legacy_project/.agent/work/legacy-d/runs/run-legacy-d-01-spec-r1.evidence/e9d496eab8b8465f861a4e903a2eff316c8ea207b3a6ab4b991c99a91ab4de67.json",
      "tests/fixtures/workflow_simplification/legacy_project/.agent/work/legacy-d/runs/run-legacy-d-01-spec-r1.evidence/review-results/4ee325b1bba83eb08622d2416e2298bf.json",
      "tests/fixtures/workflow_simplification/legacy_project/.agent/work/legacy-d/runs/run-legacy-d-01-spec-r1.evidence/review-snapshots/.my-matt-ownership.json",
      "tests/fixtures/workflow_simplification/legacy_project/.agent/work/legacy-d/runs/run-legacy-d-01-spec-r1.json",
      "tests/fixtures/workflow_simplification/legacy_project/.agent/work/legacy-d/specs/specs-legacy-d-01.md",
      "tests/fixtures/workflow_simplification/legacy_project/.agent/work/legacy-d/tickets/tickets-legacy-d-01.md",
      "tests/fixtures/workflow_simplification/legacy_project/.agent/work/legacy-e/contexts/contexts-legacy-e-01.md",
      "tests/fixtures/workflow_simplification/legacy_project/.agent/work/legacy-e/runs/lifecycle-transactions/.my-matt-ownership.json",
      "tests/fixtures/workflow_simplification/legacy_project/.agent/work/legacy-e/runs/locks/legacy-e-01.lock",
      "tests/fixtures/workflow_simplification/legacy_project/.agent/work/legacy-e/runs/locks/legacy-e-02.lock",
      "tests/fixtures/workflow_simplification/legacy_project/.agent/work/legacy-e/runs/run-legacy-e-01-spec-r1.json",
      "tests/fixtures/workflow_simplification/legacy_project/.agent/work/legacy-e/runs/run-legacy-e-02-spec-r1.json",
      "tests/fixtures/workflow_simplification/legacy_project/.agent/work/legacy-e/specs/specs-legacy-e-01.md",
      "tests/fixtures/workflow_simplification/legacy_project/.agent/work/legacy-e/tickets/tickets-legacy-e-01.md",
      "tests/fixtures/workflow_simplification/legacy_project/.agent/work/legacy-e/tickets/tickets-legacy-e-02.md",
      "tests/fixtures/workflow_simplification/legacy_project/.gitignore",
      "tests/fixtures/workflow_simplification/legacy_project/AGENTS.md",
      "tests/fixtures/workflow_simplification/legacy_project/app.py",
      "tests/fixtures/workflow_simplification/legacy_project/test_app.py"
    ],
    "directory": "tests/fixtures/workflow_simplification/legacy_project",
    "selected_by": "agents",
    "precedence_index": 4
  },
  {
    "source": "tests/fixtures/workflow_simplification/unfinished_session/AGENTS.md",
    "applies_by": "codex-native",
    "scope": [
      "tests/fixtures/workflow_simplification/unfinished_session/.agent/matt-workflow.md",
      "tests/fixtures/workflow_simplification/unfinished_session/.agent/work/turn-closure/specs/specs-turn-closure-01.md",
      "tests/fixtures/workflow_simplification/unfinished_session/.agent/work/turn-closure/tickets/tickets-turn-closure-01.md",
      "tests/fixtures/workflow_simplification/unfinished_session/.agent/work/turn-closure/tickets/tickets-turn-closure-02.md",
      "tests/fixtures/workflow_simplification/unfinished_session/AGENTS.md",
      "tests/fixtures/workflow_simplification/unfinished_session/app.py",
      "tests/fixtures/workflow_simplification/unfinished_session/review.py",
      "tests/fixtures/workflow_simplification/unfinished_session/test_app.py"
    ],
    "directory": "tests/fixtures/workflow_simplification/unfinished_session",
    "selected_by": "agents",
    "precedence_index": 4
  }
]

## 非约束性触点提示

["tools/workflow_lib", "tools/workflow.py", "skills", "resources", "tests", "README.md"]

## 同批次已提交 Ticket 的影响面（实施者声明，待核实）

### tests/fixtures/workflow_simplification/legacy_project/AGENTS.md
# Fixture rules
Use only the Python standard library.


### tests/fixtures/workflow_simplification/unfinished_session/AGENTS.md
Use the Python standard library only. Keep the greeting module and its tests in this repository.


## 测试命令

python3 -m unittest discover -s tests

## 实施计划

Agent 动手前补写：文件和接口；现状断言→代码依据；契约/共享函数/表结构/配置/锁/错误码→调用方/消费者和兼容、数据、并发、权限、性能结论；每项验收各自对应测试断言。核实技术事实与实现漏项，按当前共同授权规则直接修复并记录；只有改变已确认用户约定才按 spec-challenge 请求决定。

## 实施计划与已核实事实

- 公共 CLI 负责选择入口与必填参数；technical_refresh 单一事务实现定位、证据、点名处置、定义绑定、验证失效和预算恢复。调用方为 resolve/batch；消费者为实施状态、batch/branch 测试、审查开轮、修复与交付门禁。AC-03 至 AC-06 由临时真实 Git 仓库的公共 CLI 生命周期验证。
- 实施单位的当前 reviews 包含已开未提交轮次；旧 reopen 会将其移入 past_reviews 并开启用户批准的新 series。新增 refresh 保留当前数组与 first_review_volume，恢复缺失旧计数但不覆盖用户显式重开的新 series。AC-04、AC-06 以真实开轮/旧结果过期/第五轮拒绝及 user reopen 兼容性验证。
- 批次与整分支测试在单独文件中；只删除 Ticket test_run 不足以失效它们，因此增加 refresh_epoch 绑定，保留完整原始测试收据。审查通过的 active_review 被移除资格，原始 reviews 与 accepted 文件保留。AC-04 用当前内容不变的定义/技术处置刷新负向验证。
- 自审 pending_self_findings 从原始自审历史及追加 resolutions 归约；独立审查用 exact unit_id/finding_id 追加 technical_resolutions，状态与 repair 消费过滤后的待处置发现。AC-05 以技术、产品、correctness 混合及 evidence/contradiction/budget 停止验证。
- 规则修改全部落在现有共享资源和其消费者，不新增平行授权来源。AC-01、AC-02 通过资源/打包回归与隔离新上下文施工演练验证；当前宿主、源码、发布包和行为演练分开报告。

## 实施调整与验证记录

- 2026-10-04：首个新增 Ticket refresh 生命周期在旧 CLI 上失败（exit 1，缺少 --refresh），证明新入口回归能区分旧实现。
- 2026-10-04：11 项初始 CLI 回归及 21 项共享资源回归通过。补充混合独立挑战测试发现整分支产品挑战未显示于 batch status；已同步分支待处置发现并通过专项回归。
- 2026-10-04：扩展至 15 项公共 CLI 测试通过；增加用户显式 reopen 后刷新兼容性，避免复用旧 series。全量测试在修订过程中中断的运行不算通过；最终稳定源码需重新跑完整声明测试。
- notes-file 采用严格六字段 JSON，证据路径自动保存 sha256；这是技术实现选择，不改变 Agent 对技术/产品性质负责、runtime 只校验机械身份/状态的合同。

- 2026-10-04：374 项全量执行有 1 项人类状态提示回归（具体产品裁决选项缺失）；已恢复平实的裁决选项并通过专项检查。独立冻结审查复现新开工简报仍带旧停工指令、整分支刷新 next_command 不匹配批次测试绑定，已同步真实运行时消费者，17 项技术刷新回归通过。旧 test_run/active_review/self_review/acceptance 原始记录追加至 invalidated_evidence，保留过期原因与原停止状态。最终全量与发布 gate 需在稳定源码完成。

- 2026-10-04：最终18项刷新回归、镜像证据停止和独立差异复审通过；额外验证 .agent 临时路径符号链接在入口被拒绝、无外部写入。批次旧全量收据追加 prior_full_tests，重新测试后原结果仍完整保留。一次并行全量375项出现既有 artifact-review-finalize 快照生命周期异常，独立重跑该用例通过；后续构建使用独立 TMPDIR 隔离并行门禁的共享临时快照注册表，不将隔离通过宣称全局并发保证。最终完整源测试/批次测试/发布gate仍需实际通过。
