# 编写与审核参考

本文供本仓库迭代规则和 Skill 时按主题查阅，保存当前设计依据、研究边界及验证方法。本文不是另一份执行规范，普通业务写作和 Skill 运行无需读取。

查维护归属与取舍看第 1 节，查产品机制看第 2 节，查写作依据看第 3 节，查论文边界看第 4 节，设计验证看第 5 节。外部资料在相关迭代中按需重新查证，不设定期巡检。

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

简洁的目标是保留足够信息，而非追求最少字数。[Anthropic Skill 编写指南](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) 提醒：“Only add context Claude doesn't already have.” [Context Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) 同时说明：“minimal does not necessarily mean short”。

这些建议支持按需读取参考资料及合并重复条文，不证明某个固定长度必然有效。厂商的行数建议不是能力保证；仓库的准入、规模和格式限制是本地约定。大段解释适合留在参考资料，不能因此隐藏执行必需的约束。

### 四项审核原则的依据

审核 Skill 中的四项原则是本项目对评估和上下文方法的应用，不是厂商发布的固定清单。

- **目标的依据**：[Anthropic 成功条件与评估](https://platform.claude.com/docs/en/test-and-evaluate/develop-tests) 强调具体、可衡量且与实际需要相关的成功条件。本项目将其用于判断计划是否解决原始需求。
- **措施的依据**：[Agent 评估指南](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) 区分执行记录与最终结果，并建议检查失败轨迹。本项目据此追问措施依赖的条件；具体因果判断仍需任务证据。
- **成本的依据**：Context Engineering 将上下文视为有限资源；将执行和维护成本纳入方案审核，是本项目的工程判断，不是该文章规定的通用成本公式。
- **证据的依据**：Agent 评估指南结合任务、判定标准、重复试验和记录检查。本项目将其用于限制效果主张，官方出处只支持对应事实或建议。

这些依据来自 LLM 应用及 Agent 评估。迁移到技术方案审核需要考虑任务差异，不能因贴有官方链接就认为方案有效，也不能因方案没有厂商逐字背书就判错。

## 2. 厂商指南与宿主边界

产品机制以对应厂商资料为准，不将一个宿主的加载、导入或调用方式推及其他宿主。

- [Anthropic Agent Skills Best Practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)：按需加载、描述编写、自由度与评估。关于第三人称和触发描述的建议有具体产品语境。
- [Claude Code Best Practices](https://code.claude.com/docs/en/best-practices)：上下文管理和实际工作验证。
- [Claude Code Memory](https://code.claude.com/docs/en/memory)：CLAUDE.md 与导入机制。原文说明“there’s no guarantee of strict compliance”，所以规则进入上下文不等于每次都遵守。
- [OpenAI Codex Skills](https://developers.openai.com/codex/skills)：查 Codex 的 Skill 发现、调用和配置。
- [Cursor Rules](https://cursor.com/docs/rules)：查 User Rules、项目规则、作用范围和引用机制。
- [Cursor Skills](https://cursor.com/docs/skills)、[Cursor Subagents](https://cursor.com/docs/subagents)：查手动调用、材料可见性和子 Agent 上下文。

仓库的全局规则文件是维护源，具体宿主使用的入口不同。软链检查只验证安装关系，不能替代当前会话加载证据；缺少再次读取记录也不能证明模型未使用先前进入上下文的材料。

## 3. 写作依据与表达风险

写作依据用于解释选择，不构成新的禁词表。名称清晰与设计准确需要分别判断，来源中出现过的表达也可能不适合成品读者。

### Google 官方写作指南

术语需要与读者理解相匹配。[Words](https://developers.google.com/tech-writing/one/words) 要求：“apply the same unambiguous word or term consistently throughout your document”。该指南也允许定义新术语，因此不能把所有陌生词或中英文并用都判为错误。

格式和名称承担不同职责。[Code in text](https://developers.google.com/style/code-in-text) 根据文本用途区分代码实体与普通名称的样式，不要求为减少代码样式创造中文别名。[Tables](https://developers.google.com/style/tables) 根据内容关系选择表格，两列条件与动作表不能仅凭列数判错。仓库的具体排版偏好仍以主定义为准。

按问题查阅以下页面，无需每次全部阅读：

- 句子与段落：[短句](https://developers.google.com/tech-writing/one/short-sentences)、[主动语态](https://developers.google.com/tech-writing/one/active-voice)、[段落](https://developers.google.com/tech-writing/one/paragraphs)。
- 内容组织：[列表与表格](https://developers.google.com/tech-writing/one/lists-and-tables)、[长文档](https://developers.google.com/tech-writing/two/large-docs)、[插图](https://developers.google.com/tech-writing/two/illustrations)。
- 表达与样式：[术语](https://developers.google.com/style/jargon)、[列表](https://developers.google.com/style/lists)、[标题](https://developers.google.com/style/headings)。

### 项目实践与社区建议

[Gemini CLI 的 docs-writer](https://raw.githubusercontent.com/google-gemini/gemini-cli/main/.gemini/skills/docs-writer/SKILL.md) 是该项目的写作实践，适合参考任务组织和准确性检查，不是跨项目统一规范。

阮一峰的中文技术文档指南属于社区建议，可按需参考[文本](https://raw.githubusercontent.com/ruanyf/document-style-guide/master/docs/text.md)、[段落](https://raw.githubusercontent.com/ruanyf/document-style-guide/master/docs/paragraph.md)和[标题](https://raw.githubusercontent.com/ruanyf/document-style-guide/master/docs/title.md)。其中“唯二”改为“仅有的两种”是常用表达的例子，不足以判断业务对象、条件或并发约束是否完整。

### 通用失败模式与已知限制

表达问题可能沿材料转换传播，也可能在改写时新增；以下区分帮助选择验证对象，不直接解释某次模型的内部原因。

- 输入已有概括词，不能证明成品读者理解其含义；也不能据此否定已确认的业务决定。
- 格式调整可能改变名称对应，缩减或润色可能删除条件、动作和关联约束。更短、更顺并不证明设计保持。
- 语法检查验证结构，内容核对验证含义；某一版本的审核结果不能证明后续版本正确。
- 片段中未找到约束不等于全文没有约束；将 Agent 的解释当作原始轨迹，会混淆观察和归因。

Spec 整理阶段可能需要额外动作，但输入 Spec 存在含混表达，不能证明由 [my-to-spec](../skills/my-to-spec/SKILL.md) 产生。是否修改该 Skill，取决于其任务基线和实际缺口；这不阻碍对文稿生成、缩减和审核的局部验证。

## 4. 实证研究的适用范围

论文作为研究证据保留版本和实验范围，不视作厂商规范，也不将组间统计结果转换成单条指示的必然效果。

- [ETH：Evaluating AGENTS.md，v3](https://arxiv.org/html/2602.11988v3) 在 SWE-bench 与 CTXbench 等软件任务中观察到，上下文文件通常未提高成功率，平均推理成本增加超过 20%。该版本未发现文件长度或特定指示类别对性能有显著影响；不能概括为所有上下文都会降低成功率，也不能据此认定中文文档错误由长度或冗余造成。
- [SkillsBench，v4](https://arxiv.org/html/2602.12670v4) 比较跨任务、模型和 Agent 执行环境的 Skill 效果。附录 F.1 的数量分组针对任务附带的 Skill 数量，F.2 讨论文档长度；这些结果不是单个 Skill 的章节数上限，也不证明复述模型默认能力必然产生负作用。

两项研究都提示效果需要在具体任务中检验。本项目据此保存基线、限制未经验证的效果主张，不以论文中的阈值替代本地行为观察。

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
