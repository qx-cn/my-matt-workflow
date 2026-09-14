---
review_id: workflow-first-principles-implementation-01
review_scope: requirement-to-review-main-chain-implementation
reviewer_provenance: self
status: pass-with-residual-evidence-gaps
release_id: workflow-first-principles-v3
---

# 开发主链优化实施自审

## 结论

优化方案 P0 至 P3 的源码内工作已经按优先级完成，未发现阻止构建 release 的当前范围缺陷。本结论来自同一会话自审，不是独立 reviewer evidence；fresh-agent 与真实项目效果仍未运行，不能据此宣称工作流已经在真实开发中产生净收益。

## 按优先级复核

### P0 证据事实模型：通过

- portfolio 的四层关联统一命名为 `planned_cases`，validator 拒绝旧 `cases`，避免把场景计划称为执行证据。
- 独立 execution-evidence registry 只接受仓库内相对路径、64 位十六进制 SHA-256，并校验实际 evidence schema 与 digest。
- `check` 分开报告 `verification_plan` 和 `execution_evidence`；本轮实际结果为前者 `valid`、17 个计划 case，后者 `not-recorded`、0 条记录。

### P1 风险分级与方法边界：通过

- profile 新增正交的 `quick|standard|audited`，默认 `standard`；setup、共享 adapter、资源治理和 profile 测试共同约束。
- 主链按风险决定 Spec、Ticket 和 journal 深度；quick 有明确排除条件，standard 不为无 Ticket 单切片伪造 journal，audited 保留全部恢复门禁。
- 需求摘要、复杂需求核对、承重设计 gate 与 TDD 例外均落在现有 Skill/组合边界，没有新增重复 Skill。

### P2 runtime 控制面与热点：通过，保持增量边界

- 新增 `implementation-next-action` 作为高层入口，旧 `implementation-status` 保持兼容，并返回相同的 `next_action` / `next_gate`。
- 从 `run_journal.py` 抽出 review-result、content-addressed evidence-record、repair-plan 和 next-action 四类纯逻辑，分别具有独立单测；状态持久化、锁与 lifecycle 协调仍留在原模块，避免一次性重写。
- 自审时曾发现 evidence-record 校验尚未抽出；已补齐后重跑相关测试和完整门禁。
- runtime 无法拦截宿主聊天 final 的限制没有被掩盖；本轮只缩小误用面，不声称获得不存在的硬保证。

### P3 发布与效果验证：源码闭合，外部效果保留缺口

- `workflow-first-principles-v2` 已构建并成为 current；最终 release-aware `check` exit code 为 0，source 与 release match。
- deterministic smoke 对受影响且已注册的六个 Skill 通过，共覆盖 12 个场景；全量门禁验证 37 Skills、19 个 deterministic scenarios 和完整 unittest。
- comparative runbook 已保存为 planned / not-recorded；未调用高成本模型。
- 未安装真实宿主。最终 doctor：Codex、Claude 仍为旧 `implementation-turn-closure-v2` 且状态 `drift`，Cursor 为 `not-installed`。这是授权边界，不是伪装成完成的源码问题。

## 残余风险

1. assurance 路由只有静态、单测和 deterministic contract 证据；需要另获授权的 fresh-agent baseline/candidate 对照才能判断真实收益与 Token/耗时成本。
2. `run_journal.py` 仍是较大的状态编排模块；本轮已把纯规则抽出，但不为行数目标移动有锁和 WAL 的协调逻辑。后续只应在新增行为迫使职责变化时继续拆分。
3. 本次未提交、未推送、未安装；这些状态必须与已验证的本地 source/current release 分开报告。

## 缺陷复审后的修复

后续 defect-first review 识别出的三项 P1 已全部修复：

1. 承重 Spec 先保持 `draft` 并完成设计 Gate，通过后才晋升 `current`、发布或添加 agent-ready 标签。
2. setup 的预览与 apply 明确携带同一 `--assurance-level <confirmed-level>`；refresh 更新等级时也必须显式携带。CLI 回归测试验证 audited 创建和 quick 刷新均实际落盘。
3. execution evidence 现在保留 `release_ids`，并相对 current release 报告 `current|historical|mixed|unbound|not-recorded`；registry 同时拒绝零运行记录。

修复后构建 `workflow-first-principles-v3`，最终 release-aware `check` exit code 为 0。

## 验证回执

- 相关 runtime 单测：47 tests，exit 0。
- 较大定向回归：237 tests，exit 0（抽取 evidence-record 前；之后完整门禁再次覆盖）。
- `workflow.py validate`：37 Skills，valid。
- `workflow.py validate-evals`：19 scenarios / 18 required，valid。
- deterministic smoke：6 Skills / 12 scenarios，valid。
- 最终 `workflow.py check`：exit 0；`workflow-first-principles-v3`、static/unit/evals/release valid；execution evidence `not-recorded`，`release_ids=[]`，`release_relation=not-recorded`。
- `git diff --check`：exit 0。
