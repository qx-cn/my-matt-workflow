# 编写与审核参考

本文供本仓库迭代规则和 Skill 时按主题查阅，保存当前设计依据、研究边界及验证方法。本文不是另一份执行规范，普通业务写作和 Skill 运行无需读取。

查维护归属与取舍看第 1 节，查产品机制与工程实践看第 2 节，查写作依据看第 3 节，查研究证据的采用边界看第 4 节，设计验证看第 5 节。外部资料在相关迭代中按需重新查证，不设定期巡检。

## 1. 维护归属与设计理由

可执行要求由各自文件维护，本文只解释理由和适用边界；以下链接用于维护定位，不要求运行任务时逐一遍历。

| 内容 | 主定义位置 | 分开的理由 |
| --- | --- | --- |
| 通用写作与行为规范 | [全局规则](../rules/global.md) | 避免多个 Skill 各自维护完整规范 |
| 仓库约定与资料入口 | [仓库准则](../AGENTS.md) | 当前约定可直接找到，研究材料按需读取 |
| 技术方案生成与改写动作 | [技术方案 Skill](../skills/my-tech-design/SKILL.md) | 将通用要求落实到具体任务 |
| 审核动作、四项原则与复查上限 | [审核 Skill](../skills/my-review/SKILL.md) | 审核职责和执行要求在一处定义 |

集中定义与必要的任务提醒可以并存。[Cursor Rules](https://cursor.com/docs/rules) 建议：“Reference files instead of copying their contents.” 本项目据此优先引用，保留执行需要的短提示；这不是允许在多处维护完整定义或例外。

文件数和行数都不能单独证明维护成本下降。减少重复定义可以缩小常见修改范围，但规则含义改变时，相关动作和设计理由仍可能需要调整。规范已在上下文中时无需反复读取；仅有文件路径或安装链接，也不能证明执行者取得了正文。

### 上下文与指示长度

简洁的目标是保留足够信息，而非追求最少字数。[Anthropic Skill 编写指南](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) 提醒：“Only add context Claude doesn't already have.” [Context Engineering](https://www.anthropic.com/research/effective-context-engineering-for-ai-agents) 同时说明：“minimal does not necessarily mean short”。按需读取和围绕真实缺口补充指示仍有现行 Skill 指南支持；文章中的具体模型行为不视作长期保证。

[OpenAI 的 GPT-6 Astra 编写建议](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra) 强调精确的触发描述、按需展开材料，并提醒：“consider which models will use the instructions you leave behind”。这支持检查跨模型适用范围，不支持在未验证时统一删掉任务步骤；本项目的职责和验收要求仍以主定义为准。

这些建议支持按需读取参考资料及合并重复条文，不证明某个固定长度必然有效。厂商的行数建议不是能力保证；仓库的准入、规模和格式限制是本地约定。大段解释适合留在参考资料，不能因此隐藏执行必需的约束。

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

仓库的全局规则文件是维护源，具体宿主使用的入口不同。软链检查只验证安装关系，不能替代当前会话加载证据；缺少再次读取记录也不能证明模型未使用先前进入上下文的材料。

### 模型提示与运行环境

Harness 是模型周围的运行机制，包括工具、上下文管理和执行反馈。参考这些机制的设计经验，不要求使用资料对应的产品。

- **Google**：[Gemini 提示设计指南](https://ai.google.dev/gemini-api/docs/prompting-strategies) 说明：“These guidelines and templates are starting points.” 可参考目标、约束、上下文和示例的表达；示例数量及模型专属提示策略需要在实际模型上验证，不能成为所有 Skill 的固定要求。
- **Cursor**：[Harness 效率实践](https://cursor.com/blog/improved-token-efficiency) 讨论精简失去作用的指示、按需加载工具及子 Agent 的“coordination tax”。可参考上下文成本与协调成本的取舍；缓存、工具发现和文件读取优化由宿主实现，不能靠 AGENTS.md 复现，产品报告的节省比例也不代表本项目收益。
- **DeepSeek**：[工具调用文档](https://api-docs.deepseek.com/guides/tool_calls/) 明确：“The model itself does not execute specific functions.” [思考模式文档](https://api-docs.deepseek.com/guides/thinking_mode/) 则规定对应模式的参数及多轮消息处理。可据此区分模型输出与客户端执行职责；具体协议只在接入对应模型和 API 时适用，不写入通用规则。

当前实践支持按任务选择验证方法。[Google ADK 评估指南](https://adk.dev/evaluate/) 区分“Evaluate Trajectory and Tool Use”与“Evaluate the Final Response”；本项目参考动作记录与最终答案分别核验的思路，不引入 ADK，也不要求只有一条合法工具调用路径。

[Cursor 的 Harness 迭代实践](https://cursor.com/blog/continually-improving-agent-harness) 将离线评估与实际使用反馈结合。本文采用的工程判断是：先确认具体失败，再比较改动前后的质量和成本；Token 减少、运行更快或一次回答更顺，都不能单独证明任务完成得更好。

## 3. 写作依据与表达风险

写作依据用于解释选择，不构成新的禁词表。Google 现行指南继续支持术语一致、主动语态和按读者组织内容等稳定实践；英文语法、大小写和标点习惯不能直接成为中文规范。名称清晰与设计准确需要分别判断。

### Google 官方写作指南

术语需要与读者理解相匹配。[Words](https://developers.google.com/tech-writing/one/words) 要求：“apply the same unambiguous word or term consistently throughout your document”。该指南也允许定义新术语，因此不能把所有陌生词或中英文并用都判为错误。

格式和名称承担不同职责。[Code in text](https://developers.google.com/style/code-in-text) 根据文本用途区分代码实体与普通名称的样式，不要求为减少代码样式创造中文别名。[Tables](https://developers.google.com/style/tables) 根据内容关系选择表格，两列条件与动作表不能仅凭列数判错。仓库的具体排版偏好仍以主定义为准。

按问题查阅以下页面，无需每次全部阅读：

- 句子与段落：[短句](https://developers.google.com/tech-writing/one/short-sentences)、[主动语态](https://developers.google.com/tech-writing/one/active-voice)、[段落](https://developers.google.com/tech-writing/one/paragraphs)。
- 内容组织：[列表与表格](https://developers.google.com/tech-writing/one/lists-and-tables)、[长文档](https://developers.google.com/tech-writing/two/large-docs)、[插图](https://developers.google.com/tech-writing/two/illustrations)。
- 表达与样式：[术语](https://developers.google.com/style/jargon)、[列表](https://developers.google.com/style/lists)、[标题](https://developers.google.com/style/headings)。

### 项目实践

[Gemini CLI 的 docs-writer](https://raw.githubusercontent.com/google-gemini/gemini-cli/main/.gemini/skills/docs-writer/SKILL.md) 是该项目的写作实践，适合参考任务组织和准确性检查，不是跨项目统一规范。

本项目的中文措辞、段落行数和标题层级偏好由全局规则与对应 Skill 定义。项目偏好不依赖外部文章背书，也不能据此判定业务对象、条件或并发约束是否完整。

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
