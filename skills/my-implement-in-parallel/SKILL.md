---
name: my-implement-in-parallel
description: 分析可安全并行的 implementation Tickets，在隔离 worktree 中分别执行 my-implement，并在确认后汇入目标分支。
disable-model-invocation: true
---

# 并行实施

协调一组 implementation Tickets 的并行实施。目标是缩短独立工作的交付时间，不是最大化并发数。

## 选择并行工作

读取 Spec、eligible Tickets、阻塞边和当前代码。判断共享基础是否足够稳定，以及哪些 Ticket 的目标、依赖和预计改动边界相对独立。这里使用工程判断，不要求 Ticket 预先填写专用并行字段。

若工程骨架、核心领域模型、公共接口或数据约定仍由待实施 Ticket 决定，先用普通 `my-implement` 串行完成承重的 Foundation Ticket，再重新评估。新项目中的独立调研、原型或边界已经明确的模块仍可并行；不要把“新项目”本身当作绝对禁令。

开始前简要展示并行组、暂缓项及判断理由。只有一张适合并行，或宿主没有并行 Agent 能力时，明确降级为普通 `my-implement`。

## 执行

在开始写入前按[写操作 Gate](references/shared/adapters/write-actions.md)处理 branch 与 commit。`confirm` 时一次展示本批 Ticket、base SHA、分支、worktree 与预期提交，并等待确认；`deny` 时停止。

确认后固定同一个 `HEAD`。为每张 Ticket 创建 `.worktrees/<parallel-run>/<ticket-id>` 和独立 `agent/<topic>/<ticket-id>` 分支，再用当前宿主已有的并行 Agent 能力启动 workers。Cursor 可使用 Subagents 或 `/multitask`，Codex 使用 collaboration/subagent，Claude 使用 parallel subagents；不要假装调用宿主不存在的能力。

每个 worker 读取组合的 [my-implement 正文](references/composed/my-implement/COMPOSED.md)，只实施分配的单张 Ticket，完成或阻塞后返回协调器，不运行 `next-ticket`。worker 可自主调整不改变验收、共享接口、数据含义或其他 worker 重要假设的实现细节。

若调整可能影响当前 Spec 或其他 Ticket，worker 停止相关改动，向本协调器报告问题、证据、建议和可能影响的 Tickets。workers 不互相决定全局设计。协调器自主判断无关工作是否继续、暂停哪些 workers，以及是否需要修订 Spec/Ticket 或请求用户决定；只重新规划真正受影响的工作，不因记录或摘要不同而机械否决实现。

共享 checkout 不能代替 worktree。`agent_directory_mode: private` 时不共享或软链接整个 `.agent`，由协调器持有 canonical 状态并向 worker 提供当前 Ticket 所需的最小上下文。

## 集成

协调器收集各 worker 的候选 commit 和测试、review 证据，先确认它们仍满足当前 Spec，再从共同 base 建立临时 integration branch。由协调器处理跨 Ticket 分歧；Git 或语义冲突不得交给 workers 私下协商或静默选择一方。

在组合结果上重新运行适当的测试和一次代码 review。只有验证通过后，才展示 Ticket→commit、重要调整、冲突处理和将更新的目标分支，并等待明确确认。确认前不得更新目标分支；push 还需独立通过 external write gate。目标分支包含全部提交后才完成 canonical Tickets；失败现场默认保留。

Ticket 准入、工作范围、项目规则和产物访问继续分别由 [Ticket 选择](references/shared/adapters/ticket-selection.md)、[工作范围](references/shared/adapters/work-scope.md)、[项目规则](references/shared/adapters/project-rules.md)与[工作产物访问](references/shared/adapters/artifact-access.md)定义。
