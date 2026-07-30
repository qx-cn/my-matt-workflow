---
name: my-triage
description: 分类、验证并整理外部提交的 Bug、需求或 PR
disable-model-invocation: true
---

# My Triage

读取项目配置。没有 Tracker 时，只处理用户明确提供的本地需求文档，不模拟 Issue 平台。

对每个请求：

1. 读取正文、评论、标签；PR 还需读取 diff。
2. 检查代码中是否已经实现，并检查已有拒绝决策。
3. 推荐类别和状态，展示理由后等待用户决定。
4. Bug 先尝试复现；需求不足时逐项询问。
5. 生成耐久的 agent-ready brief：背景、已验证事实、期望行为、验收标准、限制和证据。

无 Tracker 时默认保存到 `.agent/work/<feature>/triages/triages-<feature>-<time-or-sequence>.md`。写入团队文档或 Tracker 前，先展示完整预览并获得新的明确确认。

修改标签、发表评论、改变状态或关闭请求前，同样需要新的明确确认。由 AI 发布的外部评论必须明确标注为 AI 辅助生成。

> 项目策略优先：读取 `.agent/matt-workflow.md` 的已解析生效策略；缺键或空值按 `strict-control`。本 Skill 中要求询问、确认、停止或限制后续工作的表述，除绝对安全底线外，均服从该生效策略。绝对安全底线始终不变：不得 Force Push、改写 Git 历史、执行破坏性 Git 操作，或向外部服务发送敏感信息。
