# 保证等级

配置的 assurance_level 只是建议，Topic 实际等级在需求对齐点确认。只有 quick 与 standard。

quick 必须同时满足：单会话完成；改动局部可撤回；不改持久结构、权限或对外API契约；预计一张 Ticket 足够。任一不满足就提议 standard。

quick 不写 Spec/Ticket或实施记录，直接实施、针对性测试和自审，按[交付规则](../workflow-delivery.md)形成每条验收各自的测试/代码映射，再完成 Topic。

standard 保留版本化 Spec 和依赖 Ticket，按顺序实施、测试、审查；默认批量实施：逐 Ticket 定向测试和增强自审提交，批次末全量与基线比较及独立审查后收口；整分支审查按需，非前置。保证等级不放宽[找用户的条件](../user-intervention.md)，也不能把局部检查称为全量验证。
