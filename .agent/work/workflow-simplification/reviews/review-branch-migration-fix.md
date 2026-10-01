# 整分支迁移问题修复复审

来源：用户在整体 review-agent 审查发现两项 P1 后明确要求修复。范围：Ticket08 迁移兼容和整分支审查消费历史记录的补偿修复；原 Spec revision 1 和已完成 Ticket 不变。

本次为 standard 单切片，依据版本化 Spec 直接实施并保留实际测试与自审证据；没有新 Ticket/session，不伪造旧施工协议或新 runtime 完成回执。

## 修复依据与方案

- 原 P1：旧 Spec 的普通验收条目在 implement start 被拒绝。保留现有带编号条目的提取方式；无法提取时把完整原 Spec 放入简报，由 Agent 读取，不猜测、改写或删除验收。空内容仍拒绝。
- 原 P1：已完成旧 Ticket 没有 implementations 记录，整分支 review 读取失败。优先读取新实施记录；缺少时读取旧 journal 的实际绑定。没有历史绑定时仅允许 Ticket 的固定 Agent；auto、冲突或未知绑定拒绝，不用当前默认宿主猜测，不创建伪造记录。
- 方案成立性自审：两项仅修复消费者兼容性，不改变迁移状态映射、完成历史或 Agent 绑定契约。验证使用旧版生成的 fixture 和公共 CLI 全链路，保留旧工件字节。

## 冻结范围

基线：4009709499498f5bed77e413ab4b3d4f503a7c2b。

Review-Snapshot: 0c65d13785565a95c56f33dd5b074763ac834174bf7b727f57fec6df48c6eec2

来源：self；同一上下文顺序完成 Code 与 Spec 两遍，不声称独立审查。范围是三份修复文件及相关调用链；工作区原有审核文档修改不属于修复范围。快照在保存本报告前验证为 match；保存报告后新增的证据文档不属于被审代码。各代码文件摘要见 branch-migration-fix-evidence/completion.json。

## Code

No findings.

复核简报生成、历史绑定选择、rule_material、材料冻结及重新验证、Topic 完成消费者；未知绑定拒绝，历史 Agent 与当前默认宿主不同时仍使用历史规则。保留现有新记录优先级，不写入历史文件或替代记录。

## Spec

No findings.

对照 Spec M3 执行简报、M4 整分支验收并集、第10节旧记录原样保留及本仓库历史不迁移。原两项 P1 的完整失败路径已转为通过：普通验收能进入简报并完成 Ticket；旧完成 Ticket 的验收与正确宿主规则进入整分支材料，测试、审查、提交结果、Topic归档成功，历史字节一致。

## 验证与限制

15项迁移测试通过；完整 workflow.py check exit 0；validate 为 VALID skills=32；git diff --check exit 0。红绿输出、完整 check 输出及内容核验保存于 branch-migration-fix-evidence/。测试中的 pass JSON 是已知 fixture 的校准输入，不是真实 Agent 独立审查证据。

本次运行 Python 3.14.4；未重新验证3.10、真实宿主安装或模型效果。原整体审查的两项阻断已解决，本轮复审不扩大为另一轮独立整分支审查。
