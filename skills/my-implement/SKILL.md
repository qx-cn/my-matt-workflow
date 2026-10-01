---
name: my-implement
description: 在 my-to-tickets、my-prototype 流程中作为指定阶段的工作单元被调用。
---

# 实施

先读取[保证等级](references/shared/adapters/assurance-levels.md)、已确认需求和 runtime 执行简报；工作边界是当前 Topic/Ticket 与适用规则。[找用户的条件](references/shared/user-intervention.md)决定哪些事项交用户。

动手前在执行简报补写实施计划：文件和接口、每条验收对应的可观察测试断言、Spec 隐含但尚未覆盖的输入。quick 在对话中形成同等计划，不伪造 Ticket 或实施记录。

将验收落到稳定 seam，调用 {{skill-call:my-tdd}} 完成最小行为切片；适用例外时记录依据及等价验证。每片跑最快有效测试，工作单元结束验证受影响链路；整份计划结束或集成前跑声明全量测试。只做当前必要行为。

按[实施适配](references/shared/adapters/implementation-session.md)获取和恢复状态，不在 Skill 复制 runtime 已强制的计数、事务或完成校验。调用 {{skill-call:my-code-review}}，遵循[审查循环](references/shared/review-loop.md)登记判断与处理阻断；建议留到摘要，不主动重构。

完成当前 Ticket 后在已确认范围内按依赖继续下一张。多张全部完成后做 Topic 测试和整分支审查。按[交付规则](references/shared/workflow-delivery.md)沉淀 CONTEXT/ADR、填写全部固定摘要节，再完成 Topic；未验收闭环只能报告进度。

已完成 Ticket 是历史事实，补偿或迁移另建工作；需求/范围/验收失效交用户修订。环境或证据缺失如实说明，不猜测通过。
