# 编写与审核参考

本文供本仓库迭代规则和 Skill 时按主题查阅，保存当前设计依据、研究边界及验证方法。本文不是另一份执行规范，普通业务写作和 Skill 运行无需读取；外部资料在相关迭代中按需重新查证，不设定期巡检。

## 1. 维护归属与设计理由

可执行要求由各自文件维护，本文只解释理由和适用边界；以下链接用于维护定位，不要求运行任务时逐一遍历。

| 内容 | 主定义位置 | 分开的理由 |
| --- | --- | --- |
| 通用写作与行为规范 | [全局规则](../rules/global.md) | 避免多个 Skill 各自维护完整规范 |
| 仓库约定与资料入口 | [仓库准则](../AGENTS.md) | 当前约定可直接找到，研究材料按需读取 |
| 技术方案生成与改写动作 | [技术方案 Skill](../skills/my-tech-design/SKILL.md) | 将通用要求落实到具体任务 |
| 审核动作、四项原则与复查上限 | [审核 Skill](../skills/my-review/SKILL.md) | 审核职责和执行要求在一处定义 |

集中定义与必要的任务提醒可以并存。[Cursor Rules](https://cursor.com/docs/rules) 建议：“Reference files instead of copying their contents.” 本项目据此优先引用，保留执行需要的短提示；这不是允许在多处维护完整定义或例外。

文件数和行数都不能单独证明维护成本下降。减少重复定义可以缩小常见修改范围，但宿主运行时会将常驻规则、项目准则与所调用的 Skill 合并注入同一上下文（[Claude Code Memory](https://code.claude.com/docs/en/memory#write-effective-instructions) 指出：“if two instructions contradict each other, Claude may pick one arbitrarily”），因此规则含义或边界改变时，需同步核对共生栈中的上下游规则、模板、校验脚本及设计理由，需要例外时回上游收窄适用前提而非在局部硬写矛盾条文。规范已在上下文中时无需反复读取；仅有文件路径或安装链接，也不能证明执行者取得了正文。

### 上下文与指示长度

简洁的目标是保留足够信息并处在恰当的抽象高度（Right Altitude），而非追求最少字数或堆砌边缘特例清单。[Anthropic Skill 编写指南](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) 提醒：“Only add context Claude doesn't already have.” [Context Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) 同时指出：“minimal does not necessarily mean short”，并强调在“hardcoding complex, brittle logic / stuffing a laundry list of edge cases”与“vague, high-level guidance”之间保持平衡，用通用原则配合简短典型的正反例引导行为。按需读取和围绕真实缺口补充指示仍有现行 Skill 指南支持；文章中的具体模型行为不视作长期保证。

[OpenAI 的 GPT-6 Astra 编写建议](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra) 强调精确的触发描述、按需展开材料，并提醒：“consider which models will use the instructions you leave behind”。这支持检查跨模型适用范围，不支持在未验证时统一删掉任务步骤；本项目的职责和验收要求仍以主定义为准。

这些建议支持按需读取参考资料及合并重复条文，不证明某个固定长度必然有效。[Claude Code Memory](https://code.claude.com/docs/en/memory#write-effective-instructions) 建议每份 CLAUDE.md “target under 200 lines”，这是该产品的编写建议；[OpenAI AGENTS.md 文档](https://learn.chatgpt.com/docs/agent-configuration/agents-md) 说明默认合并大小限制为 32 KiB，WorkBuddy 则将其用户记忆文件 `MEMORY.md` 硬截断到 4000 个字符（由 `scripts/sync.sh --check` 自动校验 `rules/global.md` 不超过该容量上限）。这些产品建议与加载容量限制都不能推出跨宿主的 30 行阈值，也不是能力保证。本仓库不设统一行数上限，按规则是否必要、清晰、无冲突及实际效果判断；大段解释适合留在参考资料，不能因此隐藏执行必需的约束。

### 四项审核原则的依据

审核 Skill 中的四项原则是本项目对评估和上下文方法的应用，不是厂商发布的固定清单。

- **目标的依据**：[Anthropic 成功条件与评估](https://platform.claude.com/docs/en/test-and-evaluate/develop-tests) 强调具体、可衡量且与实际需要相关的成功条件。本项目将其用于判断计划是否解决原始需求。
- **措施的依据**：[Agent 评估指南](https://www.anthropic.com/research/demystifying-evals-for-ai-agents) 区分执行记录与最终结果，并建议检查失败轨迹。本项目据此追问措施依赖的条件；具体因果判断仍需任务证据。
- **成本的依据**：Context Engineering 将上下文视为有限资源；将执行和维护成本纳入方案审核，是本项目的工程判断，不是该文章规定的通用成本公式。
- **证据的依据**：Agent 评估指南结合任务、判定标准、重复试验和记录检查。本项目将其用于限制效果主张，官方出处只支持对应事实或建议。

这些依据来自 LLM 应用及 Agent 评估。迁移到技术方案审核需要考虑任务差异，不能因贴有官方链接就认为方案有效，也不能因方案没有厂商逐字背书就判错。

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

仓库的全局规则文件是维护源，具体宿主使用的入口不同。软链检查只验证安装关系，不能替代当前会话加载证据；缺少再次读取记录也不能证明模型未使用先前进入上下文的材料。

### 授权与浏览器环境

授权范围和宿主技术权限分别判断。明确授权范围内的常规工作可以自主完成，业务规则或授权范围的变化仍需确认。[Claude Code 最佳实践](https://code.claude.com/docs/en/best-practices) 区分模型判断与权限、沙箱等强制控制。规则文本只能指导行为，不能证明对应限制已经由宿主执行。

[Playwright CLI](https://github.com/microsoft/playwright-cli/blob/main/README.md) 推荐编码 Agent 使用 CLI，同时说明“MCP remains relevant”，列出持续状态和探索自动化等场景。这支持按任务和宿主能力选择工具，不支持只有 CLI 无法完成时才能使用其他工具。[Anthropic 浏览器安全指南](https://support.claude.com/en/articles/12902428-use-claude-in-chrome-safely) 建议使用不含敏感账户的独立 Profile；该建议针对 Claude in Chrome。公开网页与开发验证使用独立环境，必要时复用已授权个人登录态，是本项目基于任务需要和账户暴露范围的工程判断，不是所有宿主的统一规定。

[Playwright 扩展](https://github.com/microsoft/playwright/blob/main/packages/extension/README.md) 的 Token 用于省去连接批准，不定义网站业务操作的授权。[CLI](https://github.com/microsoft/playwright-cli/blob/main/README.md) 的 `detach` 可以断开控制并保留外部浏览器。保留页面与保留自动化连接分别处理，具体能力需核对所用版本；不同宿主的生命周期不视作相同机制。

[Playwright 认证指南](https://playwright.dev/docs/auth) 提醒，认证状态可能包含可用于冒充账户的 Cookie 和请求头，不应提交到公开或私有仓库。隔离浏览器环境也不能消除同一账户在服务端产生的相互影响；并行修改数据时仍需隔离账户或测试数据。命名会话、页面控制归属和账户数据隔离分别核实，规则不据会话名推断隔离已经成立。

### 模型提示与运行环境

Harness 是模型周围的运行机制，包括工具、上下文管理和执行反馈。参考这些机制的设计经验，不要求使用资料对应的产品。

- **Google**：[Gemini 提示设计指南](https://ai.google.dev/gemini-api/docs/prompting-strategies) 说明：“These guidelines and templates are starting points.” 可参考目标、约束、上下文和示例的表达；示例数量及模型专属提示策略需要在实际模型上验证，不能成为所有 Skill 的固定要求。
- **Cursor**：[Harness 效率实践](https://cursor.com/blog/improved-token-efficiency) 讨论精简失去作用的指示、按需加载工具及子 Agent 的“coordination tax”。可参考上下文成本与协调成本的取舍；缓存、工具发现和文件读取优化由宿主实现，不能靠 AGENTS.md 复现，产品报告的节省比例也不代表本项目收益。
- **DeepSeek**：[工具调用文档](https://api-docs.deepseek.com/guides/tool_calls/) 明确：“The model itself does not execute specific functions.” [思考模式文档](https://api-docs.deepseek.com/guides/thinking_mode/) 则规定对应模式的参数及多轮消息处理。可据此区分模型输出与客户端执行职责；具体协议只在接入对应模型和 API 时适用，不写入通用规则。

当前实践支持按任务选择验证方法。[Google ADK 评估指南](https://adk.dev/evaluate/) 区分“Evaluate Trajectory and Tool Use”与“Evaluate the Final Response”；本项目参考动作记录与最终答案分别核验的思路，不引入 ADK，也不要求只有一条合法工具调用路径。

[Cursor 的 Harness 迭代实践](https://cursor.com/blog/continually-improving-agent-harness) 将离线评估与实际使用反馈结合。本文采用的工程判断是：先确认具体失败，再比较改动前后的质量和成本；Token 减少、运行更快或一次回答更顺，都不能单独证明任务完成得更好。

### 独立审查隔离与规格同步

独立审查与实施期规格同步分别依据时机控制、子 Agent 隔离机制与规格演进实践设定边界：

- **显式触发控制时机**：[Claude Code Skills 文档](https://code.claude.com/docs/en/skills)指出需要由人控制触发时机的工作流应设置 `disable-model-invocation: true`（原文：“Use this for workflows with side effects or that you want to control timing”），并在排障指南中将关闭自动调用列为解决过度触发的标准方案（[Cursor Skills](https://cursor.com/docs/skills) 同样使用 `SKILL.md` 的 `disable-model-invocation: true`，[OpenAI Build skills](https://learn.chatgpt.com/docs/build-skills) 则使用 `agents/openai.yaml` 的 `allow_implicit_invocation: false`）。因派生干净上下文子 Agent 审查耗时且成本高，本项目将 4 个核心 Skill 统一设为手动调用，仅在 `rules/global.md` 保留高风险代码实施完成后的一句话轻提醒，避免写文档初稿、改临时测试包或普通阅读请求误触发重型审查。
- **审查载荷隔离与范围刹车**：[Claude Academy Subagents 指南](https://academy.claude.com/courses/introduction-to-subagents/using-subagents-effectively)指出代码在视作他人编写且不带创作历史时审查效果更好（由审查子 Agent 在独立上下文中自行运行 `git diff` 与读取修改文件）；[Claude Code Best Practices](https://code.claude.com/docs/en/best-practices) 提醒跳过纯风格挑刺，否则修完每一条意见会引入多余抽象层与无意义测试。本项目据此要求主 Agent 优先传客观路径（无路径材料原样粘贴全文），禁传主 Agent 归纳的改动导览、偏离辩护与自证式测试总结，并由主 Agent 核实源码事实后只修确认成立的“必须修”，“建议”交由用户决定而不擅自扩改。
- **代码与规格不一致的分层裁决**：[Design Docs at Google](https://www.industrialempathy.com/posts/design-docs-at-google/#implementation-and-iteration) 指出实施碰撞现实时常暴露初始假设偏差，未上线系统的设计文档应同步更新；[Martin Fowler 站点 Spec-Driven Development 分析](https://www.martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html)区分了一次性 `spec-first` 与持续对齐的 `spec-anchored` 维护负担。本项目采用工程折中：代码漏写或偏离有效 Spec 时修代码；纯底层代码事实或内部签名假设有误（不改变业务规则、对外契约与范围）时以源码为准修正并回写已有的 Spec 与决定记录，不为内部细节频繁改动评审技术方案；涉及业务规则、对外契约、范围或风险取舍变化时先经用户确认再同步代码与相关设计文档。

## 3. 写作依据与表达风险

写作依据用于解释选择，不构成新的禁词表。Google 现行指南继续支持术语一致、主动语态和按读者组织内容等稳定实践；英文语法、大小写和标点习惯不能直接成为中文规范。名称清晰与设计准确需要分别判断。

### Google 官方写作指南

术语需要与读者理解相匹配。[Words](https://developers.google.com/tech-writing/one/words) 要求：“apply the same unambiguous word or term consistently throughout your document”。该指南也允许定义新术语，因此不能把所有陌生词或中英文并用都判为错误。

格式和名称承担不同职责。[Code in text](https://developers.google.com/style/code-in-text) 根据文本用途区分代码实体与普通名称的样式，不要求为减少代码样式创造中文别名。[Tables](https://developers.google.com/style/tables) 根据内容关系选择表格，两列条件与动作表不能仅凭列数判错。仓库的具体排版偏好仍以主定义为准。

按问题查阅以下页面，无需每次全部阅读：

- 句子与段落：[短句](https://developers.google.com/tech-writing/one/short-sentences)、[主动语态](https://developers.google.com/tech-writing/one/active-voice)、[段落](https://developers.google.com/tech-writing/one/paragraphs)。
- 内容组织：[列表与表格](https://developers.google.com/tech-writing/one/lists-and-tables)、[长文档](https://developers.google.com/tech-writing/two/large-docs)、[插图](https://developers.google.com/tech-writing/two/illustrations)。
- 表达与样式：[术语](https://developers.google.com/style/jargon)、[列表](https://developers.google.com/style/lists)、[标题](https://developers.google.com/style/headings)。

### 项目实践与中文工程表达

[Gemini CLI 的 docs-writer](https://raw.githubusercontent.com/google-gemini/gemini-cli/main/.gemini/skills/docs-writer/SKILL.md) 是该项目的写作实践，适合参考任务组织和准确性检查，不是跨项目统一规范。

本项目的中文措辞、段落组织和视觉层级由全局规则与对应 Skill 定义，依据以下实证研究与工程实践区分中英文差异及文档受众：

- **中英文句法差异与反翻译腔**：
  - **研究观察**：
    - [PNAS 2025 研究](https://www.pnas.org/doi/10.1073/pnas.2422455122)：指令微调模型在英文语料上的名词化（Nominalization）频率高于人类基线；
    - [ArXiv 2506.05339](https://doi.org/10.48550/arxiv.2506.05339)：偏好模型（奖励模型与 LLM 评估器）在受控反事实样本对上对冗长（`length`）、列表结构（`structure`）与专业行话（`jargon`）等表层特征存在显著偏好偏置与校准偏差；
    - [ACL 2025](https://doi.org/10.18653/v1/2025.acl-long.1308)：偏好模型对列表、加粗等特定格式模式与长度存在显著偏好（“strong biases towards specific format patterns”）；
    - [MT Summit 2025](https://aclanthology.org/2025.mtsummit-1.8/)：英译中机译语料（NMT 与 LLM）的转折连词频率超过原生中文新闻两倍，且专用翻译模型相比通用 LLM 翻译输出具有更高的因果连词比例。
  - **项目选择**：结合中文重意合、主题突出的特点，本项目保留原生英文缩写、接口与命令名，用具体动词替代“进行/实现 + 抽象名词”，允许同主题流水句承前省略主语，并停用针对英文维基百科散文的通用 `humanizer`（其第 19 条倾向于将带加粗引导词的列表改写为散文段落，易破坏工程文档的扫读结构）。这些中文工程写作规则属于项目选择，跨模型效果仍需按第 5 节方法在本地验证。
- **技术方案与施工 Spec 的受众分离**：[Design Docs at Google](https://www.industrialempathy.com/posts/design-docs-at-google/) 与 [Martin Fowler ADR 指南](https://martinfowler.com/bliki/ArchitectureDecisionRecord.html) 强调设计文档面向人类评审者，核心是倒金字塔结构、问题背景、系统上下文与备选方案权衡，而非代码级施工说明书。因此 `spec.md` 面向编码 Agent 保留源码行号与全量字段清单，而 `my-tech-design` 面向评审人隐藏源码行号与全量同名字段表，同时遵循四项工程设计原则：
  1. **首要痛点置顶与排除项降噪**：将触发需求的根本业务痛点放在第一位，调研期排除的候选方案只归入方案取舍，不混作现网系统痛点。
  2. **动机、归属前置与判据可查验**：引出分支、过滤条件、多步操作或跨组件转换前，交代业务动机与上下游、表字段归属，并指明可查验的状态判据（具体到表名、字段名与枚举值），不裸抛内部实现黑话或无归属状态词。
  3. **审慎界定不做范围与动态详略**：按 [Design Docs at Google](https://www.industrialempathy.com/posts/design-docs-at-google/#goals-and-non-goals) 仅将合理可能包含但决定延后或另案处理的事项列为不做范围，不拿无关的“不改表结构”凑数；按 [Gergely Orosz RFC 指南](https://newsletter.pragmaticengineer.com/p/rfcs-and-design-docs) 根据实际风险分配篇幅，复用现有机制的维度简写，高风险维度配图详述。
  4. **回滚分离服务版本与数据状态**：回滚预案分别评估服务镜像回滚与运行期间已落库数据、已推进游标的修复手段。
- **视觉层级、扫读与以图代字**：
  - **外部依据**：[Nielsen Norman Group 眼动追踪研究](https://www.nngroup.com/articles/layer-cake-pattern-scanning/)、[长文排版指南](https://www.nngroup.com/articles/formatting-long-form-content/)与多媒体学习中的[信号原则（Signaling Principle）](https://pmc.ncbi.nlm.nih.gov/articles/PMC8354981/)表明，读者通过标题、高亮块、双栏分块和关键词加粗/色彩对比进行扫读，并通过聚焦的简明图示（[Google Illustrating](https://developers.google.com/tech-writing/two/illustrations)）降低外在认知负荷。
  - **项目落地**：`my-tech-design` 据此要求文首提供方案总览，按内容复杂度选用双栏并排、关键差异局部高亮与聚焦画板图（飞书画板按图型采用 JSON DSL 拓扑或栅格布局、时序图等采用 Mermaid，本地 HTML 采用内联 SVG），图下不重复复述图内过程，并在写入飞书画板后导出预览图做视觉自检。

### 通用失败模式与已知限制

表达问题可能沿材料转换传播，也可能在改写时新增；以下区分帮助选择验证对象，不直接解释某次模型的内部原因。

- 输入已有概括词，不能证明成品读者理解其含义；也不能据此否定已确认的业务决定。
- 格式调整可能改变名称对应，缩减或润色可能删除条件、动作和关联约束。更短、更顺并不证明设计保持。
- 语法检查验证结构，内容核对验证含义；某一版本的审核结果不能证明后续版本正确。
- 片段中未找到约束不等于全文没有约束；将 Agent 的解释当作原始轨迹，会混淆观察和归因。

Spec 整理阶段可能需要额外动作，但输入 Spec 存在含混表达，不能证明由 [my-to-spec](../skills/my-to-spec/SKILL.md) 产生。是否修改该 Skill，取决于其任务基线和实际缺口；这不阻碍对文稿生成、缩减和审核的局部验证。

## 4. 研究证据的采用边界

现行依据取决于结论的适用性，发布日期和最新版本号只提供核验线索。研究材料需要能支持具体设计判断，不为覆盖厂商或增加引用数量而收录。

不同证据的适用边界如下：

- **产品文档**：核对当前入口、版本和适用产品。旧接口或已被替代的建议退出当前依据；引用与解释一起更新。
- **实证研究**：核对论文正文、修订版本、实验模型、宿主、任务、预算、比较基准及后续研究。结果只支持匹配的实验范围，不将成功率、成本变化或数量分组直接转换成本项目阈值。
- **较早资料**：只有适用条件明确的定理，或仍获现行官方指南、后续研究支持的稳定实践，才作为当前依据保留。未发现替代论文不能证明旧模型的观察仍适用；未发现效果也不能证明没有效果。
- **工程实践**：区分已发布能力、预览实现和厂商自身观察。官方文章不等于跨宿主最佳实践；来源冲突时先比较条件，不拼接成统一要求。

若正文暂时无法获取，先尝试官方替代入口，不能把访问失败判成结论过时。无法核实的主张不作为当前设计依据，也不凭搜索摘要补全；涉及既有规则的含义变化时，按仓库约定确认取舍。

本项目的效果仍需目标宿主和模型上的本地验证。[Anthropic Skill 指南](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) 要求覆盖实际使用的模型，并先建立基线再迭代。本文据此采用第 5 节的验证方法，不用旧模型上的性能数字推断当前 workflow 的收益。

## 5. 验证方法与未验证假设

本节是规则迭代的参考方法，不是每次业务写作的必跑流程。具体用例、模型和执行范围由获授权的验证任务确定，不引入新的测试框架或审核轮数。

Anthropic Skill 指南建议：“Create evaluations BEFORE writing extensive documentation.” 因此改动前固定旧文本、输入和判定标准，有助于避免看到结果后改变标准。判定针对含义和读者理解，不限定唯一措辞。

### 用例与对照

真实片段、报告转述和人工构造分别标明来源；缺少全文时只检验局部行为，不把占位内容当作原文，也不要求取得模型内部思考。

| 验证对象 | 可观察结果 | 结论边界 |
| --- | --- | --- |
| 名称与格式调整 | 名称仍对应同一对象，读者能解释概括名称 | 出现某个词不自动失败 |
| 缩减与润色 | 条件、动作及关键约束仍可定位 | 对照原文不等于证明实现正确 |
| 连续生成、缩减、改词 | 同一会话中各版本保持相同关键含义 | 构造序列不称历史重放 |
| 固定文稿审核 | 发现遗漏，同时保留合法术语与合理表达 | 不从片段推断整篇遗漏 |
| 读者理解 | 仅凭成品回答具体问题，再对照事实材料 | 风格印象不能替代回答结果 |
| 计划审核 | 识别无依据主张、维护风险，尊重已确认取舍 | 不要求每次提出替代方案 |

计划审核可使用明确标注的构造对照：未知加载情况被写成确定根因、多处规范定义没有维护安排、具有合理已确认取舍的方案。另留未用于修改指示的变体，检查是否只适配熟悉样例。

### 执行与判断

有效对照需要相同模型、材料、全局规则和工具条件；旧新版从独立初始上下文开始，连续改写序列内部保留同一上下文。执行者不拿标准答案，评价者尽可能不知道版本，不由受测审核指示批准自身结果。

重复试验用于观察波动，小样本不证明统计提升。记录理解结果、含义变化、漏报和误报；实际加载材料及调用消耗才是成本线索，文件行数只说明文本规模。新增错误可促使调整或撤回对应条目，新旧均通过只说明未观察到改善。

目标宿主或模型不可用时，结果仅适用于实际测试环境。规则加载、语法有效、安装关系正常和行为改善分别报告；本项目这些检查动作的实际收益仍需行为验证。

### 材料与维护

具体现场材料与试验结果存于获授权的本地非同步目录，本文只保存通用方法，不收录企业原文、内部地址或事件流水。外部指南、研究解释和项目选择分别标明；没有证据的因果解释留作假设，不写成现行规则。
