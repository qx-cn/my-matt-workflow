---
id: workflow-ticket-autonomy-01
title: 实施自主权与不重置预算的技术刷新
ticket_kind: implementation
spec_id: workflow-ticket-autonomy
spec_revision: 1
spec_ref: .agent/work/workflow-ticket-autonomy/specs/specs-workflow-ticket-autonomy-01.md
supersedes_ticket: []
compensates: []
status: complete
blocked_by: []
claimed_by:
tags: []
sequence: 1
test_commands: ["python3 -m unittest discover -s tests"]
touchpoints: ["tools/workflow_lib", "tools/workflow.py", "skills", "resources", "tests", "README.md"]
review_probes: [recovery]
execution_agent: codex
---

# 01 — 实施自主权与不重置预算的技术刷新

**要构建什么：** Agent 为已确认目标自主调整实施；技术刷新能恢复已登记技术挑战、失效旧证据，同时保留预算与真实待决事项。

## 验收标准

- [x] AC-01、AC-02：规则一致，实施调整可追溯，验收覆盖和完成历史保留。
- [x] AC-03：三个技术刷新入口与记录校验可通过真实 CLI 使用。
- [x] AC-04：刷新失效证据而保留轮数、基线、发现与历史，预算耗尽仍拒绝第五轮。
- [x] AC-05：技术/产品挑战混合时准确处置与路由，覆盖三个入口。
- [x] AC-06：旧记录和重复恢复安全，缺证据/错误身份不解除停止。
- [x] AC-07：回归、全量、冻结独立审查、场景演练和发布包验证有实际证据。
