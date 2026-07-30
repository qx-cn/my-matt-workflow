---
name: my-wayfinder
description: 为超出单会话容量的模糊工作建立逐步消除未知的决策地图
disable-model-invocation: true
---

# My Wayfinder

一个松散想法到来：它大到单个 Agent 会话装不下，又被迷雾包围——从这里到**目的地**的路还不可见。Wayfinding 的目标是找到那条路，而非直接冲向目的地。它把路径绘为共享的**决策地图**，再一次处理一个**决策 Ticket**（其解决结果是一个决定，而非待执行的构建切片），直到路线清晰。

每项工作有不同目的地，命名它是绘图的第一步，因为它塑造每个 Ticket。目的地可以是待移交并迭代的 Spec、规划开始前必须确定的决定，或数据结构迁移等就地变更。地图与领域无关：工程工作、课程内容或任何符合此形状的事项都适用。

## 规划，而不是交付

默认情况下，Wayfinder 是**规划**：每个 Ticket 解决一个决定；当通往目的地的路已经清楚、再无待决定的事项时，地图完成。想直接去做工作的冲动通常意味着已经到了地图边缘，应交给下一步工作流。某个 initiative 可在其**备注**中明确将执行带入地图；否则只产出决定，不直接交付最终成果。

## 始终用名称引用

每张地图和每个 Ticket 都有**名称**（标题）。所有给人阅读的内容——叙述和“已作决定”——都用名称引用，不用裸 ID、编号或 slug。一串 `#42`、`#43`、`#44` 无法阅读；名称可一眼理解。ID 和 URL 不会消失，而是包裹在名称的链接中，绝不能替代名称。

## 地图

项目配置了 Tracker 时，地图是该 Tracker 中标签为 `wayfinder:map` 的单一 Issue，是规范工件；其 Ticket 是地图的子 Issue。具体的子任务、阻塞关系与 frontier 查询方式依项目 Tracker 而定：读取 `.agent/matt-workflow.md` 中的配置与团队文档。

没有 Tracker 时，地图位于 `.agent/work/<initiative>/wayfinders/wayfinders-<initiative>-<time-or-sequence>.md`，Ticket 位于 `.agent/work/<initiative>/tickets/tickets-<initiative>-<time-or-sequence>.md`。地图与 Ticket 的文件名都必须同时包含类型、initiative 与可排序键；人与人之间仍以标题引用。地图是**索引**，不是内容仓库：它只摘要并链接已解决 Ticket；每个决定的详细内容只存在于一个 Ticket 中。

读取本地地图或 Ticket 时，遵循 [工作产物访问](references/shared/adapters/artifact-access.md)。

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

每个 Ticket 标记 `wayfinder:<type>`，类型为 `research`、`prototype`、`grilling` 或 `task`（见[Ticket 类型](#ticket-类型)）。这些 Ticket 的 `ticket_kind` 永远是 `wayfinder-decision`；不得改成 implementation 或交给 `my-implement`。产品取舍必须保留给用户，见[决策分类](references/policies/decision-taxonomy.md)。

会话开始时先**认领**一个 Ticket，再做任何工作：Tracker 中将其分配给当前负责人；本地 Ticket 标明认领会话、时间与负责人。未关闭、未认领的 Ticket 才可认领，以避免并行会话重复工作。

阻塞优先使用 Tracker 原生依赖关系，因为其 UI 可直观显示 frontier；只有 Tracker 没有原生阻塞时才在正文记录。本地模式在 Ticket frontmatter 或“阻塞于”章节记录。所有阻塞 Ticket 关闭后，该 Ticket 才**未受阻塞**；**frontier** 是开放、未受阻塞、未认领的子 Ticket 集合，即已知工作的边缘。

答案不属于 Ticket 正文，而是在解决时记录。解决期间产生的资产只从 Ticket 链接，不粘贴进去。

## Ticket 类型

每个 Ticket 都是 **HITL**（由能代表自己意见的人实时参与）或 **AFK**（Agent 单独驱动）。HITL Ticket 只能经实时交流解决；Agent 不能代替用户回答其一侧的问题，否则该过程已经失效。

- **研究（AFK）**：阅读文档、第三方 API 或本地知识库，找出决定所等待的事实。使用 `my-research`；需要并行时，按 `composition_policy` 启动研究子 Agent。仅当当前工作目录以外的知识确实必要时使用。
- **原型（HITL）**：制作廉价、粗糙而具体的可反应工件，以提高讨论保真度，例如大纲、粗略方案、stub，或通过 `my-prototype` 生成 UI/逻辑代码。Ticket 链接原型作为资产。适合“应该长什么样”或“应该如何行为”是关键问题时。
- **访谈（HITL）**：通过 `my-grilling` 和 `my-domain-modeling` 一次一个问题地讨论；这是默认类型。
- **任务（HITL 或 AFK）**：做出决定前必须完成的手动工作。此时没有可决定、可原型化或可研究的事情，但工作不完成讨论就被阻塞：注册服务以评估 API、配置访问权限、迁移数据以观察形状等。它是唯一“做事”而非“决定”的类型，因解除决定阻塞而存在，并不交付目的地。Agent 能独立执行时按 AFK 处理；否则提供精确的 HITL 清单。工作完成时解决；答案记录完成事项及后续 Ticket 依赖的事实（凭据位置、新 URL、行数等），但不暴露敏感数据。

## 战争迷雾

地图应**刻意不完整**：尚未看清的内容不要绘制。当前 Ticket 之外是**战争迷雾**——能察觉它们将到来，却因依赖未解决问题而无法精确定义的决定和调查。解决一个 Ticket 会清除其前方迷雾，将已经可表述的内容逐个提升为新 Ticket，直到通往目的地的路径清晰、没有 Ticket 留下。

地图“尚未明确”记录这片朦胧视野：疑似问题和未来需要回看的区域。它是通往目的地、尚在范围内却不够清晰的 frontier；按现有视野粗细记录即可，也让协作者理解工作将去向何方。

**迷雾还是 Ticket？** 判断标准是现在能否精确陈述问题，**不是**现在能否回答它：

- 问题已经清晰时创建 **Ticket**，即使它被阻塞、当前无法处理。
- 还无法如此清晰地表述时放入**尚未明确**。不要把迷雾预切成 Ticket 大小：它比 Ticket 粗糙，一个已解决问题可能让它变成多个 Ticket，也可能一个都不需要。

“尚未明确”不包括已决定事项、已存在的开放 Ticket 或范围外事项。

## 范围外

迷雾只会向**目的地**聚集。目的地确定范围，因此超出它的工作属于**范围外**，不是迷雾，也不应放进“尚未明确”。在地图单独的“范围外”章节记录：它们被有意识地排除在本次工作之外。范围而非清晰度决定它属于此处。

范围外工作永不转化——frontier 在目的地停止。它只有在目的地被重绘时才会回来，并且是新的 initiative，而非恢复原工作。

将事项排除在范围外是范围界定，不是路线步骤。若已有 Ticket 后来发现超出目的地（绘图时误纳入，或通过一次解决才暴露），关闭它，并在“范围外”留一行：摘要、为何排除，以及该关闭 Ticket 的链接。不要把它放入“已作决定”，后者只记录实际走过的路线；范围边界不是其中一步。

## 调用方式

有两种模式。除研究 Ticket 外，**每个会话绝不解决多于一个 Ticket**。依赖调用和地图完成后的交接遵循 [组合调用](references/shared/adapters/composition.md)。

需要依赖时，只加载当前阶段所需的已打包参考：[my-grilling](references/composed/my-grilling/SKILL.md)、[my-domain-modeling](references/composed/my-domain-modeling/SKILL.md)、[my-research](references/composed/my-research/SKILL.md)、[my-prototype](references/composed/my-prototype/SKILL.md) 或 [my-to-spec](references/composed/my-to-spec/SKILL.md)；自动或手动的调用及停止规则由组合适配决定。

### 绘制地图

用户带着一个松散想法调用时：

1. **命名目的地。** 使用 `my-grilling` 与 `my-domain-modeling` 澄清本地图要找到的 Spec、决定或变更；目的地决定范围，必须最先确定。
2. **绘制 frontier。** 再做一次访谈，这次按**广度优先**：展开整个空间，而非深挖某条线，找出开放决定与现在可做的第一步。若完全没有迷雾，意味着目的地路径已清晰且可在一会话内完成；不必创建地图，按 `decision_policy` 询问后续方式或在无人值守计划中记录建议。
3. **创建地图**：Tracker 模式加 `wayfinder:map` 标签；本地模式创建 `wayfinders-<initiative>-<time-or-sequence>.md`。填写目的地与备注，“已作决定”留空，在“尚未明确”勾勒迷雾。外部 Tracker 写入按项目写入策略处理。
4. **创建现已可表述的 Tickets**：作为地图子 Issue 或本地 Ticket 文件；再进行**第二轮**连接阻塞边，因为 Ticket 要先有 ID / 路径才能互相引用。其余不能表述的内容仍留在“尚未明确”。
5. **启动研究。** 对每个新建 `research` Ticket，按 `composition_policy` 选择串行执行 `my-research`，或启动研究子 Agent 并行解决；将其发现链接回 Ticket，原始研究工件存放于 `.agent/work/<initiative>/researches/researches-<initiative>-<time-or-sequence>.md`。不得自动建分支、Commit 或外传资料。
6. **停止。** 绘图只是一个会话的工作，本会话不亲自解决其他 Ticket。

### 沿地图工作

用户带着地图（URL、ID 或本地路径）调用时，Ticket 是可选的；未指定则由本 Skill 选择下一个决定。

1. 加载**地图**这个低分辨率视图，不加载每个 Ticket 正文。
2. 选择 Ticket：用户指定时使用它；否则按顺序选第一个 frontier Ticket。任何工作前先**认领**。
3. 解决它，并按需要放大：按需读取有关或已关闭 Ticket 的全文；调用“备注”中列出的 Skill。不确定时使用 `my-grilling` 与 `my-domain-modeling`。
4. 记录解决结果：将答案写为解决记录，关闭 Ticket，并在地图“已作决定”追加一个上下文指针。Tracker 模式创建评论、关闭和更新地图都必须遵守项目外部写入策略；本地模式写入 `.agent/work/`。
5. 增加新浮现的 Tickets（先创建再连线），把答案已使其清晰的迷雾提升为 Ticket，并从“尚未明确”清掉每一块已提升内容，使它只存在于新 Ticket。若答案发现本 Ticket 或其他 Ticket 超出目的地，将它列为范围外而不是作为路线结果解决。若该决定使地图其他部分失效，更新或关闭它们。

多个会话可以并行处理未受阻塞的 Ticket，预期其他会话会同时更新 Tracker 或本地地图；在写入前重新读取相关状态，避免覆盖他人结论。

地图清晰且当前已批准流程包含 Spec 阶段时，`automatic` 读取并遵守已打包的 `my-to-spec` 参考继续；`manual` 按上述方式提示显式调用并停止。当前流程未批准下一阶段时只建议，不扩展范围；不得直接跳到实现。
