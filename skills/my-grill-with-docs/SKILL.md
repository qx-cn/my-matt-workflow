---
name: my-grill-with-docs
description: 通过高强度访谈澄清设计决定，并在过程中建立 ADR 与术语表。
disable-model-invocation: true
---

本流程依赖 `my-grilling` 与 `my-domain-modeling`。读取 `.agent/matt-workflow.md` 的 `composition_policy` 并遵循[组合调用](references/shared/adapters/composition.md)：

- `my-grilling` 与 `my-domain-modeling` 都是内部方法：`automatic` 与 `manual` 都只读取当前阶段需要的 [my-grilling 正文](references/composed/my-grilling/COMPOSED.md) 和 [my-domain-modeling 正文](references/composed/my-domain-modeling/COMPOSED.md)，执行后返回宿主；不要输出另一条 Skill 调用。

本地适配：工作产物遵循 [工作产物访问](references/shared/adapters/artifact-access.md)。已解决的单个术语和满足条件的 ADR 候选可在访谈中写入个人工作区，避免结论丢失。

访谈结论经用户确认后，概括已确认决定与未决项，输出 `{{skill-call:my-to-spec}}` 作为下一步并结束。正式 Spec 与可执行计划由 `my-to-spec` 生成；本 Skill 不创建它们。
