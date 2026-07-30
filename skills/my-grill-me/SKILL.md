---
name: my-grill-me
description: 通过高强度访谈打磨计划或设计。
disable-model-invocation: true
---

`composition_policy: automatic` 时，读取并遵守 [my-grilling](references/composed/my-grilling/SKILL.md)，在当前流程中继续一次访谈。`manual` 时输出下一条显式调用并停止：Cursor / Claude 使用 `/my-grilling`，Codex 使用 `$my-grilling`。

> 项目策略优先：读取 `.agent/matt-workflow.md` 的已解析生效策略；缺键或空值按 `strict-control`。本 Skill 中要求询问、确认、停止或限制后续工作的表述，除绝对安全底线外，均服从该生效策略。绝对安全底线始终不变：不得 Force Push、改写 Git 历史、执行破坏性 Git 操作，或向外部服务发送敏感信息。
