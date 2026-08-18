---
name: my-ask-matt
description: 判断当前情境适合哪个个人 Matt Skill 或工作流。
disable-model-invocation: true
---

# 询问 Matt

不必记住每个 Skill；不确定时就问。

**工作流**是穿过多个 Skill 的路径。大部分路径沿着一条**主流程**前进，另有两个入口汇入它；其余要么独立，要么是下层共用词汇。

本 Skill 是路由索引。读取 `.agent/matt-workflow.md` 的 `composition_policy`，并遵循[组合调用](references/shared/adapters/composition.md)：选出下一跳后，Cursor / Claude 输出 `/my-<skill>`，Codex 输出 `$my-<skill>`，随后停止。不要在本 Skill 内执行被选 Skill 的方法正文；路由入口只命名，不打包。

## 主流程：想法 → 交付

这是多数工作经过的路线：你有一个想法，想把它做出来。

1. **`my-grill-with-docs`**——通过访谈把想法打磨清楚。有**代码库**时从这里开始：它会保留在领域术语和 ADR 中学到的内容。（没有代码库？使用 `my-grill-me`——见“独立使用”。两者都使用同一个 `my-grilling` 基础流程；前者会留下可追溯记录。）
2. **分支——所有问题都能靠对话解决吗？** 如果一个问题需要可运行的答案（状态、业务逻辑、必须亲眼看到的 UI），先绕到原型；两个方向都由 **`my-handoff`** 衔接（见“跨会话”）：
   - 用 **`my-handoff`** 导出，然后针对该文件开启新会话；
   - 用 **`my-prototype`** 以一次性代码回答问题；
   - 再用 **`my-handoff`** 带回学到的内容，并从原想法线程引用它。
3. **分支——这是跨多个会话的构建吗？**
   - **是** → 使用 **`my-to-spec`** 将当前线程变成 Spec，再用 **`my-to-tickets`** 拆成 tracer-bullet Ticket；每张 Ticket 都声明其**阻塞边**。本地后端时每张 Ticket 保存在 `.agent/work/<feature>/tickets/tickets-<feature>-<NN>.md`，按阻塞优先完成；真实 Tracker 时使用原生阻塞链接，因此任何已解除阻塞的 Ticket 都可领取。`my-implement` 按已解析的 `work_scope_policy` 领取 frontier。用户说「继续 / 提交并继续」不升档、不放宽该策略。
   - **否** → 在当前上下文直接使用 **`my-implement`**。

无论哪种情况，**`my-implement`** 都会按每次一个 red-green 切片驱动 **`my-tdd`**，并在提交前运行 **`my-code-review`**，从 Standards 与 Spec 两个轴审查 diff。只想以测试先行构建一个明确行为时，可单独使用 **`my-tdd`**；想针对固定基线审查分支或 PR 时，可单独使用 **`my-code-review`**。

### 上下文卫生

访谈、Spec、Ticket 与交接的阶段边界遵循[上下文卫生](references/policies/context-hygiene.md)。若会话在 `my-to-tickets` 前接近该限制，不要在降级状态硬撑；使用 `my-handoff` 并在新线程继续。

## 入口

入口是会产生工作、随后汇入主流程的起始情境。

- **Bug 和需求堆积** → **`my-triage`**。它让请求经过分诊角色，产出以后由 **`my-implement`** 接手的 agent-ready Ticket。Triage 只处理**不是你创建的**请求：外部 Bug 报告、进入的功能需求与一切原始请求。`my-to-tickets` 生成的 Ticket 已是 agent-ready，**不要**再 triage。
- **某件事坏了** → **`my-diagnosing-bugs`**。用于难解问题、间歇性故障和回归。它在拥有一个能让**此 Bug**变红的紧密反馈循环前拒绝空想；随后用回归测试修复。若事后发现没有可锁定 Bug 的合适 seam，则交给 **`my-improve-codebase-architecture`**。
- **正在解决 merge 或 rebase 冲突** → **`my-resolving-merge-conflicts`**。先审阅各方意图、逐项解决方案、验证和回滚路径，明确批准后才修改本地冲突。
- **答案只能由外部知情人提供** → **`my-to-questionnaire`**。它把澄清流程中的知识缺口写成可异步填写的发现问卷；生成问卷不等于发送，外发仍需确认。
- **需要人工完成第三方配置或一次性迁移** → **`my-wizard`**。它生成逐步确认、秘密不回显的本地向导。
- **需要重组或润色文章** → **`my-edit-article`**。先确认章节方案，默认生成新稿并保留原稿。
- **叙述读起来像 AI** → **`my-humanizer`**。先区分可改叙述与冻结契约，再去 AI 腔；不影响 Agent 执行。
- **巨大且迷雾重重的工作**——绿地项目或超出单会话的大功能 → **`my-wayfinder`**。它在 Tracker 上绘制共享的**决策 Ticket**地图，每次解决一个，产出的是**决策而不是交付物**，直到道路清晰。它比 `my-grill-with-docs` 更慢、更密，后者适合单会话可把握的想法；不要把 well-scoped 功能送进 wayfinder。

  地图清晰后，它**交接而不构建**：在 `my-to-spec` 汇入主流程，将关联决策压缩成可构建计划，再照常 `my-to-tickets` 与 `my-implement`。直接从地图跳到 `my-implement` 会丢弃关联细节；只有工作实际很小时才可直接实现。

## 代码库健康

这不是功能工作，而是维护。

- **`my-improve-codebase-architecture`**——有空就运行，让代码库持续适合 Agent 操作。它找出可加深的机会；选中一个会产生可带回 `my-grill-with-docs` 主流程的想法。这是发现候选的巡检；下面的 **`my-codebase-design`** 才是设计该候选的工作台。

## 下层词汇

两个可作为共用参考的 Skill 在其他 Skill 下方运行，各自是其词汇的唯一真相来源。当问题是**用词**而非流程时直接使用；否则由上层 Skill 拉入。

- **`my-domain-modeling`**——打磨项目的领域语言：挑战模糊术语、解决一词多义（如 “account” 承担三个含义），并把难以逆转的决策记录为 ADR。`my-grill-with-docs` 用它维持干净术语表。
- **`my-codebase-design`**——深模块词汇（module、interface、depth、seam、adapter、leverage、locality），用于设计模块形状：在干净 seam 后以小接口隐藏大量行为。`my-tdd` 与 `my-improve-codebase-architecture` 都使用这些词。

## 跨会话

- **`my-handoff`**——当线程已满或必须分支（例如进入 `my-prototype` 会话）时，将当前对话压缩为 Markdown。不要原地继续；开启新会话并引用该文件来携带上下文。它是两个上下文窗口之间、两个方向均可用的桥梁。
- **`/compact`**（内置）——留在**同一对话**，让较早回合被总结。只在阶段间的有意断点使用，并接受丢失逐字历史；不要在阶段中间 compact，否则 Agent 可能迷失。`my-handoff` 是分叉；`/compact` 是延续。

## 独立使用

- **`my-grill-me`**——与 `my-grill-with-docs` 相同的高强度访谈，但用于**没有代码库**的场景。它无状态、不保存本地内容；适合打磨任何不属于仓库的计划或设计。
- **`my-prototype`**——回答一个设计问题的小型一次性程序：这个状态模型是否合理，或 UI 应该是什么样。第一天起就把它视为可丢弃物：保留答案，删除代码。它是主流程第 2 步的绕行，也可用于任何难以在纸面定论的设计问题。
- **`my-research`**——把阅读工作委托给后台 Agent：它查阅一手来源，再在仓库留下带引用的 Markdown。阅读期间继续工作。其结果应带回 `my-grill-with-docs` 主流程；研究为思考提供材料，不取代思考。
- **`my-teach`**——围绕当前目录这个有状态学习工作区跨会话学习概念。
- **`my-writing-great-skills`**——编写和编辑优秀 Skill 的参考。

## 前置条件

在首次工程流程前运行 **`my-setup`**，配置其他工程 Skill 假设存在的 Tracker、triage 标签与文档布局。也支持自定义 Tracker。
