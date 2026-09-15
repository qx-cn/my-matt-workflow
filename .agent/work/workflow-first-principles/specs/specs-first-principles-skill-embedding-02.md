---
spec_id: first-principles-skill-embedding
revision: 1
supersedes:
status: current
source_review: ../reviews/reviews-first-principles-skill-embedding-02.md
---

# 第一性原理审查与重要 Skill 优化方案

## 目标结果

在不重复现有专项 review、不把所有任务流程化的前提下，使重要链路在承重决定处能够证明：解决的是正确目标；事实、推断和约束没有混淆；所选手段有完整因果链；更小替代方案已被合理排除；失败可被证据发现；完成由外部可观察验收定义。

最终应得到：

1. 第一梯队每个 Skill 的 snapshot-bound Deep Review 结论；
2. 若 Deep Review 确认至少三个真实消费者，一个紧凑且单一事实来源的 shared first-principles reference；
3. 一个职责受限的 `my-first-principles-review`；
4. discovery、Spec、设计 review、Ticket 拆分和 Skill review 的定点改进；
5. 能区分静态合同、deterministic、fresh-agent 与 real-project 的验证记录。

## 不改范围

- 本轮不处理第二梯队 Skill，也不顺带修改其文案、路由或 evidence exemption；新 Skill 先登记为显式调用的 specialist，不修改 `my-ask-matt`。
- 不重新设计 assurance level、implementation journal、review snapshot、receipt、repair plan、release 或安装机制。
- 不把第一性原理写成所有 Skill 都要执行的固定 checklist。
- 不把普通可逆实现细节提升为 Spec 决策或用户确认项。
- 不把新 Skill 作为需求、设计、代码、Skill 或产物专项 review 的替代品。
- 不把同会话自审写成独立 reviewer evidence；不把 planned cases 写成已执行证据。
- 不运行有显著模型成本的 comparative/fresh-agent 实验，除非另获明确授权。

## 设计原则与职责边界

### Shared reference：`resources/first-principles-reasoning.md`

shared reference 是推理合同，不是流程编排器。它引用 `artifact-finalization` 的来源分类和 `instruction-authority` 的约束/决策分类，不重新定义它们；只建议定义以下尚无单一事实来源的原语：

1. **因果链**：先从使用者可观察结果重建真实目标，区分目标与用户给出的手段、示例、类比或既有做法；再建立 `目标或主张 → 已分类的事实与约束 → 候选机制 → 可观察中间结果 → 用户结果`。任一断点都是缺口。
2. **最小反事实**：至少考虑维持现状、删除该机制或一个更小替代方案；只对承重决定要求，不机械制造多方案。
3. **可证伪预测**：写出“若该机制成立，应观察到什么；什么结果会推翻它”，并让验收证据能够捕获失败，而不只是证明步骤被执行。

reference 同时定义三条反仪式规则：简单对象不展开完整链；专项 Skill 已负责的领域判断不重复；无法取得证据时沿用既有来源分类输出 `unknown/inconclusive`，不靠更多文字补偿。

### 新 Skill：`my-first-principles-review`

**Job Contract**：当用户已有一个明确的提案、决定、流程、制度、产品机制或技术设计，并明确要判断“这个手段从根本上是否成立”时，本 Skill 通过拆解其目标、事实、约束、因果机制、替代方案和证据，使该判断更可靠。

建议 description：

> 对已形成的提案、决定、流程或设计做只读第一性原理审查，验证目标、事实、约束、因果机制、替代方案与验收是否成立；不替代领域专项 review。

建议职责：

1. 固定审查对象、目标读者和要支持的决定；输入不明确时只询问会改变对象边界的最小问题。
2. 读取对象及其直接引用的最小事实来源；区分事实、假设与未知。
3. 重建真实目标，检查是否把手段、类比、惯例或局部指标当成目标。
4. 提取不可约约束，识别把偏好或历史实现误写成硬约束的情况。
5. 重建因果链，定位无法从事实推出机制、无法从机制推出用户结果的跳跃。
6. 对承重选择检查维持现状、删除机制或更小替代方案；不要求为简单对象凑方案数量。
7. 检查可证伪预测和验收证据是否能捕获失败，而不是只证明执行过步骤。
8. 只报告会改变采用、修改或放弃决定的 finding；同一根因去重。

建议 Verdict：

- `HOLDS`：目标、约束、因果链和验收成立，没有影响决定的缺口；
- `HOLDS_WITH_GAPS`：方向成立，但存在可解除且不推翻核心机制的证据缺口；
- `VIOLATES`：目标替换、伪约束、关键因果断裂、无合理性复杂度或验收错位会改变决定；
- `INCONCLUSIVE`：缺少承重事实，无法判断是否成立。

每个 finding 包含：对象位置、失败的原语、事实/假设证据、对用户结果的影响、最小修正方向和最小验证。Skill 保持只读；不自动改文档或执行提案。

调用边界：它是直接调用的建议性专项审查，不产生 `my-review-artifact` 的正式交付 receipt。判断技术设计是否闭环并足以实施时使用 `my-review-design`；需要固定快照、跨维度检查和正式交付 Verdict 时使用 `my-review-artifact`。本轮不把新 Skill 组合进这两个 Skill，也不修改它们的调用图。

建议结构仅需 `SKILL.md` 与 `agents/openai.yaml`；满足至少三个真实消费者条件时，通用原语放 shared reference，否则内联到本 Skill。不创建 scripts、assets 或重复参考文件。沿用项目所有 `my-*` Skills 的显式调用策略。

## 第一梯队 Deep Review

Deep Review 必须依次进行。除 `my-review-skill` 自身的 bootstrap audit 外，其他目标使用修订后 `my-review-skill` 的 runtime snapshot/finalize 合同；审查目标变化后旧结论失效。顺序如下：

### P0.1 `my-review-skill`

- 由当前会话在固定快照上执行 repository-grounded bootstrap audit，验证 Job Contract、存在性 Gate、因果链、evidence level 和 Verdict 是否互相支持；可以借用其检查维度，但不得把 Skill 自己的输出当成自身有效性的独立证据。
- 走查正常、边界和失败请求，特别检查它是否把 evidence gap 自动升级成 comparative 请求。
- 结果标记为 `reviewer_provenance: self`。未发现 blocker 时可按已批准方案继续用它约束后续 Deep Review，但不声称已经证明其相对 baseline 有效；发现 blocker 时先修复并重审。独立性或 comparative 仍需另行授权。

### P0.2 `my-writing-great-skills`

- 验证它只负责指令设计，不重叠 `my-review-skill` 的存在性和职责归宿判断。
- 检查“主导词”“无效操作”“拆分”等规则是否确实改变决定，是否存在自身规则沉积。
- Verdict 若为 KEEP/TARGETED_FIX，才实施文字或层级优化。

### P0.3 discovery 闭包

依次 Deep Review `my-grilling`、`my-grill-with-docs`、`my-requirement-analysis`，但每次纳入其真实 caller/callee 和 shared resources：

- 目标与用户给出的手段、示例或类比必须分离；
- 事实自行查证，只有承重未知才询问；
- `routine` 决定不交给用户，`consequential/user-exclusive` 遵循 authority gate；
- 简单请求可快速通过，复杂请求才触发增强需求核对；
- 访谈具有可观察停止条件，不以“所有方面”制造无限问题。

### P0.4 `my-to-spec`

- 保持现有 Spec 模板轻量；只对“已确认的承重决策”增加紧凑 reasoning record。
- 每项记录引用目标/验收 ID、事实或约束来源、采用机制、被排除的最小替代方案、可证伪预测和验证方式。
- 普通实现细节、没有替代成本的简单决定不产生空记录。

### P0.5 `my-review-design`

- 在现有待决策、逻辑完整性、一致性、闭环和最终态检查上，增加高风险分支。
- 对难逆转决定检查不可约约束、最小替代方案、拒绝理由、不可逆成本和可证伪预测。
- 只报告能改变设计采用或实施准备度的问题；不重新访谈、不替用户决定、不自动修改设计。

### P0.6 `my-to-tickets`

- 将其纳入第一梯队，检查 Spec acceptance 到 Ticket acceptance 的完整 coverage。
- 验证并保留现有 tracer-bullet 纵向切片、独立演示/验证、端到端行为和真实阻塞边；这些不是待新增能力。
- 新增点只限于 Spec acceptance 到 Ticket acceptance 的完整 coverage，以及每项验收恰有明确 owner、无遗漏和无无授权重复。
- 保留大范围机械重构的 expand–contract 例外：按 package/目录迁移在旧形式仍兼容且每批保持 green 时合法；无法单批 green 时沿用 integrate-and-verify Ticket。不得用“每张都直接产生用户可见结果”否定这一现有边界。
- 对普通功能仍优先按可验证纵向能力切片；依赖边只表达真实前置条件，不能把偏好顺序伪装成阻塞。
- Ticket 不复制整份 reasoning record，只引用 Spec 决策和本 Ticket 的验收 lineage。

## 定点实施方案

Deep Review finding 经 Finding Gate 接纳后，按以下所有权实施；没有 finding 的目标不为一致性强行改写。

### P1：按确认后的消费者建立 shared reference 与资源图

1. 汇总 P0 Deep Review 后仍需要因果链、最小反事实或可证伪预测的真实消费者；至少三个时新增 `resources/first-principles-reasoning.md`，不足三个时由拥有该决定的 Skill 内联，不创建 shared resource。
2. shared reference 只引用 `instruction-authority` 和 `artifact-finalization`，不重新定义其决策分类、约束优先级或来源 taxonomy。
3. 新增 shared resource 时，在 `resources/manifest.json` 登记唯一 source、release path 和确认后的直接 consumers。
4. 更新 source walker/resource closure 所需 fixtures，确保 Codex、Cursor、Claude 投影的引用可达。

### P2：新增 `my-first-principles-review`

1. 使用项目 Skill 结构创建 `SKILL.md` 与 `agents/openai.yaml`，显式调用，不添加无用目录。
2. 在 portfolio manifest 登记 category=`quality`、discoverability=`specialist`、roles=`entry,review`、初始 criticality=`standard`；没有行为证据前不标为 critical。
3. 本轮不修改 `my-ask-matt`。用户明确调用新 Skill 时才运行；是否加入路由留给第二梯队 review 后决定。
4. 加入静态/确定性验证计划；fresh-agent 与 real-project 保持 planned 或带风险的 exemption，不能自证有效。

### P3：按 Deep Review 结果修改第一梯队

1. discovery：消除“所有决策都交给用户”的冲突，并加入目标—手段分离的条件分支。
2. Spec：加入承重 reasoning record，不改变普通 Spec 的简洁路径。
3. design review：加入不可逆决定的替代方案、成本和反证检查。
4. tickets：保留现有纵向切片、端到端行为、真实 dependency 和 expand–contract 例外，只补 acceptance coverage/ownership 中经 Deep Review 确认的缺口。
5. Skill review/authoring：复用 shared reference 中的目标、因果和反事实原语，但保留它们自己的存在性、行为证据和指令设计职责。
6. implementation/TDD/code review：本轮不增加通用 prose；只补能够验证已有风险—oracle—evidence 合同的测试或真实 evidence 记录。

## 验证方案

### 静态与单元

- 资源 manifest、直接/有效 consumers 和三宿主投影闭合。
- 新 Skill 的 metadata、显式调用策略、portfolio 角色和 composed reference 可达。
- `workflow.py validate`、完整 unittest、`validate-evals`、release-aware `check` 全部通过。

### Deterministic scenarios

至少覆盖：

1. 用户把实现手段当目标时，识别目标替换；
2. 把历史惯例当硬约束时，识别伪约束；
3. 复杂机制没有比最小替代方案提供额外用户结果时，识别无收益复杂度；
4. 因果链中间结果无法推出用户结果时，识别推导断点；
5. 验收只证明“步骤已执行”而不能捕获失败时，识别证据错位；
6. 一个简单且成立的提案返回 `HOLDS`，不制造问题；
7. 横向 Ticket 拆分没有独立验收时，要求合并或改为步骤；
8. 合法的真实依赖和纵向 Ticket 不被误判为过度设计。

测试验证决策和可观察输出，不以固定标题、措辞或关键词匹配冒充行为证据。

### Fresh-agent / real-project

先登记 planned cases，不在本轮自动运行。后续获得授权后，使用相同模型、reasoning、输入、快照和权限比较：

- baseline：无新 Skill/新 reference；
- current：当前流程；
- candidate：本方案实现。

指标包括有效 finding、误报、遗漏、用户澄清次数、Token、耗时、Spec/Ticket 返工和是否改变最终决定。至少选一个真实 Spec→Tickets→implementation 项目 trace 验证 Ticket slicing 与 reasoning lineage；没有实际记录时继续报告 `not-recorded`。

## 覆盖矩阵

| 评审事项 | 方案覆盖 |
|---|---|
| 第一梯队缺少逐项 Deep Review | P0.1–P0.6 |
| `my-to-tickets` 应进入第一梯队 | P0.6、Ticket deterministic scenarios；保留现有 expand–contract 例外 |
| discovery 决策权冲突 | P0.3、P3.1 |
| Spec 缺少证据到验收闭环 | shared 原语、P0.4、P3.2 |
| 设计审查反证不足 | shared 原语、P0.5、P3.3 |
| 需要通用第一性原理 review | `my-first-principles-review`、P2 |
| shared reference 是否必要 | shared reference 设计、P1 的至少三个真实消费者 Gate |
| 避免万能 review 和职责重叠 | 新 Skill Job Contract、职责边界、路由规则 |
| 测试/代码 review 不应继续堆 prose | P3.6、行为证据方案 |
| 第二梯队暂缓 | 不改范围、specialist 策略、后续工作；本轮不修改 `my-ask-matt` |
| 不把验证计划冒充执行证据 | Fresh-agent/real-project 段落 |

## 实施顺序与停止条件

严格按 `P0.1 bootstrap audit → P0.2 → P0.3 → P0.4 → P0.5 → P0.6 → P1 consumer Gate → P2 → P3 → 验证 → release` 推进。Deep Review 是决策前置，不假定所有候选都需要修改；某项 Verdict 为 KEEP 且无 finding 时直接保留。

出现以下情况时停止在当前批次并向用户确认：

- 新 Skill 与现有专项 review 的 Job Contract 无法形成互斥边界；
- shared reference 必须复制已有 authority/finalization 规则才能成立，或确认后的真实消费者不足三个；
- Deep Review 建议合并、退役或改变已批准 Skill 的公开调用语义；
- 方案需要升级模型/reasoning、运行高成本 comparative、写入真实外部系统或扩大到第二梯队；
- observed evidence 与当前设计假设冲突，并会改变 Verdict。

## 方案自审

本方案逐项覆盖评审 F1–F8 和用户四项意见；新增 Skill 具有受限的拟定 Job Contract，当前识别出六个拟定 shared consumers，最终集合由 Deep Review 和至少三个真实消费者 Gate 决定。authority、artifact finalization 与新原语的单一事实来源已分开，专项 review 的调用边界也已明确为本轮不组合。方案没有把第一性原理嵌入全部 37 个 Skills，也没有把 planned evidence 写成通过。

当前自审属于同会话 `self`，不是独立 reviewer evidence。实施前先对 `my-review-skill` 做固定快照的 bootstrap audit；这能发现结构问题，但不证明该 Skill 相对 baseline 有效，也不被写成独立审查。

修订后设计 Gate 在固定 snapshot `4a6f52c67bfe87319badeeb39484a6aed2fabe9249de6b42a2dc156a4275e782` 上检查待决策项、逻辑完整性、内部一致性、设计闭环和最终态表达，未发现阻止实施的剩余 blocker；snapshot finalize 返回 `match`。该结论同样是 `self`，因此方案由 `draft` 晋升为 `current`，不称为独立设计审查。

## 后续工作

第二梯队保持未处理：`my-ask-matt`、`my-diagnosing-bugs`、`my-handoff`、`my-test-report`、`my-setup`、`my-install`、`my-triage`、`my-wayfinder`、`my-resolving-merge-conflicts`。新 Skill 本轮保持显式调用的 specialist，不修改 `my-ask-matt`。只有第一梯队完成并取得真实行为反馈后，才重新排序；不因本方案存在而自动进入下一轮。
