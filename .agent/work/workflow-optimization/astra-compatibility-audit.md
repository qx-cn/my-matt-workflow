# GPT-6 Astra 指令兼容性审计

## 决策摘要

需要继续改造，但不应全面重写 Skills。当前架构已经具备共享 adapter、runtime gate、run journal 和分层证据，方向正确；Astra 暴露的是其中仍未收口的指令语义。

本次只读审计确认 4 个 P0 问题：

1. Codex `AGENTS.md` 发现方式与官方原生语义不一致；
2. workflow 没有一份完整、可执行的指令优先级与冲突处理契约；
3. `composition_policy: manual` 在 runtime 说明与 adapter 中含义相反；
4. `decision_policy: ask` 的定义过宽，部分 Skill 又使用未映射到策略值的“询问、自治或停止”。

这四项会让 Astra 比旧模型更容易加载错误规则、重复确认或提前停止。应先对齐下文 D1–D5，再实施。

## 1. 审计依据与范围

### 官方依据

- [OpenAI GPT-6 Astra 模型指南](https://developers.openai.com/api/docs/guides/latest-model)：Astra 对 Skills、`AGENTS.md` 等上下文指令更敏感；模糊或冲突规则可能导致提前暂停。官方同时建议明确用户指令与 Skill 指令的优先级，校准主动推进、子代理使用和测试范围。
- [OpenAI Codex `AGENTS.md` 指南](https://learn.chatgpt.com/docs/agent-configuration/agents-md)：Codex 在每层目录只选择一个指令文件，优先 `AGENTS.override.md`，否则 `AGENTS.md`；从项目根走到当前目录，越靠近当前目录的规则越晚加载并覆盖较早规则。

### 项目范围

只读检查了：

- 32 个 `skills/*/SKILL.md` 及其按需参考文件；
- `policies/`、`resources/adapters/`、`resources/manifest.json`；
- `composition/manifest.json`；
- `tools/workflow_lib/` 中 profile、规则解析、写操作 gate、Ticket transition、eval；
- 6 个 deterministic-contract 场景和现有 fresh-agent smoke 说明；
- 已确认的 P1–P6 和阶段③状态。

“必须、不得、停止、暂停、确认、询问”等词在 Skill Markdown 中共出现约 301 次。这个数字只是审计入口，不等于缺陷数；真正要判断的是每条指令的来源、作用范围、条件和冲突结果是否唯一。

## 2. 已经适配 Astra 的部分

### 2.1 组合调用已区分三种边

`resources/adapters/composition.md` 已区分 `router`、`method` 和 `handoff`。内部 method 在 manual/automatic 下都同轮执行并返回宿主，有意的 handoff 才能停止。这是正确方向，应保留。

### 2.2 普通实现决策已有自治边界

`policies/decision-taxonomy.md` 已把可逆实现细节与目标、范围、公开接口、数据语义、测试投入和风险承担等承重决策分开，符合 P1，也符合官方“先完成已经授权的工作”的建议。

### 2.3 runtime 已承接确定性控制

`my-implement` 使用 run context receipt、Ticket transition、write gate、review snapshot 和 run journal，而不是让 Skill 自己反复解释状态。这降低了 Astra 对重复自然语言规则产生不同理解的风险。

### 2.4 有意停止点有清楚业务目的

以下停止不应因 Astra 审计被删除：

- `my-grilling` 每次只问一个问题并等待回答；
- 安全、破坏性操作和外部写入的真实授权门禁；
- 内容阶段与前端阶段之间用于切换模型的交接；
- `single-ticket`、未批准 handoff 和用户专属产品决策。

## 3. 发现

### A-01 · P0：Codex 规则发现不符合原生 `AGENTS.md` 语义

**证据**

- `tools/workflow_lib/rules.py:82-89` 同时加入根目录的 `AGENTS.override.md` 和 `AGENTS.md`，随后直接返回；
- 它没有从项目根沿影响文件路径逐级查找嵌套 `AGENTS.md`；
- 返回项没有原生层级或覆盖顺序字段；
- `resources/adapters/project-rules.md:9` 反而把 `.agent/rules/**/*` 描述为 Codex 规则来源。

**与官方语义的差异**

Codex 每层目录只取 override、AGENTS 或 fallback 中的第一个非空文件，并从根到当前目录合并，靠近当前目录者覆盖前者。当前 resolver 会同时加载本应互斥的根文件，也会漏掉嵌套规则。

**影响**

计划、Ticket 和 review 可能绑定错误规则。Astra 更严格执行后，这会从“规则证据不精确”升级为实际行为错误。

**建议**

让 `resolve-rules` 对 Codex 复现原生项目级发现：按每个实际影响路径从 repo root 走到父目录；每层只选择一个文件；返回 `directory`、`selected_by`、`precedence_index` 和适用路径。个人全局 `~/.codex/AGENTS*` 不写入可共享 Ticket，只作为当前运行环境事实。

### A-02 · P0：没有完整的指令权威与冲突契约

**证据**

- `policies/enterprise-safety.md:3` 只说仓库规则“始终优先”，未说明它优先于什么；
- `resolve_rules()` 只返回文件元数据，不读取、比较或表达规则之间的覆盖关系；
- Ticket 准入仅要求 `rule_conflicts: []`，无法证明实际加载的规则没有冲突；
- 用户目标、已确认决定、Spec/Ticket、profile、adapter、Skill 与原生项目规则之间没有统一顺序。

**影响**

遇到冲突时，Agent 只能自行猜测覆盖关系。Astra 可能停下，也可能把编码规范错误地解释成可以扩大任务范围或授权外部写入。

**建议**

建立单一、简短的 instruction-authority 契约，并区分三种维度：

1. 平台/宿主的不可覆盖指令；
2. 用户目标、授权与项目原生规则各自能决定什么；
3. workflow 内部 profile、Spec/Ticket、policy/adapter、Skill 默认值的覆盖顺序。

仓库规则可约束代码和验证，但不能自行扩大用户目标、写操作范围或外部授权。无法按原生覆盖规则消解的同级冲突才进入 `rule_conflicts` 并暂停。

### A-03 · P0：`composition_policy: manual` 有两个相反定义

**证据**

- `resources/adapters/composition.md:11-14`：manual 下 method 与 automatic 相同，只有 handoff 输出显式调用并停止；
- `tools/workflow_lib/profile.py:157-160`：manual 仍描述为“提示用户手动启动依赖 Skill”。

**影响**

后者正是阶段 0 修复的旧语义。setup 说明或维护者可能重新把旧语义写回 Skill，Astra 也更可能逐字采用它。

**建议**

profile 的展示文案从 composition adapter 的结构化定义生成，或至少共享同一个常量；禁止另写自然语言副本。

### A-04 · P0：`decision_policy` 定义过宽且调用方映射不确定

**证据**

- `tools/workflow_lib/profile.py:166-170` 把 `ask` 概括为“遇到决策时询问”；
- `policies/decision-taxonomy.md:3` 明确普通可逆实现细节不应暂停；
- policies 目录只打包给少数 Skill，但 `my-code-review`、`my-diagnosing-bugs`、`my-domain-modeling` 等也直接读取 `decision_policy`；
- `skills/my-code-review/SKILL.md:24,44` 使用“询问、自治判断并记录证据，或停止”，没有逐项映射 `ask | autonomous | halt`。

**影响**

同一个配置值在不同 Skill 中可能产生不同动作。Astra 会倾向选择保守分支，导致 review 无基线或无 Spec 时不必要地停摆。

**建议**

把“是否需要用户决定”与“当前策略怎么处理”拆开：先用统一决策分类判断 `routine | consequential | user-exclusive`，再由 runtime/共享规则返回唯一动作。Skill 不再写“询问、继续或停止”这种选择列表。

### A-05 · P1：部分确认点没有服从同一授权模型

**证据**

- `my-to-tickets:44-53` 无条件要求用户批准 Ticket 粒度和阻塞边；
- `my-edit-article:11` 无条件等待结构方案确认；
- `my-setup` 的 apply、迁移、嵌套 Git 处理属于真实写入/破坏边界，确认合理；
- `my-humanizer` 的确认由显式 `humanizer_policy` 控制，也有唯一来源。

**影响**

目前“确认”混合了产品决定、安全授权、可逆草稿评审和风格偏好。Astra 无法知道哪些可以在用户已明确要求执行时省略。

**建议**

只保留三类阻塞确认：用户专属决定、不可逆/外部写入、新增范围或授权。可逆的本地草稿、从已批准 Spec 机械拆 Ticket、能够从用户请求直接推出的文章重组，应按 profile 执行或先产出可审阅结果，再在真正写入边界确认。

### A-06 · P1：测试范围无条件扩大

**证据**

`skills/my-implement/SKILL.md:28` 要求每张 Ticket 结束运行一次完整测试套件。OpenAI 官方指南明确提醒 Astra 可能在小任务上测试过度，并建议在相关验证通过后，只有新变化、失败或未解决风险才扩大或重复测试。

**影响**

多 Ticket 计划会重复运行相同全量测试，拖慢反馈，也可能把无关失败变成新的阻塞。

**建议**

采用三层验证：改动中运行最小针对性验证；Ticket 完成运行受影响范围验证；计划结束、发布门禁、项目规则要求或风险升级时才运行完整套件。`workflow.py check` 继续作为本项目源树改动的权威门禁，不受此通用策略放宽。

### A-07 · P1：诊断 Skill 可能在已授权只读工作前停止

**证据**

`my-diagnosing-bugs:60-71` 在无法建立紧凑 red loop 时，`ask`/`halt` 停止；并要求在 red 命令存在前不得阅读代码、建立理论。只有 autonomous 且计划预先允许时才能进入有限证据模式。

**影响**

真实 Bug 常因环境、权限或第三方状态暂时不能复现。Astra 会更严格执行“不读代码”，即使仍有日志、历史、配置和调用链等安全只读证据可收集。

**建议**

保留“不能声称已定位根因”的证据门槛，但允许在 red loop 不可得时先穷尽已授权的只读证据，再只对会改变后续策略的决定询问用户。

### A-08 · P1：子代理规则缺少工具可用性和用户策略条件

**证据**

- `my-codebase-design/DESIGN-IT-TWICE.md:21` 要求并行启动 3 个以上子代理；
- `my-wayfinder` 的研究委派则是按需要和 composition policy 选择，较合理。

**影响**

无条件数量要求会与宿主并发上限、用户禁止委派、成本要求或根本没有 Agent 工具的环境冲突。

**建议**

把委派定义为能力感知策略：仅在工具可用、用户未禁止、子任务独立且并行能改善质量或时间时使用；数量由独立方案空间和并发额度决定，不固定为 3 个以上。

### A-09 · P1：Codex 调用策略存在重复元数据

**证据**

32 个 Skill 同时在 `SKILL.md` 使用 `disable-model-invocation: true`，并在 `agents/openai.yaml` 使用 `allow_implicit_invocation: false`。本项目 validator 接受前者，但 Codex 的调用策略已经由后者表达。

**影响**

同一含义有两个来源，且前者可能属于其他宿主或旧格式。维护时容易只改一处；迁移检查也难判断哪个生效。

**建议**

先确认 Cursor/Claude 是否仍依赖 `disable-model-invocation`。若依赖，应在构建阶段按目标宿主生成相应元数据；Codex 包只保留 `agents/openai.yaml`。若不依赖，则删除重复字段，并修正 `my-writing-great-skills` 中的旧机制说明。

### A-10 · P0：现有 eval 无法证明 Astra 遵循期望语义

**证据**

- 6 个 scenario 都由 Python 根据结构化输入返回预写结果，并以 Skill SHA 防止漂移；
- `rule-contract` 只检查 `rule_evidence` 等布尔值，不测试原生 AGENTS 发现、覆盖或冲突；
- `tdd-seam-pressure` 和 `diagnosing-bugs-no-red-loop` 固定期待停止，可能把需要复审的旧行为锁成“正确”；
- `evals/VALIDATION.md` 已诚实说明 deterministic-contract 不是模型行为证据；
- 唯一主链 fresh-agent smoke 的完整独立端到端结论仍是 `inconclusive`。

**影响**

`workflow.py check` 可以全绿，但不能回答 Astra 是否重复确认、错误停止、加载错规则或过度测试。

**建议**

新增 Astra 行为 eval，不把模型名称写进 Skill 原则，只记录在证据元数据中。至少覆盖：

1. 用户已授权可逆本地工作，Skill 不应再次确认；
2. 用户要求与 Skill 建议冲突，用户要求优先；
3. 根/嵌套 `AGENTS.md` 与 override 的原生选择；
4. 同级规则真冲突时明确暂停并指出来源；
5. manual method 同轮返回宿主，manual handoff 才停止；
6. 小改动只运行相关测试，全量测试有明确升级理由；
7. 内容/前端交接和 Grill HITL 仍按设计停止；
8. 无子代理能力时能够串行降级。

每个场景同时记录模型、宿主、release、输入、原始输出、是否询问、执行到哪一步、测试命令和人工判定。与当前稳定模型做同输入对照，但不以“旧模型表现”作为正确性来源。

## 4. 建议实施顺序

### 批次 1：先消除会加载错误指令的 P0

- 修正 Codex 原生 AGENTS 发现与覆盖顺序；
- 建立 instruction-authority 契约；
- 消除 composition 和 decision 两处同名策略歧义；
- 为这些语义增加确定性测试。

### 批次 2：减少非必要暂停

- 将高频 Skill 的模糊分支改成策略值到动作的一对一映射；
- 调整 Ticket、文章和诊断中的确认时机；
- 保留安全、HITL 与有意阶段交接。

### 批次 3：校准验证与委派

- 引入风险分层测试范围；
- 将子代理使用改成能力感知策略；
- 清理 Codex/其他宿主的重复调用元数据。

### 批次 4：Astra 行为验证

- 先跑迁移前基线；
- 每批后跑 unit、deterministic-contract 和代表性 Astra fresh-agent smoke；
- 完成后跑主链 Astra smoke；
- `python3 tools/workflow.py check` 仍是每批源树门禁，但报告不得把它写成 Astra 行为通过。

## 5. 需要用户确认的设计决策

### D1 指令权威

**推荐：**平台/宿主硬约束不可覆盖；当前用户目标与明确授权决定任务范围；原生项目规则约束其适用路径内的实现和验证，但不能扩大任务或授权写操作；已批准 Spec/Ticket 约束交付；profile 和 runtime gate 决定自治与写入；shared policy/adapter 定义方法；Skill 建议与默认值最低。遇到原生规则与用户目标不能同时满足时报告冲突，不擅自覆盖任一方。

### D2 确认门槛

**推荐：**只有用户专属决定、不可逆/外部写入、新范围或新授权阻塞；可逆本地工作先完成到可审阅状态。`decision_policy: ask` 只控制承重决定，不控制普通技术细节。

### D3 测试范围

**推荐：**改动中最小测试，Ticket 结束受影响范围测试，计划/发布结束或风险升级才跑全量；项目明确要求的权威门禁始终执行。

### D4 无法复现 Bug 时的推进方式

**推荐：**允许先做日志、配置、历史和调用链等只读诊断；没有 red loop 时不得宣布根因或实施猜测性修复，只有后续路径会改变目标、范围、接口、测试投入或风险时才询问。

### D5 子代理策略

**推荐：**不固定数量；工具可用、用户未禁止、任务能独立并行且收益明确时才委派，否则串行完成或明确报告能力缺口。

## 6. 验收边界

阶段④审计完成不代表已兼容 Astra。完成兼容改造至少需要：

- D1–D5 经用户确认并落盘；
- P0/P1 源码改造通过 `python3 tools/workflow.py check`；
- 新增的确定性规则测试通过；
- 至少一轮 Astra fresh-agent 行为 eval 有完整原始证据；
- 主链、Grill HITL、内容/前端交接和外部写入门禁没有回归。
