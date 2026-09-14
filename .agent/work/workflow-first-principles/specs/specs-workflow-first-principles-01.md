---
spec_id: workflow-first-principles
revision: 1
supersedes:
status: current
---

# 开发主链优化方案

## 目标结果

在不增加新 Skill 的前提下，让需求澄清、分析、设计、开发、测试和 review 主链做到：证据名称与事实一致；低风险任务不被审计级流程拖累；承重设计不会未经评审进入实施；implementation runtime 的职责边界可独立演进；source、release 与安装态继续明确分离。

## 不改范围

- 不重新设计 37 个 Skill 的完整 portfolio。
- 不修改外部 Tracker、真实业务项目或真实宿主安装；安装需要单独授权。
- 不把同会话自审称为独立评审。
- 不为了追求目录整齐而进行无行为收益的大规模移动。
- 不把尚未运行的 comparative 或 real-project case 写成 pass。

## 优先级与实施批次

### P0：修正证据事实模型

1. 将 portfolio 四层中的 `cases` 明确定义为 `planned_cases`，表示验证计划而非执行 receipt。
2. validator 对 static、deterministic、fresh-agent 的 planned case 做现有可达性校验；real-project 允许 planned case 或 exemption。
3. 新增独立的 execution-evidence registry，只保存实际 evidence 文件、suite/case、release、status 和 content digest 的索引；不得复制 rubric 结论。
4. `check` 分别报告 `verification_plan` 和 `execution_evidence`；没有当前执行证据时返回 `not-recorded`，不能冒充失败或通过。
5. 迁移现有 manifest 和测试，保留旧 evidence 文件的历史含义，但不自动把它绑定到当前 source。

验收：不存在将场景定义称为已执行 evidence 的输出；伪造、过期或 digest 不匹配的 registry 被拒绝；未登记执行 evidence 时 source check 仍可通过但明确报告 `not-recorded`。

### P1：引入风险分级的主链保证

1. 不新增 Skill；在 profile 增加正交的 `assurance_level: quick|standard|audited`。
2. `quick`：单会话、低风险、无外部副作用任务可使用可追溯需求摘要、针对性测试和同会话自审，不强制版本化 Spec/Ticket/runtime journal。
3. `standard`：版本化 Spec；跨上下文或多切片时生成 Tickets；存在 Ticket 时使用 journal、测试 evidence 和代码审查，明确的单切片无 Ticket 工作直接报告真实验证证据，不伪造 journal。
4. `audited`：完整 Spec/Ticket 血缘、冻结输入、runtime evidence、受管 repair plan 和严格 close/transition。
5. 五档自治 preset 不暗中改变 assurance；setup 分别确认自治档与保证档。

验收：三档具有互斥、可观察的准入条件；quick 不得用于公开接口、不可逆数据、迁移、外部副作用、安全或跨会话任务；audited 保留当前所有强保证。

### P1：收敛需求、设计与测试方法边界

1. `my-grill-with-docs` 完成时输出一个可追溯需求摘要：目标、范围、约束、验收、来源/推断。
2. `my-requirement-analysis` 保留为复杂或类比驱动请求的可选独立方法，不再与普通 grill 重复完整流程。
3. Spec 含公开接口、数据语义、持久状态、迁移、安全或不可逆决策时，进入 design review gate；普通可逆实现细节不触发。
4. `my-tdd` 是行为开发的默认方法；characterization、已有充分覆盖、机械重构、配置/文档或无法先 red 的诊断可选择等价验证策略并说明依据。

验收：主链对需求摘要和设计 gate 有唯一规则来源；完成标准验证结果与证据，不要求 runtime 无法证明的仪式历史。

### P2：缩小 implementation 控制面和热点模块

1. 保持现有 CLI 兼容；新增内部 application service，统一返回唯一 `next_action`。
2. Skill/adapter 只依赖 `open`、`status/next_action`、`submit semantic result`、`close` 这组高层语义，不枚举内部恢复分支。
3. 从 `run_journal.py` 先提取无状态的 evidence validation 与 review result validation；第二步再提取 repair cycle。每步保持行为等价并运行完整测试。
4. runtime 无法拦截 host final 的限制继续如实保留；通过 next-action 行为 eval 降低误用，不宣称硬拦截。

验收：核心 validator 可独立测试；`run_journal.py` 不再拥有 evidence schema 和 review-result 全部判断；旧 CLI 与 journal 兼容测试保持通过。

### P3：发布与效果验证

1. 源码改动通过 targeted tests、完整 unittest、validate、validate-evals、smoke 和 release-aware check。
2. 构建新 release 以消除 current drift；不自动安装真实宿主。
3. 设计 baseline/candidate comparative runbook，指标至少包括完成率、返工、越界、提前结束、Token 和耗时；本轮不运行高成本模型实验，除非另获授权。

验收：current release 与 source match；comparative case 只登记为 planned，未执行时保持 `not-recorded`。

## 实施顺序

严格按 P0 → P1 assurance → P1 方法边界 → P2 runtime 解耦 → P3 release/验证推进。每一批先跑针对性测试；若发现方案会扩大公开接口、破坏兼容或需要真实宿主写入，停止在该批的正式 blocker，不绕过边界。
