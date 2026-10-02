---
id: "feature-01"
title: "Independent marker"
ticket_kind: "implementation"
spec_id: "feature"
spec_revision: 1
spec_ref: ".agent/work/feature/specs/specs-feature-01.md"
status: complete
blocked_by: []
sequence: 1
test_commands: ["python3 -B -c 'pass'"]
rule_sources: [".agent/work/feature/specs/specs-feature-01.md"]
rule_scope: ["code.txt"]
rule_constraints: ["write the marker"]
rule_conflicts: []
review_probes: ["recovery"]
execution_agent: "auto"
claimed_by:
supersedes_ticket: []
compensates: []
tags: []
---
## 要构建什么
Write marker
## 适用规则与影响区域
code.txt
## 验收标准
- [x] independent marker is written
