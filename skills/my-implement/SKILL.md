---
name: my-implement
description: 根据已批准的 Spec 或 implementation Ticket 编写并验证代码；不用于重新定义需求或只做代码审查。
disable-model-invocation: true
---

# 实施

把 runtime 提供的当前工作单元实现为可验证、可审查的代码。工作单元中的 Ticket、Spec、适用规则和允许范围是本次实施边界；调度、状态、恢复、写操作 gate 与内容快照由 runtime 管理，不在本 Skill 中重新编排。开始与交付遵循 [implementation session](references/shared/adapters/implementation-session.md)。

## 实施方法

先把验收标准落实到可观察行为，并从计划、Ticket 与现有代码中选择稳定 seam。按照 [TDD 方法](references/composed/my-tdd/COMPOSED.md)逐个完成最小 red-green 切片；只实现当前行为所需内容，不预建尚未要求的抽象或能力。

每个切片运行能最快证明该行为的最小针对性测试。工作单元结束时验证受影响模块或链路；只有整份计划结束、发布或合并前、仓库规则要求，或者风险证据表明影响面扩大时，才运行完整测试套件。

实现与计划出现偏差时，按语义影响处理：

- 可逆的局部实现细节仍满足 Spec：在当前工作单元内调整并补充证据。
- Ticket 拆分或依赖不成立，但 Spec 仍成立：返回 `blocked-by-design`，说明需要调整的 Ticket 图及证据。
- 目标、范围、公开接口、数据语义、验收或风险承担发生变化：返回 `blocked-by-design` 和 `pause-for-revision`，指出失效假设与最小 Spec 修订范围。
- 缺少环境、权限或可判定证据：返回 `blocked-by-evidence`，不要猜测通过。

已完成 Ticket 是历史事实；后续需要改变其结果时，提出引用原 Ticket 的补偿或迁移工作，不改写历史验收。

## 完成标准

提交结果前，只在 runtime `run-review-open` 固定的审查单元上应用[代码审查方法](references/composed/my-code-review/COMPOSED.md)，并由声明的 review adapter 把同一结果交回 runtime 登记；不要再生成另一份未绑定快照的“自审通过”结论。只有验收标准全部满足、必要测试通过，并且 runtime 登记的 `my-code-review` receipt 没有未解决 blocker，才返回 `completed`；同时提供改动、测试和审查证据。否则返回上述阻塞状态及恢复所需的最小信息。
