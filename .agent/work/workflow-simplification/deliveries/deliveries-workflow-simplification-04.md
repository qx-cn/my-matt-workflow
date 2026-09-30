# Ticket 04 交付

## 改动概述

完成 `workflow-simplification-04`：新增 `implement review` 开放冻结材料与 `--submit` 结果校验。材料包含 Ticket 基线以来全部内容差异、范围外列表、稳定验收、探针、直接下游、规则、Spec、已决清单、循环规则和预填结果模板；不读取实施者总结或简报计划。

结果校验逐字段检查六项预填值、四类 status、reviewer 来源及宿主声明模型、coverage、两类 severity；blocking 必须有锚定对象、位置、出错路径和可达性。冻结材料或当前内容、定义、规则、已决事项和下游验收变化时拒绝。相同结果可重试，同单元不同结论不能覆盖。只有 advisory 的 findings 登记为 pass，建议在 topic status 展示。

模块位于 `tools/workflow_lib/ticket_review.py`，独立于旧 session API。当前施工仍通过安装 runtime `20260929-234249`；仓库自身配置保留 schema 1。

## 测试结果

- 12 项审查 CLI 测试通过，覆盖五项验收及全部 Git 内容状态、删除/二进制/符号链接/执行位、忽略文件、嵌套 .agent fixture、字段篡改、缺失 coverage、来源与模型漂移、规则与决定变化、恢复重试和四种结果。
- 17 项实施 CLI、16 项 Topic 生命周期回归通过。
- 修复后声明的 `python3 -m unittest discover -s tests` 全量测试通过，真实退出码 0。最终 test evidence：`dd252cafdc4b24e090fd236c5bc2e7e32db74dafa2e22368151c5b4b04f672cc`。
- 最终测试、审查、代码与完成收据绑定内容：`7b73faccbff7b00e19bfd82ba2e43f3a9785b4807c3228c2a8aec7e7ef1b6cae`；完成历史及当前代码校验一致。
- 实现与测试文件 whitespace 检查通过。旧 runtime 清空 Ticket claimed_by 的行尾空格保留为终态原文。

## 审查发现与修复

来源为 self，不是独立审查。对 runtime 冻结快照依次执行 Code、Spec 两遍审查，覆盖 A1–A5、recovery 和 downstream-owner。

首轮 P1：过滤器排除任意路径片段 .agent，导致普通测试 fixture 被漏出材料。用冻结源在真实临时 Git 仓库复现；runtime 登记 finding 后，冻结修复方案并通过 my-review-design。唯一修复轮把过滤收窄为项目根 .agent/.git，共用判定同时覆盖 baseline 和 current；补充已跟踪修改及未跟踪新增 fixture 的 red-green 回归。

最终两遍复审无当前 Ticket 剩余阻断。review evidence：`de77bef90c5c0f24f491caf2dcc723c8e87faa48b9606a37f3379acc168e9416`；repair-plan review evidence：`6a9fc3452e3dbfaab487504ce39a0e83a2115205e92117a2bcca9b149fdff810`。

## 建议

已向直接下游 05 登记 follow-on：finish 消费归一化的 entry.status，核验当前内容、冻结材料和测试；不能把原始 result.status=findings 的仅建议结果误判，也不能接受过期 pass。详见 `handoffs-workflow-simplification-04-review-foundation.md`。

## 已知问题

当前 Ticket 无未解决 blocker。05 拥有 finish；06 拥有轮数上限、停止信号和 needs-user/reopen；07 拥有整分支审查。当前循环文字为 runtime 单处定义，09/10 的结构及共享资源改造与13 的最终工具裁剪需协调接入。尚未宣称完整新主链已可运行。

## 长期知识沉淀

无新增长期 ADR。可逆模块、记录形状和后续 owner 记录于交接。

## 用户介入记录

新增介入 0 次，沿用会话 Topic 内自动授权并保持 single-ticket。本地提交在授权内；未推送、安装、迁移其他项目或写外部系统。

## 未验证项

未执行真实宿主独立审查者派发。来源和模型校验证明宿主声明与结果一致，不能证明宿主进程或隐藏上下文。未验证机器掉电、并发实施、真实宿主安装和后续 finish 链。非 blob Git 条目、非常规内容不能冻结时明确拒绝。已有 `.agent/.matt-workflow.md.swp` 保留原状，不纳入提交。
