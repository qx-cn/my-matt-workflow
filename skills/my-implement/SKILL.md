---
name: my-implement
description: 在 my-to-tickets、my-prototype 流程中作为指定阶段的工作单元被调用。
---

# 实施

先读取[保证等级](references/shared/adapters/assurance-levels.md)、已确认需求和 runtime 执行简报；工作边界是当前 Topic/Ticket 与适用规则。[找用户的条件](references/shared/user-intervention.md)决定哪些事项交用户。

动手前在执行简报补写实施计划：文件和接口、每条验收对应的可观察测试断言、Spec 隐含但尚未覆盖的输入。quick 在对话中形成同等计划，不伪造 Ticket 或实施记录。

将验收落到稳定 seam，调用 {{skill-call:my-tdd}} 完成最小行为切片；适用例外时记录依据及等价验证。每片跑最快有效测试，工作单元结束验证受影响链路；每张 Ticket 跑声明定向测试，批次结束跑全量测试并与基线比较。只做当前必要行为。

按[实施适配](references/shared/adapters/implementation-session.md)获取和恢复状态，不在 Skill 复制 runtime 已强制的计数、事务或完成校验。提交前记录增强自审：验收对照、现状核实、影响面、对抗检查、简洁与约定、已知缺口；无内容写无及理由。高风险信号：持久状态/存量数据、并发锁、对外契约、发布回滚、改变既有行为、不可逆迁移、权限安全；多数 Ticket 不需要独立审查，只有明显高于同批次其他 Ticket 时按需触发并记录理由。批次结束调用 {{skill-call:my-code-review}} 做新上下文独立审查；高风险审查不能跳过或缩小批次范围。遵循[审查循环](references/shared/review-loop.md)登记判断与处理阻断；建议留到摘要，不主动重构。

完成当前 Ticket 后在已确认范围内按依赖继续下一张。同会话按依赖完成整个批次并逐张提交；批次末全量测试、一次独立审查、修复复审后收口。多批次最后一次审查含整个 Topic 改动清单；整分支审查可选，用户要求或跨批次共享契约风险较高时执行并记发起者与理由，修复落最后批次。按[交付规则](references/shared/workflow-delivery.md)沉淀 CONTEXT/ADR、填写全部固定摘要节，再完成 Topic；未验收闭环只能报告进度。

批次收口后 Ticket 是历史事实，补偿或迁移另建工作；需求/范围/验收失效交用户修订。环境或证据缺失如实说明，不猜测通过。
