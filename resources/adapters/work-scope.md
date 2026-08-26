# 工作范围适配

完成当前 Ticket 后，宿主 `my-implement` 必须通过安装 runtime 的 `next-ticket` 获取 transition；不得因单张 Ticket 已完成而自行结束。

- `single-ticket`：返回 `complete`，在当前 Ticket 后停止。
- `ready-frontier`：重新读取当前 feature 的本地 Ticket，选择所有依赖已完成、未认领、可验收的 implementation Ticket；按 `sequence`、再按稳定 `id` 返回下一张。关键决策、规则冲突、不可推断的关键 seam、实质性测试修复取舍或新授权时传入 blocker 并暂停。
- `approved-plan`：启动时先调用 `ticket-scope` 记录 implementation Ticket id 快照，再将每个 id 作为 `next-ticket --allowed-id` 传回 runtime；运行期间新建 Ticket 不得扩大本次已批准范围。无候选时返回正常完成。

`next-ticket` 是只读选择器。领取、验收勾选、状态设为 `complete` 和提交仍由宿主按 Ticket 生命周期完成；在这些步骤完成前不得解锁下游 Ticket。

用户说「继续」或「提交并继续」只表示在当前已生效范围内推进；不升档、不改写 `work_scope_policy`，也不放宽为全自动连续执行。
