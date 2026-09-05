---
name: my-grill-me
description: 通过高强度访谈打磨计划或设计。
disable-model-invocation: true
---

本流程是 `my-grilling` 的薄入口。读取 `.agent/matt-workflow.md` 的 `composition_policy` 并遵循[组合调用](references/shared/adapters/composition.md)：

- `my-grilling` 是内部方法：`automatic` 与 `manual` 都只读取 [my-grilling 正文](references/composed/my-grilling/COMPOSED.md)，执行后返回宿主；不要输出另一个 Skill 调用文本。

读取正文后在本次调用中直接执行访谈，立即提出第一个问题。不要停在路由提示上。
