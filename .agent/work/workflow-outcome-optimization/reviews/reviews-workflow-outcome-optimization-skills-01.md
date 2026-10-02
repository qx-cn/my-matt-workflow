# my-matt-workflow Skills 审查（只读分工产物）

- Review-Unit：`36ce314358fac1f680ba8c536ef07e1f594964478395a56578923248445b91b0`
- Target-Host：Codex；同时检查源码的可移植调用边。
- Evidence-Level：全部 findings 为 static；本分工没有运行行为对比，没有把字数下降或静态规则改善当成交付效果提升。
- 范围：32 个 `skills/*/SKILL.md`，32 个 `agents/openai.yaml`，被调用辅助材料及有行为意义的脚本。证据来自 metadata 映射的 snapshot_path。source_path/行号仅用于定位原文件。
- 生命周期：本报告不是最终审查收据，snapshot 由主 Agent 统一 finalize；仅 `status: match` 后可把结论交付用户。
- 总体结构结论：保留主链、风险分级、Spec/Ticket 血缘、增强自审及独立审查。现版已经修复“无条件两遍审查”“强制每次写作 humanizer”“所有接口设计必须并行若干 Agent”等旧问题的大部分；不重报已修复项。真正仍影响行为的部分集中在少量断开的调用边、测试证据的错误排除、局部门槛与共享权威的冲突。

## 按影响排序的 findings

### SK-01 / P1 / STRUCTURAL：首次本地分诊缺少 Spec 转换阶段

原文：`skills/my-triage/SKILL.md:54`：“维护者确认分类、状态与 brief 后……随后调用 {{skill-call:my-to-tickets}}”；`composition/manifest.json:84-87` 固定 `confirmed-local-brief → my-to-tickets` handoff。接收端 `skills/my-to-tickets/SKILL.md:12`：“从当前有效 Spec 形成 tracer-bullet 纵向切片”；`:14` 要先读源 Spec 血缘，`:22` 要填写 spec_id、spec_revision、spec_ref。`skills/my-triage/AGENT-BRIEF.md:41-68` 模板没有 Spec identity/revision/current 生成，`:3` 还把 brief 称为权威规格，但这不等于 versioned Topic Spec。`skills/my-to-tickets/TICKET-FORMATS.md:14-16` 与 `resources/adapters/ticket-selection.md:5` 均要求真正的源 Spec。

最小静态走查：已有有效 local 配置的项目第一次分诊一个新 Bug；主张已复现、brief 已确认，用户同意转入开发，但不存在对应 Topic current Spec。调用边把只有 brief 的任务交给只接受 current Spec 的拆分器。合规执行必须停下；继续执行则只能擅自造血缘或套用无关/旧 Spec。单纯确认 handoff 不能补齐这一数据契约。

最小改法：本地 confirmed brief 先检查有无与其需求匹配的有效 current Spec；没有时将 brief 作为已确认需求输入交 `my-to-spec`，不重新访谈，保留唯一设计审查关口与正常对齐点2；有匹配 Spec 才直接交 `my-to-tickets`。同步修改 composition 与唯一 user-intervention 交接清单，不单改正文。保留 triage 的外部状态机、验证主张、原始请求来源与既往拒绝知识。

验证：新 Bug 无 Spec；已有匹配 Spec；已有不匹配/被 superseded Spec 三条路径。每条生成的 implementation Ticket 必须回指正确 current revision；不得 invent lineage。当前只有 static 证据，不能说已经发生真实停摆。

### SK-02 / P1 / BEHAVIORAL：把独立存储验证一概当作实现耦合

原文：`skills/my-tdd/SKILL.md:26` 把“从旁路验证（例如不经接口而查询数据库）”归入反模式。`skills/my-tdd/tests.md:45-60` 把 `createUser → db.query` 标为 BAD，把 `createUser → getUser` 标为 GOOD。

失败路径：验收本身涉及“真实落盘、字段脱敏、数据库约束、事务原子性、重启恢复”时，独立读存储或 close/reopen 是证明契约的事实来源。若 write/read 两条 API 共用一个错误编码、缓存或投影，只经二者读回仍可能通过；独立存储检查能把该共同错误暴露出来。规则按“是否数据库查询”而不是“是否稳定外部契约”排除测试，会诱导 Agent 回避必要的验证。不会因此指控现有全部接口测试无效。

最小改法：保留“测试调用方可观察行为、稳定 seam、独立 expected source”，将禁令限定为私有实现细节的偶然结构断言。持久化与兼容本身是契约时，允许独立存储检查、跨进程/close-reopen探针、真实 adapter 的契约验证；明确证据边界。不要把每个普通 API 测试扩大为全量数据库集成。

验证：构造内存缓存正确但落盘错误、写读编解码同错、事务部分写入三个错误版本，选择的证据应能失败；修复后通过。保留现有“接口重构不应无故破坏测试”的价值。

### SK-03 / P2 / STRUCTURAL：验收证据被锁成一验收一测试

原文：`skills/my-implement/SKILL.md:10`：“每条验收分别对应独立测试断言，不共用一个测试”；`skills/my-writing-for-agents/SKILL.md:28` 的范例也是“每项验收已关联独立测试证据”；`skills/my-tdd/tests.md:23` 为 “One logical assertion per test”。

失败路径：一次真实落盘/恢复流程可以同时证明返回值、状态、资源释放和幂等性，property test 或矩阵也可按 assertion 定位多个验收。禁止共用一个测试会迫使拆分昂贵初始化/恢复场景、重复数据夹具与启动过程，或把跨验收不变量拆开而失去同一时序证据。这是明确的额外工作与证据形状限制；没有 comparative 时不宣称总体模型表现已经下降。

最小改法：要求每项验收有可定位、可独立辨别失败的断言或证据；允许多对多映射，避免“一个绿测试”遮蔽缺项。共同准备不等于共同失效；验收变更时能找到受影响证据即可。此根因由主 Agent 与共享 delivery/assurance 条款统一处理。

验证：一个真实恢复探针对应多个验收；一个参数矩阵覆盖多输入；部分验收缺断言。前两者能完成，后一者必须保持未验收。

### SK-04 / P2 / STRUCTURAL：humanizer 的局部确认与 test-report 强制调用留下双门槛

原文：`resources/humanizer.md:3`：“它不成为其他工作流写入前的强制步骤”；`skills/my-test-report/SKILL.md:90`：“写入或覆盖报告前，以嵌入模式使用 {{skill-call:my-humanizer}}”，`:92` 又说只有用户显式要求润色才修改；`skills/my-humanizer/SKILL.md:41`：“未确认不得写入或覆盖”。`resources/instruction-authority.md:5` 要求用户决定与写入确认只依据 user-intervention，`:3` 明确用户授权决定范围。

失败路径：用户已经要求生成并保存测试报告，既没有要求润色，也没有新的范围/事实立场决定。test-report 仍调用一个声明不应强制的嵌入方法，嵌入方法再要求展示冻结清单与确认。强模型可按共享权威消解并继续，但读取局部正文的 Agent 可能重复暂停；这是确定的文本冲突，未声称必然所有运行都停。

最小改法：test-report 删除 mandatory embedded humanizer 调用，普通输出直接平实写作；用户要求润色时才调。humanizer 的写入行为只引用唯一 authorization gate，已有明确文件/范围授权直接执行；冻结分类与保全契约继续保留。这项与主 Agent 的共享权威 finding 合并，避免同一根因多报。

验证：只读 humanizer review；用户显式请求原地润色；报告生成无润色请求。不得修改冻结契约，也不得额外要求已授权写入确认。

### SK-05 / P2 / STRUCTURAL：路由阶段优先级让上下文容量覆盖必需交接

原文：`skills/my-ask-matt/SKILL.md:22-28`：“按顺序判断，第一个成立项就是选择……下一阶段需要原始上下文，或者空间还够 → 继续……要换宿主、换目录或仓库、交给同事、分出支线任务 → 交接”。

失败路径：用户要求将当前成果交给另一宿主/同事，而上下文还有空间，第一条件成立使“继续”覆盖交接。反之当前原始上下文对后续无用，第二条件“清空”也会先于已明确的交接选项；下一接收者所需的固定决定/证据指针没有形成。路由不直接启动目标任务，所以影响是给出错误的下一动作。

最小改法：先处理用户指定的宿主/负责人/目录边界与任务独立性，再对保留、压缩、清空作上下文预算判断；任务分工与上下文卫生是不同轴，不做互斥的 first-match 列表。保留“只选一个下一跳、路由不代执行”的职责。

验证：空间充足但显式交接；需要保留原始上下文且换宿主；没有转移但上下文不足三案，路由输出必须满足真正任务边界。

### SK-06 / P2 / INSTRUCTIONAL：架构词汇禁止项目固有名称，且重复定义 seam 投资门槛

原文：`skills/my-codebase-design/SKILL.md:14`：“严格使用这些术语——不要用‘组件’、‘服务’、‘API’或‘边界’替代它们”；`:16-24` 有一组避免用词。`skills/my-improve-codebase-architecture/HTML-REPORT.md:106-121` 再复制整套 must/never 名词门槛。与 `skills/my-domain-modeling/SKILL.md:10` 的代码/项目语言交叉验证、`skills/my-tdd/SKILL.md:10` 的匹配项目语言存在冲突。`skills/my-codebase-design/DEEPENING.md:29`：“通常是生产和测试”两个 Adapter 才引入 port；`resources/testing-seams.md:7` 则明确 mock 不证明抽象价值，应有真实变化轴或至少两个实际 adapter。

失败路径：已有 `GridService`、public API、DDD bounded context 等名称与语义的项目，Agent 为遵守固定词表重命名读者叙述，降低与代码、ADR、Ticket 的可核对性；再把测试替身作为第二 adapter 的存在性证据，为测试专门扩大生产接口。两者都来自把方法术语提升成普遍硬规范，但涉及两种动作，实施可分别修。

最小改法：将词表保留为解释 deep-module 权衡的参考语言，项目名称/契约始终原文；不禁止通行专业术语。Seam 是否值得引入只指向共享合同，删除本地数量硬门槛和重复定义；保留依赖注入、复杂度删除测试、独立候选比较与避免测试暴露内部 port。

验证：有 DDD 领域边界、真实单一外部服务、mock 测试替身的既有系统。不得仅为词表或 adapter 数量改 public contract；真实变化轴证据成立时允许必要 seam。

## 重要但不列为核心 finding 的边界

- `my-diagnosing-bugs:62/68` 在没有可变红命令时禁止宣称根因，价值是避免猜测修复；但 captured production trace + 确定调用链可能已证明根因而本地不能复现。建议后续用真实案例验证是否需拆“根因证据充分”与“复现/回归验证已完成”，本轮没有足够 observed 支撑把该纪律整体撤销。数字“90%”“1% 不行”不作为效果证据。
- `my-wayfinder:48/61` 和 map format:37 的一会话一个非 research Ticket、约 100K token 是显式方法限制。多个低成本、已授权 AFK 决定可被强制中断，但是否偏离用户实际希望的一次一决策交互需要行为案例。因此建议改为可声明 stop_after/授权范围内 bounded advancement 的候选，不将现版整体判低效或自动改为自治执行；HITL 用户侧回答不能代填。
- `my-code-review:32-37` 的 Spec 查找先 commit Issue、再用户路径，明确 Spec 输入应优先，runtime 绑定 current revision 应为组合模式唯一源。这项由 source/lineage 所有者合并，不能把用户明确的指定对象被全局 instruction-authority 覆盖的问题重复计为必然 Bug。
- `my-test-report:76` 不允许缺验证点时从代码补写，可能挡住“从实际断言提取静态验证内容”；设计者动机不能从代码伪造。最小建议是允许据代码描述输入/断言并标 static，未知范围/设计理由继续未知。此条不涉及执行成功证明，不能放宽“只有本次实际日志可写通过”。
- `my-tech-design/scripts/check_html.py:87-90` 把同段出现“包含/不包含”当 ERROR（例如精确的一句契约即被拒）；属于 prose style 的事项更适合 advisory，而结构、导航、占位符等可继续硬校验。低使用影响，未纳入前六优先级。
- `my-wizard/template.sh:178-183` 在 SKIPPED 非空时仍显示 “Setup complete” 随后列手工余项。建议主标题按是否存在必需未完成项报告 partial；secret 序列化、目标检查与工具可用性保持具体证据，不在本轮直接执行配置或外部写入。

## 32 个 Skill 的归宿分配

表中结论是当前可证明的结构/职责归宿建议；所有 Skill 相对无 Skill 的交付增益仍无 comparative 证明。KEEP 不等于已实测有效，TARGETED_FIX 不等于已实测无效。没有足够证据退役任何有独立用户入口的工具。

| Skill | 结构归宿 | 保留的具体价值 / 改动 | 正常、边界、失败代表案（static） |
|---|---|---|---|
| my-ask-matt | TARGETED_FIX | 单一下一跳且不代执行；修 SK-05；上下文决策外置为按需卫生参考 | 普通想法路由 / 空间充足换宿主 / 交接条件被 first-match 遮蔽 |
| my-code-review | KEEP（局部 lineage 优先级澄清） | 固定基线、完整五视角、可达故障不因后续归属放行，避免只按验收发现 | runtime batch / 无 Spec 仍审 code / stale 或 bad ref 无结论 |
| my-codebase-design | TARGETED_FIX | 深模块与删除测试是有可解释作用的视角；修 SK-06，词表和例子按需引用 | 深化候选 / 项目已有 DDD/Service / 测试替身被当 port 理由 |
| my-diagnosing-bugs | KEEP（效果 INCONCLUSIVE） | 围绕能响应故障的信号、假设/二分、原始场景回归；保留无法复现时继续只读取证 | 稳定复现 / 性能或非确定性 / 缺环境访问不猜修复 |
| my-domain-modeling | KEEP | 只保存项目特有术语；ADR 三条件防模板堆积 | 冲突概念 / 无值得记录的新知识 / 未确认业务语义不能自作决定 |
| my-edit-article | KEEP | 原稿保留、目标读者驱动重组、可逆重排不另暂停 | 新稿 / 已授权原地修改 / 需改变立场才 gate |
| my-grill-me | KEEP（薄手动入口） | 无代码库时只形成需求摘要，防止伪造 Topic/Spec | 计划访谈 / 需求已明确 / 没有代码库不进主链 |
| my-grill-with-docs | KEEP | 两个承重对齐点、标明用户/仓库/推断来源，后续授权内衔接 | 已有仓库新行为 / 低风险 quick / 配置缺失先 setup |
| my-grilling | KEEP | 只问承重未知；代码可查事实不问用户；独立问题同轮 | 模糊真实目标 / 已有充分输入 / 方案类比混淆目标手段 |
| my-handoff | KEEP | 以 runtime status 为准、状态分开、历史引用不复制 | 换宿主 / 无项目临时产物 / 缺状态证据标未知 |
| my-humanizer | TARGETED_FIX | 冻结契约再润色、review 只读；修 SK-04 局部写入 gate | 可改叙述 / 全文契约 / 未经允许改变事实必须防止 |
| my-implement | TARGETED_FIX + EXTERNALIZE 可选检查细目 | 保留核实承重现状、影响面、对抗证据、批次独立审查；修 SK-03；quick 不携带无关高风险矩阵 | scoped Ticket / 机械配置小修 / Spec 与现状冲突 |
| my-improve-codebase-architecture | TARGETED_FIX（联动 SK-06） | 证据→收益/成本/风险候选，用户选中后才设计；HTML 不改结论 | content/full / 无视觉收益 / frontend 内容缺口 blocked |
| my-install | KEEP | 绝对入口、安装清单保护、source 与 project root 区分、回滚预览 | 指定宿主 install / 任意 cwd / 状态损坏不相对入口回退 |
| my-prototype | KEEP | 一问题、隔离、可抛弃、不能外推生产，获批 implementation 才吸收 | 状态或 UI 问题 / 项目无运行器 / 未授权真实写路径 |
| my-research | KEEP（薄手动入口） | 把一手来源方法作为可记忆的手动入口；正文单一资源定义 | 技术问题 / 资料缺失 / 无一手验证不能装确定 |
| my-resolving-merge-conflicts | KEEP（gate 归共享） | 保留每方意图、hunk 方案与验证/回滚；已有授权不得与共享 gate 冲突 | 已授权冲突处理 / 新意图冲突 / 范围变更需用户决定 |
| my-review-artifact | KEEP | snapshot/required_checks 闭环、多维根因去重、N/A 不凑 finding | 固定交付物 / 不适用视觉 / 缺证据 inconclusive |
| my-review-design | KEEP | 一次独立承重事实/影响面/更小替代/Spec challenge，四份结果防伪 pass | 持久状态方案 / 无风险触发 / 未决业务假设不给 pass |
| my-review-instructions | KEEP（并行深审受用户范围约束） | 先存在性再指令文字、合法归宿包括 retire、证据分级和 finding gate | 单 Skill / 用户明确多项并行 / 效果证据不足 INCONCLUSIVE |
| my-setup | KEEP | 配置探测零写入、一次确认、private/shared 归属不猜、迁移预览 | 新项目 / 有效配置不重复询问 / 既有归属冲突不删 metadata |
| my-tdd | TARGETED_FIX | 保留纵向 feedback 与独立 oracle，现版已有非 TDD 等价验证例外；修 SK-02/03 | 新行为 red/green / 已有覆盖机械修 / persisted oracle 误被禁 |
| my-teach | KEEP（非开发主链，显式按需） | 学生课程与制作记录隔离、课程价值门、答案/迁移任务、实际三视图验证 | full / content 指定止点 / 内容不全不能靠 frontend 补 |
| my-tech-design | KEEP（prose helper 小修） | 读者方案与 Agent Spec 区分、真实接口唯一原文位置、内容/前端分层 | content/full / 无图最清楚 / 缺现状证据或 blocked-by-content |
| my-test-report | TARGETED_FIX | 本次证据、关键验证面、不能把代码当执行通过；修 SK-04，允许据代码提取 static assertion | 新行为报告 / 人工待測结果留空 / 无日志不能“全通过” |
| my-to-questionnaire | KEEP | 外部知情缺口异步提取，不代答；问题数量服从信息需求 | 一名知情人 / 收件人/决策已明确可不重问 / 用户能查的事实不转采访 |
| my-to-spec | KEEP（接入 triage） | current/superseded 完整版本、不锁普通实现细节、风险设计关口 | 已确认需求 / 仅要 Spec 到此停止 / 未核实现状不能写事实 |
| my-to-tickets | KEEP（接入 SK-01） | tracer-bullet、验收 owner、真正阻塞边、完成历史补偿、heuristic 明示无实测 | current Spec / expand-contract / 无 Spec 不造 lineage |
| my-triage | TARGETED_FIX | 外部角色/主张复现/PR 差异/拒绝知识；修 SK-01，并与 batching 方法口径一致 | 新 Bug / 已实现与拒绝分别处理 / 本地新 brief 无 Spec |
| my-wayfinder | KEEP（固定 session 停止候选待行为验证） | 决策地图/迷雾/范围外分离、类型防误实施、claim 防撞工作 | frontier 决定 / 单会话已清晰不造地图 / 未批准执行不跳实现 |
| my-wizard | KEEP（helper 完成态小修） | 手动步骤、secret 隐藏输入、ignored/untracked/0600 检查、不自动 E2E | 第三方配置 / gh 未准备 / 安全落盘检查不满足停止 |
| my-writing-for-agents | TARGETED_FIX（联动 SK-03） | 必要行为/触发条件/唯一事实来源，static 不冒充效果；“独立证据”改可分辨映射 | 单指令正文 / 可达规则来自 runtime / 删除没有行为依据的句子 |

## 推荐的加载与衔接结构

1. 常驻只保留手动路由指针、权威/授权的极短入口、完成真实性；不能把全部 32 skill 正文和共享全文常驻。模型默认理解的通用语言无需反复定义。
2. 按阶段加载 current 需求/Spec/Ticket 与 runtime status/brief；阶段之间传 identity/revision/acceptance/evidence/remaining，而不传所有调查与历史。
3. 按风险加载：持久化/恢复、未知外部响应、迁移/回滚、权限/并发契约的检查细目。quick 保留验收与针对性证据，避免带上无关高风险项目的“无及理由”。
4. 人类文档入口（teach、tech-design、edit/humanizer/questionnaire、wizard、research、architecture report）保留按需，不并进开发常驻路径。入口少并不自动可靠；没有 comparative 不删除薄 alias 以人为记忆文件位置。
5. runtime 管 identity、血缘、claim、snapshot/finalize、状态与收据；Skill 管需求语义、适用验证、影响面、风险判断。helper 只硬校验可确定的契约，prose 偏好不成为拒绝完成的机械不变量。
6. 总体方案需要把来源优先级、用户确认止点、shared gate、Spec→Ticket 与 triage→Spec 边作为一组迁移，不能只删 Skill 段落让 runtime/manifest 留旧关系。

## 明确保留的好做法

- `my-grilling:8-16` 能查事实自己查，承重未知完结才收束，不无休止访谈普通实现细节。
- `my-to-spec:12/16` current version 完整改写、唯一 current、一次风险设计审查；避免补丁式历史造成规范歧义。
- `my-to-tickets:10-16/22` 每个工作切片完整、一致可发布、依赖不造顺序、coverage owner、防覆盖完成历史。
- `my-implement:14/18/20` 实施者自审和独立审查不同，补偿保留历史，不改无关环境让检查虚绿。
- `my-code-review:28/43-65` 重要既有影响可审、固定范围穷尽、可达故障不能借后续 Ticket 放行、发现基于场景而非风格。
- `my-tdd:36` 已明确允许有依据的等价验证，不能把本版误说成所有工作必须 red/green。
- `my-handoff:9-13` runtime 状态权威和提交/远端/release/各宿主安装分开。
- `my-review-instructions:56-60/72` comparative 才能证明相对效果、finding 必须可行动且有真实影响；这本身能约束“为了有产出而剪字”。

## 验证建议（供主 SPEC 汇总）

选择真实任务，固定模型/思考档位/权限/代码快照，比较 current 与 candidate，必要时加无 workflow baseline。任务包含：已有详细需求低风险修改；首次 triage 新 Bug；持久恢复写读共错；unknown-response 重试/幂等；多 Ticket 跨边集成；Spec 现状事实错误；设计已授权但请求只到 Spec；有项目 Service/API/DDD 词汇的架构判断。主要结果记录最终验收正确性、真实故障残留、首轮完成率、用户纠正次数、虚假完成/未授权动作；辅助记录 elapsed、额外确认、重复读写/测试、加载量。多个案例不应预先向评估者提示怀疑点。文档/静态 check 通过仅证明一致性与可解析性。
