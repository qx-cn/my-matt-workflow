---
name: my-to-tickets
description: 将计划、Spec 或当前对话拆成 tracer-bullet Ticket；每张声明阻塞边，并按项目配置保存或发布。
disable-model-invocation: true
---

# 拆分 Ticket

把计划、Spec 或对话拆成一组 **Ticket**：每张都是 tracer-bullet 纵向切片，并声明**阻塞**它的 Ticket。

读取 `.agent/matt-workflow.md`（含生效的 `humanizer_policy`）；缺失时先运行 `/my-setup`。

## 过程

### 1. 收集上下文

使用当前对话中已有的内容。若用户传入引用（Spec 路径、Issue 号或 URL），获取并阅读全文与评论。

### 2. 探索代码库（可选）

若尚未探索代码库，则探索以理解当前状态。Ticket 标题和描述应使用项目领域术语，并遵守相关 ADR。

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

### 4. 询问用户

将建议拆分以编号列表展示。每张 Ticket 都展示：

- **标题**：简短描述名称；
- **被谁阻塞**：必须先完成的其他 Ticket（如有）；
- **交付什么**：该 Ticket 端到端实现的行为。

询问用户：粒度是否合适（太粗/太细）；阻塞边是否正确且只依赖真正的门槛；是否要合并或再拆分。反复迭代直至用户批准。

### 5. 保存或发布已批准 Ticket

**写入前**：按 [humanizer](references/shared/humanizer.md) 服从 `humanizer_policy`，再按配置后端保存：

- **`local`** → 每张文件写入 `.agent/work/<feature-slug>/tickets/tickets-<feature-slug>-<NN>.md`，按依赖顺序从 `01` 编号（阻塞者优先）。每张的“被谁阻塞”列出依赖的编号/标题；使用下方每 Ticket 模板，绝不合成一个总文件。
- **`external`** → 先按依赖顺序预览每张 Ticket；得到明确确认后依次创建，以便阻塞边引用真实标识。若平台支持，使用原生 blocking/sub-issue 关系；否则写入阻塞 Issue。只使用项目配置的标签。
- **`project-docs`** → 先展示符合项目既有格式的补丁，确认后写入。
- **`none`** → 只在会话中输出。

处理 **frontier**：所有阻塞者都完成的 Ticket。纯线性链即从上到下。

不要关闭或修改任何父 Issue。

<local-ticket-template>

# <NN> — <Ticket 标题>

**要构建什么：** 从用户视角描述该 Ticket 端到端实现的行为，而非逐层实现清单。

**被谁阻塞：** 阻塞本 Ticket 的编号/标题，或“无——可立即开始”。

**状态：** ready-for-agent

- [ ] 验收标准 1
- [ ] 验收标准 2

</local-ticket-template>

<issue-template>

## 父项

对 Tracker 父 Issue 的引用（源是现有 Issue 时才保留；否则省略本节）。

## 要构建什么

从用户视角描述该 Ticket 端到端实现的行为，而非逐层实现。

## 验收标准

- [ ] 标准 1
- [ ] 标准 2

## 被谁阻塞

- 每张阻塞 Ticket 的引用，或“无——可立即开始”。

</issue-template>

无论采用何种形式，都避免具体文件路径和代码片段，它们很快会过期。例外是原型产生了比文字更精确的决策片段（状态机、reducer、schema、类型形状）：可内嵌并简要标注来自原型，但只保留决策丰富部分，而非可运行 demo。
