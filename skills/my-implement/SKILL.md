---
name: my-implement
description: 根据 Spec 或一组 Ticket 实施工作。
disable-model-invocation: true
---

实施用户在 Spec 或 Ticket 中描述的工作。`my-implement` 是唯一可跨 Ticket 继续的宿主：每张 Ticket 的验收、测试、审查和提交完成后，按 runtime 的 `next-ticket` 结果继续、完成或暂停。

开始每个 Ticket 时记录当前 `HEAD`。若 `.agent/work/<topic>/runs/run-<ticket-id>-spec-r<revision>.json` 已存在，先从它恢复 phase、固定点、Spec 血缘、规则、策略、test/review receipt 和 blocker，不重复初始化。否则通过安装状态记录的 `runtime_entry` 运行：

```text
run-start --repo <repo> --ticket <ticket-path> --base <HEAD> --path <planned-path> [...]
```

该命令一次解析 Ticket/Spec 血缘、实际路径规则、测试命令、composition/work-scope/decision/humanizer 策略与四类写操作 gate，并把 context receipt 写入 run journal。以该 receipt 为当前运行事实，不再从多个 adapter 重复拼装同一上下文。随后用 `ticket-transition <ticket-path> --to implementing` 校验状态变化，再认领并进入实施。新规则若改变架构、范围、接口或验收，回到计划确认；不得静默偏离已批准计划。

实施中发现计划行不通时，按影响回退，不默认重走完整访谈：

- 可逆实现细节仍能满足 Spec：在当前 Ticket 内调整并补证据。
- Ticket 拆分或依赖边错误，但 Spec 仍成立：暂停当前 Ticket，只修订受影响的 Ticket 图并重新准入。
- 目标、范围、公开接口、数据语义、验收或风险承担中的承重假设失效：用 `run-record <journal> --phase blocked-by-design --blocker pause-for-revision` 落盘，再校验 Ticket 的 `implementing → blocked-by-design → revising`；记录失败证据和影响范围，只对受影响决定进行定向访谈。新 Spec revision 确认后，重建受影响的未完成 Ticket，并在准入通过后校验 `revising → revalidated → implementing`，为新 revision 建立新的 run journal。
- 根目标本身失效：停止，由用户决定是否重新进行完整访谈。

已经 `complete` 的 Ticket 保持历史不变；若新 Spec 需要撤销、迁移或修正其结果，创建引用原 Ticket 的补偿 Ticket，不重开或改写完成记录。

在计划、Ticket 或代码可推断的 seam 上进入 `my-tdd` 阶段；只有[工作范围](references/shared/adapters/work-scope.md)定义的关键 seam 才暂停等待确认。

进入测试、实施、审查、提交和完成阶段时，用 `run-record <journal> --phase <phase>` 更新磁盘状态；实际测试摘要用 `--test-receipt`，通过审查的 `content_id` 用 `--review-receipt`。改动中运行能最快证明当前行为的最小针对性测试；Ticket 完成时运行受影响模块或链路的测试。只有整份计划完成、发布或合并前、项目规则明确要求，或者失败与风险证据表明影响面扩大时，才运行完整测试套件。相关验证通过后，没有新改动、新失败或未解决风险就不重复或扩大测试。

对预计无法在单次工具调用内完成的测试、构建、迁移等命令，应以可续接的执行会话启动，并通过同一会话持续轮询至进程退出；不得将单次返回、等待超时或输出截断视为命令终止。完成后必须检查实际退出码；命令如提供最终结果摘要，也应一并核对。

完成后，通过安装状态记录的 `runtime_entry` 运行 `review-snapshot --repo <repo> --base <实施开始的 HEAD>`，再进入 `my-code-review` 阶段审查该 `content_id` 的完整工作树。审查必须覆盖 committed、staged、unstaged、untracked；不能因为实现尚未提交就得到空 diff。若 review 后修复了任何内容，生成新快照并重新执行完整双轴审查，旧 receipt 作废。

按[写操作 Gate](references/shared/adapters/write-actions.md)已解析进 context receipt 的结果处理提交。提交后再次运行 `review-snapshot --repo <repo> --base <实施开始的 HEAD> --expect-content-id <已通过审查的 content_id> --require-clean`；只有返回 `match`，才证明 Commit 与已审查内容等价且没有遗留改动。完成 Ticket 前勾选验收项，用 `ticket-transition <ticket-path> --to complete` 校验状态变化，再更新状态、释放认领并将 journal 迁移到 `complete`；未完成这些步骤不得选择下游 Ticket。

组合阶段读取 `.agent/matt-workflow.md` 的 `composition_policy` 并遵循[组合调用](references/shared/adapters/composition.md)：

- `my-tdd` 与 `my-code-review` 都是内部方法：`automatic` 与 `manual` 都只读取当前阶段的 [my-tdd 正文](references/composed/my-tdd/COMPOSED.md) 或 [my-code-review 正文](references/composed/my-code-review/COMPOSED.md)，执行后返回宿主；不要输出另一条 Skill 调用。

adapter 继续分别定义 [Ticket 准入与选择](references/shared/adapters/ticket-selection.md)、[工作范围](references/shared/adapters/work-scope.md)、[工作产物访问](references/shared/adapters/artifact-access.md) 与 [项目规则解析](references/shared/adapters/project-rules.md) 的协议语义；当前值和路径只以 run context receipt 为准。
