---
name: my-handoff
description: 为新的 Agent 会话生成精简且可恢复的上下文交接
disable-model-invocation: true
---

# My Handoff

把当前会话压缩为一份 Markdown 交接，使新的 Agent 会话可以继续工作。若用户传入参数，将其视为下一会话的工作重点，并据此安排交接内容和建议的第一步。

交接包含：

- 下一会话目标；
- 已确认决策和范围外内容；
- 当前状态、验证证据和剩余风险；
- 相关 Spec、Ticket、ADR、原型、Commit 或 diff 的路径/URL；
- 建议手动调用的 `my-*` Skills；
- 下一步具体动作。

已有产物只引用，不复制正文。移除密钥、密码、个人身份和不必要的企业内部信息。阶段边界与最小上下文遵循[上下文卫生](references/policies/context-hygiene.md)。

## 最终校验

保存或交给下一会话前，按[产物最终校验](references/shared/artifact-finalization.md)执行四项 gate。尤其要让未参与撰写的可用上下文仅凭交接重建下一会话目标、范围外、已确认决定、剩余风险、证据和第一步，并逐一验证引用路径、URL、Commit 与当前状态。没有独立上下文能力时只做结构化自检，明确记录 `reader-reconstruction: inconclusive`，不得把它冒充 fresh-context 通过或把草稿写成已可直接继续。承重事实无法确认时标为未知并说明解除方式；会改变下一步的未知未解除时同样不得标记为可直接继续。

`my-handoff` 是项目交接目录的唯一管理者。需要保存时读取[工作产物存储](references/shared/adapters/artifact-storage.md)，使用 `type=handoffs` 和文件名 `handoffs-<topic>-<time-or-sequence>.md`；`<topic>` 使用简短的 kebab-case 名称，例如 `requirements-reset`。同一需求的后续交接只新增新文件，不覆盖历史记录，不同需求不得混放。没有项目时保存到操作系统临时目录并报告绝对路径，而非写入当前工作区。不要自动删除旧交接；只创建新文档并在新文档中引用前序交接。
