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

文档顶部必须写明 `Handoff-Status: draft | ready` 与 `Reader-Reconstruction: pass | inconclusive`。涉及软件交付状态时，只列与继续工作有关的状态面，且分别记录工作区、local commit、remote、release 和各安装宿主；不得把其中一个状态推断成另一个，缺少证据时标为 `unknown`。不适用的状态面不为凑格式而添加。

已有产物只引用，不复制正文。移除密钥、密码、个人身份和不必要的企业内部信息。阶段边界与最小上下文遵循[上下文卫生](references/policies/context-hygiene.md)。

## 最终校验

保存或交给下一会话前，按[产物最终校验](references/shared/artifact-finalization.md)执行四项 gate。尤其要让未参与撰写的可用上下文仅凭交接重建下一会话目标、范围外、已确认决定、当前状态、剩余风险、证据和第一步，并逐一验证引用路径、URL、Commit 与当前状态。

只有四项 gate 全部通过且读者重建使用独立的 fresh-context 时，才写 `Handoff-Status: ready`、`Reader-Reconstruction: pass` 并交给下一会话。没有独立上下文能力或任一 gate 未通过时，只能保存 `Handoff-Status: draft`、`Reader-Reconstruction: inconclusive` 的恢复草稿；草稿必须列出阻塞 gate、影响和解除动作，明确不可直接继续，不得输出 `resume-first-step`。承重事实无法确认时标为未知并说明解除方式。

`my-handoff` 是项目交接目录的唯一管理者。需要保存时读取[工作产物存储](references/shared/adapters/artifact-storage.md)，使用 `type=handoffs` 和文件名 `handoffs-<topic>-<time-or-sequence>.md`；`<topic>` 使用简短的 kebab-case 名称，例如 `requirements-reset`。同一需求的后续交接只新增新文件，不覆盖历史记录，不同需求不得混放。没有项目时保存到操作系统临时目录并报告绝对路径，而非写入当前工作区。不要自动删除旧交接；只创建新文档并在新文档中引用前序交接。
