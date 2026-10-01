---
id: "workflow-simplification-16"
title: "补偿修复未交回审查后的接受与度量恢复"
ticket_kind: "implementation"
spec_id: "workflow-simplification"
spec_revision: 1
spec_ref: ".agent/work/workflow-simplification/specs/specs-workflow-simplification.md"
supersedes_ticket: []
compensates: ["workflow-simplification-05", "workflow-simplification-06", "workflow-simplification-07"]
status: complete
blocked_by: ["workflow-simplification-05", "workflow-simplification-06", "workflow-simplification-07"]
claimed_by:
tags: ["independent-review-compensation"]
sequence: 16
test_commands: ["python3 -m unittest discover -s tests"]
rule_sources: [".agent/work/workflow-simplification/specs/specs-workflow-simplification.md", "resources/testing-seams.md"]
rule_scope: ["tools/workflow_lib/ticket_completion.py", "tests/test_review_resolution.py", "tests/test_topic_branch.py"]
rule_constraints: ["仅修复独立批次 round 1 未交回审查导致接受失败的根因；保持 Spec r1。", "未提交审查结果不能伪装成 reviewer 结论；度量记录真实可观察证据。", "不改写 05–07 完成事实，不实施 08–14，不推送、不安装。"]
rule_conflicts: []
review_probes: ["recovery"]
execution_agent: "auto"
---

# 16 — 未交回审查接受恢复

## 要构建什么

补偿独立批次审核 round 1 报告中的唯一 P1：连续四次公开 review 开启但不 submit，第五次置 needs-user，当前测试通过后 accept 因度量直接读取未提交 entry.reviewer 失败。Ticket 会残留 complete，branch 同根因无法归档。

## 适用规则与影响区域

- Spec r1 M4/M5/M6、Ticket/branch accept、真实度量与 AC-24；resources/testing-seams.md。
- 共享 Ticket/Topic 度量 seam 与两组公共 CLI 回归；不改变审查额度、有效 pass、定义变更或测试门。
- 已完成历史与独立原始报告保留；本补偿修复沿用批次 round 1/4，不重置批次预算。

## 验收标准

- [x] shared/private 各通过公开 CLI 开启四轮未 submit、第五次开启操作进入 needs-user；Ticket 当前声明测试通过后 accept 成功并持久化 accepted、原因、已知问题与度量，无半完成状态。
- [x] 同一中断链在多 Ticket Topic branch 路径可接受并归档，满足摘要及当前全量测试门；shared/private 都可恢复，不多做内容提交。
- [x] 未交回结果的轮次不伪造已提交 reviewer provenance；度量仍记录实际轮数和测试批次。已提交 self/independent 结论原有 provenance 保持真实，正常 finish/accept 不回归。
- [x] 针对性公开 CLI 回归、声明全量测试和 runtime 冻结增强自审通过；批次修复后另做独立审核，保存原始报告与修复映射。
