---
name: my-implement
description: 根据 Spec 或一组 Ticket 实施工作。
disable-model-invocation: true
---

实施用户在 Spec 或 Ticket 中描述的工作。

尽可能在预先约定的 seam 上使用 `/my-tdd`。

定期运行类型检查和单个测试文件；结束时运行一次完整测试套件。

完成后，使用 `/my-code-review` 审查工作。

将工作提交到当前分支。

本地适配：实施前与组合阶段仅通过 [Ticket 准入与选择](references/shared/adapters/ticket-selection.md)、[工作范围](references/shared/adapters/work-scope.md)、[组合调用](references/shared/adapters/composition.md) 和 [工作产物访问](references/shared/adapters/artifact-access.md) 确定本地控制。
