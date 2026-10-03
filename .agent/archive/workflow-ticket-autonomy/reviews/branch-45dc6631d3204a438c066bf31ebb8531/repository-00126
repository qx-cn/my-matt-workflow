---
name: my-triage
description: 通过分诊角色的状态机推进 Issue 和外部 PR：分类、验证、按需追问，并编写可供 Agent 执行的简报。
disable-model-invocation: true
---

# 分诊

通过一小组分诊角色构成的状态机，推进项目 Issue 跟踪器中的事项。

面向报告者或维护者写评论时，按[面向读者写作](references/shared/reader-first-writing.md)先给已确认事实、具体缺口、需要它的原因和下一动作；Agent 简报继续按自身格式编写。

如果此仓库将外部 Pull Request 视为请求入口（见 Issue 跟踪器配置），分诊也涵盖它们：**PR 是附带代码的 Issue**——使用相同的角色、状态和状态机，只在下文标注“针对 PR”的地方有所差异。依据跟踪器配置，将裸 `#42` 解析为 Issue 或 PR。

分诊期间发布到 Issue 跟踪器的每一条评论或 Issue **都必须**以以下免责声明开头：

```
> *此内容由 AI 在分诊期间生成。*
```

## 参考文档

- [AGENT-BRIEF.md](AGENT-BRIEF.md) —— 如何编写经久可用的 Agent 简报
- [OUT-OF-SCOPE.md](OUT-OF-SCOPE.md) —— `.out-of-scope/` 知识库的工作方式

## 角色

先按后端分支：以下标签角色与 Tracker 状态转换用于外部 Tracker。local brief 只使用本地类别/状态语义，不要求外部标签映射；本地 workflow 配置缺失时才按后端段完成 setup。

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

这些是外部 Tracker 的规范角色名称，真实标签映射从该 Tracker 的配置、已有有效标签或维护者取得；缺少时只请求所缺映射，不调用只配置 local workflow 的 setup 代替它。

状态转换：未标记的 Issue 通常先进入 `needs-triage`；随后可转为 `needs-info`、`ready-for-agent`、`ready-for-human` 或 `wontfix`。报告者回复后，`needs-info` 返回 `needs-triage`。维护者可随时覆盖——标出看起来异常的转换，并在继续前询问。

## 后端边界

`my-to-tickets` 已创建的结构化 implementation Ticket 不进入 triage；`wayfinder-decision` 和 `wayfinder:*` Ticket 也不进入 triage。

- **外部 Tracker**：保留 Tracker 原生的类别、状态、评论与 Agent brief；`ready-for-agent` 仍表示该外部事项已附上可执行简报。
- **本地后端**：triage 不自行伪造 implementation Ticket。维护者确认分类、状态与 brief 后，把确认后的 brief、原请求路径或 URL、评论/附件来源和验证证据保存到 `.agent/work/<topic>/triage/triage-<topic>-<time-or-sequence>.md`。只要求分诊或 brief 时保存后交付，不自动开开发。下一阶段已授权时读取[保证等级](references/shared/adapters/assurance-levels.md)，复用已确认等级与摘要；缺本地 workflow 配置时输出 {{skill-call:my-setup}} 下一跳并停止，保留原请求与 confirmed brief；配置完成后恢复本分诊入口，不把 setup 当作外部 Tracker 映射修复。复用匹配 current Spec 的 Topic，否则在用户选定 Topic 下用 `topic start --repo <repo> --topic <topic> --level <quick|standard>` 建立必要状态，已有 active Topic 先核对而不重复创建。standard 核对 current Spec 是否匹配并覆盖 brief：有则交 {{skill-call:my-to-tickets}}；没有则先交 {{skill-call:my-to-spec}}，改变既有定义则正式修订。已确认 quick 且仍满足原低风险准入时交 {{skill-call:my-implement}}，不造 Spec/Ticket；不符合准入则在既有对齐点说明升级原因。传递确认的 brief、来源和验证，不重复访谈；独立设计关口只在 to-spec 的风险触发处执行。下一阶段与止点按[用户决定与授权](references/shared/user-intervention.md)处理，已授权直接调用；跨会话保存[恢复包](references/policies/context-hygiene.md)。`my-to-tickets` 生成完整血缘 Ticket，不借用不匹配 Spec。

读取既有本地 Ticket 时按 [Ticket 准入与选择](references/shared/adapters/ticket-selection.md) 判断；旧 Ticket 缺少 `ticket_kind` 时按歧义处理，不猜测。

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
4. **追问（如需要）。** 只有未决需求会改变交付时调用 {{skill-call:my-grilling}}，按其方法解决决定性歧义；只有承重领域术语含义未清时调用 {{skill-call:my-domain-modeling}}。两条件分别判断，不把查证代码事实或普通信息补充变成两方法必调。决策写入项目实际声明的领域来源或 ADR，不假设固定存在 `CONTEXT.md`。
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

若维护者说“将 #42 移到 ready-for-agent”，信任他们并直接应用角色。核对既有授权覆盖的操作（角色变更、评论、关闭），然后执行；未授权后果按共享授权规则处理。跳过追问。若在没有追问会话的情况下移至 `ready-for-agent`，询问他们是否想编写 Agent 简报。

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
