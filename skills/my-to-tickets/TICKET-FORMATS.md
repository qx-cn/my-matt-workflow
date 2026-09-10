# Ticket 格式

确定 `task_backend` 后，只读取对应格式。

## local

每张 Ticket 使用一个文件：

```markdown
---
id: <feature-slug>-<NN>
title: <Ticket 标题>
ticket_kind: implementation
spec_id: <源 Spec 的稳定 id>
spec_revision: <源 Spec revision>
spec_ref: <源 Spec 路径或 URL>
supersedes_ticket: []
compensates: []
status: ready-for-agent
blocked_by: []
claimed_by:
tags: []
sequence: <NN>
rule_sources: []
rule_scope: []
rule_constraints: []
rule_conflicts: []
review_probes: [] # 仅 recovery、unknown-response；按 Spec 声明
execution_agent: <auto|codex|cursor|claude>
---

# <NN> — <Ticket 标题>

**要构建什么：** 从用户视角描述该 Ticket 端到端实现的行为，而非逐层实现清单。

## 适用规则与影响区域

- 规则来源：
- 影响区域：
- 实施约束：
- 验证：

## 验收标准

- [ ] 验收标准 1
- [ ] 验收标准 2
```

`blocked_by` 必须是 YAML 列表，使用已创建 Ticket 的唯一 id、路径或标题；无阻塞时保留 `[]`。领取时仅填写 `claimed_by`，完成阻塞 Ticket 时将其 `status` 设为 `complete`。正文状态行不能替代 frontmatter，也不能据此猜测旧 Ticket 类型。

修订未完成 Ticket 时，`supersedes_ticket` 指向被替代项；补偿已完成工作时，`compensates` 指向历史 Ticket。新 Ticket 始终绑定当前 Spec revision。关闭前勾选全部验收项。

## external

```markdown
## 父项

对 Tracker 父 Issue 的引用（源是现有 Issue 时才保留；否则省略本节）。

## Spec 血缘

- Spec id：
- Revision：
- 来源：
- 替代或补偿的 Ticket（如有）：

## 要构建什么

从用户视角描述该 Ticket 端到端实现的行为，而非逐层实现。

## 验收标准

- [ ] 标准 1
- [ ] 标准 2

## 被谁阻塞

- 每张阻塞 Ticket 的引用，或“无——可立即开始”。

## 适用规则与影响区域

- 规则来源：
- 影响区域：
- 实施约束：
```

## project-docs 与 none

`project-docs` 遵循项目既有格式，但仍完整保留 Spec 血缘、端到端行为、验收标准、阻塞边、适用规则与影响区域。`none` 使用相同信息结构，只在会话中输出。
