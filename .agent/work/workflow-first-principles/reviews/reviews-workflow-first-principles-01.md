---
review_id: workflow-first-principles-01
reviewed_source: 06d5a11
review_scope: requirement-to-review-main-chain
reviewer_provenance: self
status: findings
---

# 开发主链第一性原理审查

## 结论

本 workflow 的根本目标，是把不确定的 Agent 工作转化为受用户意图约束、可恢复、可审计、且有真实证据支持的代码变更。宏观分层方向正确：Skill 负责语义方法，runtime 负责快照、权限、生命周期和证据不变量；但默认流程深度、证据语义和 implementation 控制面尚未收敛。

机制层已经较强地支持范围约束、不可变快照、测试与审查 receipt、跨会话恢复和跨宿主投影；尚无证据证明整条链路相对简单流程在真实项目中提高成功率、减少返工或值得其时间与 Token 成本。

## Findings

### P1：fresh-agent 计划被表述成已存在的行为证据

`portfolio/manifest.json` 的 `fresh_agent.cases` 只关联 suite 中的场景定义。`tools/workflow_lib/portfolio.py` 不读取实际运行记录，`workflow.py check` 也只验证 suite 结构。这能证明“计划测什么”，不能证明场景针对当前 release 执行过或通过。

影响：portfolio coverage、执行证据和 release 准入三种事实混在同一个 `evidence` 名称下，容易把待执行 case 当作已取得的 fresh-agent evidence。

### P1：当前 source、current release 与安装态分叉

审查时 `main` 与 `origin/main` 均为 `06d5a11`，工作树干净；297 项单测通过。`workflow.py check` 因 `current release is stale: releases/implementation-turn-closure-v2` 失败。`doctor` 显示 source valid、current release drift，Codex 与 Claude 的旧 release 自身 valid，Cursor not-installed。

影响：当前源码修复尚未形成可安装产品，不能把 source test pass 当作用户已在运行修复版。

### P1：主链端到端效果没有闭合证据

已有主链 fresh-agent 记录为 `inconclusive`：观察到 Spec、Ticket、TDD、测试和 review snapshot，但没有观察到完整提交、Ticket 完成、测试报告和最终 handoff。各主链 Skill 的 real-project 层仍为 exemption，也没有相同模型、输入和权限下的 baseline/candidate 对照。

影响：目前只能确认合同和基础设施，不能确认 workflow 的实际净收益。

### P2：默认流程深度没有按风险分级

五档 profile 主要控制确认、写入和连续执行，并不决定任务需要 Quick、Standard 还是 Audited 级保证。低风险、单会话改动仍可能承担 Spec、Ticket、journal、snapshot、receipt、repair plan 和 close/transition 的完整成本。

### P2：需求核对与设计评审存在，但主链缺少风险触发条件

`my-grilling` 与 `my-requirement-analysis` 都承担需求理解职责，前者在主链、后者是显式 specialist。`my-to-spec` 默认直接交给 `my-to-tickets`，初始设计并没有基于公开接口、状态、数据语义或不可逆风险触发 `my-review-design`。

### P2：强制 TDD 把一种方法当成完成结果

`my-implement` 要求每项验收经历 red-green-refactor，但 runtime 最终只验证代码、测试和审查 evidence，并不能验证每个 red-green 历史。该合同不适合已有覆盖的小修、characterization、机械重构、配置和迁移类变更。

### P2：控制面仍泄漏给 Agent

runtime 已拥有大量机械状态，但 Agent 仍需正确串联多条 CLI。runtime 又无法拦截宿主发送 final，只能依靠 Skill 文字约束。最关键的不变量仍不在可强制的边界上。

### P2：`run_journal.py` 是 implementation 扩展热点

该模块约 2,152 行，同时承担 admission、test/review evidence、repair plan、completion、parallel session 和 close/transition；多个核心函数超过 100 行。新增 review 或 recovery 行为会跨多个职责和大量 fixtures 扩散。

## 五项判断

- 过度设计：安全内核本身不过度；对低风险任务默认应用完整流程属于过度。
- 目标实现：机制目标大部分实现，真实开发效果目标尚未证明。
- 稳定性：源码确定性测试较强；运行、发布和端到端行为稳定性中等偏低。
- 可扩展性：普通 Skill 和宿主投影较好；implementation 生命周期扩展成本高。
- 架构：宏观合理；证据模型、风险分级和 runtime 控制面需要收敛。

