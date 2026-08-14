# Ticket 准入、完成与选择适配

本适配描述 Ticket 准入、完成与选择的本地约定。本地 Ticket 使用 YAML frontmatter：`ticket_kind` 只能是 `implementation` 或 `wayfinder-decision`；`status`、`blocked_by`（YAML 列表）和 `claimed_by` 必须显式存在。`claimed_by:` 的显式空标量表示未认领；缺失、列表或映射都无效，绝不把它们推断为未认领。缺失或旧式 `ticket_kind` 同样是歧义，绝不推断。

实施候选必须同时是 `ticket_kind: implementation`、`status: ready-for-agent`、未认领、每个 `blocked_by` Ticket 的 `status: complete`，并至少有一个未勾选的验收复选框。它还必须声明有效 `execution_agent`、非空 `rule_sources`、`rule_scope`、`rule_constraints`，且 `rule_conflicts: []`；实施前运行 `workflow.py validate-ticket <ticket-path>` 验证。`wayfinder-decision` 或任何 `wayfinder:*` 标签永远不得进入实施，即使其他字段看似就绪。引用只可按唯一的 id、路径或标题解析；孤儿、歧义和依赖环必须先修复。

自动选择只从合格候选中按 `sequence`、再按稳定 id 排序。用户明确选择的 Ticket 不合格时，报告全部缺项并停止；不得静默重选。Triage 不重新处理已有结构化 implementation Ticket；Wayfinder Ticket 也不转换为 implementation。

Wayfinder frontier 只包括 `ticket_kind: wayfinder-decision`、`status: open`、显式未认领且所有 `blocked_by` Ticket 已 `complete` 的 Ticket；其选择规则与 implementation 完全独立。读取 frontier 时按稳定排序（`sequence` 升序、再按 id 字典序）输出；用户明确指定不合格 Ticket 时报告全部缺项并停止，不得静默回退或重选。

关闭 implementation Ticket 前，所有验收复选框必须勾选；否则保留开放状态并说明未完成项。用户专属产品取舍不由这个机械门槛代替。
