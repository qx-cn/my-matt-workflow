---
name: my-grill-me
description: 通过高强度访谈打磨计划或设计。
disable-model-invocation: true
---

本流程依赖 `my-grilling`。读取 `.agent/matt-workflow.md` 的 `composition_policy` 并遵循[组合调用](references/shared/adapters/composition.md)：

- `automatic`：只读取 [my-grilling 正文](references/composed/my-grilling/COMPOSED.md)。
- `manual`：Cursor / Claude 输出 `/my-grilling`，Codex 输出 `$my-grilling`，随后停止。
