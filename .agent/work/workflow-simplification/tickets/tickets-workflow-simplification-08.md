---
id: "workflow-simplification-08"
title: "预览并安全迁移旧项目产物"
ticket_kind: "implementation"
spec_id: "workflow-simplification"
spec_revision: 1
spec_ref: ".agent/work/workflow-simplification/specs/specs-workflow-simplification.md"
supersedes_ticket: []
compensates: []
status: complete
blocked_by: ["workflow-simplification-07"]
claimed_by:
tags: []
sequence: 8
test_commands: ["python3 -m unittest discover -s tests"]
rule_sources: [".agent/work/workflow-simplification/specs/specs-workflow-simplification.md", "resources/testing-seams.md"]
rule_scope: ["tools/**", "tests/**"]
rule_constraints: ["Spec 核心模型为状态与命令唯一权威；范围外工作不实施。", "验证仅断言可观察命令结果、状态、提交、归档和度量，不复刻内部算法。", "只在 fixtures/临时项目执行迁移；不操作用户其他项目，本仓库历史 work 文档不转换。"]
rule_conflicts: []
review_probes: ["recovery"]
execution_agent: "auto"
---

# 08 — 预览并安全迁移旧项目产物

**要构建什么：** 旧项目先得到零写入迁移摘要，再在 apply 前备份并转换；旧的进行中 Ticket 能恢复，无法判断的条目明确列出。

**被谁阻塞：** 07 — 审查整分支并完成或放弃 Topic

## 适用规则与影响区域

- 规则来源：源 Spec revision 1（M2 迁移、M3 快照、M7 I-8/I-9；第 10 节；AC-04/27 旧格式拒绝、35、36）；共享测试 seam 约定。当前 Codex resolve-rules 未发现仓库原生规则；execution_agent 保持 auto，实施前按实际绑定 Agent 和修改路径重新解析。
- 影响区域：tools/**、tests/**。
- 实施约束：只在 fixtures/临时项目执行迁移；不操作用户其他项目，本仓库历史 work 文档不转换。 关键契约以源 Spec 原文为准；不推送、不建 MR、不写外部系统。
- 验证：使用 Ticket 01 的旧 runtime 样例，通过 subprocess 证明预览零写入、备份内容、状态续跑和幂等性。
- 测试边界：以上 test_commands 为声明；与项目配置的匹配在新 runtime 生效后校验。旧 runtime 施工并非本 Spec 的必需条件，不能伪造实施 receipt。

## 验收标准

- [x] 项目级旧配置或长期 Spec 使全部读取配置的代表命令停止并提示 migrate，文件不变；非法新配置指出字段。Topic 级旧格式只阻止该 Topic，overview 标需要迁移；历史记录和 archive 不误报。
- [x] migrate 默认列出文件、转换类别及无法自动判断项，零写入；apply 先备份 agent，排除 git 与已有备份，写入备份忽略规则，转换后满足 I-A1。
- [x] 配置转换为九键 schema 2，audited 转 standard，非 local 列为无法自动迁移；Spec/Ticket 仅在可唯一推断时补字段，测试声明取全量集合，空集合不猜。
- [x] AC-35 A–E 样例全部满足预期：A 的实施中 Ticket 能走完测试审查 finish；B 测试后可 accept 或修订 reopen；C 变 implementing；D 完成历史保留且直接迁移归档；E 整 Topic 拒绝自动迁移。
- [x] 实施中记录沿用旧基线、测试/审查证据清空；无基线不猜；定义快照绑定转换后文件。已完成 Ticket 和其记录正文不改写，交接原样保留。
- [x] 分片术语与 ADR 合并到项目级位置，冲突列出不自动合并；长期 Spec 只在备份保留；归档重名拒绝；第二次运行除 E 外无需迁移。
