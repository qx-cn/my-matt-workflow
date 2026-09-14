---
name: my-implement
description: 根据已批准的 Spec 或 implementation Ticket 编写并验证代码；不用于重新定义需求或只做代码审查。
disable-model-invocation: true
---

# 实施

先读取项目 `assurance_level` 并遵循[开发保证等级](references/shared/adapters/assurance-levels.md)。`quick` 以当前对话中已确认的可追溯需求摘要为工作单元，不伪造 runtime journal；完成针对性测试和同会话代码自审后按实际证据交付。`standard` 在存在 Ticket 时使用 runtime session；没有 Ticket 的单一切片以版本化 Spec 为边界并保存实际测试和 review 证据。`audited` 必须使用 runtime 提供的工作单元和完整 [implementation session](references/shared/adapters/implementation-session.md)。工作单元中的 Ticket、Spec、适用规则和允许范围始终是实施边界；使用 session 时调度、状态、恢复、写操作 gate 与内容快照由 runtime 管理，不在本 Skill 中重复编排。

## 实施方法

先把验收标准落实到可观察行为，并从计划、Ticket 与现有代码中选择稳定 seam。行为新增或修复默认按照 [TDD 方法](references/composed/my-tdd/COMPOSED.md)完成最小 red-green 切片；符合 TDD 例外时记录依据并采用等价验证策略。只实现当前行为所需内容，不预建尚未要求的抽象或能力。

每个切片运行能最快证明该行为的最小针对性测试。工作单元结束时验证受影响模块或链路；只有整份计划结束、发布或合并前、仓库规则要求，或者风险证据表明影响面扩大时，才运行完整测试套件。

## 回合完成

使用 runtime session 时遵循[implementation session](references/shared/adapters/implementation-session.md)的回合关闭契约。已跑局部测试、正在施工或等待下一步都只是进度；可以用 commentary 汇报，但不得因此发送 final 或结束实施。恢复、普通校验错误或 repair-plan 通过后，向 runtime 查询当前 gate，并完成它指向的闭环；只有 runtime 已登记可关闭的结果并完成适用的范围 transition，才可对用户结束回合。无 runtime session 的 quick/standard 单切片只有在验收、必要测试、自审和证据摘要全部闭合后才能结束。

实现与计划出现偏差时，按语义影响处理：

- 可逆的局部实现细节仍满足 Spec：在当前工作单元内调整并补充证据。
- Ticket 拆分或依赖不成立，但 Spec 仍成立：返回 `blocked-by-design`，说明需要调整的 Ticket 图及证据。
- 目标、范围、公开接口、数据语义、验收或风险承担发生变化：返回 `blocked-by-design` 和 `pause-for-revision`，指出失效假设与最小 Spec 修订范围。
- 缺少环境、权限或可判定证据：返回 `blocked-by-evidence`，不要猜测通过。

已完成 Ticket 是历史事实；后续需要改变其结果时，提出引用原 Ticket 的补偿或迁移工作，不改写历史验收。

## 完成标准

提交结果前，自动在 runtime 固定的审查单元上应用[代码审查方法](references/composed/my-code-review/COMPOSED.md)，不要求用户再次调用 Skill，也不要再生成另一份未绑定快照。默认以 `self` 提交增强自审覆盖；只有用户显式要求时才创建独立 reviewer session。把 `pass | findings | inconclusive | blocked-by-design` 的同一结果交回 runtime 登记，不得生成未绑定的“自审通过”结论。

代码审查出现 finding 时，先进入 runtime 固定的 repair-plan 门：方案逐项覆盖当前 finding、验收、根因、最小改动、验证和不改范围，再由[设计成立性](references/composed/my-review-design/COMPOSED.md)增强自审。方案通过前不改代码；通过后按 runtime gate 修复、测试并重新审查。默认仅允许这一轮修复；最终复审的新有效 finding 由 runtime 作为正式 `blocked-by-review` 登记。`full-auto` 最多允许 profile 声明的五轮。连续出现相同根因时停止逐点补丁并返回 `blocked-by-design`。只有验收标准全部满足、必要测试通过，并且 runtime 登记的 `my-code-review` pass receipt 没有未解决 blocker，才返回 `completed`；同时提供改动、测试和审查证据。否则返回上述阻塞状态及恢复所需的最小信息。
