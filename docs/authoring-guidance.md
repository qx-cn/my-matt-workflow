# 编写与审核参考

本文供本仓库迭代规则和 Skill 时按主题查阅，保存当前设计依据、研究边界及验证方法。本文不是另一份执行规范，普通业务写作和 Skill 运行无需读取；外部资料在相关迭代中按需重新查证，不设定期巡检。

---

## 1. 维护归属与设计理由

可执行要求由各自文件维护，本文只解释理由和适用边界；以下链接用于维护定位，不要求运行任务时逐一遍历。

| 内容 | 主定义位置 | 分开的理由 |
| --- | --- | --- |
| 通用写作与行为规范 | [全局规则](../rules/global.md) | 避免多个 Skill 各自维护完整规范 |
| 仓库约定与资料入口 | [仓库准则](../AGENTS.md) | 当前约定可直接找到，研究材料按需读取 |
| 需求澄清与代码前置核查 | [澄清 Skill](../skills/my-grill/SKILL.md) | 先查源码再分批追问边界与取舍，源头避免自造黑话 |
| 单一方案内容与增量契约写作 | [方案写作 Skill](../skills/my-tech-design/SKILL.md) | 剥离 XML/HTML/DSL 格式负担，专注读者视角、增量契约与配图策划 |
| 飞书/画板/HTML 视觉排版与确定性校验 | [排版发布 Skill](../skills/my-doc-publish/SKILL.md) | 承接定稿 Markdown 独立处理留白分区、画板宽屏精修与两级脚本校验 |
| 审核动作、盲读与复查上限 | [审核 Skill](../skills/my-review/SKILL.md) | 区分无背景文档盲读与源码审查，按路径引用原始规范文件，防止逼技术方案塞满内部代码细节 |

集中定义与必要的任务提醒可以并存。[Cursor Rules](https://cursor.com/docs/rules) 建议：“Reference files instead of copying their contents.” 本项目据此优先引用，保留执行需要的短提示，不在多处维护重复的完整定义；`my-review` 审查时同样按产物类型传入原始规范文件路径，不抄写上游条文副本。

文件数和行数都不能单独证明维护成本下降。宿主运行时会将常驻规则、项目准则与所调用的 Skill 合并注入同一上下文，而 [Claude Code Memory](https://code.claude.com/docs/en/memory#write-effective-instructions) 指出：“if two instructions contradict each other, Claude may pick one arbitrarily”。

因此规则含义或边界改变时，需同步核对关联文件中的上下游规则、模板、校验脚本及设计理由；需要例外时回上游收窄适用前提，不在局部硬写矛盾条文。规范已在上下文中时无需反复读取，仅有文件路径或软链也不能证明执行者已读到正文。

### 内容写作与视觉排版的阶段解耦

将内容选材写作（`my-tech-design`）与飞书 XML / 画板 JSON / 本地 HTML 渲染（`my-doc-publish`）拆分为前后两步，依据以下工程实践与实证研究：

- **提示链拆分降低单步负荷**：[Anthropic: Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents) 指出将复杂文档任务拆为顺序步骤可降低单次调用难度（原文：“trading off latency for higher accuracy, by making each LLM call an easier task”），并在 Appendix 2 提醒避免内容生成时背负繁重格式转义负担（原文：“Make sure there's no formatting 'overhead' such as... string-escaping any code it writes”）。
- **并发约束叠加引发遵循率下降**：实证研究 [Large Language Models Can Follow Instructions, But Not Many at Once (ArXiv 2608.12426)](https://arxiv.org/abs/2608.12426)（测试 15 个模型在 k=1..12 条确定性约束下的表现）与 [When Instructions Multiply (ArXiv 2509.21051)](https://arxiv.org/abs/2509.21051) 表明，单次叠加多项约束时整体满足率显著衰减，其中结构类约束退化速度约为词汇约束的 2 倍。
- **本地工程迁移边界**：上述论文仅针对单轮受控基准，不能直接换算为固定条数上限。结合本地实测观察，本项目采用“纯 Markdown 定稿 + 独立排版渲染 + 脚本两级校验”架构；同时遵循 [Claude Academy Subagents 指南](https://academy.claude.com/courses/introduction-to-subagents/using-subagents-effectively) 对串联子 Agent 丢失中间上下文（Sequential Subagent Pipelines）的警示，用定稿 `design.md` 交接已决定的需求和设计，在干净会话中由主 Agent 直接顺序完成写作与排版，仅在已积攒大量排障日志的长会话中才派子 Agent 隔离。

### 上下文与指示长度

遇到长 diff 或被截断的输出，保留文件路径和已核实的位置，需要时再读取原文。Anthropic 将这类做法称为保留 “lightweight identifiers”，也建议为循环设置 “stopping conditions”。本仓在审查中按问题交回证据和缺口。若定向查询仍无进展，就交回部分结论，续查只补缺口。[上下文工程](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) · [构建 Agent](https://www.anthropic.com/engineering/building-effective-agents)

简洁的目标是处在恰当的抽象高度（Right Altitude），而非单纯压缩字数或堆砌边缘特例：

- **删减代码可读事实**：[Anthropic Skill 编写指南](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) 提醒：“Only add context Claude doesn't already have.” [Claude Code 官方最佳实践](https://code.claude.com/docs/en/best-practices) 给出明确删减判据：“1. Could it find this by reading the code? 2. Would it actually go and look? If both are yes, leave it out”。
- **确定性门禁替代重复强调**：[Claude Code 官方最佳实践](https://code.claude.com/docs/en/best-practices) 指出反复加粗仍易漏掉的要求应升级为脚本或 Hook（“If you keep adding emphasis to a `CLAUDE.md` line and Claude still misses it, that's a sign the line belongs in a hook”），并指出即使另派模型检查也不具确定性（“A `prompt` or `agent` hook asks another model to decide, so it isn't deterministic either”）；[Steering Claude Code](https://claude.com/resources/articles/steering-claude-code-skills-hooks-rules-subagents-and-more) 强调 “A real guardrail needs to be deterministic”；[OpenAI Harness Engineering](https://openai.com/index/harness-engineering/) 同样强调在自定义校验报错中直接写明修复指令（“we write the error messages to inject remediation instructions into agent context”）。
- **按需补充与正反例引导**：[Cursor Agent 最佳实践](https://cursor.com/blog/agent-best-practices) 建议仅在重复犯错时补充规则（“Start simple. Add rules only when you notice the agent making the same mistake repeatedly”）；[Context Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) 强调在脆弱特例与空泛口号之间保持平衡，用通用原则配简短正向改写例子引导行为。

[OpenAI 的 GPT-6 Astra 编写建议](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra) 强调精确的触发描述与按需展开材料，并提醒：“consider which models will use the instructions you leave behind”。这支持在经济档模型（如轻量快速模型）上实测拆分步骤与脚本兜底，不在未验证时盲目删掉关键边界。

[Claude Code Memory](https://code.claude.com/docs/en/memory#write-effective-instructions) 建议每份 `CLAUDE.md` “target under 200 lines”；[OpenAI Codex AGENTS.md 文档](https://developers.openai.com/codex/guides/agents-md) 说明默认合并上限为 32 KiB，WorkBuddy 则将 `MEMORY.md` 硬截断到 4,000 个字符（由 `scripts/sync.sh --check` 自动校验 `rules/global.md` 不超限）。确定性版式与画板碰撞检查统一交给 `check_html.py` 与 `check_feishu.py` 执行。

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
- [Claude Code Memory](https://code.claude.com/docs/en/memory)：`CLAUDE.md` 与导入机制。原文说明“there's no guarantee of strict compliance”，且指出桌面端 **Cowork** 模式会跳过本身为软链的 `~/.claude/CLAUDE.md` 并不加载本机 `~/.claude/skills/`。
- [OpenAI Codex Skills](https://developers.openai.com/codex/skills)：查 Codex 的本地 Skill 发现、软链支持和 `agents/openai.yaml` 调用配置。
- [Cursor Rules](https://cursor.com/docs/rules)：查 User Rules、项目规则、作用范围和引用机制。
- [Cursor Skills](https://cursor.com/docs/skills) 与 [Cursor Subagents](https://cursor.com/docs/subagents)：查手动调用、材料可见性和子 Agent 上下文（注意 **Cursor Cloud Agents** 仅同步 `~/.cursor/skills/`，不同步 `~/.agents/skills/`；本仓库软链脚本面向本机 IDE 与 CLI 会话）。
- WorkBuddy 本地适配：桌面端扫描配置根目录下的 `skills/`（跟随软链并支持 `disable-model-invocation`），并将配置根目录下的 `MEMORY.md` 作为用户级记忆注入（硬截断为 4,000 字符）；本仓库通过可选环境变量 `WORKBUDDY_CONFIG_DIR` 按需建立软链，避免在公开仓库硬编码路径。

### 授权与浏览器环境

授权范围和宿主技术权限分别判断。明确授权范围内的常规工作可以自主完成，业务规则或授权范围的变化仍需确认。[Claude Code 最佳实践](https://code.claude.com/docs/en/best-practices) 区分模型判断与权限、沙箱等强制控制。

[Playwright CLI](https://github.com/microsoft/playwright-cli/blob/main/README.md) 推荐编码 Agent 使用 CLI，同时说明“MCP remains relevant”，列出持续状态和探索自动化等场景。[Anthropic 浏览器安全指南](https://support.claude.com/en/articles/12902428-use-claude-in-chrome-safely) 建议使用不含敏感账户的独立 Profile；公开网页与开发验证使用独立环境，必要时复用已授权个人登录态，是本项目基于任务需要和账户暴露范围的工程判断。

[Playwright 扩展](https://github.com/microsoft/playwright/blob/main/packages/extension/README.md) 的 Token 用于省去连接批准，不定义网站业务操作的授权。[CLI](https://github.com/microsoft/playwright-cli/blob/main/README.md) 的 `detach` 可以断开控制并保留外部浏览器。[Playwright 认证指南](https://playwright.dev/docs/auth) 提醒认证状态可能包含敏感 Cookie 和请求头，不应提交仓库。

### 模型提示与运行环境

- **Google**：[Gemini 提示设计指南](https://ai.google.dev/gemini-api/docs/prompting-strategies) 说明：“These guidelines and templates are starting points.”
- **Cursor**：[Harness 效率实践](https://cursor.com/blog/improved-token-efficiency) 讨论精简失去作用的指示、按需加载工具及子 Agent 的“coordination tax”；[Harness 迭代实践](https://cursor.com/blog/continually-improving-agent-harness) 将离线评估与实际使用反馈结合。
- **DeepSeek**：[工具调用文档](https://api-docs.deepseek.com/guides/tool_calls/) 明确：“The model itself does not execute specific functions.”
- **Google ADK**：[评估指南](https://adk.dev/evaluate/) 区分“Evaluate Trajectory and Tool Use”与“Evaluate the Final Response”。

### 单一设计文档与跨厂商实践取舍

- **三级任务梯度与退役重叠多文档**：[Cursor Agent 最佳实践](https://cursor.com/blog/agent-best-practices) 指出极简单改动无需先写计划（“Not every task needs a detailed plan. For quick changes... jumping straight to the agent is fine”），[Cursor Dynamic Planning](https://cursor.com/blog/dynamic-planning-agents) 支持单人中等改动用内置动态计划；而 [Martin Fowler 站点对 Spec-Driven Development 的实测反思](https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html) 指出多步 SDD 工具生成大量重叠且照抄代码的 Markdown 文件，审查负担重于直接审代码（“They were repetitive, both with each other, and with the code that already existed... I'd rather review code than all these markdown files”）。本项目据此确立三级梯度：极小改动直接编码，单人中等改动用内置 Plan Mode，跨模块或需团队评审的需求在设计期默认维护一份本地 `design.md` 与对应的飞书文档（上线期按需另出《发布文档》与《测试报告》，涉及多独立子系统或不同评审团队的大型项目按评审边界拆分）。
- **跨厂商冲突裁决（OpenAI / Google / 外部画板技能）**：
  1. **对比 OpenAI Harness Engineering**：[OpenAI Harness Engineering](https://openai.com/index/harness-engineering/) 面向零人工编码的新建仓库，将多类文档入库 Git 并运行多轮自动互审循环，同时指出云端文档对仓库内 Agent 不可见（“Knowledge that lives in Google Docs... are not accessible to the system”）。本项目面向存量业务仓与飞书评审，只采纳其“守住不变量不微操实现”（“By enforcing invariants, not micromanaging implementations”）与“脚本报错注入修复指引”两条准则，并通过同步本地 `.agent/work/<主题>/design.md` 补齐编码会话的本地可读性。
  2. **对比 Google Design Docs**：[Design Docs at Google](https://www.industrialempathy.com/posts/design-docs-at-google/) 反对在纯散文设计文档中粘贴表结构与接口定义（“copy-pasting complete schema definitions should be avoided”）。因本项目的 `design.md` 同时充当新会话编码的契约基线，故采取折中方案：只贴本次新增或修改的增量 DDL（如 `ALTER TABLE`）与变更 Proto 片段，不复制未改动的存量完整表结构。
  3. **结合本机 `lark-whiteboard` 场景库与分流路线**：本机 `lark-whiteboard` 提供 JSON DSL 场景范式（`scenes/comparison.md`、`flowchart.md`、`swimlane.md`、`architecture.md`）以及 SVG 路由（`routes/svg.md`）。实测常规节点连线图走 JSON DSL 最稳（自动排版且文字与框体绑定），而 `whiteboard-cli --check` 会漏检 SVG 中独立 `<text>` 溢出 `<rect>`；因此 `my-doc-publish` 按图型分流：跨组件时序图用 Mermaid，常规流程图与对比图默认用 JSON DSL，定制示意图、时间轴或非对称信息图允许走 SVG 但须本地渲染 PNG 并用 `Read` 核查，两轮修不好则回退 JSON DSL。
- **显式触发控制时机**：[Claude Code Skills 文档](https://code.claude.com/docs/en/skills) 指出设置 `disable-model-invocation: true` 会将 Skill 从模型自动匹配上下文中彻底移除（“removes the skill from Claude's context entirely”，[Cursor Skills](https://cursor.com/docs/skills) 同理，[OpenAI Codex Skills](https://developers.openai.com/codex/skills) 设 `allow_implicit_invocation: false`）。因此保留第三人称 `description` 服务于 `/` 菜单展示与按需开启自动匹配，而在 `rules/global.md` 飞书同步条显式指明 `~/.agents/skills/my-doc-publish/SKILL.md` 路径补齐调用链路。
- **独立只读审查、跳过纯风格与会话纠偏**：[Claude Academy Subagents 指南](https://academy.claude.com/courses/introduction-to-subagents/using-subagents-effectively) 界定了独立审查的适用边界；[Claude Code 官方最佳实践](https://code.claude.com/docs/en/best-practices) 给出具体做法：派未见过编写过程的只读审查者避免作者思维定势（“A fresh reviewer does help, because it hasn't seen your reasoning”），代码审查跳过纯风格挑刺（`Skip style`）聚焦正确性与契约，在无关任务之间清空上下文（“/clear between unrelated tasks”），连续两次纠正失败就回退重开（“after two failed corrections run `/clear` and write a better prompt instead of a third”），修 Bug 先写失败测试再修复。[Cursor Agent 最佳实践](https://cursor.com/blog/agent-best-practices) 同样建议跑偏时回退重跑（“Revert the changes, refine the plan... and run it again”），[Design Docs at Google](https://www.industrialempathy.com/posts/design-docs-at-google/#implementation-and-iteration) 指出未上线系统的变更应同步更新设计文档。

---

## 3. 写作依据与表达风险

### Google 官方写作指南与领域统一语言

- **术语与统一语言**：[Google Words](https://developers.google.com/tech-writing/one/words)（“apply the same unambiguous word or term consistently”）与 [Martin Fowler: Ubiquitous Language](https://martinfowler.com/bliki/UbiquitousLanguage.html) 强调在代码、文档与讨论中使用同一套领域词汇。团队日常固定直呼英文的服务简称、动作词与对象名（如 Approve、Reject、Dry Run、Webhook）原样保留英文，不按字面猜全称机翻或在多套中文译名间摇摆。
- **消除句内罗列与渐进式展开**：[Lists and tables](https://developers.google.com/tech-writing/one/lists-and-tables) 指出句内堆砌多项的 Embedded list 难于扫读（“Try to transform embedded lists into either bulleted lists or numbered lists”），并要求表格单元格精炼（“concise cell content”）；[Organizing large documents](https://developers.google.com/tech-writing/two/large-docs) 强调渐进式展开，不在开头倾倒边缘概念。本项目据此在 `TEMPLATES.md` 固化状态矩阵、存量接口校验切换表、跨组件时序图（[Fowler: State Machine](https://martinfowler.com/dslCatalog/stateMachine.html) 与 [Decision Table](https://martinfowler.com/dslCatalog/decisionTable.html)）及边缘兼容收尾小表，并用脚本检查分号连串罗列与超长单元格。
- **标题与图示**：[Headings and titles](https://developers.google.com/style/headings) 支持简短动宾或名词短语作为章节标题，不手写序号；[Illustrating](https://developers.google.com/tech-writing/two/illustrations) 提出先写结论式图注再画图（“write the caption before creating the illustration... They explain the takeaway”），并限制单图信息密度（“strive to avoid visual run-ons”）。

### 中文防造词机制与科学作图闭环

- **选材精简而非压缩句子（防止删语法成分造半截话）**：[Anthropic: Prompting Claude Fable 5](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5) 明确区分了“可读”与“简短”，指出压短篇幅靠的是裁剪无关信息，而非把句子压成残缺片段、缩写或箭头符号串（原文：“Being readable and being concise are different things, and readability matters more. The way to keep output short is to be selective about what you include (drop details that don't change what the reader would do next), not to compress the writing into fragments, abbreviations, arrow chains like A → B → fails, or jargon”）。同时结合中文重意合、主题突出的语法特征，本项目允许同主题连续动作承前省略主语，仅在切换执行方或对象时交代归属，并用“表内放 1 至 2 行完整短结论、复杂前提移至表下分点详述”的结构减负，不靠删掉前提和因果来硬凑短句。
- **研究观察与本项目实战边界**：
  - **论文各自结论（不跨范围外推）**：
    - [Liang et al. (IJCNLP-AACL 2026)](https://aclanthology.org/2026.aacl-long.164.pdf) 指出汉语复合构词具有高动态生产力（原文：“reflected in the productivity of compounding, where morphemes are combined through word-formation relations to create interpretable lexical forms”）；《中国科技术语》2026 年 [《“大语言模型”相关新词造词特点分析》](https://www.term.org.cn/CN/10.12339/j.issn.1673-8578.2026.02.006) 指出大模型相关新词集中体现为缩略与外语直译。
    - [ACL 2025 (Lost in Literalism)](https://aclanthology.org/2025.acl-long.630.pdf) 与 [WMT 2026 (MELT)](https://aclanthology.org/2026.wmt-main.25/) 观察到模型在中文生成中仍会残留英文修饰骨架；[MT Summit 2025](https://aclanthology.org/2025.mtsummit-1.8/) 显示英译中机译语料的转折连词频率超过原生中文新闻两倍。
    - [PNAS 2025](https://www.pnas.org/doi/10.1073/pnas.2422455122) 观察到指令微调模型在英文语料上的名词化（Nominalization）频率高于人类基线。
    - [ArXiv 2506.05339](https://doi.org/10.48550/arxiv.2506.05339) 与 [ACL 2025](https://doi.org/10.18653/v1/2025.acl-long.1308) 证实偏好模型（奖励模型与 LLM 评估器）对冗长（`length`）、专业行话（`jargon`）以及列表、加粗等特定格式模式存在显著偏置（“strong biases towards specific format patterns”）。
  - **本项目实战观察与历史取舍**：
    - 在中文技术方案实战中，模型常把动词压到句尾堆成偏正名词词组或喊四字公文口号（属于本项目实战观察，非上述英文论文直接结论）；因此我们在动作和规则句中推行“具体动词开头”，而章节标题与分类标签仍按 Google Headings 允许简短自然的日常名词短语。
    - 本仓的工程文档保留便于核对的列表和表格。通用 `humanizer` 面向英文维基百科风格的散文，直接套用其列表改写建议，可能把逐项可查的条件写进同一段。
  - **用正向例句指导写作**。在要求模型避免特定词的实验中，作者将观察到的违规分为两类，其中 87.5% 属于 “priming failure”。另一项研究用合成语料测试五个模型同时遵循多条指令的表现。两项研究的实验条件都不同于中文工程文档写作。本仓选择在规则中给正向改写例子，在生成后用 `check_feishu.py` 的 `WARN` 提醒作者核对可疑用词。[Semantic Gravity Wells](https://arxiv.org/abs/2601.08070) · [Prompt Design at Scale](https://arxiv.org/abs/2607.19257) · [Anthropic 提示指南](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)
  - **三项落地举措**：① 选用代码真实标识符与现代汉语日常词，把源码注释中的生硬译词转译为日常动宾短句，参考 [中文技术文档写作风格指南](https://zh-style-guide.readthedocs.io/_/downloads/zh-cn/latest/pdf/) 与 [简明技术中文规范](https://github.com/mzopedia/simplified-technical-chinese/blob/HEAD/%E8%A7%84%E8%8C%83.md)；② 在 `TEMPLATES.md` 区分格式样例型文件与需列全量映射表的业务路由/字典配置，避免单业务长样本过拟合；③ 通过初稿白板口头复述自检和关键评审稿 `my-review` 盲读消除同会话自检盲点（参考 [WMT 2026 MELT](https://aclanthology.org/2026.wmt-main.25/)“verification contributes most to quality improvement”）。
- **配图策划与预览复核**：
  - **四层嵌套与空间索引理论**：[Tamara Munzner: A Nested Model for Visualization Design and Validation (IEEE TVCG 2009)](https://www.cs.ubc.ca/labs/imager/tr/2009/NestedModel/NestedModel.pdf) 将可视化设计拆为问题定性、数据与操作抽象、视觉编码选型和布局算法四层，指出上游选材失误必然导致下游级联失效（原文：“an upstream error inevitably cascades to all downstream levels. If a poor choice was made in the abstraction stage, then even perfect visual encoding and algorithm design will not create a visualization system that solves the intended problem”）。[Larkin & Simon (Cognitive Science 1987)](https://doi.org/10.1111/j.1551-6708.1987.tb00863.x) 证明好图之所以胜过千言，在于把同一阶段或同一对象的新旧状态摆在相邻空间位置降低工作记忆负荷；[Daniel Moody: The "Physics" of Notations (IEEE TSE 2009)](https://doi.org/10.1109/tse.2009.67) 提出 **Cognitive Fit**（“visual horses for cognitive courses”，不同认知问题用不同图型）、**Complexity Management**（用模块化包含框管理复杂度，不拉单列长链）与 **Dual Coding**（边界框虚实、色彩语义与精炼文字互补）。
  - Google 技术写作课建议先写图注，“It is often helpful to write the caption before creating the illustration.” 架构图的内容和边界取决于读者需要回答的问题。[Google 技术写作](https://developers.google.com/tech-writing/two/illustrations) · [Architects Zoom In and Out](https://architectelevator.com/architecture/architects-zoom/) · [C4 图示约定](https://c4model.com/diagrams/notation)
  - 在文本生成可编辑图的研究中，Feynman 先选择内容、规划代码，再迭代调整。VISTA 用确定性算法布局，再结合源码和实图修正局部问题。这些实验评估各自的作图系统。本仓的分工是由 `my-tech-design` 写结论图注、选算例和改动边界、确定图型，再由 `my-doc-publish` 渲染并核对预览。[DiagramAgent](https://openaccess.thecvf.com/content/CVPR2025/html/Wei_From_Words_to_Structured_Visuals_A_Benchmark_and_Framework_for_CVPR_2025_paper.html) · [Feynman](https://arxiv.org/abs/2603.12597) · [VISTA](https://aclanthology.org/2026.emnlp-main.2403/)
- **扫读分组、长文后半程衰减与两级脚本门禁**：
  - **视觉信号与中文排版**：[NN/g Layer-Cake Scanning](https://www.nngroup.com/articles/layer-cake-pattern-scanning/) 与多媒体学习信号原则（[Mayer 综述引述](https://doi.org/10.47941/jep.3588)、[Cognitive Processing 实验](https://link.springer.com/article/10.1007/s10339-020-01002-5)）支持用分组色块、浅灰表头与适度关键词标记降低扫读负荷；W3C [中文排版需求 CLReq](https://www.w3.org/TR/clreq/#emphases) 指出汉字印刷一般不用机械斜体。
  - **长文本后半程衰减防控**：[LongWeave (arXiv:2510.24345)](https://arxiv.org/abs/2510.24345) 证实模型遵循指令的能力随生成长度增加而逐段衰减（原文：“Stepwise deviations show that the ability to follow instructions gets worse as the output becomes longer”），[VOLTBench (arXiv:2605.01357)](https://arxiv.org/html/2605.01357) 记录了长文生成中后段的跳节现象（`Section Skipping`）。在本仓样本里还观察到文档后半篇缺少层次或漏写《方案取舍》，因此把这两项列入核查。上述长文基准没有测试飞书 XML。
  - **三层落地职责划分**：
    1. **脚本校验**（`check_feishu.py` / `check_html.py`）：`ERROR` 阻断客观必错或平台报错项（`check_html.py` 只检查客观结构 `ERROR`；两脚本合计覆盖 XML 语法与嵌套禁令、冗余 `<ol seq="auto">`、双码点变体 emoji、占位符、标题跳级、章节分割线与相邻块空行、无灰底表头、中文斜体与非链接下划线、破折号、`<callout>` 小标题紧贴或尾冒号、表内超长命令、极端文字墙、画板 Schema 错配与客观压框等）；`check_feishu.py` 另用 `WARN` 提醒启发式可读性与构图问题（偏长段落或列表、窄格偏长、分号或斜杠枚举罗列、密集 `<code>` 灰框、标题含顿号、疑似夸张或重复词、后半程视觉偏淡或无标色、技术方案未见《方案取舍》、折线的节点端缺少显式锚点、画板高瘦长链或节点偏多），由作者逐条核查。
    2. **Skill 默认结构与视觉映射**（`my-tech-design` 自动衔接 `my-doc-publish`）：分清背景与实施难点、突出改造前后对比、业务规则配置列全量映射表、按三步策划配图，在发布阶段复核预览、全篇各章保持一致视觉层次。
    3. **人工微调留白**：将画板像素级拖拽、特定参会人关注点的临时标黄及等价表格/卡片取舍留给作者在飞书页面微调。

---

## 4. 研究证据的采用边界

各来源按自身证明范围采用，不跨场景外推：

- **产品文档**：核对当前入口、版本和适用产品。
- **实证研究**：核对论文正文、实验模型、任务与比较基准；结果只支持匹配的实验范围，不将论文实验数字直接换算成本项目硬阈值。
- **较早资料与工程实践**：区分已发布能力、厂商自身观察与跨宿主适用性；无法核实的主张不作为设计依据。

---

## 5. 验证方法与未验证假设

改动前固定问题基线与判定标准，优先使用未参与规则编写的真实跨项目样本（Held-out Case）以及目标经济档模型做端到端生成与人类阅读体验对照，不由待审的新版 `my-review` 自举批准自身产出。具体现场材料存于本地非同步目录，不提交公开仓库。
