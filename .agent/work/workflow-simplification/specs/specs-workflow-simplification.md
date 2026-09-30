---
spec_id: workflow-simplification
revision: 1
supersedes:
status: current
---

# My Matt Workflow 精简重构

本 Spec 自包含：施工者只需要本文和被改造的仓库（My Matt Workflow 源码仓库）。上游内容来自公开仓库 `mattpocock/skills` 的提交 `c55ee46`，需要吸收的部分已写进第 7 节。

本文只规定外部行为、状态、不变量和验收；runtime 的内部步骤、数据结构和文件名由施工者设计，以满足验收为准。**"核心模型"一节是状态与命令的唯一定义**，其他章节只引用它；两处说法冲突时，以核心模型为准。

**称呼约定**
- **用户**：本工作流唯一的使用者。
- **Agent**：在用户项目中运行本工作流的编码 Agent。
- **施工者**：实施本 Spec 的 Agent。
- **旧版**：施工开始时仓库 HEAD 的代码与格式。

**术语**
- **Topic**：用户项目中 `.agent/work/<topic>/` 下的一项工作。
- **Ticket**：standard 等级下的一个实施切片。
- **内容**：用户项目里被 git 跟踪的文件，加上未被 `.gitignore` 忽略的未跟踪文件，但不含 `.agent/` 和 `.git/`。
- **内容干净**：内容相对 HEAD 没有任何改动。
- **全量测试集合**：配置 `test_commands` 中不以 ` *` 结尾的所有条目。
- **阻断级问题**：违反某条验收或某个明确的不变量，并且能写出一条真实可达出错路径的审查问题。其余审查问题统称为**建议**。

## 问题陈述

旧版把证据链、门禁和配置维度做得很重，但用户最缺的注意力、额度和状态清晰度并没有因此改善，语义缺陷也照样会漏过。下面的依据来自用户 7 个真实项目的日志、在玩具仓库里的实跑，以及与上游的对照：

- **人工介入多，成本高。**
  - 每张 Ticket 需要 16–44 个用户轮次。
  - 实跑一个单 Ticket 的小功能，用了 45 次 runtime 命令、手写 12 个文件，还手抄了约 18 次哈希。
  - 7 个项目中有 6 个把默认的手动接力改成了自动。
  - 配置有 5 档预设、19 个键，组合起来很难预测。
- **质量有漏洞。**
  - 同会话自审时，偷懒给出的"通过"让语义缺陷一路走到了归档。
  - 改动 Ticket 范围外的文件，没有任何提示。
  - 测试失败时，记录测试的命令仍然退出 0。
- **审查不收敛。** 一个文档审查会话跑了 34 轮仍未通过：
  - 56 条阻断问题中，73% 是上一轮修复带进来的；
  - 所有问题都进入了修复循环；
  - 轮数上限只在 Ticket 路径上生效，而这次循环是主 Agent 自己反复派出审查者，根本没经过 runtime。
- **机制没有接进 Skill。** 审查结果格式、归档流程都没写进任何 Skill；长期 Spec 发布功能从未在真实项目上跑通过。
- **入口和文本过重。**
  - 39 个 Skill 全部只能手动调用，构建时要把被调用方的正文复制进调用方。
  - 近一半 Skill 从未被调用过。
  - 主链文本按内容去重后约 58K 字符。

## 目标结果

- **人工介入只发生在两个对齐点。** 之后 Agent 逐张实施、独立审查、自动修复、逐张本地提交，只在"找用户的条件"下才找用户。
- **Topic 由 `topic complete` 自动收尾。** 它生成交付摘要、沉淀长期知识、归档并记录度量。
- **一张干净的 Ticket 只需五步**：`implement start → test → review → review --submit → finish`，Agent 不手写任何哈希或内容 id。
- **审查能收敛。** 由新上下文的审查者负责审查，所有审查都遵守同一套审查循环规则。
- **Skill 精简到 32 个。** 只有被调用方可以由模型调用；不再有正文副本；主链文本不超过 35,000 字符。
- **旧项目可以迁移。** 先预览，确认后执行，执行前备份。

判断标准：
- 主指标：每张 Ticket 的人工介入次数。
- 护栏：逃逸缺陷不增加；额度不超出用户可接受的上限。

这些指标通过交付摘要、`.agent/metrics.jsonl` 和 `workflow.py metrics` 在后续使用中观察。本次验收只验证机制存在且可用。

## 范围边界

**范围内**
- 本仓库的 `skills/`、`resources/`、`policies/`、`composition/`、`portfolio/`、`evals/`、`tools/`、`tests/`；
- `README.md`、`.gitignore`、`.github/workflows/`；
- 本仓库自身的 `.agent/matt-workflow.md`。

**范围外**
- 宿主目录（`~/.codex`、`~/.cursor`、`~/.claude`），以及实际安装；
- 在用户其他项目上实际执行迁移；
- Stop 钩子；
- 实测飞书阶段；
- 冻结 Skill 的方法正文；
- 并行实施、非 `local` 后端、长期 Spec；
- 自动推送、自动建 MR、自动写外部系统；
- 本仓库 `.agent/work/**` 中已有的文档；
- `chatgpt/` 目录。

## 核心模型

### M1. 参数与定位

- 除 `artifact-review-*` 外，M6 中的命令都接受 `--repo <路径>`，默认为当前目录。
- `--topic <t>` **只用于选择 Topic**，不表示操作模式。
  - 当存在多个活动 Topic 时，操作某个 Topic 的命令必须带上它；只有一个活动 Topic 时可以省略。
  - `topic start` 必须带 `--topic`。
- `--ticket <id>` 用于选择 Ticket。
  - Ticket id 本身包含 Topic，带了 `--ticket` 就不需要再带 `--topic`。
  - 省略时，取所选 Topic 中唯一一张处于 `implementing` 或 `needs-user` 的 Ticket（I-T3 保证最多一张）；如果没有，报错并提示运行 `topic status`。
- Ticket id 的格式为 `<topic>-<NN>`；验收编号的格式为 `<ticket-id>#A<n>`，n 是验收复选框在正文中的顺序。
- `artifact-review-*` 沿用旧版参数，不适用本节规则。

### M2. Topic

**状态**
- **无状态文件**，分两种：
  - **待补建**：Topic 下有 Ticket；
  - **文档 Topic**：Topic 下没有 Ticket，例如调研、技术方案、交接。
- **`active`**：记录等级（`quick` 或 `standard`）、开始时间和 Topic 基线提交。
- **`archived`**：位于 `.agent/archive/<topic>/`，记录结果（`complete` 或 `abandoned`）、时间和原因；由迁移归档的，注明"迁移归档"。

**进入 `active`**

| 路径 | 前置条件 | 等级与基线 |
|---|---|---|
| `topic start --level L` | Topic 不存在，或者是文档 Topic；`.agent/archive/<topic>/` 不存在；内容干净；L 为 standard 时满足 I-T1 | 等级 L；基线为当前 HEAD |
| 由 `implement start` 自动补建 | Topic 处于待补建；归档目录不存在；满足 I-T1 | standard；基线为当前分支与 `default_base_branch` 的分叉点 |
| `migrate --apply` | 旧 Topic 含有未完成的 Ticket；满足 I-T1 和 I-T3，否则列为"无法自动迁移" | standard；基线取旧实施记录中最早的基线提交，没有时同上 |

**进入 `archived`**
- 通过 `topic complete`、`resolve --branch --accept`、`topic abandon`，见 M5。
- `migrate --apply` 会把 Ticket 已全部完成的旧 Topic 直接归档。
- 归档目录已经存在时，一律拒绝，不覆盖。

**不变量**
- **I-T1**：standard Topic 的全量测试集合不能为空。每条进入 standard `active` 的路径都要检查；对 standard Topic 执行 `topic test`、`topic review`、`topic complete` 时，再检查一次。
- **I-T2**：`topic start` 要求内容干净。
- **I-T3**：同一个 Topic 中，处于 `implementing` 和 `needs-user` 的 Ticket 合计最多一张。`implement start` 和迁移时检查。

**分支规则**
- 生效时机：standard Topic 第一次执行 `implement start` 时，或 quick Topic 执行 `topic start` 时。
- 当前分支是 `default_base_branch`：创建或切换到 `<topic>` 分支，已存在就直接切换。
- 当前分支是其他分支：留在原分支。

### M3. Ticket

**状态**：`ready-for-agent`、`implementing`、`needs-user`、`complete`。

| 触发 | 状态变化 | 前置条件 | 结果 |
|---|---|---|---|
| `implement start` | ready-for-agent → implementing | 依赖全部 complete；内容干净；满足 I-T3 和 I-K2；Topic 是 standard `active`，或者处于待补建（按 M2 自动补建）。quick Topic 拒绝 | 记录 Ticket 基线（当前 HEAD）和定义快照；生成执行简报；执行分支规则 |
| runtime 登记 | implementing → needs-user | 该 Ticket 的审查进入 needs-user（M4） | 记录原因 |
| `implement finish` | implementing → complete | 见 M5 | 见 M5 |
| `resolve --ticket <id> --accept` | needs-user → complete | 见 M5 | 见 M5 |
| `resolve --ticket <id> --reopen` | implementing 或 needs-user → implementing | 定义已变化（见下） | 重新读取并校验定义（I-K2），更新定义快照；该 Ticket 的审查历史和测试记录作废，轮数和停止信号从零开始计算；保留代码和 Ticket 基线 |
| `topic abandon` | 状态不变，随 Topic 一起归档 | — | — |

**定义已变化**：与定义快照相比，满足任一条件。定义快照取最近一次 `start`、`reopen` 记录的内容；由迁移建立的实施记录，取迁移转换后的 Ticket 和 Spec。
- Ticket 文件有改动，但不计 `status`、`claimed_by` 和验收复选框的勾选状态；
- `spec_ref` 指向的 Spec 文件有改动。

**I-K1**：Ticket 处于 `implementing` 或 `needs-user` 时，如果 `test_commands` 与定义快照不同，`implement test`、`implement finish`、`resolve --accept` 都会拒绝，并给出两条出路：恢复原值；或者由用户确认修订，然后执行 `resolve --reopen`。

**I-K2**：Ticket 必须声明至少一条 `test_commands`，每一条都要匹配配置中的某个条目。匹配方式：
- 两边都用 `shlex.split` 拆成 argv。
- 配置条目以 ` *` 结尾时，表示"前缀 argv 加零个或多个参数"。例如 `go test *` 能匹配 `go test ./internal/foo/...` 和 `go test`，但不能匹配 `go testify`。

### M4. 由 runtime 管理的审查

runtime 只管理两类审查对象：
- **Ticket 审查**：审查范围是 Ticket 基线以来的全部内容改动，验收取该 Ticket 的验收。
- **整分支审查**：只用于有多张 Ticket 的 standard Topic。审查范围是 Topic 基线以来的全部内容改动，验收取所有 Ticket 验收的并集。

文档审查（Spec、技术方案、Skill 文本等）不由 runtime 计数，由第 4 节的审查循环规则约束。

**轮次**
- 每执行一次 `review` 算一轮。
- 每个对象最多 4 轮，从创建时或最近一次 `--reopen` 起算。
- 如果第 4 轮仍有阻断问题，对象进入 `needs-user`，不会再开第 5 轮。
- 一轮有阻断问题、修改内容后再开下一轮，算一次修复，因此最多修复 3 次。
- 审查通过后，内容一旦改动，通过记录就失效，需要再开一轮，并占用轮数。

**进入 `needs-user` 的条件**（任一满足即进入）
- 审查结论为 `blocked-by-design`（需要修改 Spec 或验收）或 `inconclusive`（证据不足）；
- 第 4 轮仍有阻断问题；或者 4 轮已经用完，而当前内容没有有效的审查通过记录（例如第 4 轮通过后内容又被改动）。后一种情况在请求开第 5 轮时登记：`implement review` 或 `topic review` 会把对象置为 `needs-user`，并拒绝开新一轮；
- 出现以下任一停止信号：
  - **同一根因**：连续两次复审都有阻断问题，并且落在紧挨着的上一次修复差异之内。
  - **同一处连续修改**：相邻两次修复的差异，在同一文件中的行区间重叠。比较时，两次差异都换算到它们之间那份快照的行号。
  - **前后矛盾**：审查者用 `contradicts` 指向之前某一轮的问题。
  - **体积膨胀**：相对基线的"增加行 + 删除行"，超过第一轮审查时的 1.5 倍。

对象处于 `needs-user` 时，runtime 拒绝开新一轮。整分支审查处于 `needs-user` 时，`topic complete` 拒绝执行，`topic status` 显示原因。

**整分支审查的 `--reopen`**
- 前置条件：从整分支审查首次开启或最近一次 `--reopen` 之后，任一 Ticket 文件（不计项同 M3）或 Spec 文件有改动。
- 效果：整分支审查历史作废，轮数和停止信号从零开始计算。
- Ticket 审查的 `--reopen` 见 M3。整分支审查的 `--accept` 见 M5。

### M5. 记录、提交与 `.agent/`

**记录绑定**
- 测试通过记录和审查通过记录都绑定到内容。
- 内容一变，记录就失效。
- `.agent/` 下的改动不影响这些记录。

**`implement finish`**
- 前置条件：
  - Ticket 处于 `implementing`；
  - Ticket 声明的每条测试，在当前内容上都有通过记录；
  - 有绑定当前内容的 Ticket 审查通过记录；
  - 经历过修复时，提供了 `--notes-file`；
  - 验收复选框全部勾选。
- 结果：
  - 把内容改动做成一次代码提交，标题为 `<ticket-id>: <标题>`；有修复时，正文附上修复思路；没有内容改动时，不做代码提交；
  - Ticket 状态改为 `complete`；
  - 追加一条度量记录：`kind: ticket`，`outcome: complete`；
  - 返回下一张 Ticket，或者提示运行 `topic complete`。

**`resolve --ticket <id> --accept --reason`**
- 前置条件：
  - Ticket 处于 `needs-user`；
  - Ticket 声明的每条测试，在当前内容上都有通过记录；
  - 满足 I-K1。
- 结果：
  - 把内容改动做成一次代码提交，正文附上理由和已知问题；没有内容改动时，不做代码提交；
  - Ticket 状态改为 `complete`；
  - 剩余的阻断问题记为"已知问题"，显示在 `topic status` 中；
  - 追加一条度量记录：`kind: ticket`，`outcome: accepted`。

**`topic complete`**

| Topic 类型 | 前置条件 | 结果 |
|---|---|---|
| 文档 Topic | — | 归档，追加 `kind: topic` 度量；`level` 和 runtime 观察不到的字段填 null |
| 待补建 | — | 拒绝，提示先运行 `implement start` |
| quick | ① 全量测试集合不为空时，由它在当前内容上运行，必须全部通过；集合为空时，标记为"未配置测试"<br>② 交付摘要各节齐全，其中包括"验收对照" | 有内容改动时，做一次代码提交；归档；追加 `kind: quick` 度量 |
| standard，没有 Ticket | — | 拒绝，提示先拆分 Ticket，或者 `topic abandon` |
| standard，单张 Ticket | Ticket 已 complete；内容干净；交付摘要各节齐全 | 归档；追加 `kind: topic` 度量 |
| standard，多张 Ticket | ① 所有 Ticket 已 complete<br>② 有绑定当前内容的整分支审查通过记录<br>③ 由它在当前内容上运行全量测试集合，必须全部通过<br>④ 交付摘要各节齐全 | 有内容改动时，做一次"Topic 收尾修复"提交；归档；追加 `kind: topic` 度量 |

**`resolve --branch --accept --reason`**
- 前置条件：整分支审查处于 `needs-user`，并满足上表"standard，多张 Ticket"一行中除②以外的全部条件。
- 结果：与该行相同；剩余的阻断问题记为已知问题；度量记为 `outcome: accepted`。

**`topic abandon --reason`**
- 适用于任何未归档的 Topic。
- 结果：
  - 以 `abandoned` 归档；
  - 不改动内容，只在输出中列出尚未提交的内容；
  - 追加一条度量记录：`kind: topic`，`outcome: abandoned`。

**`.agent/` 提交**
- **I-A1**：`implement finish`、`resolve … --accept`、`topic complete`、`topic abandon`、`migrate --apply` 结束时，`.agent/` 下都不能有未提交的改动。
  - private 模式：在 `.agent/` 嵌套仓库中提交。
  - shared 模式：在主仓库中提交，可以与代码提交合并，也可以单独提交。
- **I-A2**：private 模式下，主仓库的提交不包含 `.agent/`。

### M6. 命令总表

| 命令 | 作用 | 定义 |
|---|---|---|
| `topic start --topic <t> --level quick\|standard` | 创建 Topic | M2 |
| `topic status` | 只读。显示 Topic 状态、各 Ticket 状态、需要用户处理的对象及原因、累计的建议和已知问题，以及下一条完整命令 | — |
| `topic test` | 在当前内容上运行全量测试集合并登记结果。任一命令失败即非零退出，并输出失败的命令、退出码和输出末尾；集合为空时，报告"未配置测试"并非零退出 | — |
| `topic review [--submit <文件>]` | 整分支审查。前置条件：多 Ticket 的 standard Topic、所有 Ticket 已完成、有绑定当前内容的 `topic test` 通过记录 | M4 |
| `topic complete` | 收尾 | M5 |
| `topic abandon --reason` | 放弃 | M5 |
| `implement start --ticket <id>` | 开始 Ticket | M3 |
| `implement test [-- <argv>]` | Ticket 须处于 `implementing` 或 `needs-user`。不带 argv 时，依次运行 Ticket 声明的测试并登记结果；带 argv 时，运行一条匹配配置的命令，只用来看进度，不作为完成依据。输出方式同 `topic test` | M3、M5 |
| `implement review [--submit <文件>]` | Ticket 须处于 `implementing`。执行 Ticket 审查：冻结内容，生成材料包和结果骨架；`--submit` 校验结果并登记，格式错误时逐个指出字段 | M4 |
| `implement finish [--notes-file <文件>]` | 完成 Ticket | M5 |
| `implement status` | 只读。显示 Ticket 状态，以及根据记录判断的下一条完整命令：测试失败，或审查后内容有改动时，不会给出 `finish` | — |
| `resolve (--ticket <id> \| --branch) [--topic <t>] (--accept \| --reopen) --reason "<理由>"` | 处理进入 `needs-user` 的 Ticket 审查或整分支审查；`--reopen` 也可以用于 `implementing` 状态的 Ticket | M3、M4、M5 |
| `migrate [--apply]` | 迁移 | 第 10 节 |
| `metrics [--topic <t>]` | 汇总度量 | 第 11 节 |
| `artifact-review-*`（旧版已有） | 产物审查快照与结果校验，见第 4 节 | — |

- 所有命令都按 argv 执行，不经过 shell。
- 只支持串行实施和 `local` 后端。

### M7. 全局不变量

- **I-1**：不推送，不建 MR，不写外部系统。
- **I-2 提交门槛**：内容的每一次提交，都必须满足下列之一：
  - **Ticket 完成提交**：Ticket 声明的测试已通过，且 Ticket 审查已通过，两者都绑定这次提交的内容；
  - **Ticket 接受提交**：Ticket 声明的测试已通过，绑定这次提交的内容，并且有用户的接受记录；
  - **收尾修复提交**：全量测试已通过，绑定这次提交的内容，并且整分支审查已通过或已被用户接受；
  - **quick 提交**：全量测试已通过（没有配置时要标注），并且交付摘要中有"验收对照"。
- **I-3 提交粒度**：每张 Ticket 最多一次提交；有多张 Ticket 的 Topic 最多再加一次收尾修复提交；quick 最多一次提交。
- **I-4**：依赖顺序不能越过；I-T3 始终成立。
- **I-5**：runtime 管理的每个审查对象最多审查 4 轮，只有 `--reopen` 能重置。
- **I-6**：审查来源如实记录。宿主派不出新上下文审查者时，来源记为 `self`，并在交付摘要中写明。
- **I-7**：I-T1、I-K1、I-K2、I-A1、I-A2 都成立。
- **I-8**：迁移默认不写入任何文件；`--apply` 前先备份；已完成的历史记录不改写；推断不出的不猜。
- **I-9**：发现旧格式就停下来，提示迁移，不静默兼容。
- **I-10**：已归档的 Topic 只读，归档目录不会被覆盖。
- **I-11**：支持 Python 3.10 及以上；`check` 不修改被跟踪的文件。

## 行为与验收

编号为 AC-xx。"测试"表示由自动化测试判定；"核对"表示由审查者对照本 Spec 核对文本。

### 1. 主链与找用户的条件

**主链**
1. **访谈**：用户调用 `my-grill-with-docs`。
   - 每轮列出所有互不依赖的问题，每个问题附推荐答案；用户可以全部采纳，也可以只改其中几项。
   - 依赖其他答案的问题放到下一轮；会大幅影响其他问题的，单独问。
   - 形成摘要前，对复杂或靠类比描述的请求先做需求核对（来自原 `my-requirement-analysis`）。
   - 没有代码库时，改用 `my-grill-me`。它只输出需求摘要，不进入主链。
2. **对齐点 1**：Agent 输出需求摘要，包括目标、范围、约束、可观察验收，每项注明来源；同时按第 2 节的清单提议保证等级。用户确认后，Agent 执行 `topic start`。
3. **quick**：直接实施，然后执行 `topic complete`。
4. **standard**：Agent 依次调用 `my-to-spec`、`my-to-tickets`，然后把 Spec 和 Ticket 拆分一起交给用户审阅，内容包括每张 Ticket 做什么、依赖关系、测试命令、测试边界。这是**对齐点 2**。
5. **通过后**：按依赖顺序逐张完成 Ticket。如果有多张 Ticket，全部完成后先跑 `topic test` 和 `topic review`。然后 Agent 沉淀长期知识、写交付摘要，最后执行 `topic complete`。

**找用户的完整条件**

这份清单只在一个共享资源里定义，相关 Skill 都引用它。除以下情况外，Agent 不请求确认：
- 对齐点 1 和对齐点 2；
- 用户专属的决定：产品取舍、成功指标、优先级、不可逆的承诺；
- Ticket 或整分支审查进入 `needs-user`；文档审查达到上限，或出现停止信号（第 4 节）；
- 推送、建 MR、写外部系统，每次都要问；
- 修改 `.agent/` 之外、Spec 没有写明的项目文档；
- `setup` 写入前、`migrate --apply` 前，各问一次；
- 主链之外的阶段交接（`my-triage`→`my-to-tickets`、`my-wayfinder`→`my-to-spec`、`my-prototype`→`my-implement`）：问一次，用户同意后直接调用；
- 环境阻塞。

用户在对话中临时要求更严格时，Agent 照做，不需要写进配置。

**验收**
- AC-01（核对）`my-grilling` 与 `my-grill-with-docs` 按轮批量提问，每题附推荐答案；`my-grill-with-docs` 包含需求核对，结束时输出注明来源的摘要和保证等级提议。
- AC-02（核对）主链相关 Skill 的文本共同表达上述主链，中间不要求用户手动调用下一个 Skill；"找用户的完整条件"只在一处定义。
- AC-03（测试）分支规则在三种情况下都成立：在默认分支上且目标分支不存在；目标分支已存在；从非默认分支开始。每次有内容改动的 `implement finish` 都产生一次代码提交，全程没有推送。

### 2. 保证等级与 quick

- `assurance_level` 只接受 `quick` 或 `standard`。配置中的值只是建议，每个 Topic 实际用哪一档，在对齐点 1 确认。
- quick 准入条件，全部满足才用 quick，任何一条不满足就用 standard：
  - 单会话能完成；
  - 改动局部、可撤回；
  - 不改持久化结构、权限或对外 API 契约；
  - 预计一张 Ticket 就能做完。
- quick 不写 Spec 和 Ticket，也不建实施记录。实施完成后自审，在交付摘要的"验收对照"一节逐条写出"验收 → 测试 → 代码位置"，多条验收不能共用同一个测试。

**验收**
- AC-04（测试）`assurance_level` 为 `audited` 时，代表性命令（第 10 节）报错并提示运行 `migrate`；为其他非法值时，报配置校验错误并指出是哪个字段。
- AC-05（测试）quick：
  - 内容不干净时，`topic start` 拒绝；
  - 缺少"验收对照"，或全量测试失败时，`topic complete` 拒绝；
  - 成功时，Topic 已归档，有一次代码提交，有 `kind: quick` 的度量记录，没有实施记录。
- AC-06（测试）配置里只有带 `*` 的测试命令时，`topic start --level standard` 和自动补建都拒绝。

### 3. 实施会话

**执行简报**：由 `implement start` 生成，随 Topic 一起归档，不进入 Spec 血缘。
- runtime 写入：Ticket 全文、`spec_ref` 所指 Spec 的验收部分、已完成前置 Ticket 的提交和改动文件、适用规则（沿用 `resolve-rules`）、测试命令。
- Agent 动手前补写"实施计划"：要改的文件和接口、每条验收对应的测试断言、Spec 隐含但测试没覆盖的输入。

**Ticket 格式**：本地文件 `.agent/work/<topic>/tickets/tickets-<topic>-<NN>.md`，frontmatter 包括：
- `id`、`title`、`ticket_kind: implementation`；
- `spec_id`、`spec_revision`、`spec_ref`；
- `status`、`blocked_by`、`sequence`；
- `test_commands`（非空）；
- `rule_sources`、`rule_scope`、`rule_constraints`、`rule_conflicts`；
- `review_probes`（只能是 `recovery`、`unknown-response`）；
- `execution_agent`、`claimed_by`、`supersedes_ticket`、`compensates`、`tags`。

除 `test_commands` 外，其余字段都沿用旧版语义。正文保留"要构建什么""适用规则与影响区域""验收标准（复选框）"三节。

**验收**
- AC-07（测试）一张干净的 Ticket 按五步完成；Agent 在结果文件中只填写判断字段。
- AC-08（测试）测试失败时，`implement test` 非零退出，输出包含失败的命令和退出码；之后 `implement status` 不会给出 `finish`，`implement finish` 拒绝。
- AC-09（测试）审查通过后修改任一内容文件，`finish` 拒绝，`status` 指向重新测试和审查；只修改 `.agent/` 下的文件或被忽略的文件时，不受影响。
- AC-10（测试）以下情况 `implement start` 拒绝：依赖未完成；内容不干净；同一 Topic 已有 `implementing` 或 `needs-user` 的 Ticket；Topic 为 quick。
- AC-11（测试）结果中的预填字段与当前冻结的审查单元不一致时，`--submit` 拒绝，并指出是哪个字段。
- AC-12（测试）配置为 `python3 -m unittest *` 时：
  - Ticket 声明 `python3 -m unittest tests.test_foo`，校验通过；
  - 声明 `python3 -m unittestx`，或者列表为空，校验失败；
  - `implement test -- python3 -m unittest tests.test_other` 可以执行，但不作为完成依据；
  - 在 `implementing` 期间修改 `test_commands`，`test` 和 `finish` 都拒绝。
- AC-13（测试）审查材料包包含 Ticket 基线以来的全部内容改动；不在 `rule_scope` 中的文件单独列出。
- AC-14（测试）有两个活动 Topic 时，不带 `--topic` 的操作被拒绝；`implement test --topic A` 只运行 Topic A 中当前 Ticket 的测试。

### 4. 审查与修复

新增共享资源"审查循环规则"，`my-implement`、`my-code-review`、`my-review-design`、`my-review-artifact`、`my-review-instructions`、`my-tech-design` 都引用它。它的适用范围有两部分：
- M4 中由 runtime 管理的两类审查；
- 文档审查：设计审查、产物审查、指令审查、技术方案自检，以及主 Agent 临时派发的审查。

**独立审查**
- standard 下，由宿主派出新上下文的审查者。
- 审查者只读材料包，材料包包括：冻结的改动、验收（整分支审查时为所有 Ticket 验收的并集）、下游 Ticket 列表、已决事项清单、审查循环规则、结果骨架。
- 审查者不读实施者的总结，也不读执行简报中的"实施计划"。
- 审查者继承实施者的模型和思考档位，不得为省额度而降级；审查结果中写明实际使用的模型。
- 整分支审查如需更强的模型，由用户临时指定。

**严重度**
- 只有阻断级问题进入修复循环。
- 建议不修复、不触发复审，写进交付摘要。
- 属于下游 Ticket 的问题，按建议处理。
- 只有建议时，结论就是通过。

**第一轮与复审**
- 第一轮必须穷尽，并附覆盖清单：每条验收、每个 `review_probes` 探针、每个不变量，都要标注为无问题、对应某个问题，或不适用（附理由）。
- 阻断级问题要写明：锚定对象、位置（文件和行区间）、出错路径、可达性。
- 复审只看本轮修复的差异和它可能影响的地方；范围外新发现的问题，默认按建议处理。

**修复约束**
- 修复只允许改正、删除、收窄。需要新增规则、场景或要求时，结论改为 `blocked-by-design`。
- 修复前，先找出同一事实在别处的写法，一起修改。
- 文档类产物中，同一条规则只在一处定义。
- 修复思路写在 `--notes-file` 里，不另写修复方案文档。

**文档审查**（由 Skill 文本约束，runtime 不计数）
- 适用同样的严重度、第一轮与复审、修复约束和停止信号。"体积膨胀"以第一轮审查时的字节数为基准，多个产物一起审查时合并计算。
- 每个产物最多审查 4 轮。扩大范围、补审、用户说"直到通过"，都不重置轮数。
- Agent 在 `.agent/work/<topic>/reviews/review-log-<topic>.md` 中逐轮记录：产物、轮次、阻断数、建议数、修改范围、体积。没有 Topic 时，在对话中报告同样的信息。
- 达到上限或出现停止信号时，Agent 停下来向用户说明情况，由用户选择：接受现状、修订后重开，或放弃。

**已决事项清单**：`.agent/work/<topic>/decided/decided-<topic>.md`。
- Agent 在对齐点和用户裁决后追加记录。
- 审查者不得重开清单中的事项；有异议时，结论为 `inconclusive`。

**汇报**：写明已用轮数和剩余额度，不写趋势判断。

**结果骨架**（JSON）
- runtime 预填：`unit_id`、`content_id`、`round`、`acceptance`、`probes`、`downstream_tickets`。
- 审查者填写：
  - `status`：`pass`、`findings`、`blocked-by-design`、`inconclusive` 之一；
  - `reviewer`：`{provenance: independent|self, model}`；
  - `coverage`：`[{target, result: ok|finding|not-applicable, finding_id?, reason?}]`；
  - `findings`：`[{id, severity: blocking|advisory, summary, anchor, location?, failure_path?, reachability?, contradicts?, downstream_ticket?}]`。
- 阻断级问题的 `location`、`failure_path`、`reachability` 必填；结论为 `pass` 时不能含有阻断级问题。

**`artifact-review-*`**
- 方法名改为 `reader-first-writing`、`final-state-writing`、`visual-communication`、`artifact-finalization`、`humanizer`；设计类产物再加 `review-design`。
- 删除 `--kind repair-plan` 和 `--parallel`。
- 保留 `--expect-content-id`。
- 不计轮数。

**验收**
- AC-15（核对）"审查循环规则"覆盖 M4 和本节全部要点（包括文档审查的轮数、日志、停止条件），6 个 Skill 都引用它。
- AC-16（测试）结果只含建议时，登记为通过，建议出现在 `topic status` 中。
- AC-17（测试）轮数计算：
  - 同一 Ticket 第 4 轮仍有阻断问题时，进入 `needs-user`，`implement review` 拒绝开第 5 轮；
  - 第 2 轮通过后改动内容，下一轮计为第 3 轮；
  - 第 4 轮通过后又改动内容，再执行 `implement review` 时，拒绝开第 5 轮，对象进入 `needs-user`；之后可以执行 `resolve --accept`。
- AC-18（测试）4 个停止信号各有一个触发用例，`needs-user` 的原因分别对应。
- AC-19（测试）Ticket 级 `resolve`：
  - **`--accept`**：
    - 测试在当前内容上通过时：有内容改动就产生一次提交；Ticket 变为 complete，度量 `outcome: accepted`，已知问题出现在 `topic status` 中；
    - 测试未通过时拒绝。
  - **`--reopen`**：
    - 只改了 `status`、`claimed_by` 或复选框时拒绝；
    - Ticket 或 Spec 有改动后，从 `needs-user` 或 `implementing` 都能执行：回到 `implementing`，轮数归零，保留代码，新的 `test_commands` 生效。
- AC-20（测试）整分支级 `resolve`：
  - `--accept`：Topic 归档；有内容改动时产生收尾修复提交；度量 `outcome: accepted`。
  - `--reopen`：在 Ticket 或 Spec 有改动后执行，整分支审查的轮数归零。
  - `artifact-review-*` 不接受 `--topic`，也不计轮数。
- AC-21（测试）以下情况 `--submit` 报错，并指出具体字段：缺少必填字段；阻断级问题缺少位置、出错路径或可达性；结论为 `pass` 却含有阻断级问题。

### 5. 长期知识、Topic 目录与交付摘要

**删除长期 Spec 发布**
- 删除 `archive-spec`、对 `.agent/specs/` 的读写、canonical spec 与 `spec-review` 记录、`my-to-spec` 中把长期 Spec 作为基线的步骤，以及 README 中的相关说明。
- Topic 内 Spec 的 `revision`、`supersedes` 保留。
- 系统行为以测试为准。
- 长期知识只放两处：`.agent/CONTEXT.md`（术语）和 `.agent/adr/NNNN-<slug>.md`（难以撤回的决定），在 Topic 收尾时由 Agent 沉淀。`my-domain-modeling` 改为写入这两处，不再按 Topic 分片。

**Topic 目录**

| 路径 | 内容 |
|---|---|
| `requirements/requirements-<topic>-01.md` | 需求摘要 |
| `specs/` | Spec |
| `tickets/` | Ticket |
| `decided/decided-<topic>.md` | 已决事项清单 |
| `reviews/review-log-<topic>.md` | 文档审查日志 |
| `deliveries/deliveries-<topic>-01.md` | 交付摘要 |
| `handoffs/` | 交接 |
| `designs/` | 技术方案 |

- runtime 管理的其他文件由施工者设计，放在 Topic 目录内。
- `work-overview` 列出活动 Topic、待补建 Topic 和文档 Topic，不列出已归档的 Topic。

**交付摘要**：各节标题固定，runtime 按标题检查是否齐全：
- 改动概述
- 测试结果
- 审查发现与修复
- 建议
- 已知问题（没有就写"无"）
- 长期知识沉淀（没有就写"无"）
- 用户介入记录（次数和原因）
- 未验证项
- 验收对照（仅 quick）

`my-test-report` 保留为手动入口，用于出正式的测试报告。

**交接（`my-handoff`）**
- 只在两种情况下使用：换宿主、换目录或换人；访谈结论尚未写成 Spec，但需要保存。
- 取消 ready/draft 门禁和独立重建要求。
- 实施阶段靠提交记录和 `status` 恢复，不需要交接。

**验收**
- AC-22（测试）`archive-spec`、`archive-topic`、`archive-show`、`archive-list` 已删除；runtime 不读写 `.agent/specs/`。
- AC-23（测试）`topic abandon` 之后：
  - Topic 已归档，并记录了原因；
  - `work-overview` 不再列出它；
  - 对其中的 Ticket 执行 `implement start` 被拒绝；
  - 未提交的内容保持不变，并在输出中列出。
- AC-24（测试）在 private 和 shared 两种模式下，各跑一遍以下流程：单 Ticket standard、多 Ticket standard（含一次整分支审查修复）、`resolve --ticket --accept`、`resolve --branch --accept`、`topic abandon`。验证 I-A1、I-A2、I-3。
- AC-25（测试）Topic 生命周期：
  - 待补建的 Topic 由 `implement start` 自动补建后，可以用 `topic complete` 完成；
  - 文档 Topic 可以直接 `topic complete`；
  - 以下情况 `topic start` 拒绝：Topic 已是 active；Topic 处于待补建；同名的归档目录已存在；
  - 没有 Ticket 的 standard Topic 执行 `topic complete` 时拒绝。
- AC-26（核对）`my-to-spec` 不再引用长期 Spec；`my-domain-modeling` 写入 `.agent/CONTEXT.md` 和 `.agent/adr/`；`my-handoff` 采用上述使用条件。

### 6. 配置与 setup

`.agent/matt-workflow.md` 的 frontmatter 只保留以下键：

| 键 | 取值 |
|---|---|
| `schema_version` | `2` |
| `task_backend` | 只能是 `local` |
| `agent_directory_mode` | `private` 或 `shared` |
| `default_base_branch` | — |
| `test_commands` | — |
| `standards_sources` | — |
| `domain_sources` | — |
| `default_execution_agent` | `auto`、`codex`、`cursor`、`claude` 之一 |
| `assurance_level` | `quick` 或 `standard` |

**删除**
- 5 档预设及兼容别名；
- 配置键：`branch_policy`、`commit_policy`、`external_write_policy`、`docs_writeback`、`composition_policy`、`work_scope_policy`、`decision_policy`、`max_repair_rounds`、`humanizer_policy`、`review_commands`；
- 配置正文中的预设说明。

这些配置原来控制的行为，一律固定为本 Spec 描述的行为。

**setup**
- `setup --repo <p>` 只做探测并展示，不写入。
- `setup --repo <p> --apply` 写入配置；private 模式下，沿用旧版的嵌套 Git 初始化。
- Agent 在两步之间只确认一次。

**删除命令** `write-gate`、`decision-gate`。指令权威相关资源改为引用"找用户的完整条件"。

**验收**
- AC-27（测试）配置含有已删除的键，或 `schema_version` 不是 2 时，代表性命令都停止，并提示运行 `migrate`；新配置可以正常工作。
- AC-28（测试）`skills/`、`resources/`、`policies/` 中不再出现已删除的命令名和配置键名。

### 7. Skill 组织

**合并**：39 个 Skill 合并为 32 个。
- `my-reader-first-writing`、`my-final-state-writing`、`my-visual-communication`、`my-artifact-finalization` 并入 `my-review-artifact`。规则保留在 `resources/` 中，由 `my-review-artifact` 直接读取；humanizer 也改为读取资源文件，不再调用 `my-humanizer`。
- `my-review-skill` 与 `my-review-agent-rules` 合并为 `my-review-instructions`，宿主差异作为参数传入，审查方法采用 `my-writing-for-agents`。
- `my-first-principles-review` 并入 `my-review-design`。
- `my-requirement-analysis` 并入 `my-grill-with-docs`。
- `my-writing-great-skills` 改名为 `my-writing-for-agents`。
- `resources/governance.json` 中指向已合并 Skill 的归属，改为指向合并后的 Skill。

**调用方式**：被其他 Skill 调用的 Skill 可以由模型调用，其余只能手动调用，唯一依据是组合清单。

调用边分三类：
- `method`：在当前阶段内调用，调用完返回；
- `handoff`：主链之外的阶段交接，调用前先问用户一次；
- `chain`：主链交接，对齐点之后自动进行。

`routable_entries`（`my-ask-matt` 路由表，列出其余 31 个 Skill）不算调用边。

调用边：
- `my-grill-me` → `my-grilling`（method）
- `my-grill-with-docs` → `my-grilling`、`my-domain-modeling`（method）；→ `my-to-spec`（chain）
- `my-to-spec` → `my-review-design`（method）；→ `my-to-tickets`（chain）
- `my-to-tickets` → `my-implement`（chain）
- `my-implement` → `my-tdd`、`my-code-review`（method）
- `my-review-artifact` → `my-review-design`（method）
- `my-review-instructions` → `my-writing-for-agents`（method）
- `my-triage` → `my-grilling`、`my-domain-modeling`（method）；→ `my-to-tickets`（handoff）
- `my-wayfinder` → `my-grilling`、`my-domain-modeling`、`my-prototype`（method）；→ `my-to-spec`（handoff）
- `my-prototype` → `my-implement`（handoff）
- `my-improve-codebase-architecture` → `my-codebase-design`、`my-grilling`、`my-domain-modeling`（method）

可以由模型调用的 11 个：`my-grilling`、`my-domain-modeling`、`my-codebase-design`、`my-tdd`、`my-code-review`、`my-review-design`、`my-to-spec`、`my-to-tickets`、`my-implement`、`my-prototype`、`my-writing-for-agents`。它们的描述只写"在哪个流程的哪一步被调用"。

只能手动调用的 21 个：`my-ask-matt`、`my-setup`、`my-install`、`my-grill-me`、`my-grill-with-docs`、`my-handoff`、`my-research`、`my-diagnosing-bugs`、`my-resolving-merge-conflicts`、`my-triage`、`my-wayfinder`、`my-wizard`、`my-to-questionnaire`、`my-teach`、`my-tech-design`、`my-test-report`、`my-edit-article`、`my-humanizer`、`my-improve-codebase-architecture`、`my-review-artifact`、`my-review-instructions`。

`my-research` 的方法正文原样移到 `resources/` 下的一个共享文件，`my-research` 和 `my-wayfinder` 都指向它。

**取消正文复制**
- 删除构建时把被调用 Skill 的正文复制进调用方的机制，即构建产物中的 `references/composed/**`。
- 调用方改为按宿主语法调用该 Skill。
- 共享资源仍按资源清单分发。

**宿主投影**
- Cursor、Claude：只能手动调用的 Skill 保留 `disable-model-invocation: true`；可以由模型调用的不设置这一项。
- Codex：`agents/openai.yaml` 的 `allow_implicit_invocation`，手动 Skill 设为 `false`，可由模型调用的设为 `true`。
- 构建和安装时的校验，改为以组合清单为准。
- 删除 `portfolio/` 及其校验代码。

**冻结**
- 冻结 `my-diagnosing-bugs`、`my-resolving-merge-conflicts`、`my-triage`、`my-wayfinder`、`my-wizard`、`my-research`、`my-prototype`、`my-to-questionnaire` 这 8 个 Skill 的方法正文。
- 它们只同步以下全局改动：调用元数据、删除已不存在的配置键与命令引用、正文副本改为调用 Skill、阶段交接方式，以及 `my-research` 正文移入共享资源。

**吸收上游**（冻结的 Skill 不吸收）
1. **`my-tdd`**：红绿循环中去掉重构。重构属于审查阶段，可以作为建议提出。
2. **`my-writing-for-agents`**：适用于 Skill、AGENTS.md、CLAUDE.md，默认动作是删除。
   - **指针**：Skill 描述，以及 AGENTS.md 中指向某份文档的那一行，都是指针；措辞决定 Agent 何时去读。要写清目标是什么、在哪些情况下需要读；关键词放在最前面；每种情况只写一个触发条件；删掉正文已经说明的身份信息。
   - **两种负担**：常驻内容会带来上下文负担；让人记住有哪些文档会带来认知负担。认知负担只花在需要人判断的地方。
   - **信息分层**：分为文件内步骤、文件内参考、外置参考。所有情况都需要的内容放在文件内，只有部分情况需要的放到外置参考。同一概念的内容集中写；文档过长时，按情况或按顺序拆分。
   - **完成条件**：每一步都以可判定的完成条件结束。先把条件写清楚；只有写不清、并且确实出现过提前收工时，才把后续步骤拆到新的上下文里。
   - **表达**：用模型熟悉的概念词做关键词，尽量正向表述。只有无法正向表述的硬约束才用禁令，并同时给出正向目标。
   - **剪枝**：每个意思只在一处定义；能从环境里查到的不要复述；逐句检查是否还相关；模型默认就会做的事，整句删掉。
   - **调用方式**：只有 Agent 或其他 Skill 需要触发时，才设为可由模型调用。两个手动 Skill 共用的内容，放到普通文件里；手动入口多时，用一个路由 Skill 做索引。
3. **`my-ask-matt`**：在阶段边界按顺序判断，第一个成立的就是答案：
   1. 下一阶段需要原始上下文，或者空间还够 → 继续；
   2. 上下文对后续已经没用 → 清空；
   3. 要换宿主、换目录或仓库、交给同事、分出支线任务 → 交接；
   4. 任务不需要人干预就能完成 → 交给子 Agent；
   5. 以上都不是 → 压缩上下文，并说明要保留什么。

   除"继续"外，其他选项都会损失一部分原始信息。
4. **`my-improve-codebase-architecture`**：用户没有指定方向时，先看最近约 20 个提交，从反复改动的热点入手；热点分散时再扩大范围。"20"是本项目自定的数字，上游没有给出。
5. **`my-to-spec`**：删掉"也可称 PRD"这句说法。

**验收**
- AC-29（测试）`skills/` 下恰好是上面列出的 32 个 Skill；构建产物中没有 `references/composed/`；源码中没有复制正文的代码。
- AC-30（测试）组合清单中的被调用方恰好是那 11 个；三种宿主投影的调用元数据都符合"被调用方可由模型调用，其余只能手动调用"。
- AC-31（核对）冻结的 Skill 只有上面列出的全局改动。
- AC-32（核对）上游的 5 项都已吸收；`my-review-instructions` 采用了 `my-writing-for-agents` 的方法。

### 8. 技术方案（`my-tech-design`）

- **正文不写**：函数名、文件路径、逐字段映射、分页和排序、逐项列举的错误分支、测试用例清单、列长和索引细节。正文只写契约、口径和边界。
- **删除**"每个改动面都要在四处有位置"的要求。
- **固定章节**，压缩时也不能删：
  - "数据与接口变更"：逐项列出 Proto、RPC/HTTP、库表结构、数据变更 SQL、MQ、配置。有改动就贴实际的 DDL、DML 或 proto 片段，没有改动就写"无"。这类原文只出现在这一节。
  - "上线顺序"、"回滚"、"待确认项"。
- **与 Spec 的关系**：实现级的约定留在 Spec。读者能访问 Spec 时给链接；访问不了时，方案要能独立读懂。
- **被否方案和推翻条件**：默认只放在语义工件里。只有读者需要了解取舍时，才在正文写一句。
- **可选输入"参考文档"**：提供时，沿用它的章节结构和大致篇幅；表格单元格一般只写一两句。
- **交付前两步自检**，写进完成条件，并遵守审查循环规则中的文档审查规定：
  - 按最终态写作的要求审一遍；
  - 检查悬空引用。
- **草稿**只放在 `.agent/work/<topic>/designs/` 下。
- **可选阶段 `feishu <语义工件> [wiki 地址]`**：
  - 只读语义工件；内容有缺失时，返回 `blocked-by-content`；
  - 调用宿主已有的飞书文档工具写入；宿主没有这个工具时，停下并说明；
  - 给了 wiki 地址，就在该目录下创建；
  - 目标文档已有评论时，只更新有改动的章节；
  - 标注"未实测"。

**验收**
- AC-33（核对）以上内容已全部写进 `my-tech-design`。

### 9. 可读性与文本量

- runtime 已经强制的规则，从 Skill 正文中删除。正文只保留意图、判断标准和一两个例子。
- 面向用户的输出使用平实的中文，不用自造术语，也不出现内部状态名。
- `my-humanizer` 作为手动入口保留，不再是流程中的强制步骤。

**主链文本量 ≤ 35,000 字符**（约 1.75 万 token，比旧版减少约 40%；用户决定的上限）

测量方法：
- **对象**：`my-grill-with-docs`、`my-grilling`、`my-domain-modeling`、`my-to-spec`、`my-to-tickets`、`my-implement`、`my-tdd`、`my-code-review`、`my-review-design`，取构建后 Cursor 投影的安装件。
- **范围**：每个 Skill 的 `SKILL.md`，加上从它出发、经相对链接能到达的同一 Skill 目录下的全部 Markdown（传递闭包）。
- **计数**：所有文件按内容去重后，对 Python 字符串长度求和。
- **参考值**：用同样的方法测量旧版 release，并在对象中加入 `my-requirement-analysis`，约 58,300 字符。

**验收**
- AC-34（测试）提供测量函数和对应测试，断言结果不超过 35,000；测试注释中记录施工前测得的基线值。

### 10. 旧产物迁移

**旧格式**：旧版 runtime 产出或接受的格式，分为项目级和 Topic 级。

- **项目级**：旧配置（含已删除的键、`assurance_level: audited`，或 `schema_version` 不为 2），或者存在 `.agent/specs/`。
  - 除 `migrate` 外，所有读取配置的命令都停止，提示运行 `migrate`，不修改任何文件。
  - 代表性命令：`work-overview`、`topic status`、`implement status`、`implement start`、`validate-ticket`、`topic start`、`metrics`。
- **Topic 级**：Ticket 缺少 `test_commands` 或使用旧状态；存在不属于已完成 Ticket、且没被新记录取代的旧实施记录；按 Topic 分片的术语表。
  - 只有操作这个 Topic 的命令停止；`work-overview` 把它列为"需要迁移"。
- **历史记录**：属于已完成 Ticket、或已被新记录取代的旧实施记录，视为历史，不算格式错误。`.agent/archive/**` 不做检查。

**`migrate`**
- 不带 `--apply`：只输出摘要，列出将修改的文件、每类改成什么、无法自动判断的项；零写入。
- 带 `--apply`：依次执行
  1. 把 `.agent/` 复制到 `.agent/backup-<YYYYmmdd-HHMMSS>/`，不含 `.git/` 和已有的备份；
  2. 确保 `.agent/.gitignore` 含有 `backup-*/`；
  3. 执行转换；
  4. 按 I-A1 提交。
- 已经是新格式时，报告"无需迁移"。

**转换规则**
- **配置**：保留有效的键，丢弃已删除的键；`audited` 改为 `standard`；`schema_version` 设为 2。非 `local` 后端列为无法自动迁移。
- **Spec**：缺少 frontmatter 时，`spec_id` 从目录推断，`revision` 从文件序号推断；推断不出来的列进摘要。
- **Ticket 字段**：
  - 缺少的 frontmatter 从文件名和标题推断；
  - `test_commands` 填入全量测试集合，集合为空时列为无法迁移；
  - 推断不出来的列进摘要。
- **Ticket 状态与实施记录**

| 旧状态 | 新状态 | 实施记录 |
|---|---|---|
| `ready-for-agent` | `ready-for-agent` | 无 |
| `complete` | `complete` | 旧记录原样保留，作为历史 |
| `implementing`、`revalidated` | `implementing` | 新建一条记录：沿用旧记录的基线，不带测试和审查记录；旧记录作为历史 |
| `blocked-by-design`、`revising` | `needs-user`（原因："迁移自旧版阻塞"） | 同上 |

  - 旧记录没有基线的，列为无法迁移。
  - 迁移后违反 I-T3 的 Topic（旧版的并行实施），整个 Topic 列为无法自动迁移。
- **Topic**：
  - 含未完成 Ticket 的，按 M2 补建状态；
  - Ticket 全部完成的，直接归档，结果为 complete，注明"迁移归档"。
- **分片的术语与 ADR**：合并到 `.agent/CONTEXT.md` 与 `.agent/adr/`。有冲突的定义列进摘要，不自动合并。
- **`.agent/specs/`**：保留在备份中，然后删除。
- **交接文件**：原样保留。

**本仓库自身**：`.agent/matt-workflow.md` 转为新格式；`.agent/work/**` 不改动。

**验收**
- AC-35（测试）用施工前旧版 runtime 生成的样例运行 `migrate`。样例包括：旧配置、分片术语表，以及以下 Topic：
  - **A**：含 ready、complete、implementing 三张 Ticket；
  - **B**：只含一张 blocked-by-design 的 Ticket；
  - **C**：只含一张 revalidated 的 Ticket；
  - **D**：Ticket 全部 complete；
  - **E**：含一张 implementing 和一张 blocked-by-design。

  检查：
  - 不带 `--apply` 时零写入；
  - 带 `--apply` 时生成备份（不含 `.git/`），`.agent/.gitignore` 含有 `backup-*/`；
  - A 中 implementing 的 Ticket 能继续走完 `test → review → review --submit → finish`；
  - B 能通过 `resolve --accept`（测试通过后）完成，也能在修订后 `--reopen` 继续；
  - C 回到 implementing；
  - D 被归档，并注明"迁移归档"；
  - E 被列为无法自动迁移；
  - 再次运行时，除 E 外报告"无需迁移"。
- AC-36（测试）项目级旧格式时，代表性命令全部停止，文件不变。只有 Topic 级旧格式时，只影响该 Topic，`work-overview` 把它列为"需要迁移"。

### 11. 验证、度量、构建与文档

**删除**
- `evals/` 整个目录；
- `validate-evals`、`validate-agent-evidence`、`smoke` 三个命令，以及对应的模块和测试；
- `.gitignore` 中针对 evals fixture 的例外规则。

**`check`**
- 只运行 `tests/` 下的测试，包括：
  - runtime 单元测试；
  - 以测试形式实现的仓库静态校验：Skill 元数据、Markdown 链接、组合清单、资源清单、调用方式；
  - 端到端测试。
- 端到端测试在临时 git 玩具仓库中运行，以标准库 `unittest` 作为测试命令，通过子进程调用 CLI。覆盖 quick 与 standard、private 与 shared，以及各 AC 中的缺陷注入。
- `check` 不修改被跟踪的文件。

**度量**：`.agent/metrics.jsonl` 每行一条 JSON。

| 字段 | 取值 |
|---|---|
| `kind` | `ticket`（finish 或 accept）、`topic`（standard 完成、整分支接受、放弃、文档 Topic 完成）、`quick` |
| `topic` | — |
| `ticket` | 非 `ticket` 记录为 null |
| `level` | 文档 Topic 为 null |
| `started_at`、`finished_at` | — |
| `outcome` | `complete`、`accepted`、`abandoned` |
| `test_runs` | — |
| `review_rounds` | — |
| `findings` | `{blocking, advisory}` |
| `repair_rounds` | — |
| `needs_user_count` | — |
| `command_errors` | 因用法或校验错误导致的非零退出次数，不含测试失败 |
| `reviewer_provenance` | `independent`、`self`、`mixed` |
| `tests_configured` | — |

- runtime 观察不到的字段填 null。
- `metrics` 按 Topic 汇总。

**构建**：`build` 完成后清理 release，只保留当前版本、上一个版本，以及被安装状态引用的版本。

**命令清单**
- **保留**：`setup`、`validate`、`check`、`doctor`、`build`、`install`、`deploy`、`prune-releases`、`resolve-rules`、`inspect-rules`、`validate-ticket`、`work-overview`、`review-snapshot`、`artifact-review-snapshot`、`artifact-review-open`、`artifact-review-submit`、`artifact-review-verify`、`artifact-review-finalize`。
- **新增**：`topic`（`start`、`status`、`test`、`review`、`complete`、`abandon`）、`implement`（`start`、`test`、`review`、`finish`、`status`）、`resolve`、`migrate`、`metrics`。
- **删除**：`refresh-project`、`validate-evals`、`validate-agent-evidence`、`smoke`、`decision-gate`、`write-gate`、`ticket-transition`、`next-ticket`、`ticket-scope`、`run-context`、`run-start`、`implementation-open`、`implementation-submit`、`implementation-close`、`implementation-status`、`implementation-next-action`、`run-record`、`run-code-receipt`、`run-test-evidence`、`run-review-evidence`、`run-review-submit`、`run-review-open`、`implementation-repair-plan-open`、`implementation-repair-plan-review-open`、`implementation-repair-plan-review-submit`、`archive-spec`、`archive-topic`、`archive-show`、`archive-list`。

**README**：按新的流程、命令和配置重写，删掉已移除的功能。维护章节写明两条约定：
- 修改工作流的提交，要写一行 `Trigger:`，说明由哪个项目的什么问题触发；
- 在度量证明有必要之前，不新增门禁。

**验收**
- AC-37（测试）`python3 tools/workflow.py check` 在 Python 3.10 和 3.14 上通过，之后 `git diff --exit-code` 为 0。
- AC-38（测试）`workflow.py --help` 列出的命令恰好等于"保留"加"新增"；调用"删除"清单中的命令时，报"未知命令"。
- AC-39（测试）度量记录包含上表的全部字段；`metrics` 能按 Topic 汇总。
- AC-40（测试）`build` 之后，只剩当前版本、上一个版本，以及被安装状态引用的 release。
- AC-41（核对）README 写明了两条约定，且不再描述已删除的功能。

## 已确认的承重决策

以下决定都已经过用户确认。

- **LD-1 可恢复优先，而非可审计。**
  - 事实：唯一的使用者是用户本人；`.agent/.git` 中没有任何提交，没人复核审计记录。
  - 做法：保留 4 类机械检查（测试失败、审查后改动、越序、审查单元不匹配）；删除 `audited`、修复方案门禁、发布审查哈希链。
  - 推翻条件：出现外部审计要求，或逃逸缺陷上升。
- **LD-2 两个对齐点，写入授权固定。**
  - 事实：7 个项目中有 6 个改成了自动；用户对旧版两个极端预设都不满意；业界数据显示，用户会批准 97% 的逐条确认，却否决了 39% 的计划。
  - 被排除：保留预设，只改默认值。
  - 推翻条件：介入次数不降，或出现越权写入。
- **LD-3 两档等级，runtime 真正区分。**
  - 事实：旧版的三档在 runtime 中没有区别。
  - 推翻条件：quick 被用于跨边界的改动。
- **LD-4 独立审查，加统一的审查循环规则。**
  - 事实：
    - 偷懒的自审"通过"放过了语义缺陷；
    - 一次独立复审，在 3 张已通过的 Ticket 中查出 1 个 P1；
    - 那次 34 轮的审查中，73% 的阻断问题由修复引入，而且循环完全没有经过 runtime；
    - 本 Spec 自身的前几轮审查也重现了"修复引入新问题"。
  - 做法：runtime 只管理 Ticket 审查和整分支审查；文档审查由 Skill 文本约束，并留有日志。
  - 被排除：只加轮数上限；按模型档位分级；由 runtime 为文档审查计数（实测不能防止上述循环，还会引入对象标识、参数冲突等复杂度）。
  - 推翻条件：审查几乎总在上限处停下，或逃逸缺陷上升。
- **LD-5 小实施接口，加执行简报。**
  - 事实：一张干净的 Ticket 需要 13 条命令；测试失败时仍退出 0；实施过程中读文件约 600 次；测试命令只接受逐字相同；`ticket-transition` 可以绕过完成条件。
  - 被排除：保留旧命令，外面再包一层。
  - 推翻条件：命令报错次数高。
- **LD-6 调用方式由组合清单决定，取消正文复制。**
  - 事实：一个 release 中有 10 份 `my-review-design`；18 个 Skill 从未被调用。
  - 被排除：全部改为自动触发。
  - 推翻条件：出现未经请求的自动调用。
- **LD-7 不维护长期 Spec；统一以 `topic complete` 收尾；接受即完成。**
  - 事实：长期 Spec 从未被使用，依赖要删除的结构，而且会与代码背离；"已接受但仍在实施"的中间状态，会带来接受失效和测试命令无法生效等死路。
  - 推翻条件：确实需要按功能汇总的当前行为。
- **LD-8 迁移，而非兼容。**
  - 事实：7 个项目都是旧格式，其中有进行中的记录，也有完成后没归档的 Topic。
  - 推翻条件：大量内容落入"无法自动判断"。
- **LD-9 验证看行为，度量看结果。**
  - 事实：37 个 eval 场景只是复述规则；执行证据为 0；57% 的修复在 72 小时内被返工。
  - 推翻条件：删除后出现曾被 eval 捕获的回归。
- **LD-10 技术方案的体例约束。**
  - 事实：技术方案曾被写成实现清单；压缩时删掉了 SQL；草稿留在了仓库根目录。
  - 推翻条件：仍然写成实现清单。

## 验证策略

- **要证明什么**：核心模型的每一条状态迁移、前置条件和不变量；迁移；调用方式与投影；主链文本量。
- **现有基础**：`tests/` 下基于 `unittest` 的测试，已经会在临时目录构造仓库和 `.agent/`，可作为写法先例；统一入口是 `workflow.py check`。
- **新增**：端到端测试模块；文本量测量函数。
- **好测试的标准**：只断言外部行为，即命令结果、文件状态、提交、归档、度量。"核对"类 AC 由审查者对照本 Spec 核对。
- **自检**：runtime 完成后，逐行对照 M2–M5 中的表格和不变量，确认每一行至少有一个测试覆盖。

## 施工顺序

1. **先采集基线，这一步必须最先做。**
   - 用旧版 runtime 生成 AC-35 需要的旧格式样例，放在 `tests/fixtures/`；
   - 复制 `evals/fixtures/my-implement/unfinished-session/`；
   - 按第 9 节的方法测量旧版的文本量。
2. **runtime 核心**：按核心模型实现配置 v2、旧格式检测、`topic`、`implement`、`resolve`、`.agent` 提交、度量；同时删除旧命令。
3. **`migrate`**。
4. **组合清单与构建**：调用边与投影；删除正文复制和 portfolio；清理 release。
5. **Skill 与资源文本**：
   - 合并 Skill，吸收上游改动；
   - 新增两份共享资源："审查循环规则"和"找用户的完整条件"；
   - 移动 `my-research` 正文；
   - 改造 `my-tech-design`；
   - 同步冻结 Skill 的全局改动；
   - 精简到文本量上限以内。
6. **测试与清理**：端到端测试；删除 `evals/`；调整 `check`。
7. **README 与本仓库配置。**

实施时不需要使用本工作流自身的 runtime 或 Skill。

## 依据与未知

**依据**
- **用户确认**：
  - 全部承重决策与默认行为；
  - 核心模型中的各项选择：`--topic` 只用于选择；`resolve` 只处理 Ticket 和整分支；接受即完成；`--reopen` 的定义；文档审查由 Skill 文本约束；统一以 `topic complete` 收尾；自动补建；standard 必须有全量测试；迁移时直接归档已完成的 Topic。
- **仓库事实**：旧版的命令集、组合清单、资源清单、CI（Python 3.10 与 3.14，`check` 后执行 `git diff --exit-code`）、测试命令的逐字匹配、调用元数据校验、Ticket 字段与状态迁移表。
- **执行证据**：玩具仓库实跑与缺陷注入；34 轮审查会话的取证；7 个真实项目的只读统计。
- **外部来源**：`mattpocock/skills@c55ee46`，已写进第 7 节。

**假设与未知**
- **宿主派不出新上下文审查者**：退回自审，按 I-6 如实记录。
- **文档审查**：只靠 Skill 文本约束，强度弱于 runtime；是否足够，要靠审查日志和度量观察。
- **实际效果**：尚未测量。
- **飞书阶段**：无法实测。
- **35,000 字符上限**：如果不删承重内容就达不到，施工者应停下来，报告测量结果和剩余内容的构成，不得为了达标删除承重规则。
