---
name: my-implement
description: 根据 Spec 或一组 Ticket 实施工作。
disable-model-invocation: true
---

实施用户在 Spec 或 Ticket 中描述的工作。`my-implement` 是唯一可跨 Ticket 继续的宿主：每张 Ticket 的验收、测试、审查和提交完成后，按[工作范围](references/shared/adapters/work-scope.md)调用 runtime 的 `next-ticket`，并遵守其 `continue`、`complete` 或 `pause` 结果。

开始每个 Ticket 前，按 [项目规则解析](references/shared/adapters/project-rules.md) 用 Ticket 的 `execution_agent` 和实际将修改的路径重新解析规则，并通过安装状态记录的 `runtime_entry` 运行 `validate-ticket <ticket-path>`。新规则若改变架构、范围、接口或验收，回到计划确认；不得静默偏离已批准计划。

在计划、Ticket 或代码可推断的 seam 上进入 `my-tdd` 阶段；只有[工作范围](references/shared/adapters/work-scope.md)定义的关键 seam 才暂停等待确认。

定期运行类型检查和单个测试文件；结束时运行一次完整测试套件。

对预计无法在单次工具调用内完成的测试、构建、迁移等命令，应以可续接的执行会话启动，并通过同一会话持续轮询至进程退出；不得将单次返回、等待超时或输出截断视为命令终止。完成后必须检查实际退出码；命令如提供最终结果摘要，也应一并核对。

完成后进入 `my-code-review` 阶段审查工作。

按[写操作 Gate](references/shared/adapters/write-actions.md)处理提交；完成 Ticket 前勾选验收项、更新状态并释放认领；未完成这些步骤不得选择下游 Ticket。

组合阶段读取 `.agent/matt-workflow.md` 的 `composition_policy` 并遵循[组合调用](references/shared/adapters/composition.md)：

- `automatic`：只读取当前阶段的 [my-tdd 正文](references/composed/my-tdd/COMPOSED.md) 或 [my-code-review 正文](references/composed/my-code-review/COMPOSED.md)。
- `manual`：输出对应的 `/my-<skill>`（Cursor / Claude）或 `$my-<skill>`（Codex）后停止。

实施前的本地控制仍由 [Ticket 准入与选择](references/shared/adapters/ticket-selection.md)、[工作范围](references/shared/adapters/work-scope.md)、[工作产物访问](references/shared/adapters/artifact-access.md) 和 [项目规则解析](references/shared/adapters/project-rules.md) 确定。
