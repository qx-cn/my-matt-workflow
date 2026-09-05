---
name: my-to-tickets
description: 将计划、Spec 或当前对话拆成 tracer-bullet Ticket；每张声明阻塞边，并按项目配置保存或发布。
disable-model-invocation: true
---

# 拆分 Ticket

把计划、Spec 或对话拆成一组 **Ticket**：每张都是 tracer-bullet 纵向切片，并声明**阻塞**它的 Ticket。

读取 `.agent/matt-workflow.md`（含生效的 `humanizer_policy`）；缺失时先运行 `/my-setup`。发布到 Tracker 或项目文档前遵循[写操作 Gate](references/shared/adapters/write-actions.md)。

## 过程

### 1. 收集上下文

使用当前对话中已有的内容。若用户传入引用（Spec 路径、Issue 号或 URL），获取并阅读全文与评论。按[最终态写作](references/shared/final-state-writing.md)只将当前有效决定转成 Ticket。

记录源 Spec 的 `spec_id`、`revision` 与路径/URL。没有正式 Spec 时，为已批准计划分配等价的稳定 id、revision 与可定位引用；不得创建无来源血缘的 `ready-for-agent` Ticket。

### 2. 探索代码库（可选）

若尚未探索代码库，则探索以理解当前状态。Ticket 标题和描述应使用项目领域术语，并遵守相关 ADR。起草前按 [项目规则解析](references/shared/adapters/project-rules.md) 为 `execution_agent` 解析规则；未解决的规则冲突不得生成 `ready-for-agent` Ticket。

寻找 prefactor 机会，让实施更容易：“先让变更容易，再做容易的变更。”

### 3. 起草纵向切片

将工作拆成 **tracer bullet** Ticket。

<vertical-slice-rules>

- 每个切片穿过每一层（schema、API、UI、测试）的狭窄但**完整**路径：是纵向，而非某层的水平切片；
- 完成的切片必须能独立演示或验证；
- 每个切片应能放进一个全新的上下文窗口完成；
- 所有 prefactoring 应先完成。

</vertical-slice-rules>

为每张 Ticket 给出**阻塞边**：即开始它之前必须完成的其他 Ticket。没有阻塞者可立即开始。

**大范围重构是纵向切片的例外。** 大范围重构是一次机械变更——如改列名、重定共享符号——其 blast radius 覆盖整个代码库，单次编辑会同时破坏数千调用点，无法让任何纵向切片保持 green。不要强行改成 tracer bullet；使用 **expand–contract**：先 expand，在旧形式旁加入新形式而不破坏任何内容；再按 blast radius 分批迁移调用点（按 package 或目录），每批一张被 expand 阻塞的 Ticket。旧形式仍在，因此批次之间 CI 保持 green；最后在所有迁移批次完成后 contract，删除旧形式。若连批次都无法单独 green，仍保留顺序，但让它们共享集成分支，并让所有批次阻塞最后的 integrate-and-verify Ticket；只有最后一张承诺 green。

### 4. 审阅拆分并按需确认

将建议拆分以编号列表展示。每张 Ticket 都展示：

- **标题**：简短描述名称；
- **被谁阻塞**：必须先完成的其他 Ticket（如有）；
- **交付什么**：该 Ticket 端到端实现的行为。
- **适用规则与影响区域**：规则来源、影响模块/目录/glob，以及由规则推出的实施约束。

先自检粒度是否过粗或过细、阻塞边是否只依赖真正门槛，以及是否有应合并或再拆分的 Ticket。若这些都能从已批准 Spec、项目规则和代码推断，分类为 `routine`，按[指令权威与决策 Gate](references/shared/instruction-authority.md)继续保存可审阅草稿，不要求用户再次批准机械拆分。

只有拆分暴露出会改变目标、范围、公开接口、数据语义、测试投入或风险承担的未知时，才分类为 `consequential` 并执行 `decision-gate`；`confirm` 时连同编号方案和具体分歧询问，`allow` 时记录依据后继续，`pause` 时停止。用户专属产品取舍分类为 `user-exclusive`，不得由自动策略决定。

### 5. 保存或发布 Ticket

输入是修订版 Spec 时，先做影响映射：已完成 Ticket 保持 `complete` 且不改正文；需要撤销或迁移其结果时新增补偿 Ticket。受影响的未完成 Ticket 进入 `revising`，更新来源、验收和阻塞边，通过 `validate-ticket` 后标为 `revalidated`；不受影响的 Ticket 保留原血缘。不得删除历史 Ticket 或把完成记录改写成“未发生”。

**写入前**：按 [humanizer](references/shared/humanizer.md) 服从 `humanizer_policy`，再按配置后端保存：

- **`local`** → 每张文件写入 `.agent/work/<feature-slug>/tickets/tickets-<feature-slug>-<NN>.md`，按依赖顺序从 `01` 编号（阻塞者优先）。每张的“被谁阻塞”列出依赖的编号/标题；使用下方每 Ticket 模板，绝不合成一个总文件。
- **`external`** → 先按依赖顺序预览每张 Ticket；得到明确确认后依次创建，以便阻塞边引用真实标识。若平台支持，使用原生 blocking/sub-issue 关系；否则写入阻塞 Issue。只使用项目配置的标签。
- **`project-docs`** → 先展示符合项目既有格式的补丁，确认后写入。
- **`none`** → 只在会话中输出。

处理 **frontier**：所有阻塞者都完成的 Ticket。纯线性链即从上到下。

不要关闭或修改任何父 Issue。

<local-ticket-template>

```yaml
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
execution_agent: <codex|cursor|claude>
---
```

# <NN> — <Ticket 标题>

**要构建什么：** 从用户视角描述该 Ticket 端到端实现的行为，而非逐层实现清单。

## 适用规则与影响区域

- 规则来源：
- 影响区域：
- 实施约束：
- 验证：

`blocked_by` 必须填 YAML 列表，使用已创建 Ticket 的唯一 id、路径或标题；无阻塞时保留 `[]`。领取时仅填写 `claimed_by`，完成阻塞 Ticket 时将其 `status` 设为 `complete`。不要依靠正文状态行或猜测旧 Ticket 的类型。

`spec_id`、`spec_revision` 与 `spec_ref` 是实施准入字段。修订既有 Ticket 时，`supersedes_ticket` 指向被替代的未完成 Ticket；补偿已完成工作时用 `compensates` 指向历史 Ticket，新 Ticket 自身仍绑定当前 Spec revision。

## 验收标准

- [ ] 验收标准 1
- [ ] 验收标准 2

关闭前勾选全部验收项；进入实施前必须通过安装状态记录的 `runtime_entry` 运行 `validate-ticket <ticket-path>`。本地准入、引用校验与排序由 [Ticket 准入与选择](references/shared/adapters/ticket-selection.md) 执行。

</local-ticket-template>

<issue-template>

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

</issue-template>

无论采用何种形式，都避免具体文件路径和代码片段，它们很快会过期。例外是原型产生了比文字更精确的决策片段（状态机、reducer、schema、类型形状）：可内嵌并简要标注来自原型，但只保留决策丰富部分，而非可运行 demo。
