---
name: my-grill-with-docs
description: 通过高强度访谈打磨计划或设计，并在过程中建立 ADR 与术语表。
disable-model-invocation: true
---

运行一次 `/my-grilling` 会话，并使用 `/my-domain-modeling` Skill。

本地适配：组合调用遵循 [组合调用](references/shared/adapters/composition.md)，工作产物遵循 [工作产物访问](references/shared/adapters/artifact-access.md)，最终确认后、写入前按 [humanizer](references/shared/humanizer.md) 的 `humanizer_policy` 执行。
