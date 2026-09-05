# 决策分类

自治只可处理可逆的执行细节：已批准 Ticket 内的实现选择、已验证证据的解释，以及不改变用户目标的顺序调整。`decision_policy: ask` 也不表示对每个普通技术细节暂停；在 `ready-frontier` 流程中，只对无法由 Ticket、计划或代码推断且会改变范围、公开接口、测试投资或风险承担的关键决定暂停。

调用方不得自行写“询问、继续或停止”的选择列表。先分类为 `routine`、`consequential` 或 `user-exclusive`，再执行 runtime `decision-gate` 返回的唯一动作。

以下是用户专属产品决定，绝不因 `decision_policy: autonomous` 自动决定：目标或范围、用户体验取舍、成功指标、优先级、公开承诺、不可逆数据或兼容性选择，以及冲突的产品需求。遇到这类决定时保留问题和证据，等待用户；Wayfinder 的 `wayfinder-decision` Ticket 正是用来承载这些决定，不能转入实施池。

写操作、外部发布、分支和提交的门槛仍由项目配置与[写操作边界](write-boundaries.md)独立决定；决策分类不放宽它们。
