---
name: my-grill-with-docs
description: 通过高强度访谈打磨计划或设计，并在过程中建立 ADR 与术语表。
disable-model-invocation: true
---

运行一次 `/my-grilling` 会话，并使用 `/my-domain-modeling` Skill。

访谈结束后、输出可执行计划前，按 [项目规则解析](references/shared/adapters/project-rules.md) 建立规则地图。计划必须包含 `## 适用的项目规范` 与 `## 对本计划的约束`；未解决的规则冲突或路径匹配不得伪装成已可执行计划。

本地适配：组合调用遵循 [组合调用](references/shared/adapters/composition.md)，工作产物遵循 [工作产物访问](references/shared/adapters/artifact-access.md)，项目规范遵循 [项目规则解析](references/shared/adapters/project-rules.md)，最终确认后、写入前按 [humanizer](references/shared/humanizer.md) 的 `humanizer_policy` 执行。
