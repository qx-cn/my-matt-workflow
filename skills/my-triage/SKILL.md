---
name: my-triage
description: 通过分诊角色的状态机推进 Issue 和外部 PR：分类、验证、按需追问，并编写可供 Agent 执行的简报。
disable-model-invocation: true
---

# 分诊

通过一小组分诊角色构成的状态机，推进项目 Issue 跟踪器中的事项。

如果此仓库将外部 Pull Request 视为请求入口（见 Issue 跟踪器配置），分诊也涵盖它们：**PR 是附带代码的 Issue**——使用相同的角色、状态和状态机，只在下文标注“针对 PR”的地方有所差异。依据跟踪器配置，将裸 `#42` 解析为 Issue 或 PR。

分诊期间发布到 Issue 跟踪器的每一条评论或 Issue **都必须**以以下免责声明开头：

```
> *此内容由 AI 在分诊期间生成。*
```

## 参考文档

- [AGENT-BRIEF.md](AGENT-BRIEF.md) —— 如何编写经久可用的 Agent 简报
- [OUT-OF-SCOPE.md](OUT-OF-SCOPE.md) —— `.out-of-scope/` 知识库的工作方式

## 角色

两种**类别**角色：

- `bug` —— 有功能损坏
- `enhancement` —— 新功能或改进

五种**状态**角色：

- `needs-triage` —— 需要维护者评估
- `needs-info` —— 等待报告者补充信息
- `ready-for-agent` —— 已完整说明，可交给离线 Agent
- `ready-for-human` —— 需要人工实现
- `wontfix` —— 不会执行

针对 PR，同样的状态要结合其附带代码理解：`ready-for-agent` 表示已附上简报，Agent 应对该 diff 执行下一步；`ready-for-human` 表示已可由人工合并。

每个已分诊的 Issue 都应恰好带有一个类别角色和一个状态角色。如果状态角色冲突，先标出冲突并询问维护者，不得执行其他操作。

这些是规范角色名称——Issue 跟踪器中实际使用的标签字符串可能不同。映射应已提供给你；若未提供，请运行 `/setup-matt-pocock-skills`。

状态转换：未标记的 Issue 通常先进入 `needs-triage`；随后可转为 `needs-info`、`ready-for-agent`、`ready-for-human` 或 `wontfix`。报告者回复后，`needs-info` 返回 `needs-triage`。维护者可随时覆盖——标出看起来异常的转换，并在继续前询问。

## 本地 Ticket 门卫

`my-to-tickets` 已创建的结构化 implementation Ticket 不进入 triage；`wayfinder-decision` 和 `wayfinder:*` Ticket 只保留为用户决策，也不进入 triage。若分诊结果需要保存到本地，使用以下 `ready-for-agent` 模板，且只在维护者确认分类和状态后写入：

```yaml
---
id: <topic>-<NN>
title: <可执行标题>
ticket_kind: implementation
status: ready-for-agent
blocked_by: []
claimed_by:
tags: []
sequence: <NN>
---
```

`blocked_by` 必须是 YAML 列表；旧 Ticket 缺少 `ticket_kind` 时按歧义处理，不猜测。可实现性、引用与完成门禁均由 [Ticket 准入与选择](references/shared/adapters/ticket-selection.md) 判断。

## 调用

维护者调用 `/triage`，并用自然语言描述想做什么。理解该请求后执行。示例：

- “显示所有需要我关注的事项”
- “我们看看 #42”（Issue 或 PR）
- “将 #42 移到 ready-for-agent”
- “哪些事项已可供 Agent 领取？”

## 显示需要关注的事项

查询 Issue 跟踪器，并按从旧到新的顺序展示三个桶：

1. **未标记** —— 从未分诊。
2. **`needs-triage`** —— 正在评估。
3. **报告者自上次分诊记录以来有活动的 `needs-info`** —— 需要重新评估。

当 PR 在范围内时，将外部 PR 包含在这些桶中，并为每一行标记 `[PR]` 或 `[issue]`。发现阶段只展示*外部* PR（跟踪器配置定义谁属于外部）；协作者正在进行中的 PR 不是分诊工作。该过滤仅适用于发现；无论作者是谁，始终分诊被明确点名的 PR。

显示数量及每项一行摘要。让维护者选择。

## 分诊特定 Issue 或 PR

1. **收集上下文。** 阅读完整的 Issue 或 PR（正文、评论、标签、作者、日期；PR 还要读 diff）。解析既有分诊记录，避免重新询问已解决的问题。借助项目的领域词汇表探索代码库，遵循该区域的 ADR。对代码库执行两项检查：(a) **冗余性**——按领域概念（而不只是请求的措辞）搜索是否已有请求行为的实现，并报告搜索位置。若已存在，它是“已实现”的 `wontfix`（步骤 5）。(b) **既往拒绝**——阅读 `.out-of-scope/*.md`，并找出与本请求相似的记录。
2. **提出建议。** 告知维护者类别和状态建议及理由，并给出与请求相关的简要代码库摘要——包括是否已实现。等待指示。
3. **验证主张。** 在追问前，先检查主张是否成立。对于 Bug，按报告者的步骤复现。对于 PR，确认 diff 是否实现其声称的内容——检出它，并运行相关测试或命令。报告结果：已确认（附代码路径）、失败，或细节不足（这是强烈的 `needs-info` 信号）。已确认的验证会形成更有力的 Agent 简报。
4. **追问（如需要）。** 若请求还需充实，同时运行 `/grilling` 与 `/domain-modeling` Skill——每次提出一个问题以将其打磨清楚，明确领域术语，并在决策达成时内联更新 `CONTEXT.md`/ADR。
5. **应用结果：**
   - `ready-for-agent` —— 发布 Agent 简报评论（[AGENT-BRIEF.md](AGENT-BRIEF.md)）。
   - `ready-for-human` —— 使用与 Agent 简报相同的结构，但说明为何不可委派（判断调用、外部访问、设计决策、手动测试）。
   - `needs-info` —— 发布分诊记录（见下方模板）。
   - `wontfix` —— 关闭，评论取决于*原因*：
     - **已实现** —— 变更已存在于代码库。指出所在位置；**不要**写入 `.out-of-scope/`（该知识库记录的是*被拒绝*的请求，而不是已构建的功能）。
     - **被拒绝（Bug）** —— 礼貌说明后关闭。
     - **被拒绝（增强）** —— 写入 `.out-of-scope/`，从评论链接到它，再关闭（[OUT-OF-SCOPE.md](OUT-OF-SCOPE.md)）。
   - `needs-triage` —— 应用该角色。若有部分进展，可选地发表评论。

## 快速状态覆盖

若维护者说“将 #42 移到 ready-for-agent”，信任他们并直接应用角色。确认即将执行的操作（角色变更、评论、关闭），然后执行。跳过追问。若在没有追问会话的情况下移至 `ready-for-agent`，询问他们是否想编写 Agent 简报。

## 需要更多信息模板

```markdown
## 分诊记录

**我们目前已确认的内容：**

- 要点 1
- 要点 2

**仍需要你（@reporter）提供的内容：**

- 问题 1
- 问题 2
```

将在追问期间已解决的所有内容记在“目前已确认的内容”下，避免丢失工作。问题必须具体且可操作，不能写成“请提供更多信息”。

## 恢复之前的会话

若 Issue 或 PR 上存在既有分诊记录，阅读它们，检查报告者是否已回答未解决的问题，并在继续前给出更新后的全貌。不得重新询问已解决的问题。
