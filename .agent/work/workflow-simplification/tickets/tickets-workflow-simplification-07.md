---
id: "workflow-simplification-07"
title: "审查整分支并完成或放弃 Topic"
ticket_kind: "implementation"
spec_id: "workflow-simplification"
spec_revision: 1
spec_ref: ".agent/work/workflow-simplification/specs/specs-workflow-simplification.md"
supersedes_ticket: []
compensates: []
status: complete
blocked_by: ["workflow-simplification-06"]
claimed_by: 
tags: []
sequence: 7
test_commands: ["python3 -m unittest discover -s tests"]
rule_sources: [".agent/work/workflow-simplification/specs/specs-workflow-simplification.md", "resources/testing-seams.md"]
rule_scope: ["tools/**", "tests/**"]
rule_constraints: ["Spec 核心模型为状态与命令唯一权威；范围外工作不实施。", "验证仅断言可观察命令结果、状态、提交、归档和度量，不复刻内部算法。", "分支内容修复后的测试/审查必须重新绑定；归档 Topic 不写入；全量测试在每条 standard 入口与收尾检查。"]
rule_conflicts: []
review_probes: ["recovery"]
execution_agent: "auto"
---

# 07 — 审查整分支并完成或放弃 Topic

**要构建什么：** 多张 Ticket 完成后，可按全量测试和整分支审查收尾；用户可裁决分支审查，或放弃 Topic 并保留未提交代码。

**被谁阻塞：** 06 — 限制审查轮数并处理 Ticket 裁决

## 适用规则与影响区域

- 规则来源：源 Spec revision 1（M2、M4 分支、M5、M6、M7；第 5 节；AC-20 分支、23、24）；共享测试 seam 约定。当前 Codex resolve-rules 未发现仓库原生规则；execution_agent 保持 auto，实施前按实际绑定 Agent 和修改路径重新解析。
- 影响区域：tools/**、tests/**。
- 实施约束：分支内容修复后的测试/审查必须重新绑定；归档 Topic 不写入；全量测试在每条 standard 入口与收尾检查。 关键契约以源 Spec 原文为准；不推送、不建 MR、不写外部系统。
- 验证：真实临时 git 仓库验证完整提交序列、两种 agent 模式、分支裁决、放弃保留脏内容。
- 测试边界：以上 test_commands 为声明；与项目配置的匹配在新 runtime 生效后校验。旧 runtime 施工并非本 Spec 的必需条件，不能伪造实施 receipt。

## 验收标准

- [x] topic test 执行全部无星号命令，空集合和失败均非零退出；topic review 仅用于多 Ticket standard，要求所有 Ticket complete 及绑定当前内容的全量测试通过。
- [x] 整分支材料覆盖 Topic 基线以来全部内容，验收取 Ticket 并集；轮数和四种停止信号独立于 Ticket 对象，needs-user 时 complete 拒绝。
- [x] 多 Ticket complete 再次运行全量测试，校验摘要及有效整分支审查；有收尾内容改动时最多一次收尾修复提交，归档并追加 Topic 度量。
- [x] branch accept 要求 needs-user、全量测试及其余收尾条件；结果归档，有内容则收尾提交，accepted 度量和已知问题进入摘要。branch reopen 仅在其快照以来 Ticket/Spec 定义改变时归零。
- [x] topic abandon 可放弃任意未归档 Topic，原因与 abandoned 度量持久化；未提交内容原样保留并列出；overview 不再显示，归档 Ticket start 拒绝。
- [x] 按 AC-24 在 private/shared 各完整运行单 Ticket、多 Ticket 含分支修复、Ticket accept、分支 accept、abandon；验证 I-A1、I-A2、I-3，包括无内容无需代码提交与归档重名拒绝。
