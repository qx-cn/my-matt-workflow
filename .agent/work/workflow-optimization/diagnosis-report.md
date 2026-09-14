# my-matt-workflow 优化诊断报告

> 读者：项目维护者。用途：决定阶段②应确认哪些原则，以及阶段③先改什么。  
> 调研快照：2026-09-04。GitHub 数字会变化；Stars 只作为入选门槛，不作为质量结论。  
> 仓库说明：用户文本中的 `/Users/admin/wsp/futu/my-matt-workflow` 未挂载，本报告审计当前实际工作区 `/Users/sherly/CS/wsp/ai/my-matt-workflow`。

## 1. 调研发现（按文档类型分类，附来源链接与认可度指标）

### 1.1 面向人的文章与一般写作

| 对象 | 认可度、活跃度与采用证据 | 可复用结论 |
| --- | --- | --- |
| [`blader/humanizer`](https://github.com/blader/humanizer) | 约 39.3k Stars、3.4k Forks；2026-07 发布 2.9.x，近月仍有 2.11.x 演进；支持 Skills CLI、Claude 插件及跨 Agent 安装。 | 风格修改必须服从信息保真；按文本类型选择力度；有作者样本时匹配真实声音；禁止为了“自然”新增事实。值得借鉴的是“保留什么”的契约，而不是照搬禁词表。相关的近期信息丢失 [Issue #212](https://github.com/blader/humanizer/issues/212) 也说明：仅做表面去 AI 腔可能删掉排序、同时性等承重语义。 |
| [`mattpocock/skills`](https://github.com/mattpocock/skills) 中的 [`edit-article`](https://github.com/mattpocock/skills/blob/main/skills/personal/edit-article/SKILL.md?plain=1) 与 [`writing-shape`](https://github.com/mattpocock/skills/blob/main/skills/in-progress/writing-shape/SKILL.md?plain=1) | 仓库约 195.8k Stars、16.9k Forks；2026-08-06 仍有合并提交；官方 marketplace 与 `npx skills` 可安装。skills.sh 快照显示 `edit-article` 约 197.9k、`writing-shape` 约 298.8k 安装。 | 先确定读者的前置知识，再按信息依赖组织文章；每个段落/区块都应为读者完成一个任务；原始材料只读，发现材料缺口时明确暴露，不靠模型补造。表格、列表、正文、引用按信息形状选择，而不是默认一种形式。 |

此类文档的质量核心是“读者读完会发生什么”，其次才是自然度。`my-humanizer` 目前重视冻结区和事实保真，这是正确方向；不足在于上游文档 Skill 普遍没有先声明读者、用途和期望影响。

### 1.2 技术文档、方案、教程与报告

| 对象 | 认可度、活跃度与采用证据 | 可复用结论 |
| --- | --- | --- |
| [`anthropics/skills`](https://github.com/anthropics/skills) 的 [`doc-coauthoring`](https://github.com/anthropics/skills/blob/main/skills/doc-coauthoring/SKILL.md?plain=1) | 约 173.5k Stars、20.6k Forks；最近提交记录为 2026-08-21；Anthropic 官方维护，可用于 Claude.ai、API 与插件。 | 写作流程从“文档类型、主要读者、期望影响、既有模板”开始；逐节迭代；最后让无会话背景的新 Agent 以真实读者问题测试文档，并检查歧义、矛盾和隐含前置知识。这比作者自查更能发现“作者脑中有、文档里没有”的内容。 |
| [`github/awesome-copilot`](https://github.com/github/awesome-copilot) 的 [`SE: Tech Writer`](https://github.com/github/awesome-copilot/blob/main/agents/se-technical-writer.agent.md) | 约 38.5k Stars、4.9k Forks；GitHub 官方组织维护，2026-08-25 仍发布质量报告，近月仍有大量 PR；面向 GitHub Copilot 的公开定制集合。 | 不同读者需要不同深度：初级工程师需要定义与“为什么”，高级工程师需要直接的技术细节，技术负责人关心决策与团队影响，非技术方关心结果。代码示例应运行，版本与依赖应核实，事实应交叉引用官方来源。 |

技术文档不能只追求完整。好的技术文档先告诉特定读者要判断什么，再按风险逐层展开；准确性需要代码、运行结果和版本来源，而不是“写得像真的”。

### 1.3 面向 Agent 的 Spec、Prompt、Skill 与执行文档

| 对象 | 认可度、活跃度与采用证据 | 可复用结论 |
| --- | --- | --- |
| [`obra/superpowers`](https://github.com/obra/superpowers) 的 [`writing-skills`](https://github.com/obra/superpowers/blob/main/skills/writing-skills/SKILL.md?plain=1) | GitHub API 快照为 281,465 Stars、25,213 Forks，2026-09-03 仍有 push；也被打包进 OpenAI 的公开 [`plugins`](https://github.com/openai/plugins) 仓库。 | 先观察无 Skill 时的失败，再以同一场景验证 Skill；不同失败用不同表达：漏字段用结构槽位，行为分支用可观察条件，输出形状错误用正向配方，纪律逃逸才用禁令。单次样本不够，需 fresh context、多次重复并看方差。流程图只用于非显然决策或循环，不用于线性步骤。 |
| [`mattpocock/skills`](https://github.com/mattpocock/skills) 的 [`writing-for-agents`](https://github.com/mattpocock/skills/blob/main/skills/productivity/writing-for-agents/SKILL.md) | 认可度与活跃度同 1.1；该 Skill 在 skills.sh 快照约 197.3k 安装。 | 区分步骤与参考资料；每一步要有清晰、可检查且足够严格的完成条件；按分支做渐进披露；一个含义只保留一个权威位置；环境能便宜查到的事实不应抄进文档。指针写法决定 Agent 是否会加载目标，不能只看文件是否存在。 |
| [`anthropics/skills`](https://github.com/anthropics/skills) 的 [`skill-creator`](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md?plain=1) | 认可度与活跃度同 1.2；官方参考实现。 | 三层加载：metadata → `SKILL.md` → 按需 resources；确定性、重复性工作放脚本；变体资料分文件，只加载当前分支；用 eval 衡量触发与输出，不把结构校验当行为证明。 |

这一类文档不应套“人类文章要有温度”的规则。它们首先要低歧义、可寻址、可执行、可验证；自然语言润色不能改动命令、枚举、验收标准和状态语义。

## 2. 好 skill 的特质

综合三类对象，好的 Skill 有八个共同特质：

1. **入口准确**：名称与 description 让宿主知道何时用、何时不用，不把完整流程塞进 description。
2. **职责单一但能闭环**：完成一个可命名的用户任务；入口、执行、结束或交接都可观察，不把“输出下一条命令”误当完成。
3. **指令形状匹配失败类型**：缺字段用模板，条件行为用明确谓词，输出形状用正向配方，硬底线才用禁令。
4. **完成条件可检查**：每一步知道何时完成；关键声称能追溯到文件、命令、运行结果或用户确认。
5. **渐进披露有理由**：所有路径都需要的内容留在正文；分支专属参考按需加载；确定性规则尽量交给脚本或 runtime。
6. **面向实际消费者**：人读文档先定义读者、用途和决策；Agent 读文档优先结构、约束、状态与低歧义。
7. **保真且不过度决定**：不补造事实；不把仍未确认的选择写成最终设计；不在设计阶段固定可由实现阶段安全决定的细节。
8. **验证真实行为**：结构检查、确定性 contract、fresh-agent eval、真实项目 smoke 分层陈述；不能用第一层替代后两层。

简言之：好 Skill 不是规则多，而是以最少上下文稳定改变正确的行为，并留下能证明它确实改变了行为的证据。

## 3. 项目缺点诊断

### 3.1 可靠性问题比文案问题更急

- **代码审查可能审不到刚实现的代码。** `my-implement` 在提交前进入 review（`skills/my-implement/SKILL.md:17-19`），但 `my-code-review` 固定使用 `git diff <fixed-point>...HEAD`（`skills/my-code-review/SKILL.md:21-25`）。三点 Commit diff 不含 staged、unstaged 和 untracked 改动；当前流程又在 review 之后才 commit。Matt 上游的 [`implement` 文档](https://github.com/mattpocock/skills/blob/main/docs/engineering/implement.md) 也记录了同一未修复问题。结果是 review 可能因空 diff 失败，或只审到旧 Commit，形成假门禁。
- **`manual` 把内部方法调用与用户可见阶段交接混成一种“打印命令后停止”。** 默认 README 强调所有 Skill 手动调用；但 `my-implement`、`my-grill-with-docs` 都需要宿主在子阶段结束后恢复自己的状态和后续步骤。`skills/my-implement/SKILL.md:21-24` 与 `skills/my-grill-with-docs/SKILL.md:7-10` 没有恢复协议。阶段 0 的 `my-grill-me` 只是最小、已知实例；主链路仍有同类断链风险。
- **缺少持久的运行态。** Ticket 有 `status/blocked_by/claimed_by`，但没有记录一次 implement run 的 fixed base、当前子阶段、已审 diff 身份、失败原因、Spec 版本。中断后只能从松散文件推断，难以证明 review 和 test 针对的是同一批改动。

### 3.2 Spec 与 Ticket 过度规定，却缺少最终校验

- `my-grill-with-docs` 在访谈后要求产出“可执行计划”（`skills/my-grill-with-docs/SKILL.md:12-14`），随后主链又进入 `my-to-spec`，形成计划与 Spec 两个可能漂移的权威文本。
- `my-to-spec` 一方面宣称“不重新访谈”，另一方面强制再确认 seam（`skills/my-to-spec/SKILL.md:7,15-17`）；职责边界不清。
- “很长、非常全面”的用户故事清单（`skills/my-to-spec/SKILL.md:39-49`）会系统性制造上下文和审阅成本；“整个代码库 seam 理想数量是一个”（`:15`）把架构偏好写成跨项目硬结论，证据不足。
- `my-to-tickets` 既要求 Ticket 在新上下文中自足，又把规则来源、范围、约束等复制进每张 Ticket。自足是必要的，但复制的完整规则容易与 Spec、runtime 解析结果漂移；应只保留 Ticket 特有摘要和权威引用。
- `final-state-writing` 只规定“不保留被取代候选”，没有验证最终文档是否遗漏、矛盾或写错；“写得干净”不等于“写得正确”。

### 3.3 面向人输出的规则不统一

- `my-test-report` 已明确读者、用途、证据边界，是当前最成熟的人读文档 Skill。
- `my-tech-design` 虽声明默认读者，但把“只要存在关系就默认画图”“总览必须有图”写成硬规则（`skills/my-tech-design/SKILL.md:41,89-103`），与“只有明显降低理解成本才可视化”冲突。152 行正文加大模板与渲染义务，也让内容、排版、模板三者纠缠。
- `my-edit-article` 直接规定每段不超过 240 字符，却没有先问文章读者、载体、目标和作者声音；长度代理替代了读者效果。
- `my-research` 重视来源，但没有先定义报告的决策读者、需要作出的决定与摘要层级。
- `my-teach` 的教学设计质量较高，但没有明确把学习者类型作为首次硬输入；并硬编码 `/Users/admin/.agents/skills/humanizer/SKILL.md`（`skills/my-teach/SKILL.md:51`），不具可移植性。

### 3.4 验证覆盖与声明强度不匹配

- 仓库有 32 个 Skill、126 个 unittest 方法，但只有 5 个 eval scenario，覆盖注册表中的 7 个 Skill；按 Skill 数仅 15.6% 有 scenario。
- 当前 eval 主要校验 JSON contract 和源文件 SHA；这能防结构漂移，不能证明 Cursor/Codex/Claude 在真实上下文中按要求执行。
- 阶段 0 的新测试证明源文本不再输出 `/my-grilling` 或 `$my-grilling`，权威 `check` 也已通过；它仍不是三种真实宿主的端到端调用证据。后续报告不得把它写成已完成真实 smoke。

## 4. 可借鉴点（映射到具体文件）

| 借鉴点 | 建议映射 | 预期收益 |
| --- | --- | --- |
| “文档类型、读者、期望影响”作为人读文档的前三个输入 | `my-tech-design`、`my-test-report`、`my-research`、`my-edit-article`、`my-to-questionnaire`、`my-teach`、`my-review-design` | 避免一个模板服务所有人；章节与长度由决策任务决定。 |
| fresh-context reader test | 新增共享的文档最终校验资源，供 `my-to-spec`、`my-handoff`、`my-tech-design`、重要研究/报告按风险调用 | 发现隐含上下文、歧义、矛盾与检索失败。 |
| 信息保真优先于去 AI 腔 | `resources/humanizer.md`、`skills/my-humanizer/SKILL.md` 及所有 embedded 调用方 | 防止润色删掉排序、并行、否定、置信度和证据状态。 |
| 按失败类型选择指令形状 | `skills/my-writing-great-skills/SKILL.md` 与 eval 规范 | 少写泛化禁令；先观测失败，再决定模板、条件或 guardrail。 |
| 行为 eval：baseline → with-skill → 多次 fresh-context → 看方差 | `evals/`、`tools/workflow_lib/evals.py`、`smoke-registry.json` | 把“格式有效”与“Skill 有效”分开，优先覆盖主链断点。 |
| 精确 review 对象与独立审查上下文 | `my-code-review`、`my-implement`，必要时由 runtime 生成 review manifest | 确保 review 看到 staged、unstaged、untracked，并能证明 review 与提交对象一致。 |
| 一义一处、环境事实不抄写 | `resources/adapters/`、`my-to-tickets`、`project-rules.md` | 减少规则重复与失效缓存；Ticket 保留必要快照和权威引用。 |
| 模板/脚本按需加载 | `my-tech-design`、`my-teach`、`my-wizard` 及 `resources/manifest.json` | 主 Skill 保留方法，版式和机械校验下沉；不强迫所有分支加载。 |

## 5. 架构评估（含 H1/H2 验证结论）

### H1：不建议把六个 adapter 合成一个 `runtime-conventions.md`

**结论：挑战该假设，弊大于利。**

当前实测：六文件共 81 行、49 行非空、8,524 B，不是约 51 个物理行；它们分别为 composition 1,824 B、ticket selection 1,945 B、work scope 1,208 B、write actions 588 B、artifact access 515 B、project rules 2,444 B。

| 维度 | 当前拆分 | 合并后 | 判断 |
| --- | --- | --- | --- |
| DRY | 每个语义已有一个源文件，通过 `resources/manifest.json` 分发；没有同义副本。 | 仍是一个事实源，只是物理文件变少；不会减少语义重复。 | 无收益；若不同章节被多个 Skill 重新解释，反而容易产生隐性重复。 |
| 指针深度 | Skill → 对应 adapter，一级指针。 | Skill → 单文件锚点，仍是一级指针。 | 深度不变，只减少文件名数量。 |
| Skill 正文加载成本 | 按消费者只打包/读取需要的关注点。 | Markdown 加载通常是整文件；锚点不能保证只占用一个章节。 | 明显变差。只需 artifact access 的 `my-diagnosing-bugs`、`my-domain-modeling`、`my-review-design` 将从 515 B 升到 8,524 B，约 16.6 倍；`my-resolving-merge-conflicts` 约 14.5 倍。只有需要全部六项的 `my-implement` 持平。 |

真正问题不是“文件太多”，而是 `my-implement` 正文有 9 个 adapter 指针、同一链接重复出现，以及文档层与 runtime 已执行的判断没有统一结果载体。建议保留按关注点拆分，并让 runtime 输出一次解析后的“小型运行上下文/receipt”；Skill 引用结果，不重复解释命令细节。

### H2：其他架构优化空间

1. **把组合边分型**：至少区分 `router handoff`、`phase handoff`、`internal method`。`manual` 只控制用户可见的入口/阶段授权；显式调用宿主后，其内部方法若不扩大范围，应在宿主内执行并返回。阶段 0 已为单依赖薄入口做窄修，阶段③应统一模型。
2. **增加最小 run journal**：每次 implement 记录 Ticket id、Spec revision、base SHA、review snapshot、phase、test/review receipt、blocker。磁盘成为可恢复状态，不把控制流藏在聊天里。
3. **建立 artifact finalization gate**：将来源追踪、内部一致性、fresh-reader 重建、事实正确性分层；`my-review-design` 可复用其中只读检查，但不应承担所有文档类型。
4. **Spec 版本与 Ticket 血缘**：Ticket 记录来自哪个 Spec revision；修改设计时能算出 affected open tickets，不靠全文搜索猜测。
5. **缩小 Skill 正文中的 runtime 细节**：`project-rules.md` 等保留协议语义，参数与当前路径由 `runtime_entry --help` 和 receipt 提供；避免安装布局变化导致文字缓存失效。
6. **验证分层**：static/schema → deterministic runtime → fresh-agent behavior eval → 真实项目 smoke。`check` 可继续做前三层中的前两层；后两层单独报告，不能混成一个 `valid`。

当前值得保留的架构：源树与稳定 release 分离、shared resources 单一来源、写操作 gate、Ticket 依赖图和 source hash 校验。这些不是本轮需要推倒的部分。

## 6. 主工作流链路评估

`/my-grill-with-docs → /my-to-spec → /my-to-tickets → /my-implement → /my-test-report`

| 链路段 | 当前问题 | 建议目标态 |
| --- | --- | --- |
| grill-with-docs → to-spec | 前者已经准备“可执行计划”，后者又整理 Spec；manual 子 Skill 退出后无宿主恢复点。 | grill 只产出确认过的 decision ledger、术语与必要 ADR；to-spec 是唯一 Spec 生成者。内部 grilling/domain-modeling 返回宿主，不靠打印命令续链。 |
| to-spec | “不重新访谈”与 seam 确认冲突；长用户故事和单 seam 偏好制造无关细节；没有最终正确性 gate。 | 对已有决定只做综合；发现新承重决策则明确退回 targeted grill，不在 to-spec 偷偷访谈。模板按功能复杂度生成，强调不变量、范围、验收、未知与证据来源。 |
| to-spec → to-tickets | Spec 决策与 Ticket 规则复制，缺少 revision 血缘；Ticket 能否覆盖全部验收主要靠作者自查。 | 先建立 requirement → acceptance → ticket coverage 矩阵；每张 Ticket 引用 Spec revision，只内联本 Ticket 必需的约束。 |
| to-tickets → implement | `validate-ticket` 管结构与准入，但没有“设计后来失效”的状态转换；manual 的 TDD/review 交接会丢宿主连续性。 | runtime 支持 `pause-for-revision`；内部 TDD/review 返回结构化 receipt；实施只在已批准范围内自治。 |
| implement → code-review | review diff 不含未提交改动；untracked 也没有身份；两轴模板强调 smell 数量，弱化真实 Bug 路径、风险和测试缺口。 | claim 时固定 base；生成包含 committed/staged/unstaged/untracked 的不可歧义 review snapshot；发现须附路径、影响场景、证据、严重度和建议验证。修复后重审受影响项。 |
| implement → test-report | 报告 Skill 很成熟，但若上游 receipts 不结构化，只能从日志重建，容易把历史记录与本次证据混淆。 | test/review/runtime 都产出带对象身份的 receipt；报告只汇总，不重新猜测执行事实。 |

链路的首要目标不是再加一个 Skill，而是保证每次交接都传递“权威对象 + 版本/哈希 + 当前状态 + 下一步”，并且接收方能机械验证。

## 7. 文档 skill 读者导向审计

下表覆盖会产出文档、报告、评论或供人审阅文本的 Skill；Agent 主读文档也列出，以避免误套人类写作规则。

| Skill / 产物 | 主要读者 | 用途 | 读者最关心 | 审计结论 |
| --- | --- | --- | --- | --- |
| `my-edit-article` / 文章 | 文章目标受众、作者 | 让原稿更清楚且保留作者立场 | 论点、前置知识、证据、声音、载体节奏 | **缺口大**：只问结构，不问读者/用途/载体；240 字符上限不应是通用硬约束。 |
| `my-tech-design` / HTML 技术方案 | 不了解细节但要评审的工程师 | 判断方案是否成立、风险是否可接受 | 一句话结论、改动面、承重决策、代价、风险、验证 | **方向对，过度图示**：读者定义清楚，但“凡关系默认画图、总览必须画图”把版式置于理解收益之上。 |
| `my-test-report` / Markdown 测试报告 | 评审者、发布决策者 | 判断测了什么、没测什么、证据能说明什么 | 验收覆盖、实际运行、缺口、风险、可追溯性 | **最好**：读者/用途/证据边界明确；应把 receipt 输入标准化并继续控制篇幅。 |
| `my-teach` / 课程与参考资料 | 特定学习者 | 真正掌握并能在真实场景运用 | 先备知识、准确解释、递进、练习反馈、掌握证据 | **较好**：认知桥梁与练习原则强；开始前还需明确初学者/有基础及现实任务，移除绝对用户路径。 |
| `my-to-questionnaire` / 问卷 | 外部知情人；次要读者是发件人 | 一次异步回复填补决策缺口 | 为什么问、投入时间、优先问题、答案如何使用 | **好**：读者与用途最明确；应补“问题数量/预计耗时由收件人情境决定”，并做发送前歧义检查。 |
| `my-research` / 研究报告 | 当前决策者及后续复核者 | 用证据支持产品/技术决定 | 结论、证据强度、适用时间、分歧、对决定的含义 | **缺口中等**：来源规则好，但没有强制 decision question 与结论优先结构。 |
| `my-review-design` / 评审报告 | 方案 owner / 决策者 | 找出会阻碍批准或实施的问题 | 最严重问题、依据、影响、未知 | **较好**：明确只报实质问题并按影响排序；可增加 reader reconstruction 检查，但不应机械显示空分类。 |
| `my-code-review` / 审查报告 | 实现者、合并决策者 | 阻止错误代码进入下一步 | 可复现 Bug、需求偏差、风险、严重度、修复/验证方式 | **缺口大**：review 对象错误；固定两轴和 smell 清单可能产生噪声；没有统一严重度、置信度与回归证据。 |
| `my-improve-codebase-architecture` / 候选 HTML | 维护者 | 选择值得深入的架构机会 | 摩擦证据、收益、成本、风险、推荐强度 | **缺口中等**：决策信息齐全，但每个候选强制前后图，可能用装饰替代证据；临时文件也与统一产物策略不一致。 |
| `my-diagnosing-bugs` / 诊断结论 | 报告者、修复者 | 确认根因、复现与预防 | 准确症状、红/绿命令、根因证据、剩余不确定性 | **方法强，输出弱**：过程门禁详细，但没有短的最终诊断报告契约，容易把过程日志当结论。 |
| `my-domain-modeling` / 术语表、ADR | 未来工程师与 Agent | 统一语言、保存难逆转决策 | 精确定义、边界、例子；ADR 的背景/决定/代价 | **较好**：严格限制术语表不含实现；需把 ADR 的读者问题明确到“以后为何不重新争论”。 |
| `my-prototype` / 结论 Markdown | 设计决策者、实现者 | 用可抛弃证据回答一个问题 | 问题、实验边界、观察、结论、不能推出什么 | **缺口中等**：已有问题/结论/依据；应显式写假设、失败案例与外推边界。 |
| `my-triage` / Issue 评论 | 报告者、维护者 | 推进分类、补信息、决定下一步 | 已确认事实、具体缺口、为什么需要、下一动作 | **较好**：needs-info 模板清楚；`AGENT-BRIEF` 是 Agent 主读，应与人类评论分开优化。 |
| `my-wizard` / 向导与 README | 执行手工配置的人 | 安全完成外部 UI/配置步骤 | 当前一步、准确路径、秘密处理、进度、回滚 | **较好**：读者任务明确；动态外部 UI 必须核实，不应将易漂移路径硬编码进长期模板。 |
| `my-to-spec` / Spec | 人类批准者 + 实施 Agent | 固化当前设计与验收 | 人关心目标/范围/代价；Agent 关心不变量/验收/未知/证据 | **混合读者未分层**：长故事对两类读者都昂贵；应有决策摘要和机器执行区。 |
| `my-to-tickets` / Ticket | 实施 Agent；人类复核者 | 在新上下文完成一个纵向切片 | 自足范围、验收、依赖、权威来源、停止条件 | **Agent 导向正确**：但模板重复过多，且缺 Spec revision 与变更失效状态。 |
| `my-handoff` / 交接 | 新 Agent 为主，人类可审计 | 在新上下文恢复 | 当前目标、已确认决定、证据、风险、第一步 | **Agent 主读，不应用文章规则**：现有引用而不复制是对的；需要增加 source revision 与恢复完整性校验。 |
| `my-writing-great-skills` / Skill | Agent 为主，Skill 作者次要 | 稳定改变 Agent 行为 | 触发、步骤、条件、完成标准、失败场景 | **应保持 Agent 导向**：补 fresh-agent 多次行为 eval；不需要“更有温度”。 |

## 8. 机制问题方案（M1/M2/M3）

### M1：AI 写的代码怎么 review

**建议采用“对象固定 → 风险分层 → 独立审查 → 证据化发现 → 修复回归”的闭环。**可参考 Superpowers 的 [`requesting-code-review`](https://github.com/obra/superpowers/blob/main/skills/requesting-code-review/SKILL.md?plain=1)：每个任务后、重大功能后、合并前审查，并给 reviewer 精确需求与 base/head；也可参考 Anthropic 的 [`code-review` 插件](https://github.com/anthropics/claude-code/blob/main/plugins/code-review/README.md) 用独立视角、历史上下文与置信度过滤。但本项目不应照搬固定 4-agent 或 80 分阈值，应按个人工作流控制成本。

`my-code-review` 建议改为：

1. 明确三种目标：PR/commit range、已提交分支、当前工作树。工作树 review 必须包含 committed since base、staged、unstaged、untracked，生成文件清单与内容哈希；空对象直接失败。
2. 保留 Spec 与 Standards 两轴，但把“正确性/真实 Bug 路径”和“测试能否抓住回归”放在每轴共同的证据要求中；Fowler smell 只在确实影响此次改动时报告，不逐项扫清单。
3. 每条发现固定为：严重度、文件/行、失败场景或被违反的不变量、证据、影响、建议验证。无法说明可观察影响的只作为建议，不算 blocker。
4. 高风险变更按需增加 security/performance/data-consistency reviewer；低风险单 reviewer。隔离上下文用于减少实现者自证偏差，不为了并行而并行。
5. 修复 P0/P1 后运行针对性回归，再仅重审受影响 diff；所有 blocker 关闭后才进入 commit gate。

融入 `my-implement`：领取 Ticket 时记录 `BASE_SHA`；实现与测试后由 runtime 生成 review snapshot；review receipt 绑定 snapshot hash；修复会使 hash 变化，必须重审；commit 后核对 commit tree 与已通过 snapshot 等价。这样“review 过”才对应实际将提交的代码。

### M2：Spec 与会话文档的最终一致性、正确性校验

不要做一个模糊的“正确性评分”。把主张按来源分型，建立四道 gate：

1. **来源账本**：每条承重目标、约束、决定、验收、未知分别标记来源为“用户已确认 / 当前代码或配置 / 外部一手来源 / 推断”。没有来源的承重内容不得悄悄进入最终态。
2. **内部一致性**：检查术语、状态、枚举、范围、主流程、异常路径、验收是否在不同章节互相冲突；检查最终态是否残留被取代方案。可复用 `my-review-design` 的逻辑。
3. **无背景读者重建**：fresh Agent 只看文档，回答“目标、非目标、用户可见行为、关键不变量、失败路径、验收、未知”。将回答与来源账本比较；答不出或答偏说明文档缺上下文。Anthropic `doc-coauthoring` 的 Reader Testing 提供了成熟参考。
4. **事实正确性**：仓库事实重新读当前代码/配置并记录版本或 hash；外部事实核对一手来源与日期；算法/迁移等技术主张用例子、测试或原型验证；产品取舍只能由用户确认。不同证据类型分别给 `confirmed / assumed / missing`，不互相替代。

对 `my-to-spec`：写完草稿后先生成内部 coverage/claim ledger，再跑 gate；只有会改变目标、公开行为、范围或风险承担的问题才退回 targeted grill。对 `my-handoff`：额外检查所有路径/引用存在、状态与最后 receipt 一致、第一步能在新会话执行。小文档可只做来源与一致性自检；跨系统或承重设计再启动 fresh-reader。

### M3：implement 发现 Ticket 或 Spec 行不通时如何回退

**不默认重走完整访谈；按影响半径回退。**

| 发现类型 | 处理 | 是否访谈 |
| --- | --- | --- |
| Ticket 内可逆实现细节，目标/接口/验收/风险不变 | 记录证据，在 Ticket 内改实现，补测试，继续 | 否 |
| Ticket 拆分或依赖错误，但 Spec 仍成立 | 暂停当前 Ticket；修正依赖图或拆出新 Ticket；重新验证 frontier | 只确认会改变批准范围的部分 |
| Spec 的承重决定、接口、范围或验收失效 | 进入 `pause-for-revision`；写 change request，列出失败证据和受影响项；只对失效决策调用 targeted `my-grill-me`；生成新 Spec revision/amendment，再重建受影响 Ticket | 是，但只访谈受影响分支 |
| 根目标、用户价值或关键约束被证伪 | 暂停整个 initiative；从目标层重新对齐 | 可能需要完整访谈 |

部分 Ticket 已完成时，不篡改历史：完成项仍标记 complete，并记录它基于哪个 Spec revision；若新决定要求撤销或迁移其行为，新增 compensating/migration Ticket。尚未开始的受影响 Ticket 标记 superseded 或重新生成；进行中的 Ticket 保留工作树与证据，明确选择“继续利用 / 安全回退 / 丢弃原型”，任何破坏性回退另行确认。恢复前重新计算依赖 frontier、重新跑规则解析与 Ticket validation。

建议新增最小状态机：`implementing → blocked-by-design → revising → revalidated → implementing`。change request 至少包含触发证据、失效假设、影响的 Spec 条目/Ticket、已完成工作的影响、建议选项和恢复条件。

## 9. 改进建议清单：按优先级排序，每条附证据来源与影响范围

| 优先级 | 建议 | 证据来源 | 影响范围 |
| --- | --- | --- | --- |
| P0 | 修正 review 对象，覆盖 staged/unstaged/untracked，并用 snapshot/commit 等价性闭环 | 本地 `my-implement:17-19`、`my-code-review:21-25`；Matt 上游 [`implement` 已知问题](https://github.com/mattpocock/skills/blob/main/docs/engineering/implement.md) | `my-code-review`、`my-implement`、runtime、测试/eval |
| P0 | 重构 composition 语义：内部方法必须返回宿主；manual 仅控制入口或真正阶段授权 | 阶段 0 实际 bug；本地 `my-implement:21-24`、`my-grill-with-docs:7-10` | composition manifest/adapter、三个宿主 Skill、跨 Agent eval |
| P0 | 为 Spec/handoff 引入来源、一致性、reader reconstruction、事实正确性 gate | 当前 `final-state-writing` 只处理最终态；Anthropic [`doc-coauthoring`](https://github.com/anthropics/skills/blob/main/skills/doc-coauthoring/SKILL.md?plain=1) | `my-to-spec`、`my-handoff`、`my-review-design`、共享资源 |
| P1 | 精简 Spec：删除“很长用户故事”和通用单 seam 硬结论，改为按风险覆盖目标、边界、不变量、验收和未知 | 本地 `my-to-spec:15,39-49`；Matt [`writing-for-agents`](https://github.com/mattpocock/skills/blob/main/skills/productivity/writing-for-agents/SKILL.md) | `my-to-spec`、`my-to-tickets`、已有 eval fixture |
| P1 | 建立 Spec revision、Ticket 血缘与 `pause-for-revision` 回退状态机 | M3 的当前空白；现有 Ticket 只有准入/完成/选择 | Ticket schema、transitions/runtime、implement、handoff |
| P1 | 将 Skill 验证拆层，优先补主链 fresh-agent 行为 eval 与真实项目 smoke | 32 Skills / 5 scenarios；Superpowers [`writing-skills`](https://github.com/obra/superpowers/blob/main/skills/writing-skills/SKILL.md?plain=1) | `evals/`、smoke registry、CI/check 报告语义 |
| P1 | 为所有人读文档增加 reader brief；把图示改为收益条件而非默认义务 | 第 7 节审计；GitHub [`SE: Tech Writer`](https://github.com/github/awesome-copilot/blob/main/agents/se-technical-writer.agent.md) | `my-tech-design`、`my-edit-article`、`my-research`、`my-teach` 等 |
| P1 | 保留六 adapter 拆分；改为 runtime 输出一次已解析 context/receipt，清掉正文重复指针 | H1 实测：515 B → 8,524 B 的最坏加载膨胀；`resources/manifest.json` 已做选择性分发 | resources、manifest、runtime、主要宿主 Skill |
| P2 | 移除绝对用户路径，统一通过安装状态/环境解析共享 Skill | 本地 `my-teach:51` 在当前 `/Users/sherly` 环境即失配 | `my-teach`、安装器、可移植性测试 |
| P2 | 内容、版式、模板按加载与复用边界拆分；先从 `my-tech-design` 和 `my-teach` 做 | Anthropic [`skill-creator`](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md?plain=1) 的 progressive disclosure；当前 tech-design 152 行加大模板 | HTML/课程类 Skill、assets、check scripts |

建议阶段③按 P0 三项分别成批，每批 `check`；P1 先改 schema/runtime，再改 Skill 文案，避免先写一套稍后又被 runtime 推翻的规则。

## 10. 附录·原则草案：P1–P6 的采纳/修正/挑战

### P1 Skill 轻量有弹性

**建议：修正后采纳。**

保留“轻量、实现细节不在设计阶段写死、产品或难逆转决策上报用户”。补两条边界：一是安全、权限、数据兼容、证据真实性等底线必须明确且可执行；二是“难”不等于“要问”，只有会改变目标、公开接口、范围、测试投资或风险承担且无法从批准材料推断的决策才上报。普通可逆实现细节由 Agent 自治。依据是 `writing-for-agents` 的可检查完成条件与项目现有 `decision-taxonomy`。

### P2 面向人的文档读者导向

**建议：采纳并具体化。**

每个人读产物开始前明确：主要读者、用途、读完要作出的决定或动作、读者已有知识、最关心的风险。结论先行，正文只保留支持该决定的证据；长度由问题复杂度决定，不设统一“越短越好”或字符上限。`my-test-report` 可作为本项目基线，Anthropic reader testing 用于重要文档验收。

### P3 表达方式按读者选择

**建议：采纳，并用它修正 `my-tech-design`。**

人类文档只在图表能明显降低理解成本时使用；Agent 文档优先文字定义、结构槽位和可解析状态。图不能成为唯一规则载体。删除“有关系就默认画”“总览必须画”的普遍硬要求，改成先写读者问题，再选择最小表达。Superpowers 明确把流程图限制在非显然决策、循环与 A/B 选择，支持这一修正。

### P4 my-teach 课程质量

**建议：修正后采纳。**

开始前不只确认“初学者/有基础”，还确认现实学习任务、已有证据与成功标准。课程深度以能解释、能迁移、能完成真实练习为准；可增加篇幅和课数，但一课仍保持一个可验证收获。正确性通过一手来源、可运行例子、练习反馈和 learning record 共同证明，不能由语言流畅度代替。

### P5 my-humanizer 不造词

**建议：挑战绝对表述，改为窄而可执行的版本。**

采纳“不乱造词、不用生僻词、术语专业、描述简明、难点讲通俗”。但不应按语法形态一概禁止“动词 + 宾语”组合；`状态查询`、`规则解析` 等可能正是项目既有专业词。更稳妥的原则是：优先项目既有术语和模型已熟悉的常用词；不得为显得高级而自造抽象名词；确需新术语时先证明现有词无法准确表达、明确定义，并由用户确认。Matt 的 `writing-for-agents` 也认为新 leading word 可以定义，但现有词优先。

### P6 内容、排版、模板分离

**建议：修正后采纳。**

按职责与加载边界分离，而不是机械要求每个 Skill 都拆成三个文件：Skill 正文放方法与选择条件；内容事实来自输入/来源账本；复杂版式放 assets；机械校验放 scripts；大而分支专属的参考按需加载。很小且只用一次的模板可内联，避免为了“分层”增加无收益指针。H1 的实测正说明：文件分离要服务选择性加载，不能只追求目录整齐。
