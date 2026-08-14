---
name: my-grill-with-docs
description: 通过高强度访谈打磨计划或设计，并在过程中建立 ADR 与术语表。
disable-model-invocation: true
---

本流程依赖 `my-grilling` 与 `my-domain-modeling`。读取 `.agent/matt-workflow.md` 的 `composition_policy` 并遵循[组合调用](references/shared/adapters/composition.md)：

- `automatic`：只读取当前阶段需要的 [my-grilling 正文](references/composed/my-grilling/COMPOSED.md) 和 [my-domain-modeling 正文](references/composed/my-domain-modeling/COMPOSED.md)。
- `manual`：输出对应的 `/my-<skill>`（Cursor / Claude）或 `$my-<skill>`（Codex），随后停止。

访谈结束后、输出可执行计划前，按 [项目规则解析](references/shared/adapters/project-rules.md) 为目标 `execution_agent` 解析规则。计划项必须逐项给出影响区域、规则、约束和验证；未解决的规则冲突或路径匹配不得伪装成已可执行计划。

本地适配：工作产物遵循 [工作产物访问](references/shared/adapters/artifact-access.md)，项目规范遵循 [项目规则解析](references/shared/adapters/project-rules.md)，最终确认后、写入前按 [humanizer](references/shared/humanizer.md) 的 `humanizer_policy` 执行。
