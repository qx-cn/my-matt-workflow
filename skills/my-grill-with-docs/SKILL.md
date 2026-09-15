---
name: my-grill-with-docs
description: 通过高强度访谈澄清设计决定，并在过程中建立 ADR 与术语表。
disable-model-invocation: true
---

本流程依赖 `my-grilling` 与 `my-domain-modeling`。读取 `.agent/matt-workflow.md` 的 `composition_policy`、`assurance_level`，遵循[开发保证等级](references/shared/adapters/assurance-levels.md)与[组合调用](references/shared/adapters/composition.md)：

- `my-grilling` 与 `my-domain-modeling` 都是内部方法：`automatic` 与 `manual` 都只读取当前阶段需要的 [my-grilling 正文](references/composed/my-grilling/COMPOSED.md) 和 [my-domain-modeling 正文](references/composed/my-domain-modeling/COMPOSED.md)，执行后返回宿主；不要输出另一条 Skill 调用。
- 复杂、隐含或类比驱动的请求在摘要形成后读取[需求核对正文](references/composed/my-requirement-analysis/COMPOSED.md)，作为风险触发的方法返回宿主；普通请求不重复核对。

本地适配：工作产物遵循 [工作产物访问](references/shared/adapters/artifact-access.md)。已解决的单个术语和满足条件的 ADR 候选可在访谈中写入个人工作区，避免结论丢失。

用户以具体方案、类比或既有做法表达需求时，应用[第一性原理推理](references/shared/first-principles-reasoning.md)中的因果链，先把使用者可观察目标与所给手段分开。只有两者差异会改变目标、范围、约束或验收时才进入访谈；不要把“重新发明方案”变成每次请求的固定步骤。

访谈结论经用户确认后，生成一份可追溯需求摘要：目标、范围、明确约束、可观察验收，以及每项来自用户原文、仓库事实还是尚未确认的推断。`quick` 且满足低风险准入时，输出 `{{skill-call:my-implement}}`；其他等级输出 `{{skill-call:my-to-spec}}`。正式 Spec 与可执行计划由 `my-to-spec` 生成；本 Skill 不创建它们。
