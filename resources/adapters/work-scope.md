# 工作范围适配

完成当前 Ticket 后是否继续由已解析的 `work_scope_policy` 决定：`single-ticket` 在当前 Ticket 完成后停止；`ready-frontier` 可领取所有阻塞者已完成的 Ticket；`approved-plan` 可按依赖顺序完成同一已批准计划。

用户说「继续」或「提交并继续」只表示在当前已生效范围内推进；不升档、不改写 `work_scope_policy`，也不放宽为全自动连续执行。
