# Ticket 准入与选择适配

实施前，Ticket 必须同时满足：`ticket_kind: implementation`、`status: ready-for-agent`、所有 `blocked_by` 已完成、至少一条可验证验收标准，且不带 `wayfinder:*` 标记。`ticket_kind: wayfinder-decision` 或带 `wayfinder:*` 的 Ticket 永不进入实施；未解决的产品决定必须保留给用户。

用户指定的 Ticket 不满足准入时，说明具体缺项并停止；不得静默改选。只有用户明确确认改选后，才可从可实施集合中按既有确定性顺序选择另一张。缺少类型的旧 Ticket 不猜测，按现有模板和明确状态无法唯一判断时请求确认。
