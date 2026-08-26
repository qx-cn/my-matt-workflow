# 写操作 Gate

任何受 profile 控制的写操作先通过安装 runtime 的 `write-gate`，再执行；该命令只返回 `allow`、`confirm`、`deny` 或 `pause`，不会执行写入。

- `branch` 读取 `branch_policy`；`commit` 读取 `commit_policy`；`external` 读取 `external_write_policy`；`docs` 读取 `docs_writeback`。
- `confirm` 必须等待用户，`deny` 不得执行，`allow` 可继续。
- 即使 `external_write_policy: allow`，新外部目标或未包含在已批准 Ticket/计划内的操作也返回 `pause`；固定安全禁止项永远不可放宽。
