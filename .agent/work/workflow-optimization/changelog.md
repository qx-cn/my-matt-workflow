# Workflow Optimization Changelog

## 批次 1：Review 对象与快照闭环

- 改了什么：新增只读 runtime 命令 `review-snapshot`，以固定点的 merge base 和当前完整工作树生成内容寻址的 `content_id`；分别列出 committed、staged、unstaged、untracked 来源，但快照身份不受暂存位置变化影响。
- 改了什么：`my-code-review` 改为审查同一内容快照，tracked 内容读取完整 diff，untracked 内容逐项读取；两个审查轴共享 receipt，内容变化后必须完整重审。
- 改了什么：`my-implement` 在实施开始记录基线，审查后提交，再以原 receipt 和 `--require-clean` 验证 Commit 与已审查内容等价。
- 改了什么：新增 runtime 行为测试与 Skill 契约测试，并刷新受影响 eval 的源哈希。
- 原则依据：P1。Skill 保留审查决策与关键门禁，内容哈希、状态枚举和等价性校验由确定性 runtime 执行；没有写死具体审查模型。
- 验证：`python3 -m unittest discover -s tests` 通过 128 项；构建 release `workflow-opt-review-snapshot-v1` 后，`python3 tools/workflow.py check` 返回整体 `valid`。

## 批次 2：Composition 类型化语义

- 改了什么：composition manifest 升级为 v2，每条 `callers` 边必须声明 `kind: method | handoff`；路由入口继续由 `routable_entries` 单独表达。
- 改了什么：共享 composition adapter 明确三种控制流：router 只命名入口，method 同轮执行并返回宿主，handoff 才按策略决定自动继续或显式调用后停止。
- 改了什么：`my-grill-me`、`my-grill-with-docs`、`my-implement`、`my-improve-codebase-architecture` 的内部依赖在 manual 下不再输出下一条 Skill 文本；`my-wayfinder → my-to-spec` 保留为真正阶段交接。
- 改了什么：增加清单类型校验、非法 kind 回归测试及 manual 内部方法返回宿主的契约测试，并刷新受影响 eval 源哈希。
- 原则依据：P1。组合规则保持在轻量共享 adapter 与机器可检验 manifest 中；仅真正授权边界暂停，普通内部方法由宿主自治执行。
- 验证：`python3 -m unittest discover -s tests` 通过 130 项；构建 release `workflow-opt-composition-v2` 后，`python3 tools/workflow.py check` 返回整体 `valid`。

## 批次 3：Spec 与 Handoff 最终校验 Gate

- 改了什么：新增共享资源 `artifact-finalization.md`，将来源账本、内部一致性、读者重建和事实正确性定义为四个互不抵消的 `pass | blocked` gate。
- 改了什么：按主张类型分别复核用户确认、仓库事实、外部一手来源、实际执行证据与假设/未知；承重未知未解除时禁止写入、发布或交接。
- 改了什么：`my-to-spec`、`my-handoff`、`my-review-design`、`my-final-state-writing` 接入该 gate；Spec 增加精简的“依据与未知”，handoff 增加 fresh-context 重建与链接复核。
- 改了什么：为 `my-wayfinder` 补充传递资源消费者，保证其组合内嵌的 `my-to-spec` 在 release 中不断链；增加资源分发和 Skill 接入测试。
- 原则依据：P1、P2。正确性与证据门禁是明确底线；成品只展示影响读者决策的依据与未知，不机械暴露完整工作表。
- 验证：`python3 -m unittest discover -s tests` 通过 132 项；构建 release `workflow-opt-finalization-gate-v1` 后，`python3 tools/workflow.py check` 返回整体 `valid`。

## 批次 4：Spec 精简、Revision 与 Ticket 回退

- 改了什么：`my-to-spec` 移除“很长且全面”的用户故事要求和“全项目理想一个 seam”的通用结论，改为按风险描述目标、范围、行为与验收、不变量、承重决定和验证策略。
- 改了什么：Spec 增加稳定 `spec_id`、递增 `revision`、`supersedes` 和不可覆盖的历史版本；Ticket 增加 `spec_id/spec_revision/spec_ref` 血缘及替代/补偿引用。
- 改了什么：runtime 新增只读 `ticket-transition` gate，校验 `ready-for-agent → implementing → complete` 与 `implementing → blocked-by-design → revising → revalidated → implementing`；进入 `revalidated` 前重验规则与血缘，进入 `complete` 前检查验收复选框。
- 改了什么：`my-implement` 按影响级别局部回退，默认不重走完整访谈；已完成 Ticket 保持历史不变，变化通过补偿或迁移 Ticket 表达。
- 原则依据：P1。Spec 不锁死可逆实现细节；公开接口、数据语义、验收和风险仍作为承重决定；schema 与状态迁移由 runtime 确定性校验。
- 验证：`python3 -m unittest discover -s tests` 通过 138 项；构建 release `workflow-opt-spec-revision-v1` 后，`python3 tools/workflow.py check` 返回整体 `valid`。

## 批次 5：验证分层与主链行为证据

- 改了什么：为 static、unit、deterministic-contract 与 fresh-agent-smoke 定义不可互相替代的证据层级；`check` 和历史命名的 `smoke` 命令显式返回自身证据等级。
- 改了什么：新增主链 fresh-context 契约场景，覆盖最终校验、Spec revision、Ticket 血缘、完整 review 快照与证据型测试报告；它仍只属于确定性契约证据。
- 改了什么：增加隔离主链行为用例与最小 fixture。独立代理生成了 Spec、Ticket、实现、6 项通过的实际测试和测试报告；因用量上限中断，主代理完成最终审查、提交等价性与单 Ticket 收口，记录明确标为混合 smoke，不冒充完整独立通过。
- 改了什么：行为用例发现 Ticket parser 不接受标准 YAML 块列表；runtime 已同时支持行内列表和块列表，并新增回归测试。
- 原则依据：P1、P2。验证声明与真实证据严格对齐；确定性门禁放在 runtime，报告只给决策所需的结论、范围和限制。
- 验证：`python3 -m unittest discover -s tests` 通过 140 项；构建 release `workflow-opt-validation-layers-v2` 后，`python3 tools/workflow.py check` 返回整体 `valid`，并分别标明 static、unit 与 deterministic-contract 证据等级。

## 批次 6：读者导向与内容/前端阶段分离

- 改了什么：新增共享 reader-first 规则；面向人的文章、研究、测试/评审/诊断报告、术语与 ADR、问卷、triage 评论、向导等在写作前先确定读者、用途、动作、已有知识和风险，成品结论先行，不机械展示 reader brief。
- 改了什么：`my-tech-design`、`my-improve-codebase-architecture`、`my-teach` 保留单一入口，内部支持 `content`、`frontend <artifact>`、`full`；默认先落盘结构化语义工件并停止，允许用户切换模型后从同一入口继续前端阶段。
- 改了什么：三个 Skill 各自拆出 `CONTENT.md` 与 `FRONTEND.md`。内容阶段不生成 HTML/CSS/JS；前端阶段只消费语义工件与模板，缺内容返回 `blocked-by-content`，不得修改事实、结论、约束或教学答案。
- 改了什么：移除技术方案“总览必须有图”和架构候选“每项必须前后图”的默认义务；只有图示显著降低理解成本时才写 `visual_intent`。`my-edit-article` 移除统一 240 字符段落上限。
- 改了什么：`my-teach` 强化学习者类型、现实任务、递进练习、掌握证据与一手来源校验，并移除 `/Users/admin/...` 绝对 humanizer 路径；`my-humanizer` 增加不造词边界，同时保留正常专业“动词＋宾语”表达。
- 原则依据：P2、P3、P4、P5、P6。读者分析是内部约束；表达方式由信息形状决定；内容、模板、渲染与模型角色在真实工件边界分离。
- 验证：`python3 -m unittest discover -s tests` 通过 143 项；构建 release `workflow-opt-document-stages-v1` 后，`python3 tools/workflow.py check` 返回整体 `valid`。

## 批次 7：运行上下文 Receipt 与 Run Journal

- 改了什么：保留六个 adapter 按关注点拆分，不合并成整块 `runtime-conventions.md`；新增 `run-context`，一次解析 Ticket/Spec 血缘、实际路径规则、测试命令、composition/work-scope/decision/humanizer 策略及四类写 gate，并生成内容寻址 `context_id`。
- 改了什么：新增 `run-start` 与 `run-record`。每个 Ticket/Spec revision 在 `.agent/work/<topic>/runs/` 有独立 JSON journal，原子记录 phase、base SHA、context receipt、test/review receipt、blocker 和事件历史。
- 改了什么：`my-implement` 优先从既有 journal 恢复；新运行只解析一次 context，阶段变化及时落盘。设计失效进入 `blocked-by-design` 必须有 blocker，新 Spec revision 使用新 journal，历史不覆盖。
- 改了什么：修正非 Git 源树复制测试，使其先构建与复制后源树相匹配的 release，再验证 `check`，避免测试依赖开发工作区旧 release。
- 原则依据：P1。确定性解析、状态迁移和原子持久化在 runtime；Skill 只保留恢复规则、关键门禁和决策边界。
- 验证：`python3 -m unittest discover -s tests` 通过 147 项；构建 release `workflow-opt-run-journal-v1` 后，`python3 tools/workflow.py check` 返回整体 `valid`。

## 批次 8：证据化代码审查

- 改了什么：`my-code-review` 将 Standards 与 Spec 明确为同一次 review 的内部分析方法；`manual` 与 `automatic` 都在同一次调用中完成并返回汇总，不再要求用户分别启动。
- 改了什么：新增统一发现契约：P0/P1/P2 严重度、最小位置、失败场景或不变量、证据与 high/medium 置信度、影响及回归验证。低置信度内容只能作为待核实问题，P2 不抬高为 blocker。
- 改了什么：Fowler smell 从固定扫清单改为按需诊断词汇；无法说明本次变更的可观察影响时不算发现。高风险变更按认证、敏感数据、迁移一致性、并发、性能或协议兼容增加视角，低风险不为并行而并行。
- 改了什么：移除两轴固定 400 字限制；内容改变后仍以新 `content_id` 重跑双轴，P0/P1 关闭并有针对性回归后才能进入提交 gate。
- 原则依据：P1、P2。审查保留风险门禁与证据格式，同时让模型按实际变更选择审查深度；报告服务于修复与合并决策，不以统一字数压缩信息。
- 验证：`python3 -m unittest discover -s tests` 通过 147 项；构建 release `workflow-opt-code-review-v1` 后，`python3 tools/workflow.py check` 返回整体 `valid`。

## Astra 批次 1：指令权威与原生规则语义

- 改了什么：Codex `resolve-rules` 改为沿每个影响路径从仓库根走到父目录；每层只选择首个非空的 `AGENTS.override.md`、`AGENTS.md` 或显式配置 fallback，并返回目录、选择原因、适用路径和目录深度覆盖序号；不再把 `.agent/rules` 冒充 Codex 原生规则。
- 改了什么：新增共享 `instruction-authority.md`，明确平台/宿主、用户目标与授权、原生项目规则、Spec/Ticket、profile/runtime、共享方法和 Skill 默认值各自的权力边界；同步修正 enterprise safety 与 setup 默认说明。
- 改了什么：新增确定性 `decision-gate`，把 `routine | consequential | user-exclusive` 与 `ask | autonomous | halt` 映射为唯一的 `allow | confirm | pause`；`my-code-review` 的缺基线、缺 Spec 分支不再列出三个模糊选项。
- 改了什么：composition policy 的展示文案改为引用 runtime 共享常量；`manual` 明确为 method 同轮执行、只有已授权 handoff 显式交接，不再恢复阶段 0 前的旧含义。
- 原则依据：P1、P7.1、P7.2。自然语言只保留权力边界和分类方法；路径选择、策略映射与覆盖顺序由 runtime 确定性执行。
- 验证：受影响的 workflow/resource/composition 测试通过 125 项；构建 release `astra-instruction-semantics-v2` 后，`python3 tools/workflow.py check` 返回整体 `valid`。这证明静态、unit 与 deterministic-contract 门禁通过，不等同于 Astra 真实行为已验证。

## Astra 批次 2：减少非必要暂停

- 改了什么：`my-to-tickets` 对可从已批准 Spec 推断的粒度与依赖执行自检后直接生成可审阅草稿；只有承重未知才走 `consequential` gate，用户专属产品取舍仍必须确认。
- 改了什么：`my-edit-article` 不再为普通、可逆的章节重排单独等待确认；新稿仍默认保留原文，原地覆盖仍保留破坏性确认边界。
- 改了什么：`my-diagnosing-bugs` 在尚无 red loop 时继续穷尽日志、配置、历史、测试、调用链和一手文档等只读证据，并允许隔离探针；没有 red 证据时仍禁止宣称根因或实施猜测性修复。
- 改了什么：领域上下文归属改为明确的 `consequential` gate；纯文档仓库的原型语言成为无需暂停的 `routine` 选择；Wayfinder 在路线已清晰时直接报告结果，只在下一阶段已授权时 handoff。
- 原则依据：P1、P7.2、P7.4。已授权的可逆本地工作主动推进；承重决定、破坏性写入与阶段授权继续保留明确边界。
- 验证：受影响的 workflow/resource/eval 测试通过 130 项；构建 release `astra-confirmation-flow-v1` 后，`python3 tools/workflow.py check` 返回整体 `valid`。刷新 eval 哈希只证明契约工件与源码一致，不提升为真实模型行为证据。

## Astra 批次 3：风险分层验证、能力感知委派与宿主元数据

- 改了什么：`my-implement` 改为改动中跑最小针对性测试、Ticket 完成跑受影响模块或链路，只有计划完成、发布/合并、项目规则要求或风险升级时才跑完整套件；通过后无新变化或风险不重复扩大。
- 改了什么：`DESIGN-IT-TWICE.md` 移除“3 个以上子代理”的固定数量；只有工具可用、用户未禁止、任务可独立切分且并行有收益时才委派，否则主 Agent 串行生成不同方案并承担最终验证。
- 改了什么：保留可移植源码中的两套显式调用声明，但安装时按目标投影。Codex 安装件只保留 `agents/openai.yaml`，Cursor/Claude 安装件只保留 `disable-model-invocation: true`；安装状态记录投影目标。
- 证据：Cursor 官方 [Agent Skills](https://prod.cursor.com/docs/skills) 与 Claude Code 官方 [Skills](https://code.claude.com/docs/en/slash-commands) 均要求 `disable-model-invocation: true` 表达仅用户调用，因此不能从跨宿主源码直接删除；Codex 继续使用现有 `agents/openai.yaml`。
- 原则依据：P1、P7.3、P7.5。验证投入服从风险；委派服从能力和收益；宿主专属控制不以两条重复指令同时进入目标 Agent 上下文。
- 验证：受影响的 workflow/eval 测试通过 118 项，新增 Codex 与 Cursor 安装投影回归测试；构建 release `astra-validation-delegation-v1` 后，`python3 tools/workflow.py check` 返回整体 `valid`。

## Astra 批次 4：真实行为证据与状态一致性

- 改了什么：新增 9 项 Astra fresh-agent 行为场景，覆盖已授权工作不重复确认、用户指令优先、Codex 原生规则覆盖、未解冲突、manual method/handoff、风险分层测试、有意 HITL 停止点、串行委派 fallback 和主工作流。
- 改了什么：新增严格行为证据 schema、runtime validator 与 `validate-agent-evidence` CLI。`pass` 必须由 `gpt-6-astra` 运行、保留原始输出且所有 rubric 为 true；`fail` 必须至少有一项 false；`--require-complete` 只表示场景记录齐全，不冒充全部通过。
- 改了什么：真实 Astra 行为测试发现普通本地文件写入被误描述为“通用 write gate”；已把共享指令收窄为只有 `branch`、`commit`、`external`、`docs` 四类 profile 写入走 write gate。
- 行为证据：ChatGPT app 内置 Codex CLI 0.153.0、`gpt-6-astra`、release `astra-behavior-eval-v1` 运行 9 项，结果为 8 pass、1 inconclusive。主链已完成 Spec/Ticket 血缘与准入、三轮 TDD、7 项验收测试（exit 0）和完整工作树 snapshot；账户周额度在 commit 前耗尽，因此提交等价性、Ticket complete、测试报告和最终交接未观察到。
- 原则依据：P1、P6、P7.1–P7.5。轻量确定性 gate 与真实模型行为证据分层；有意的人类/模型交接保持可观察停止；宿主沙箱与 workflow 授权分别记录。
- 验证：结构化证据校验返回 9 runs、8 pass、1 inconclusive；`python3 -m unittest discover -s tests` 通过 160 项；构建 release `astra-behavior-eval-v2` 后，`python3 tools/workflow.py check` 返回整体 `valid`。

## Astra 行为验证成本收口

- 改了什么：记录主链第三次续跑会话；该会话只读核对既有 snapshot、journal 与测试证据，尚未提交或改变临时仓库时主动中断。
- 证据边界：本次约消耗 40,438 tokens，但没有补齐 commit equivalence、Ticket complete、测试报告或最终 handoff，因此总结果仍为 8 pass、1 inconclusive。
- 后续约束：默认不再调用 Astra 补齐最后一项；只有用户明确接受成本时才可从保留状态继续，且不得把未观察到的结果记为通过。
- 原则依据：P1、P7.3。验证投入服从风险与成本，证据结论不得超过实际观察。
- 验证：行为证据 validator 返回 9 runs / 8 pass / 1 inconclusive；`python3 -m unittest discover -s tests` 通过 160 项；`python3 tools/workflow.py check` 对 release `astra-behavior-eval-v2` 返回整体 `valid`。

## 发布与本地安装

- 提交：本地 `main` 已创建 `667b3f2 feat: harden workflow instructions for Astra`，35 个源树文件，未包含 `.agent` 工作产物。
- Codex：安装 `astra-behavior-eval-v2` 成功；install-state 回读为 32 Skills、`metadata_projection: codex`、Skills home `/Users/sherly/.agents/skills`。
- Claude：安装 `astra-behavior-eval-v2` 成功；install-state 回读为 32 Skills、`metadata_projection: claude`、Skills home `/Users/sherly/.claude/skills`。
- 推送：自动安全审查在首次 `git push origin main` 前拦截；披露具体远端 `https://github.com/qx-cn/my-matt-workflow.git` 并取得用户明确授权后，成功推送 `589317c..667b3f2`。本地与远端 `main` 均为 `667b3f25b1e769116cbbfd38a5651f937fa781c3`，领先/落后为 0/0。
