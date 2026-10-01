# Repair plan

仅修复当前 Ticket 的安装引用保留保证；不修改 Spec 或下游方法语义。

## Finding 09-custom-home-retention
- Acceptance IDs: workflow-simplification-09#A6
- Root cause: deploy-build-drops-explicit-agent-home
- Change: command_deploy 将显式 agent_home 传给 _build_release；后者将它加入默认安装状态根后交给 build_release。保留已有 source gate、release lock 和状态校验。清除已核实未跟踪的 my-teach Python 缓存文件，使最终 receipt 仅绑定源码。
- Verification: 先在 temp repository 和 custom home 实际构建并安装 r1，随后通过 _build_release 的 CLI seam 构建三次；补丁前 r1 被清理，补丁后保留 r1/r3/r4。只替换耗时 source gate，实际构建、安装状态与清理执行真实代码。再跑已声明完整 tests，重开冻结 Code/Spec 双遍自审。
- Out of scope: 不新增公开命令、持久宿主注册表或真实宿主写操作；不改变其他六条验收、Ticket 10/11 方法、Ticket13 文件清理或施工 profile；不推送或部署。
