# Ticket 03 交付

## 改动概述

完成 `workflow-simplification-03`：新增 `implement start/test/status` 与 schema 2 Ticket 校验。开始前验证血缘、依赖、测试匹配、内容干净、Topic 等级和唯一实施约束；第一次实施执行分支规则，切换后重新读取准入材料，拒绝目标分支状态、定义或配置变化。生成包含规则全文、前置提交与文件、验收和实施计划占位的简报。

每条真实子进程测试分别绑定运行前的内容，失败输出命令、退出码与输出末尾并非零退出。显式 argv 仅作进度，定义中的 test_commands 漂移拒绝继续。pending Topic 下一步命令包含可实施 Ticket id，兑现 Ticket 02 交接。

新模块 `tools/workflow_lib/ticket_implementation.py` 独立于旧 session API；旧 Ticket 列表解析先保留合法 JSON 引号。施工配置仍为 schema 1，任务由已安装 runtime `20260929-234249` 管理。

## 测试结果

- 17 个实施 CLI 测试通过，覆盖六项验收及切换后准入变化、规则重读、逐条内容身份、失败输出非 UTF-8 字节、绑定宿主和多 Topic 隔离。
- Topic 生命周期 16 项、旧 Ticket 校验 12 项回归通过。
- Ticket 声明的 `python3 -m unittest discover -s tests` 全量测试通过，退出码 0。最终 test evidence：`5cc2d127614d03a290b615a1130a1bfc1a1eb9a3ed92784d8ae03bba2e1b0a5f`。
- 测试、审查与完成收据绑定内容 `60e177154066db0609b02562c63943029f36ab3888f8637fbaf530a574c64ddb`；完成历史校验通过。
- 实现与测试 diff whitespace 检查通过。旧 runtime 清空 Ticket claimed_by 留下行尾空格，保留管理器写出的终态原文。

## 审查发现与修复

按当前已安装 profile 做 self 审查，如实记录来源；不是独立审查。Code、Spec 两遍审查覆盖 A1–A6、recovery 和 downstream-owner。

首轮两项 P1：切换分支后沿用缓存准入材料可能覆盖 needs-user；整批测试共用内容身份可能使在另一内容上运行的命令冒充当前内容的通过依据。runtime 登记问题后，冻结修复方案并通过 my-review-design；补充 red-green 回归，在唯一批准修复轮修复。复审无剩余阻断。

修复方案 review evidence：`caabf97ba61aea92704811accc8272830f855cb569802f43900a5b03affe783c`。最终 review evidence：`7c0a7dd37d18bdaa64316d1a4366ce5527e2e629657e81cbb8bb957bbc3dc47a`。

## 建议

无当前 Ticket 新增建议。Ticket 04 使用本轮基线、定义快照和逐条测试记录接入冻结审查，接口见新交接文件。

## 已知问题

当前 Ticket 无未解决 blocker。审查材料、finish、resolve/reopen、整分支收尾与公共命令裁剪分别由后续 Ticket 实施；未宣称完整新 workflow 可用。

## 长期知识沉淀

无新增长期 ADR。当前接口与恢复边界记录于交接。

## 用户介入记录

新增介入 0 次，沿用本会话 Topic 内自动授权，保持 single-ticket；执行本地提交，未推送、安装或写外部系统。

## 未验证项

未验证进程强制终止、机器掉电或并发实施；未验证真实宿主安装、其他项目迁移和后续收尾链。仓库已有 `.agent/.matt-workflow.md.swp` 保留原状，不纳入提交。
