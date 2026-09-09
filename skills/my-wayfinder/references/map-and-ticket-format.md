# 地图与 Ticket 格式

项目配置了 Tracker 时，地图是该 Tracker 中标签为 `wayfinder:map` 的单一 Issue，是规范工件；其 Ticket 是地图的子 Issue。具体的子任务、阻塞关系与 frontier 查询方式依项目 Tracker 而定：读取 `.agent/matt-workflow.md` 中的配置与团队文档。

没有 Tracker 时，地图位于 `.agent/work/<initiative>/wayfinders/wayfinders-<initiative>-<time-or-sequence>.md`，Ticket 位于 `.agent/work/<initiative>/tickets/tickets-<initiative>-<time-or-sequence>.md`。地图与 Ticket 的文件名都必须同时包含类型、initiative 与可排序键；人与人之间仍以标题引用。地图是**索引**，不是内容仓库：它只摘要并链接已解决 Ticket；每个决定的详细内容只存在于一个 Ticket 中。

读取本地地图或 Ticket 时，遵循 [工作产物访问](shared/adapters/artifact-access.md)。

每个会话只加载一次低分辨率地图。开放 Ticket 不列在地图正文；在 Tracker 中由查询发现，在本地由 `tickets/` 中带有开放状态的文件发现。

```markdown
## 目的地

<完成地图意味着什么：本次工作所要找到的 Spec、决定或变更。用一两行描述；每次会话在选择 Ticket 前都先对齐它。>

## 备注

<领域；每次会话应查阅的 Skill；本 initiative 的长期偏好>

## 已作决定

<!-- 索引：每个关闭 Ticket 一行，足以判断相关性；细节在其链接中 -->

- [<已关闭 Ticket 标题>](link) — <答案的一行摘要>

## 尚未明确

<!-- 仍在范围内、却还不能写成 Ticket 的迷雾；frontier 推进后才转化 -->

## 范围外

<!-- 被明确排除在目的地之外的工作；已关闭，且永不转化 -->
```

### Tickets

每个 Ticket 都是地图的子 Issue，或是本地 `tickets/` 下的一个文件；其正文只写一个可在约一个 100K token Agent 会话内解决的问题：

```markdown
---
id: <initiative>-<NN>
title: <决策 Ticket 标题>
ticket_kind: wayfinder-decision
status: open
blocked_by: []
claimed_by:
tags:
  - wayfinder:<research|prototype|grilling|task>
sequence: <NN>
---

# <决策 Ticket 标题>

## 问题

<本 Ticket 要解决的决定或调查>
```

每个 Ticket 标记 `wayfinder:<type>`，类型为 `research`、`prototype`、`grilling` 或 `task`（见[Ticket 类型](#ticket-类型)）。这些 Ticket 的 `ticket_kind` 永远是 `wayfinder-decision`；不得改成 implementation 或交给 `my-implement`。产品取舍必须保留给用户，见[决策分类](policies/decision-taxonomy.md)。

会话开始时先**认领**一个 Ticket，再做任何工作：Tracker 中将其分配给当前负责人；本地 Ticket 标明认领会话、时间与负责人。未关闭、未认领的 Ticket 才可认领，以避免并行会话重复工作。

阻塞优先使用 Tracker 原生依赖关系，因为其 UI 可直观显示 frontier；只有 Tracker 没有原生阻塞时才在正文记录。本地模式在 Ticket frontmatter 或“阻塞于”章节记录。所有阻塞 Ticket 关闭后，该 Ticket 才**未受阻塞**；**frontier** 是开放、未受阻塞、未认领的子 Ticket 集合，即已知工作的边缘。

答案不属于 Ticket 正文，而是在解决时记录。解决期间产生的资产只从 Ticket 链接，不粘贴进去。

## Ticket 类型

每个 Ticket 都是 **HITL**（由能代表自己意见的人实时参与）或 **AFK**（Agent 单独驱动）。HITL Ticket 只能经实时交流解决；Agent 不能代替用户回答其一侧的问题，否则该过程已经失效。

- **研究（AFK）**：阅读文档、第三方 API 或本地知识库，找出决定所等待的事实。使用 `my-research`；需要并行时，按 `composition_policy` 启动研究子 Agent。仅当当前工作目录以外的知识确实必要时使用。
- **原型（HITL）**：制作廉价、粗糙而具体的可反应工件，以提高讨论保真度，例如大纲、粗略方案、stub，或通过 `my-prototype` 生成 UI/逻辑代码。Ticket 链接原型作为资产。适合“应该长什么样”或“应该如何行为”是关键问题时。
- **访谈（HITL）**：通过 `my-grilling` 和 `my-domain-modeling` 一次一个问题地讨论；这是默认类型。
- **任务（HITL 或 AFK）**：做出决定前必须完成的手动工作。此时没有可决定、可原型化或可研究的事情，但工作不完成讨论就被阻塞：注册服务以评估 API、配置访问权限、迁移数据以观察形状等。它是唯一“做事”而非“决定”的类型，因解除决定阻塞而存在，并不交付目的地。Agent 能独立执行时按 AFK 处理；否则提供精确的 HITL 清单。工作完成时解决；答案记录完成事项及后续 Ticket 依赖的事实（凭据位置、新 URL、行数等），但不暴露敏感数据。
