---
name: my-grill-with-docs
description: 通过高强度访谈打磨计划或设计，并在过程中建立 ADR 与术语表。
disable-model-invocation: true
---

按组合策略运行 `my-grilling`，并在需要领域词汇时使用 `my-domain-modeling`。

读取 `.agent/matt-workflow.md`（含生效的 `humanizer_policy`）。

## 过程

1. `composition_policy: automatic` 时读取并遵守 [my-grilling](references/composed/my-grilling/SKILL.md)；需要领域词汇时读取并遵守 [my-domain-modeling](references/composed/my-domain-modeling/SKILL.md)。`manual` 时输出当前运行时的下一条显式调用并停止：Cursor / Claude 使用 `/my-grilling` 或 `/my-domain-modeling`，Codex 使用 `$my-grilling` 或 `$my-domain-modeling`。

2. 访谈阶段只在对话中提问，不写正式结论；不在此阶段调用 `/humanizer`。

3. 用户确认共同理解后，准备落盘：
   - grill → `.agent/work/<topic>/grills/grills-<topic>-<time-or-sequence>.md`
   - 新术语与 ADR 候选 → `.agent/work/<topic>/domain/`
   - 写回团队正式文档前另展示补丁并取得确认。

4. **最终确认后、写入前**：按 [humanizer](references/shared/humanizer.md) 服从 `humanizer_policy`，再写入上述工作产物。中途草稿与追问不落盘、不 humanizer。

> 项目策略优先：读取 `.agent/matt-workflow.md` 的已解析生效策略；缺键或空值按 `strict-control`。本 Skill 中要求询问、确认、停止或限制后续工作的表述，除绝对安全底线外，均服从该生效策略。绝对安全底线始终不变：不得 Force Push、改写 Git 历史、执行破坏性 Git 操作，或向外部服务发送敏感信息。
