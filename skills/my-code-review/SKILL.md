---
name: my-code-review
description: 从固定基线开始，沿 Standards 与 Spec 两个独立轴审查变更；适用于分支、PR 或进行中的修改。
disable-model-invocation: true
---

# 代码审查


对 `HEAD` 与用户提供的固定点之间的 diff 做两轴审查：

- **Standards**——代码是否符合仓库已记录的编码标准？
- **Spec**——代码是否忠实实现了原始 Issue、PRD 或 Spec？

两轴应在相互隔离的审查上下文中完成，随后并列汇总，避免互相污染。

## 过程

### 1. 固定基线

用户说的固定点就是基线：Commit SHA、分支、tag、`main`、`HEAD~5` 等。若没有指定，优先使用实施开始记录的 `HEAD`；仍无法确定时按 `decision_policy` 询问、自治判断并记录证据，或停止。

只记录一次 diff 命令：`git diff <fixed-point>...HEAD`（三点比较，因此以 merge-base 为基准）；同时记录 `git log <fixed-point>..HEAD --oneline`。

继续前确认固定点可解析（`git rev-parse <fixed-point>`）且 diff 非空。坏 ref 或空 diff 必须在此处失败，不得拖入后续审查。

### 2. 定位 Spec 来源

按以下顺序找来源：

1. Commit 信息中的 Issue 引用（`#123`、`Closes #45`、GitLab `!67` 等）；按项目配置的 Tracker 工作流获取；
2. 用户传入的路径；
3. 与分支或功能匹配的 `.agent/work/`、`docs/`、`specs/` 下的 PRD/Spec；
4. 若都没有，按 `decision_policy` 询问、报告“无 Spec 可用”，或停止。

没有 Spec 时跳过 Spec 轴，并明确报告原因。

### 3. 定位 Standards 来源

查找仓库中说明代码写法的文件，例如 `CODING_STANDARDS.md`、`CONTRIBUTING.md`、`AGENTS.md`。

无论仓库是否有文档，Standards 轴都带以下 Fowler code smell 基线。两条规则约束它：

- **仓库优先。** 仓库明确标准总是优先；若仓库认可某做法而基线会标记，则压制该 smell。
- **始终是判断。** 每个 smell 都是带标签的启发式（如“可能的 Feature Envy”），不是硬违规；仓库标准同理，工具已强制的事项不再重复报告。

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

**Standards 审查**需获得完整 diff、Commit 列表、定位到的 Standards 文件及以上 smell 基线；报告每个相关文件/hunk 中的：文档标准违反（引用文件和规则），以及基线 smell（名称与 hunk）。区分硬违规与判断；少于 400 字。此外必须按下方报告模板输出 `### 注释` 与 `### 命名`（不得省略、不得并入 smell 列表）：

- `### 注释`：注释是否与代码行为一致；不一致则报告。文案审阅按 [humanizer](references/shared/humanizer.md) 服从 `humanizer_policy`；保留有意简短的领域用语。
- `### 命名`：函数名、变量名（以及类型名，若 diff 涉及）列于此。可引用 Mysterious Name 作依据，但发现必须出现在本小节。仓库已有命名标准时，仓库标准优先。

**Spec 审查**需获得完整 diff、Commit 列表和 Spec 内容；报告缺失或部分实现的要求、未要求的范围蔓延、看似实现但错误的行为。每项引用 Spec 行；少于 400 字。此外必须按下方报告模板输出 `### 注释`：

- `### 注释`：是否与 Spec / ADR / 相关文档一致；冲突则报告。无 Spec 时跳过本小节并写明原因（与跳过 Spec 轴相同）。

`composition_policy: automatic` 时，可在当前流程加载两个隔离审查；`manual` 时提示用户分别启动审查，而不混合两轴。

### 5. 汇总

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

最后一行统计每轴发现数量及该轴最严重问题；不要跨轴选出单一“赢家”。

## 为什么是两轴

同一变更可以通过一轴而失败另一轴：遵循所有标准却做错需求，等于 **Standards 通过、Spec 失败**；完全实现需求却破坏项目约定，等于 **Spec 通过、Standards 失败**。分开报告避免一轴遮蔽另一轴。
