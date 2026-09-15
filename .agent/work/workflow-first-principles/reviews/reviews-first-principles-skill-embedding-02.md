---
review_id: first-principles-skill-embedding-02
reviewed_source: c83c1f629c7515d66643e2c39200fffc6c8823b3
review_scope: critical-workflow-skills-and-first-principles-ownership
reviewer_provenance: self
status: findings-and-recommendations
---

# 重要链路 Skill 与第一性原理机制审查

## 结论

需求澄清、Spec、设计 Gate、实施、测试和代码审查主链已经完成过系统级第一性原理审查，相关 P0–P3 问题也已实施修复；不应再从头重复一轮相同审查。当前需要的是按影响排序的单 Skill Deep Review，以及对少数“证据如何推出决定”的缺口做定点增强。

现状只能证明架构合同、静态约束、单元测试和 deterministic scenarios 有效，不能证明全部关键 Skill 相对无 Skill baseline 有净收益。审查时重新运行 `python3 tools/workflow.py check`，结果为 37 Skills、unit、19 个 deterministic scenarios 和 current release `workflow-first-principles-v3` 有效；17 个 fresh-agent case 仍只是 planned cases，execution evidence 为 `not-recorded`。

第一性原理应作为承重决定处的稀疏控制：追问真实目标、事实与推断、不可破坏的约束、方案的因果机制、最小替代方案、可证伪证据和外部验收。它不应成为每个 Skill 重复的一张通用 checklist，也不应把 runtime 已经强制的快照、receipt、恢复和关闭机制重新写入 Skill。

## 已经完成的审查范围

- `my-requirement-analysis` 已区分用户原文、仓库事实和未确认推断，并对复杂或类比驱动请求进行需求核对。
- `my-to-spec` 已覆盖目标、范围、不变量、验收、验证策略、依据和未知，并在承重设计进入下游前运行设计 Gate。
- `my-implement` 与 `my-tdd` 已按 assurance level 调整实施和验证强度，并允许有依据的非 TDD 等价验证；`my-code-review` 不直接消费 assurance level，而是按实际风险加深审查。快照、证据和关闭仍由 runtime 管理。
- 自审默认标记为 `self`，不会被写成独立 reviewer evidence。
- `my-review-skill` 已具备 Job Contract、存在性 Gate、因果链和证据分级，`my-writing-great-skills` 已负责 Skill 的指令设计而不替代根本性审查。

以上是系统级与职责级审查，不等于每个关键 Skill 都已经完成独立 Deep Review。

## 当前需要处理的事项

### F1：第一梯队仍需要逐项 Deep Review

第一梯队应包含：

1. `my-review-skill`：它是后续 Skill 审查的元工具，先验证其 Verdict 和 evidence boundary。
2. `my-writing-great-skills`：验证其是否真正减少无效操作、重复和规则沉积。
3. `my-grilling`、`my-grill-with-docs`、`my-requirement-analysis`：作为同一 discovery 行为闭包逐项审查，重点验证目标与手段分离、提问停止条件和决策权边界。
4. `my-to-spec`：验证承重决定能否从来源和约束追溯到验收，而不是只有分散字段。
5. `my-review-design`：验证不可逆设计是否比较替代方案、说明不可逆成本并给出可证伪预测。
6. `my-to-tickets`：验证每个 Ticket 是否对用户结果作出独立、必要、可验收的贡献，且拆分没有按目录或技术层机械切割。

`my-to-tickets` 接受用户意见加入第一梯队。理由是它把已批准设计转换为实际实施边界、依赖和所有权；错误拆分会把正确 Spec 变成错误执行顺序或越界工作，且当前 portfolio 明确把真实项目中的 slicing quality 标为未测量。

### F2：discovery 中存在决策权边界冲突候选

`my-grilling` 当前把所有“决策”概括为用户应逐项回答，而共享 `instruction-authority` 把已批准范围内的普通、可逆执行细节定义为 `routine`，应由 Agent 继续。组合调用时可能造成过度访谈，把实现细节错误上交用户。应在 Deep Review 中确认影响路径，再把访谈对象收窄到用户专属或会改变目标、范围、公开接口、数据语义、测试投入和风险承担的决定。

### F3：承重决定缺少紧凑的证据到验收闭环

`my-to-spec` 已分别记录来源、决定和验收，但没有要求重要决定形成显式的 `目标/主张 → 事实与约束 → 替代方案 → 决定 → 可证伪预测 → 验收` 关系。字段齐全不自动证明推导成立。只对承重决定补这条链；普通可逆实现细节不得因此进入 Spec。

### F4：设计审查对不可逆选择的反证力度不足

`my-review-design` 已检查逻辑完整性、一致性和设计闭环，但没有明确要求：哪些约束是不可约的、是否存在更小替代方案、为什么拒绝替代方案、选择错误的不可逆成本，以及什么观察会推翻设计。该增强只应用于公开接口、数据语义、迁移、安全/权限、持久状态或难逆转架构决定。

### F5：测试与代码审查更需要行为证据，不需要继续堆规则

`my-tdd`、`my-implement` 和 `my-code-review` 已经具有可观察行为、独立 oracle、风险加深、双遍审查、finding gate 和 runtime evidence。下一步应以真实变更验证 `风险/失败模式 → 独立 oracle → test/runtime evidence`，而不是增加一套重复的第一性原理文字。

### F6：需要通用第一性原理审查能力，但必须限制职责

接受新增 `my-first-principles-review`，但不接受“任何内容都由它全面审查”的定位。它作为用户显式选择的 specialist，只审查已经形成的提案、决定、流程、制度、产品机制或技术设计，其目标与手段之间是否有可成立的因果链；不替代：

- `my-requirement-analysis` 的需求理解核对；
- `my-review-design` 的设计可实施性与设计闭环；
- `my-code-review` 的代码正确性审查；
- `my-review-skill` 的 Skill 存在性、归宿和行为证据审查；
- `my-artifact-finalization` 的来源、一致性、读者重建和事实正确性 Gate。

合法结果应为 `HOLDS | HOLDS_WITH_GAPS | VIOLATES | INCONCLUSIVE`。它只读、不替用户做产品取舍、不自动修改对象；发现违背第一性原理时输出最小修正方向和解除证据缺口的方法。用户问“这个提案从根本上是否成立”时使用它；用户问“技术设计是否闭环并足以实施”时使用 `my-review-design`；需要固定快照和正式交付 Verdict 时仍使用 `my-review-artifact`。本轮不把新 Skill 接入后两者的组合图。

### F7：第一性原理应抽象为 shared reference

接受抽象，但 shared reference 只保存尚无权威归属的稳定推理原语，不保存各 Skill 的执行顺序、输出模板、来源分类或授权规则。它与现有资源的边界为：

- `instruction-authority` 回答“谁有权决定、是否需要确认”；
- `artifact-finalization` 回答“产物中的主张是否可追溯、一致且事实正确”；
- 新的 first-principles reference 引用前两者，并且只定义“目标到手段的因果链、最小反事实和可证伪预测”。

当前识别出六个拟定消费者：`my-first-principles-review`、`my-grill-with-docs`、`my-to-spec`、`my-review-design`、`my-to-tickets` 和 `my-review-skill`。最终消费者由逐项 Deep Review 确认；各消费者只引用与自身决定相关的部分，不复制全文。若确认后的真实消费者不足三个，则不新建 shared reference，把所需原语放回拥有该决定的 Skill。

### F8：第二梯队暂缓

接受暂不处理 `my-ask-matt`、`my-diagnosing-bugs`、`my-handoff`、`my-test-report`、`my-setup`、`my-install`、`my-triage`、`my-wayfinder`、`my-resolving-merge-conflicts` 等第二梯队 Skill。新 Skill 本轮登记为用户显式调用的 specialist，不修改 `my-ask-matt` 路由。暂缓不代表判定第二梯队有效；portfolio 中相应 evidence gap 保持原状，也不把它们纳入本轮完成声明。

## 五项总体判断

- 是否需要继续第一性原理 review：需要定点继续，不需要重复整条主链。
- 是否应嵌入重要 Skill：应嵌入承重决策点，不应普遍复制。
- 是否应新增 Skill：有条件需要；必须是独立可调用的因果成立性审查，而非万能 review。
- 是否应新增 shared reference：当前有六个拟定消费者，倾向新增；Deep Review 后至少三个真实消费者仍需要时才落地，而且只抽象尚无归属的推理原语。
- 当前最重要的证据缺口：逐 Skill Deep Review 和真实项目行为证据，而不是更多静态规则。
