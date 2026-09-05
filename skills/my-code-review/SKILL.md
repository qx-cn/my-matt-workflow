---
name: my-code-review
description: 从固定基线开始，沿 Standards 与 Spec 两个独立轴审查变更；适用于分支、PR 或进行中的修改。
disable-model-invocation: true
---

# 代码审查

输出给实现者和合并决策者前，先按[面向读者写作](references/shared/reader-first-writing.md)确定他们要据此修复、批准或阻止什么。

对用户提供的固定点与当前完整工作树之间的同一份内容快照做两轴审查。快照必须同时覆盖已提交、已暂存、未暂存与未跟踪内容：

- **Standards**——代码是否符合仓库已记录的编码标准？
- **Spec**——代码是否忠实实现了原始 Issue、PRD 或 Spec？

两轴应在相互隔离的审查上下文中完成，随后并列汇总，避免互相污染。

两轴是一次 review 内部的分析方法，不是新的 Skill 入口。`composition_policy` 为 `manual` 或 `automatic` 都必须在同一次调用中完成两轴并回到汇总；不得只输出下一条调用文本后停止。

## 过程

### 1. 固定审查对象

用户说的固定点就是基线：Commit SHA、分支、tag、`main`、`HEAD~5` 等。若没有指定，优先使用实施开始记录的 `HEAD`；仍无法确定时按 `decision_policy` 询问、自治判断并记录证据，或停止。作为 `my-implement` 的阶段时，将暂停原因交回宿主的 Ticket transition；不得因审查已结束而终止可继续的 workflow。

通过安装状态记录的 `runtime_entry` 运行 `review-snapshot --repo <repo> --base <fixed-point>`。记录其 `resolved_fixed_point`、`merge_base`、`head`、`content_id`、`change_sources` 和 `changes`；`content_id` 是本轮 review receipt，绑定实际文件内容，不绑定暂存位置。

审查输入按快照读取：

- 以 `git diff --binary <merge_base>` 读取所有 tracked 内容；它同时覆盖基线后的 committed、staged 与 unstaged 结果，而 Commit 列表只作上下文，不能代替这份 diff；
- 以 `git log <merge_base>..HEAD --oneline` 读取 Commit 列表；
- 对 `change_sources.untracked` 中的每个路径读取完整内容；二进制或无法直接阅读的文件记录类型、大小及可用检查结果，不得静默跳过；
- 两个审查轴必须使用同一 `content_id` 和同一 `changes` 路径集合。

坏 ref 或 `status: empty` 必须在此处失败。只要修复或生成步骤改变了内容，就重新生成快照并重跑两个审查轴；旧 receipt 立即失效，不能只复查修改过的一个轴。

### 2. 定位 Spec 来源

按以下顺序找来源：

1. Commit 信息中的 Issue 引用（`#123`、`Closes #45`、GitLab `!67` 等）；按项目配置的 Tracker 工作流获取；
2. 用户传入的路径；
3. 与分支或功能匹配的 `.agent/work/`、`docs/`、`specs/` 下的 PRD/Spec；
4. 若都没有，按 `decision_policy` 询问、报告“无 Spec 可用”，或停止。

读取 `.agent/work/` 产物时，遵循 [工作产物访问](references/shared/adapters/artifact-access.md)。

没有 Spec 时跳过 Spec 轴，并明确报告原因。

### 3. 定位 Standards 来源

按 [项目规则解析](references/shared/adapters/project-rules.md) 为该变更的 `execution_agent` 发现并匹配 Standards 来源；必须按 diff 中实际文件路径判定规则是否适用。

无论仓库是否有文档，Standards 轴都带以下 Fowler code smell 基线。它是按需诊断词汇，不是逐项打勾清单。三条规则约束它：

- **仓库优先。** 仓库明确标准总是优先；若仓库认可某做法而基线会标记，则压制该 smell。
- **始终是判断。** 每个 smell 都是带标签的启发式（如“可能的 Feature Envy”），不是硬违规；仓库标准同理，工具已强制的事项不再重复报告。
- **可观察影响。** 无法说明本次变更中可能失败的场景、不变量或维护风险时，不报告为发现；最多放入非阻断建议。

- **Mysterious Name**：函数、变量或类型名称未说明其含义。→ 改名；若无法诚实命名，说明设计不清晰。
- **Duplicated Code**：同一逻辑形状出现在多个 hunk 或文件。→ 提取共享形状并由两处调用。
- **Feature Envy**：方法访问别的对象数据多于自身数据。→ 将方法移至其依恋的数据。
- **Data Clumps**：同一组字段或参数反复一起传递。→ 打包为类型再传递。
- **Primitive Obsession**：原始值或字符串代替应有独立类型的领域概念。→ 建立小类型。
- **Repeated Switches**：对同一类型的 `switch` / `if` 级联反复出现。→ 多态化，或共用一个 map。
- **Shotgun Surgery**：一次逻辑变更迫使 diff 中许多分散文件同时修改。→ 将会一起变化的知识聚到一个模块。
- **Divergent Change**：一个文件因多个无关理由被修改。→ 分拆，使每个模块只有一种变化原因。
- **Speculative Generality**：Spec 不需要的抽象、参数或扩展点。→ 删除并内联，直到真实需求出现。
- **Message Chains**：调用者不应依赖的长 `a.b().c().d()` 导航。→ 在第一个对象后隐藏遍历。
- **Middle Man**：类或函数主要只做转发。→ 删除中间层，直接调用真实目标。
- **Refused Bequest**：子类或实现者忽略/覆盖大部分继承内容。→ 放弃继承，使用组合。

### 4. 分别审查

**Standards 审查**需获得完整快照内容、Commit 列表、按实际路径匹配的规则地图及以上 smell 基线；报告相关文件/hunk 中有证据支持的标准违反与本次确有影响的 smell。区分硬违规与判断，并输出 `### 注释` 与 `### 命名`（不得并入 smell 列表）：

- `### 注释`：注释是否与代码行为一致；不一致则报告。文案审阅按 [humanizer](references/shared/humanizer.md) 服从 `humanizer_policy`；保留有意简短的领域用语。
- `### 命名`：函数名、变量名（以及类型名，若 diff 涉及）列于此。可引用 Mysterious Name 作依据，但发现必须出现在本小节。仓库已有命名标准时，仓库标准优先。

**Spec 审查**需获得完整快照内容、Commit 列表和 Spec 内容；报告缺失或部分实现的要求、未要求的范围蔓延、看似实现但错误的行为。每项引用 Spec 位置，并输出 `### 注释`：

- `### 注释`：是否与 Spec / ADR / 相关文档一致；冲突则报告。无 Spec 时跳过本小节并写明原因（与跳过 Spec 轴相同）。

对认证授权、敏感数据、迁移/一致性、并发、性能热路径或兼容协议等高风险改动，按实际风险增加相应审查视角；低风险变更不为并行而增加 reviewer。新增视角仍使用同一 `content_id`，其发现进入对应 Standards 或 Spec 轴。

### 5. 发现契约

只有能定位、能解释影响且有证据的事项才算发现。每项固定包含：

- **严重度**：`P0` 会造成安全越权、数据丢失/破坏、不可恢复故障或核心路径普遍失败；`P1` 是需求偏差或高概率真实 Bug，合并前应修复；`P2` 是局部维护或测试风险，不阻断合并。
- **位置**：文件与最小行范围或 hunk。
- **失败场景/不变量**：什么输入、状态或调用路径会失败，或违反哪条仓库规则/Spec。
- **证据与置信度**：代码路径、测试、命令输出或文档引用；只使用 `high` / `medium`。低置信度内容作为待核实问题，不伪装成发现。
- **影响与验证**：影响谁或什么，以及修复后应运行的最小回归验证。可以给修复方向，但不要求 reviewer 代写实现。

P0/P1 是 blocker。修复后先运行针对性回归；任何内容变化都会产生新 `content_id`，因此两个轴都要基于新快照重审。P2 可在最终汇总中单列，不得抬高为 blocker。

### 6. 汇总

在 `## Standards` 与 `## Spec` 下呈现两轴报告，**不要合并或重新排序**。形状必须如下（可无发现时写“无”）：

```text
## Standards
…smell / 标准违反…
### 注释
…
### 命名
…

## Spec
…需求符合性…
### 注释
…
```

报告开头写明 `Review-Snapshot: <content_id>`、基线与 `head`。按严重度再按文件位置排列每轴发现，最后统计每轴 P0/P1/P2 数量、最严重问题及 blocker 状态；不要跨轴选出单一“赢家”。

## 为什么是两轴

同一变更可以通过一轴而失败另一轴：遵循所有标准却做错需求，等于 **Standards 通过、Spec 失败**；完全实现需求却破坏项目约定，等于 **Spec 通过、Standards 失败**。分开报告避免一轴遮蔽另一轴。
