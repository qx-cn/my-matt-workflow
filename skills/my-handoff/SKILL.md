---
name: my-handoff
description: 为新的 Agent 会话生成精简且可恢复的上下文交接
disable-model-invocation: true
---

# 交接

只用于换宿主、换目录或换人，或访谈结论尚未形成 Spec 但需要保存。实施恢复依靠提交与 runtime status。按[找用户的条件](references/shared/user-intervention.md)处理阶段交接。

交接保留下一会话目标、已确认决定与范围外、当前状态与验证依据、剩余风险、相关材料位置和第一步。既有产物只引用；移除秘密和不必要个人信息。提交、远端、release与各宿主安装状态按实际证据分别说明，未知保持未知。

直接核对引用与事实，按[最终态写作](references/shared/final-state-writing.md)表达有效决定；不使用 ready/draft 或独立读者重建门槛。依[产物存储](references/shared/adapters/artifact-storage.md)新增 handoffs-<topic>-<time-or-sequence>.md，不覆盖历史；无项目则保存临时目录并报告路径。上下文选择遵循[上下文卫生](references/policies/context-hygiene.md)。
