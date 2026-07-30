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

已有产物只引用，不复制正文。移除密钥、密码、个人身份和不必要的企业内部信息。

`my-handoff` 是项目交接目录的唯一管理者。项目内按需求 topic 分目录保存：`.agent/work/<topic>/handoffs/handoffs-<topic>-<time-or-sequence>.md`；`<topic>` 使用简短的 kebab-case 名称，例如 `requirements-reset`。同一需求的后续交接只新增新文件，不覆盖历史记录，不同需求不得混放。没有项目时保存到操作系统临时目录，而非当前工作区。不要自动删除旧交接；只创建新文档并在新文档中引用前序交接。

> 项目策略优先：读取 `.agent/matt-workflow.md` 的已解析生效策略；缺键或空值按 `strict-control`。本 Skill 中要求询问、确认、停止或限制后续工作的表述，除绝对安全底线外，均服从该生效策略。绝对安全底线始终不变：不得 Force Push、改写 Git 历史、执行破坏性 Git 操作，或向外部服务发送敏感信息。
