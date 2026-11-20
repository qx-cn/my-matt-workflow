# 编写与审核参考

本文供本仓库迭代规则和 Skill 时按主题查阅，保存当前设计依据、研究边界及验证方法。本文不是另一份执行规范，普通业务写作和 Skill 运行无需读取；外部资料在相关迭代中按需重新查证，不设定期巡检。

---

## 1. 维护归属与设计理由

可执行要求由各自文件维护，本文只解释理由和适用边界；以下链接用于维护定位，不要求运行任务时逐一遍历。

| 内容 | 主定义位置 | 分开的理由 |
| --- | --- | --- |
| 通用写作与行为规范 | [全局规则](../rules/global.md) | 避免多个 Skill 各自维护完整规范 |
| 仓库约定与资料入口 | [仓库准则](../AGENTS.md) | 当前约定可直接找到，研究材料按需读取 |
| 评审向内容裁剪与纯 Markdown 写作 | [方案写作 Skill](../skills/my-tech-design/SKILL.md) | 剥离 XML/HTML/DSL 格式负担，专注读者视角、人话表达与极简图意 |
| 飞书/画板/HTML 视觉排版与确定性校验 | [排版发布 Skill](../skills/my-doc-publish/SKILL.md) | 承接定稿 Markdown 独立处理留白分区、画板防撞框与版式脚本门禁 |
| 审核动作、盲读与复查上限 | [审核 Skill](../skills/my-review/SKILL.md) | 区分无背景文档盲读与源码审查，防止逼技术方案塞满内部代码细节 |

集中定义与必要的任务提醒可以并存。[Cursor Rules](https://cursor.com/docs/rules) 建议：“Reference files instead of copying their contents.” 本项目据此优先引用，保留执行需要的短提示；这不是允许在多处维护完整定义或例外。

文件数和行数都不能单独证明维护成本下降。减少重复定义可以缩小常见修改范围，但宿主运行时会将常驻规则、项目准则与所调用的 Skill 合并注入同一上下文（[Claude Code Memory](https://code.claude.com/docs/en/memory#write-effective-instructions) 指出：“if two instructions contradict each other, Claude may pick one arbitrarily”）。

因此规则含义或边界改变时，需同步核对关联文件中的上下游规则、模板、校验脚本及设计理由；需要例外时回上游收窄适用前提，不在局部硬写矛盾条文。规范已在上下文中时无需反复读取，仅有文件路径或软链也不能证明执行者已读到正文。

### 内容写作与视觉排版的阶段解耦

将“面向读者的内容选材与人话写作（`my-tech-design`）”同“飞书 XML / 画板 JSON / 本地 HTML 渲染（`my-doc-publish`）”拆分为前后两个独立阶段，依据以下工程实践与实证研究：

- **提示链拆分降低单步负荷**：[Anthropic: Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents) 在论述 Prompt Chaining 时指出，将复杂文档任务拆解为顺序子步骤可通过降低单步复杂度提升准确度（原文：“trading off latency for higher accuracy, by making each LLM call an easier task”），并在 Appendix 2 提醒避免生成内容时背负繁重格式转义负担（原文：“Make sure there's no formatting 'overhead' such as... string-escaping any code it writes”）。
- **并发约束叠加引发指令遵循坍塌**：实证研究 [Large Language Models Can Follow Instructions, But Not Many at Once (ArXiv 2608.12426)](https://arxiv.org/abs/2608.12426)（在 15 个模型、36 类确定性可验证约束上测试 \(k=1..12\) 组合）与 [When Instructions Multiply (ArXiv 2509.21051)](https://arxiv.org/abs/2509.21051) 表明，单次生成叠加多项约束时整体满足率显著衰减，其中需全程追踪的结构类约束退化速度约为词汇约束的 \(2\times\)。
- **本地工程迁移边界**：上述论文结论仅适用于其单轮多约束受控基准，不能直接换算为本项目的固定条数阈值；结合本地实测观察（单步混做 340 行 Spec 删减、反黑话改写、飞书 XML 与多块画板坐标时，模型退化为照搬 Spec 密文并产出撞框画板），本项目采用“纯 Markdown 定稿 + 独立排版渲染 + 脚本确定性门禁”架构。

### 上下文与指示长度

简洁的目标是保留足够信息并处在恰当的抽象高度（Right Altitude），而非追求最少字数或堆砌边缘特例清单。[Anthropic Skill 编写指南](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) 提醒：“Only add context Claude doesn't already have.” [Claude Code 官方最佳实践](https://code.claude.com/docs/en/best-practices) 给出明确删减判据（原文：“1. Could it find this by reading the code? 2. Would it actually go and look? If both are yes, leave it out”），并指出反复靠加粗强调仍易漏掉的硬性规则应升级为确定性脚本或 Hook（原文：“If you keep adding emphasis to a `CLAUDE.md` line and Claude still misses it, that's a sign the line belongs in a hook”）；[OpenAI Harness Engineering](https://openai.com/index/harness-engineering/) 同样强调在自定义 Linter 报错信息中直接注入修复指引（原文：“we write the error messages to inject remediation instructions into agent context”），[Cursor Agent 最佳实践](https://cursor.com/blog/agent-best-practices) 建议规则从简、仅在重复犯错时按需补充（原文：“Start simple. Add rules only when you notice the agent making the same mistake repeatedly”）。[Context Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) 同时强调在硬编码脆弱特例与空洞口号之间保持平衡，用通用原则配合简短典型的正反例引导行为。

[OpenAI 的 GPT-6 Astra 编写建议](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra) 强调精确的触发描述、按需展开材料，并提醒：“consider which models will use the instructions you leave behind”。这支持在轻量经济模型（如 `hydrogen` / `Haiku`）上实测拆分步骤与脚本兜底，不支持在未验证时盲目删掉关键边界。

这些建议支持按需读取参考资料及合并重复条文，不证明某个固定长度必然有效。[Claude Code Memory](https://code.claude.com/docs/en/memory#write-effective-instructions) 建议每份 CLAUDE.md “target under 200 lines”；[OpenAI AGENTS.md 文档](https://learn.chatgpt.com/docs/agent-configuration/agents-md) 说明默认合并大小限制为 32 KiB，WorkBuddy 则将其用户记忆文件 `MEMORY.md` 硬截断到 4000 个字符（由 `scripts/sync.sh --check` 自动校验 `rules/global.md` 不超过该容量上限）。本仓库按规则是否必要、清晰、无冲突及实际效果判断；确定性版式与画板碰撞检查交给 `check_html.py` 与 `check_feishu.py` 执行。

### 四项审核原则的依据

审核 Skill 中的四项原则是本项目对评估和上下文方法的应用，不是厂商发布的固定清单。

- **目标的依据**：[Anthropic 成功条件与评估](https://platform.claude.com/docs/en/test-and-evaluate/develop-tests) 强调具体、可衡量且与实际需要相关的成功条件。本项目将其用于判断计划是否解决原始需求。
- **措施的依据**：[Agent 评估指南](https://www.anthropic.com/research/demystifying-evals-for-ai-agents) 区分执行记录与最终结果，并建议检查失败轨迹。本项目据此追问措施依赖的条件；具体因果判断仍需任务证据。
- **成本的依据**：Context Engineering 将上下文视为有限资源；将执行和维护成本纳入方案审核，是本项目的工程判断，不是该文章规定的通用成本公式。
- **证据的依据**：Agent 评估指南结合任务、判定标准、重复试验和记录检查。本项目将其用于限制效果主张，官方出处只支持对应事实或建议。

---

## 2. 厂商指南与工程实践

产品机制以对应厂商的现行文档为准，工程文章用于提出待验证的改进方向。模型成绩和厂商声誉不能替代建议与本地问题的对应关系。

### 宿主机制

查加载、导入和调用方式时，使用实际宿主的文档，不将一个产品的机制推及其他产品。

- [Anthropic Agent Skills Best Practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)：按需加载、描述编写、自由度与评估。关于第三人称和触发描述的建议有具体产品语境。
- [Claude Code Best Practices](https://code.claude.com/docs/en/best-practices)：上下文管理和实际工作验证。
- [Claude Code Memory](https://code.claude.com/docs/en/memory)：CLAUDE.md 与导入机制。原文说明“there’s no guarantee of strict compliance”，所以规则进入上下文不等于每次都遵守。
- [OpenAI Build skills](https://learn.chatgpt.com/docs/build-skills)：查 Codex 的本地 Skill 发现、软链支持和调用配置；页面中的 ChatGPT 分发方式与 Codex 本地加载分别适用。
- [Cursor Rules](https://cursor.com/docs/rules)：查 User Rules、项目规则、作用范围和引用机制。
- [Cursor Skills](https://cursor.com/docs/skills)、[Cursor Subagents](https://cursor.com/docs/subagents)：查手动调用、材料可见性和子 Agent 上下文。
- WorkBuddy 本地适配：桌面端扫描配置根目录下的 `skills/`（跟随软链并支持 `disable-model-invocation`），并将配置根目录下的 `MEMORY.md` 作为用户级记忆注入（硬截断为 4000 字符）；本仓库通过可选环境变量 `WORKBUDDY_CONFIG_DIR` 按需建立软链，避免在未安装该宿主的机器上创建目录或在公开仓库硬编码专有路径。

### 授权与浏览器环境

授权范围和宿主技术权限分别判断。明确授权范围内的常规工作可以自主完成，业务规则或授权范围的变化仍需确认。[Claude Code 最佳实践](https://code.claude.com/docs/en/best-practices) 区分模型判断与权限、沙箱等强制控制。

[Playwright CLI](https://github.com/microsoft/playwright-cli/blob/main/README.md) 推荐编码 Agent 使用 CLI，同时说明“MCP remains relevant”，列出持续状态和探索自动化等场景。[Anthropic 浏览器安全指南](https://support.claude.com/en/articles/12902428-use-claude-in-chrome-safely) 建议使用不含敏感账户的独立 Profile；公开网页与开发验证使用独立环境，必要时复用已授权个人登录态，是本项目基于任务需要和账户暴露范围的工程判断。

[Playwright 扩展](https://github.com/microsoft/playwright/blob/main/packages/extension/README.md) 的 Token 用于省去连接批准，不定义网站业务操作的授权。[CLI](https://github.com/microsoft/playwright-cli/blob/main/README.md) 的 `detach` 可以断开控制并保留外部浏览器。[Playwright 认证指南](https://playwright.dev/docs/auth) 提醒认证状态可能包含敏感 Cookie 和请求头，不应提交仓库。

### 模型提示与运行环境

- **Google**：[Gemini 提示设计指南](https://ai.google.dev/gemini-api/docs/prompting-strategies) 说明：“These guidelines and templates are starting points.”
- **Cursor**：[Harness 效率实践](https://cursor.com/blog/improved-token-efficiency) 讨论精简失去作用的指示、按需加载工具及子 Agent 的“coordination tax”；[Harness 迭代实践](https://cursor.com/blog/continually-improving-agent-harness) 将离线评估与实际使用反馈结合。
- **DeepSeek**：[工具调用文档](https://api-docs.deepseek.com/guides/tool_calls/) 明确：“The model itself does not execute specific functions.”
- **Google ADK**：[评估指南](https://adk.dev/evaluate/) 区分“Evaluate Trajectory and Tool Use”与“Evaluate the Final Response”。

### 单一设计文档、独立审查隔离与规格同步

- **退役重型多文档，收敛为单一设计文档**：[Martin Fowler 站点对 Spec-Driven Development 的实测反思](https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html)指出，多步 SDD 工具生成大量重叠且照抄代码的 Markdown 文件，审查负担甚至重于直接审代码（原文：“They were repetitive, both with each other, and with the code that already existed... I’d rather review code than all these markdown files”）；[Claude Code 官方最佳实践](https://code.claude.com/docs/en/best-practices)明确建议代码里能直接读到的内容不要写进规格文档（原文：“1. Could it find this by reading the code? 2. Would it actually go and look? If both are yes, leave it out”）；[OpenAI Harness Engineering](https://openai.com/index/harness-engineering/) 与 [Cursor Dynamic Planning](https://cursor.com/blog/dynamic-planning-agents) 同样强调小改动用轻量临时计划，复杂需求守住业务不变量与架构边界而非在文档中微操代码实现（原文：“By enforcing invariants, not micromanaging implementations”）。本项目据此退役重叠的代码级 `spec.md` 与独立 `decided.md`，一个需求只维护唯一一份 `design.md`（及对应飞书文档），内含对外契约、关键规则、方案取舍表与验收场景，编码阶段结合宿主 Plan Mode 与自动化测试闭环。
- **显式触发控制时机**：[Claude Code Skills 文档](https://code.claude.com/docs/en/skills)指出需由人控制时机的工作流应设置 `disable-model-invocation: true`（[Cursor Skills](https://cursor.com/docs/skills) 同理，[OpenAI Build skills](https://learn.chatgpt.com/docs/build-skills) 使用 `allow_implicit_invocation: false`）。本项目将 4 个核心 Skill 统一设为手动调用。
- **会话操纵、独立审查与规格同步**：[Claude Academy Subagents 指南](https://academy.claude.com/courses/introduction-to-subagents/using-subagents-effectively)与 [Claude Code 官方最佳实践](https://code.claude.com/docs/en/best-practices)指出，将同一任务委托给子 Agent 并不会变得更聪明，但未见过编写过程的只读审查子 Agent 能有效消除作者盲区（原文：“A fresh reviewer does help, because it hasn't seen your reasoning”）；同时强调任务切换时清空上下文、连续两次纠正失败就回退重开（原文：“after two failed corrections run `/clear` and write a better prompt instead of a third”），以及修 Bug 时先写可复现的失败测试再修复（原文：“write a failing test that reproduces it, then fix it”）。[Cursor Agent 最佳实践](https://cursor.com/blog/agent-best-practices) 同样建议实现跑偏时回退改动、改清计划重跑（原文：“Instead of trying to fix it through follow-up prompts, go back to the plan. Revert the changes, refine the plan... and run it again”）；[Design Docs at Google](https://www.industrialempathy.com/posts/design-docs-at-google/#implementation-and-iteration) 指出未上线系统的设计变更应同步更新设计文档。本项目已将上述官方厂商准则固化进 `rules/global.md`、`AGENTS.md`、4 个核心 Skill 与 `README.md`。

---

## 3. 写作依据与表达风险

### Google 官方写作指南与领域统一语言

- 术语与统一语言：[Google Words](https://developers.google.com/tech-writing/one/words)（“apply the same unambiguous word or term consistently”）与 [Martin Fowler: Ubiquitous Language](https://martinfowler.com/bliki/UbiquitousLanguage.html) 强调在代码、文档与团队讨论中严格使用同一套领域词汇。本项目明确要求团队日常固定使用的英文系统简称、动作词与对象名（如 `Approve`、`Reject`、`Dry Run`、`Webhook`）原样保持英文，禁止模型按字面猜全称机翻或在多套中文译名间摇摆。
- 消除句内罗列与渐进式展开：[Lists and tables](https://developers.google.com/tech-writing/one/lists-and-tables) 指出句内堆砌多项的 Embedded list 极难阅读（“Generally speaking, embedded lists are a poor way to present technical information. Try to transform embedded lists into either bulleted lists or numbered lists”），并要求表格保持单元格精炼（“Tables should have clear headers, concise cell content”）；[Organizing large documents](https://developers.google.com/tech-writing/two/large-docs) 强调渐进式展开（Progressive Disclosure），避免在主线开头同时倾倒过多边缘概念。本项目据此在 `TEMPLATES.md` 固化状态矩阵、存量接口校验切换表、跨组件时序图（[Fowler: State Machine](https://martinfowler.com/dslCatalog/stateMachine.html) 与 [Decision Table](https://martinfowler.com/dslCatalog/decisionTable.html)）及边缘兼容收尾小表，并在 `check_feishu.py` 硬拦截分号句内罗列与超长表格单元格。
- 标题与图示：[Headings and titles](https://developers.google.com/style/headings) 支持简短动宾或名词短语，不手写序号；[Illustrating](https://developers.google.com/tech-writing/two/illustrations) 提出先写结论式图注再画图（“write the caption before creating the illustration... They explain the takeaway”），并限制单图信息密度（“strive to avoid visual run-ons”）。

### 项目实践与中文工程表达

- **中英文句法差异与反电报体黑话**：
  - **研究观察**：[PNAS 2025](https://www.pnas.org/doi/10.1073/pnas.2422455122) 观察到指令微调模型名词化频率高于人类基线；[ArXiv 2506.05339](https://doi.org/10.48550/arxiv.2506.05339) 与 [ACL 2025](https://doi.org/10.18653/v1/2025.acl-long.1308) 证实偏好模型对冗长、专业行话（`jargon`）和列表格式存在显著偏置；[MT Summit 2025](https://aclanthology.org/2025.mtsummit-1.8/) 显示机译语料转折连词频率超原生中文两倍。
  - **项目选择**：保留原生英文缩写与真实代码名，团队日常固定直呼英文的服务简称和动作词原样保留英文；首次提及新概念或后置动作时先用白话讲明作用，新增对外文件配真实样例，标题只写单一主题（禁顿号堆砌），根除缺宾语简称、机翻词与生造四字标签（脚本用视觉字宽放宽正常解释空间，同时硬拦截表格超长单元格与分号堆砌），并停用面向英文散文的通用 `humanizer`。
- **受众分离、扫读信号与工程图表的三层边界**：
  - **外部依据**：
    - **扫读与邻近分组**：[NN/g Layer-Cake Scanning](https://www.nngroup.com/articles/layer-cake-pattern-scanning/) 与 [How People Read Online](https://www.nngroup.com/articles/how-people-read-online/) 指出读者主要注视各级标题与显著块来定位目标小节（“fixations made mostly on the page’s headings and subheadings... front-loading”），并建议按格式塔邻近原则（Gestalt proximity）用恰当间距和带边框或底色的分块区分不同内容组。
    - **信号原则与中文行内格式避坑**：多媒体学习信号原则研究（[Mayer 综述引述](https://doi.org/10.47941/jep.3588)、[Cognitive Processing 实验](https://link.springer.com/article/10.1007/s10339-020-01002-5)）证实，对关键结构与核心词做颜色或粗体标记可降低外在认知负荷，但过度或不一致涂色会削弱提示效果（“Overuse or poorly designed cues can overwhelm or distract learners, reducing their effectiveness”）；W3C [中文排版需求 CLReq](https://www.w3.org/TR/clreq/#emphases) 指出汉字印刷传统中一般不使用机械斜体做强调（无原生斜体字库时几何倾斜易发虚锯齿）。本项目据此将胶囊高亮与彩色文字放在白底正文与竖线结论块（`<blockquote>`）中而非叠涂在同色 `<callout>` 内，辅以废弃项 `<del>` 与核查清单 `<checkbox>`，避开中文斜体与非链接下划线。
    - **架构与状态图表标准**：[C4 Model Notation](https://c4model.com/diagrams/notation) 强调每张图应具备标明类型与范围的标题、自解释的容器职责短句及单向具体动作连线标签（“ask yourself whether each diagram can stand alone, and be (mostly) understood without a narrative”）；[Design Docs at Google](https://www.industrialempathy.com/posts/design-docs-at-google/)、[Martin Fowler ADR](https://martinfowler.com/bliki/ArchitectureDecisionRecord.html) 与 [Gergely Orosz RFC 指南](https://newsletter.pragmaticengineer.com/p/rfcs-and-design-docs) 强调设计文档服务于快速理解决策与边界。
  - **项目落地（三层职责划分）**：
    1. **脚本硬门禁**（`check_feishu.py` / `check_html.py`）：自动检查一级大章 `<hr/>` 分割线与二级小节 `<p></p>` 空行留白、`<checkbox>` 禁套 `<p>` 防错行、段落与表格单元格字宽上限、长命令外提代码块、单段密集 `<code>` 灰框上限、分号连串罗列、窄栏禁塞代码或宽表，以及画板自适应高度、连线 `label` 与显式锚点防撞框。
    2. **Skill 默认结构与视觉映射**（`my-tech-design` 自动衔接 `my-doc-publish`）：按讲方案顺序写背景和具体能力、主干居前兼容收尾；按需选用状态权限矩阵、存量接口校验切换表、跨服务时序图与文件样例；按内容需要搭配 `<blockquote>` 结论块、`<grid>` 双栏卡、警示 `<callout>` 与白底重点高亮。
    3. **人工微调留白**：将画板像素级拖拽、特定参会人关注点的临时标黄及等价表格/卡片取舍留给作者在飞书页面微调，不把主观偏好硬写成死配额。

---

## 4. 研究证据的采用边界

各来源按自身证明范围采用，不跨场景外推：

- **产品文档**：核对当前入口、版本和适用产品。
- **实证研究**：核对论文正文、实验模型、任务与比较基准；结果只支持匹配的实验范围，不将论文实验数字直接换算成本项目硬阈值。
- **较早资料与工程实践**：区分已发布能力、厂商自身观察与跨宿主适用性；无法核实的主张不作为设计依据。

---

## 5. 验证方法与未验证假设

改动前固定问题基线与判定标准，优先使用未参与规则编写的真实跨项目样本（Held-out Case）以及目标经济模型（如 `hydrogen`）做端到端生成与人类阅读体验对照，不由待审的新版 `my-review` 自举批准自身产出。具体现场材料存于本地非同步目录，不提交公开仓库。
