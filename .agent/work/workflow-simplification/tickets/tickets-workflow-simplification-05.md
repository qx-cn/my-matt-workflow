---
id: "workflow-simplification-05"
title: "按五步完成并提交单张 Ticket"
ticket_kind: "implementation"
spec_id: "workflow-simplification"
spec_revision: 1
spec_ref: ".agent/work/workflow-simplification/specs/specs-workflow-simplification.md"
supersedes_ticket: []
compensates: []
status: complete
blocked_by: ["workflow-simplification-04"]
claimed_by: 
tags: []
sequence: 5
test_commands: ["python3 -m unittest discover -s tests"]
rule_sources: [".agent/work/workflow-simplification/specs/specs-workflow-simplification.md", "resources/testing-seams.md"]
rule_scope: ["tools/**", "tests/**"]
rule_constraints: ["Spec 核心模型为状态与命令唯一权威；范围外工作不实施。", "验证仅断言可观察命令结果、状态、提交、归档和度量，不复刻内部算法。", "测试失败、内容变化、缺失审查和未勾验收均不能绕过提交门槛；不推送。"]
rule_conflicts: []
review_probes: ["recovery"]
execution_agent: "auto"
---

# 05 — 按五步完成并提交单张 Ticket

**要构建什么：** 一张干净的 Ticket 可沿 start、test、review、review submit、finish 完成；runtime 自动绑定证据并提交，Agent 无须手写哈希。

**被谁阻塞：** 04 — 冻结完整审查材料并校验结果

## 适用规则与影响区域

- 规则来源：源 Spec revision 1（M3、M5 finish/单 Ticket complete、M6、M7；AC-03 提交、07、09、25 单 Ticket 收尾）；共享测试 seam 约定。当前 Codex resolve-rules 未发现仓库原生规则；execution_agent 保持 auto，实施前按实际绑定 Agent 和修改路径重新解析。
- 影响区域：tools/**、tests/**。
- 实施约束：测试失败、内容变化、缺失审查和未勾验收均不能绕过提交门槛；不推送。 关键契约以源 Spec 原文为准；不推送、不建 MR、不写外部系统。
- 验证：用真实提交、状态、归档及退出码证明完整五步；缺陷注入验证 stale 记录、notes 和摘要拒绝。
- 测试边界：以上 test_commands 为声明；与项目配置的匹配在新 runtime 生效后校验。旧 runtime 施工并非本 Spec 的必需条件，不能伪造实施 receipt。

## 验收标准

- [x] 干净 Ticket 五步完成，结果文件只填写判断字段；每条声明测试和审查通过均绑定当前内容，验收复选框全勾选才允许 finish。
- [x] 通过后修改任一内容文件，finish 拒绝且 status 指向重测和复审；只修改 agent 或忽略文件不失效。测试失败也不能 finish。
- [x] finish 有内容时最多一次代码提交，标题为 ticket id 加标题；无内容时不做代码提交；经历修复必须提供 notes-file，修复思路进入提交正文。
- [x] Ticket 状态变 complete，追加 kind ticket/outcome complete 度量；返回真正合格的下一张 Ticket，否则指向 topic complete。
- [x] 单 Ticket standard 在 Ticket complete、内容干净和摘要齐全后归档；自动补建的 Topic 也能完成；全部终点满足 shared/private 的 I-A1、I-A2 和每 Ticket 一次代码提交。
