# feature-01 执行简报

## Ticket

---
id: "feature-01"
title: "Independent marker"
ticket_kind: "implementation"
spec_id: "feature"
spec_revision: 1
spec_ref: ".agent/work/feature/specs/specs-feature-01.md"
status: "ready-for-agent"
blocked_by: []
sequence: 1
test_commands: ["python3 -B -c 'pass'"]
rule_sources: [".agent/work/feature/specs/specs-feature-01.md"]
rule_scope: ["code.txt"]
rule_constraints: ["write the marker"]
rule_conflicts: []
review_probes: ["recovery"]
execution_agent: "auto"
claimed_by: ""
supersedes_ticket: []
compensates: []
tags: []
---
## 要构建什么
Write marker
## 适用规则与影响区域
code.txt
## 验收标准
- [ ] independent marker is written


## Spec 验收

- AC-01: independent marker is written

## 已完成前置 Ticket

## 适用规则

[]

## 非约束性触点提示

无：Ticket 未提供触点提示

## 同批次已提交 Ticket 的影响面（实施者声明，待核实）

### .agent/work/feature/specs/specs-feature-01.md
---
spec_id: feature
revision: 1
---
# Fixture Spec
## 验收标准
- AC-01: independent marker is written


## 测试命令

python3 -B -c 'pass'

## 实施计划

Agent 动手前补写：文件和接口；现状断言→代码依据；契约/共享函数/表结构/配置/锁/错误码→调用方/消费者和兼容、数据、并发、权限、性能结论；每项验收各自对应测试断言。事实冲突按 spec-challenge 停止，不任选一边实现。
