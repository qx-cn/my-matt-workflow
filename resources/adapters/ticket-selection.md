# Ticket 准入、完成与选择适配

本适配的可执行真相来源是 `tools/workflow_lib/tickets.py`。本地 Ticket 使用 YAML frontmatter：`ticket_kind` 只能是 `implementation` 或 `wayfinder-decision`；`status`、`blocked_by`（YAML 列表）和 `claimed_by` 必须显式存在。缺失或旧式 `ticket_kind` 是歧义，绝不推断。

实施候选必须同时是 `ticket_kind: implementation`、`status: ready-for-agent`、未认领、每个 `blocked_by` Ticket 的 `status: complete`，并至少有一个未勾选的验收复选框。`wayfinder-decision` 或任何 `wayfinder:*` 标签永远不得进入实施，即使其他字段看似就绪。引用只可按唯一的 id、路径或标题解析；孤儿、歧义和依赖环必须先修复。

自动选择只从合格候选中按 `sequence`、再按稳定 id 排序。用户明确选择的 Ticket 不合格时，报告全部缺项并停止；不得静默重选。Triage 不重新处理已有结构化 implementation Ticket；Wayfinder Ticket 也不转换为 implementation。

关闭 implementation Ticket 前，所有验收复选框必须勾选；否则保留开放状态并说明未完成项。用户专属产品取舍不由这个机械门禁代替。
