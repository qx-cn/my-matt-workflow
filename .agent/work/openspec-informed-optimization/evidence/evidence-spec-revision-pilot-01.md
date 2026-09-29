# Spec 修订索引试用：Trader V1 控制入口

状态：只读、限范围试用；用于检验修订索引的写法，不修改 Trader 的 Spec 或 Ticket，也不构成其正式影响评审。

## 来源与范围

- 仓库：`/Users/sherly/CS/wsp/trader`，2026-09-29 只读查看。
- 当前修订：`.agent/work/trader-v1/specs/specs-trader-v1-20260917.md`，`revision: 20260917`，继承 `20260908`。
- 直接前版：同目录的 `specs-trader-v1-20260908.md`。它是完整 Spec，足以判断本次控制入口变化；`specs-trader-v1-20260731.md` 属更早的历史修订，可供血缘核查。
- Ticket 例子：`.agent/work/trader-v1/tickets/tickets-trader-v1-07a.md`，查看时为 `blocked-by-design`；本文只核对控制入口这一项，不声称完成全量 Ticket 影响映射。

## 试用索引

| 类型 | 本版最终条款 | 前版依据 | 受影响验收及 Ticket 例子 |
| --- | --- | --- | --- |
| 新增 | 20260917 Spec §1：明确 `trader serve <config>` 服务入口、Telegram long polling、处理结果对应的持久化 offset，并排除公网 webhook。 | 20260908 Spec §8.1 已规定单进程和 SQLite writer lease，也列出 `internal/control` 的职责；此前未规定该 CLI 服务入口、接收方式与 offset 推进条件。 | Ticket 07a 的生产宿主与 CLI 服务入口有显式验收；持久化 offset 见 Ticket 工作范围，验收清单未单列推进、重启续接或失败不推进，待正式影响映射核对。 |
| 修改（细化） | 20260917 Spec §1：将已有的白名单个人确认约束具体化为白名单私聊中的确认 callback，并明确群聊、非白名单及其他通道不得取得交易控制权。 | 20260908 Spec §9 已要求“状态改变只接受白名单个人确认”，§8.1 已排除飞书控制接口；本次细化私聊、callback 和控制身份与通知收件人的区分。 | Ticket 07a 的授权/确认集成验收。 |

本试用没有把“不实现公网 webhook”列为移除行为：前版没有要求实现 webhook，因而不存在可定位的旧要求可被删除。后续正式映射仍须逐项检查其他未完成 Ticket、已完成 Ticket 的补偿需求和完整验收覆盖。

## 试用结论与限制

索引能把本次改变的行为、前版依据和一个未完成 Ticket 的验收及缺口连起来，同时避免复制旧版规范。当前修订是继承式补充文件；判断本次控制入口变化，需要把它与直接前版的完整有效条款一起读，而不能仅把两份文件作逐行差异比较。本例不需要再追溯 20260731 才能给这些变化分类。本文未测量阅读时间，也没有验证索引能提高真实交付结果。
