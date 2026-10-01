---
id: "workflow-simplification-17"
title: "补偿修复 release 引用保留与安装清理竞态"
ticket_kind: "implementation"
spec_id: "workflow-simplification"
spec_revision: 1
spec_ref: ".agent/work/workflow-simplification/specs/specs-workflow-simplification.md"
supersedes_ticket: []
compensates: ["workflow-simplification-09"]
status: complete
blocked_by: ["workflow-simplification-09"]
claimed_by:
tags: ["independent-review-compensation"]
sequence: 17
test_commands: ["python3 -m unittest discover -s tests"]
rule_sources: [".agent/work/workflow-simplification/specs/specs-workflow-simplification.md", "resources/testing-seams.md"]
rule_scope: ["tools/workflow_lib/release.py", "tools/workflow_lib/installer.py", "tools/workflow_lib/release_references.py", "tests/test_skill_packaging_v2.py"]
rule_constraints: ["补偿独立批审核09-C1/09-C2，仅修复AC-40，保持Spec r1。", "安装与删除共享引用锁；无法证明无引用的旧版不得猜测删除。", "原09完成及原始审核不变，不实施12–14；只使用临时安装根，不推送或真实安装。"]
rule_conflicts: []
review_probes: ["recovery"]
execution_agent: "auto"
---

# 17 — release 引用与清理补偿

用户已授权修复独立批审核问题。来源：review-workflow-simplification-09-independent.json 的09-C1/09-C2；Spec第11节AC-40。

## 验收标准

- [x] 自定义安装根安装的旧release在后续普通build中保留且verify与再次install成功；不要求每次build重新传home。
- [x] build的source gate期间成功安装旧release后，清理保留最新有效引用；安装与引用读取/删除共享同步边界，不影响既有安装事务恢复。
- [x] 已知受管理release仍只保留当前、上一版及真实引用；升级后过期引用不永久pin，损坏引用登记拒绝清理，无法发现历史自定义根的旧release保守保留。
- [x] 两条原缺陷可观察red/green、相关及声明全量测试通过，冻结快照自审和独立修复复审有证据；原始报告和修复映射保留。
