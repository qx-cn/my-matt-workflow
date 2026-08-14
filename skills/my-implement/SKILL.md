---
name: my-implement
description: 根据 Spec 或一组 Ticket 实施工作。
disable-model-invocation: true
---

实施用户在 Spec 或 Ticket 中描述的工作。

开始每个 Ticket 前，按 [项目规则解析](references/shared/adapters/project-rules.md) 用 Ticket 的 `execution_agent` 和实际将修改的路径重新解析规则，并运行 `python3 tools/workflow.py validate-ticket <ticket-path>`。新规则若改变架构、范围、接口或验收，回到计划确认；不得静默偏离已批准计划。

在预先约定的 seam 上进入 `my-tdd` 阶段。

定期运行类型检查和单个测试文件；结束时运行一次完整测试套件。

完成后进入 `my-code-review` 阶段审查工作。

将工作提交到当前分支。

组合阶段读取 `.agent/matt-workflow.md` 的 `composition_policy` 并遵循[组合调用](references/shared/adapters/composition.md)：

- `automatic`：只读取当前阶段的 [my-tdd 正文](references/composed/my-tdd/COMPOSED.md) 或 [my-code-review 正文](references/composed/my-code-review/COMPOSED.md)。
- `manual`：输出对应的 `/my-<skill>`（Cursor / Claude）或 `$my-<skill>`（Codex）后停止。

实施前的本地控制仍由 [Ticket 准入与选择](references/shared/adapters/ticket-selection.md)、[工作范围](references/shared/adapters/work-scope.md)、[工作产物访问](references/shared/adapters/artifact-access.md) 和 [项目规则解析](references/shared/adapters/project-rules.md) 确定。
