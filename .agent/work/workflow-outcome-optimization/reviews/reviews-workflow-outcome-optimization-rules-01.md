# my-matt-workflow 资源、策略与加载结构审查

Review-Unit: `原固定审查metadata（持久来源索引见 ../evidence/source-manifest.json）` 的固定 review_unit
Content-ID: `36ce314358fac1f680ba8c536ef07e1f594964478395a56578923248445b91b0`
Target-Host: codex / cursor / claude（检查项目现有投影机制，未运行宿主真实任务）
Evidence-Level: static；R1 有 narrow observed（同团队用快照提取原函数执行 targeted probes）；这不是真实 Agent/完整 CLI 运行；没有 comparative
Verdict: TARGETED_FIX（资源体系与按需外置方向保留，行为契约和治理需修订）
Publication state: 根 Agent 尚需对同一文件列表 finalize；此文件是团队内部审查材料，不是已完成 snapshot finalize 的公开报告。

## 范围与边界

已逐份读取快照中的 39 个对象：36 份 Markdown，`composition/manifest.json`、`resources/manifest.json`、`resources/governance.json`；为验证影响路径还读了相关 Skill、打包/投影代码、测试与 review runtime 快照。证据引用是 source_path 和冻结内容的行号，不从 live path 取证。

用户本轮要求诊断、方案、SPEC，不实施。因此本报告只提候选改动，不修改源码、规则、安装或发布状态。用户本轮明确授权规则与 Skill 拆开并行深审，覆盖多个对象不受现有审查方法“逐个深审”的默认步骤限制。

安装复制、宿主目录中的可读取文件、模型实际读取、常驻进入上下文是四个不同状态。`resources.py:154-159` 仅 `copy2` 到 Skill 目录；`release.py:267-272,297-330` 为组合边与 Markdown 链接计算 effective consumers。没有任何这类代码证明资源正文已被模型读取。当前配置没有 resources `consumers: "*"`。不能据此说所有规则一直占用上下文，也不能凭文件总字节证明 token 浪费或效果下降。

## 优先问题与可执行修改

### R1. 合法修复已经通过，也会因修改几何形态停在 needs-user

原文：`resources/review-loop.md:25-30` 将“同一处连续修改：相邻两次修复在同一文件的行区间重叠”和“代码相对基线的增加行加删除行超过第一轮的1.5倍”定义成停止信号；`:32` 进入用户状态后拒绝继续审查。

确定性影响路径：冻结 `tools/workflow_lib/review_loop.py:98-100` 只判断同路径和区间 overlap，不判断最终 result 是否 pass；`:105-107` 只判断增删量。`ticket_review.py:338-365` 登记结果后仍运行 signals，再 stop。这意味着第一次修复遗漏一个条件，第二次把同一行修正确，最后审查 `pass` 也会 needs-user；第一次审查改动很小，后来补齐本来必需的失败处理也会仅因体积被停。此机制不会直接证明代码更错，但可以确定地阻止已有通过证据的结果收口，制造额外裁决和停滞。团队 probe 收据 `../evidence/my-matt-quality-review-stop-probes.json` 已执行快照提取的原始 signals 函数：`status=pass, findings=[]` 时，相邻修复重叠返回同处连续修改；`volume=2, first_review_volume=1` 返回体积膨胀。这是 narrow observed，不是完整 CLI/宿主真实行为发生率。

改动：保留最多 4 轮与没有当前有效通过记录不能完成的 gate。将重叠、体积与局部反复变成诊断信号；只有仍有 blocking、缺有效通过或已确认的范围/承重设计需要改变才阻止完成。与既往 finding 不同不自动等于产品裁决；要求说明新证据和因果影响。

预期改善：避免“已修好却不能继续”；保留真正防止无限审查的预算和完成不变量。验证：同 hunk 第二次修复后当前 pass、增删超过 1.5 倍但行为范围不扩大且当前 pass、达到第 4 轮仍 blocking 三类 fixture。前两者允许正常收口，第三类仍停止。实际成功率和用户介入成本待真实任务比较。

### R2. 单一事实来源只约束文件摆放，没有消除主链旧协议和语义重复

原文：`resources/adapters/work-scope.md:3` 写“全部完成后多 Ticket 做 Topic test/review”；`resources/adapters/implementation-session.md:7-9` 已改成 `batch test/review/close`，`topic review` 可选、不执行不阻断完成。`resources/manifest.json:124-130` 将旧 work-scope 给 `my-tdd`；`composition/manifest.json:47-57` 把 tdd 作为 implement method；`my-tdd/SKILL.md:22` 在 seam 歧义路径明确指向 work-scope。不是不可达历史笔记。

另一个例子：`resources/user-intervention.md:3` 是唯一确认清单和已确认授权持续有效，`:8` 每次外部写都问；`policies/enterprise-safety.md:6-7` 又以项目配置驱动确认并宣称“工作流不 Push、不建 MR、不写外部系统”，`adapters/write-actions.md:3` 则确认后直接完成、不另定义配置门槛。同一行为会在不同入口被解释成禁用、每次许可或沿用许可。

治理缺口：`resources/governance.json:48-50,132-142` 的所谓 validation 是 `test_shared_workflow_contracts_survive_host_projection`，冻结测试 `tests/test_workflow_texts_v2.py:17-44` 实际只证文件存在、安装正确、没有 composed bodies；`resource_governance.py:158-163` 只验证 selector 是存在的方法。它没有声称实现语义测试，也不应被当作语义正确证据。work-scope 的冲突说明“资源每份都归档”未保证行为契约同步。

改动：实施生命周期命令只有 implementation-session/runtime 定义，work-scope 只定义范围、继续边界、历史补偿和指针；唯一授权规则覆盖所有入口；治理清单分开打包可达性、机械协议、模型行为方法，不要求每份行为文档用一个文件存在测试冒充语义保障。新增少量跨入口行为 contract fixture，验证命令、必选/可选与授权分支一致；不引入无效 keyword grading。

预期改善：避免走入不存在命令、把可选审查当必需、在不同 Skill 里取不同许可规则。保留 composition/resource manifest 的严格 inventory、稳定闭包与宿主投影。

### R3. 验收到测试的映射被错误升级成“每条验收一个独占测试”

原文：`resources/workflow-delivery.md:24` “多条验收不能共用同一个测试”；`skills/my-implement/SKILL.md:10` “每条验收分别对应独立测试断言，不共用一个测试”。前半句要求可定位独立断言合理，后半句把承载断言的测试 case 也唯一化。

具体行为：一次真实 persisted lifecycle 测试可能同时断言关闭、重新打开、恢复状态、下游调用与幂等性，各断言分别证明不同验收。现规则会使其映射无效，Agent 可能拆成多个只证明局部事件的 case，反而丢失跨生命周期证据；也会给无需新测试的文档修正或已覆盖小改动制造空壳测试需求。这里证明的是静态不合适约束和可达风险，没有直接断言当前 Agent 已这样失败。

改动：每条验收映射到可定位的断言、运行结果或对该改动适用的其他证据；允许一个真实行为测试承载多个不同验收，但必须指出各自断言和覆盖边界。禁止“同一个泛化测试通过”代替多个行为证明。standard 六节自审保留承重证据，quick 只输出改变读者判断的验收、影响面、最可能失败路径、未验证项；不要求无风险类别都填空。

预期改善：鼓励真正端到端/持久化行为验证，减少镜像式测试与纯映射仪式。验证：生命周期多断言合格；一个 smoke test 映射全部验收但没有相应断言不合格；已有测试已覆盖的可逆小改动可引用重跑证据；缺外部验证时必须说明边界。

### R4. 授权持续有效与“每次都问”冲突，冲突修复有另一套无限暂停规则

原文：`resources/user-intervention.md:3` “已确认的授权继续有效…其他可逆实施细节直接推进”；`:8` “推送、建 MR、写外部系统，每次都问”；`policies/merge-conflict-approval.md:3` “未经用户对该方案的明确批准，不得编辑冲突文件、暂存、提交、continue、abort 或 push”，`:5` “出现新的不确定性立即停止”；`skills/my-resolving-merge-conflicts/SKILL.md:9-13` 同样载入。

具体行为：用户已经要求“解决这次合并冲突，验证后本地提交”的情况下，能力可查、可逆的 routine hunk 仍被当成必须再批准的新工作；用户明确要求推送指定分支后，已有授权仍不能满足“每次问”。无需获批的事实查询、可逆实施和真正产品/不可逆取舍混在一起，主链唯一清单无法提供确定答案。

改动：共享确认规则先检查该具体动作、目标与后果是否已获授权，已获授权直接完成；未授权发布的确认留到可审阅产物完成后。冲突 Skill 自动查两侧意图和测试，对于批准范围内可逆解决推进；仅会改变行为取舍、丢失任一方意图、扩大范围/不可逆动作且未获授权时询问。保留危险 Git 操作和信息外发边界；不因删除重新询问而默认获得 unsolicited push/install 权限。

预期改善：减少任务同意后反复找用户、降低 routine 冲突处理中断；权限边界更具体。验证：已授权 local conflict resolution 完成、不丢双方语义；无法兼容的产品冲突等待裁决；明确 push 目标的授权不重复问；没有 push 授权的开发请求不得推送。

### R5. 上下文规则规定了新上下文，却没有主链执行入口，并且要求不可恢复的大推理阶段

原文：`policies/context-hygiene.md:3` “访谈、Spec 与 Ticket 拆分…同一个未中断上下文…进入已批准 Ticket 的实施…新的上下文”；`:7` `/compact` “只用于阶段间”。冻结 Skill 中唯一具体 context-hygiene 指针是 `my-handoff/SKILL.md:13`。主链 grill-with-docs → to-spec → to-tickets → implement 不读取此 policy；`my-implement/SKILL.md:16` 要同会话整个批次。

具体行为：只启动主链不会自然获得这条规则；在 handoff 时读到，又可能将已经压缩/断开的需求讨论视为不满足输入条件。大 Topic 的访谈、事实核实、Spec、依赖拆分无法承诺永远在同一未中断上下文；把阶段内压缩禁掉会阻止必要恢复。没有证据说明所有 Agent 都已被它卡住，也没有 evidence 证明上下文占用是当前第一根因。

改动：保留“既有工件只引用、结构化 runtime 状态优先、无密钥/无关信息”。删除绝对未中断要求。在任何接近容量、探索分支或职责转换时允许 checkpoint/compact；恢复必须有当前目标、授权/已决事项、active Topic/Ticket/batch、必要证据与第一步。实施者可连续一个批次，也可使用恢复上下文；独立 reviewer 必须真实新上下文，并如实记录 self fallback。上下文指南由主链/宿主在触发情形接入，并验证恢复路径，而不是只为handoff复制文件。

预期改善：上下文丢失不再使流程失效，改善长任务恢复的可靠性；不凭缩短字数判效果。

## 次级但明确的修改

- `review-loop.md:17` “修复只改正、删除或收窄。需要新增规则、场景或要求时返回 blocked-by-design”混淆补齐已批准行为与新增需求。改成：补齐原范围所需逻辑/场景/验证属于修复；仅扩大用户行为、承重设计或风险承诺才回对齐。新负向测试本身不构成新增需求。此条主要是 static 风险，未见 runtime 对“新增场景”机械强制。
- `review-loop.md:9` “审查者不得重开；异议 inconclusive 交用户”应限定产品决定；新代码/运行证据可否定原事实时更新事实和影响，不把事实变成用户专属裁决。影响已批准目标或风险承担再请求决定。
- `artifact-finalization.md:17` “清空结论后…fresh-context”不能在同一上下文证明认知隔离。实际新上下文才称独立；无法派发时记录 self/缺口。不删除来源、内部一致性与事实正确性 gates。
- `artifact-finalization.md:27-29` 未知若影响可执行决定应 blocking，未知仅限制验证置信/真实环境验证应在可交接工件公开记录边界。明确区分 draft、可供用户批准的 proposal、已批准可执行 Spec、完成交付；不能把尚待用户批准的提案一概拒绝保存，也不能将未知润色成确定事实。
- 本轮用户明确要求不默认偏好图示。`visual-communication.md:3-13`、`reader-first-writing.md:15`、`document-rendering.md:28,32` 的“按结构类型默认必须图示/none直接阻断”应统一改成目标读者理解/解析成本判断；保持图外关键文字定义、承重内容不由frontend发明、布局可读性要求。这是新用户约束适配，不声称旧教学规范已被效果实验否定。

## 做得好的部分与保留依据

1. `instruction-authority.md:3-5` 已明确平台/宿主硬约束、用户范围/授权、路径项目规则与 Spec/Ticket 的关系，并限制项目规则不自授权；方向正确，改为唯一可消费决策规则后保留。
2. `requirement-analysis.md:3,9,13,15` 给简单请求快速通过，复杂歧义才启动独立核对，没有子 Agent 如实 self。`requirement-reviewer-brief.md:16` 明确不为显示价值制造歧义。保留这种按风险触发，不统一强加 reviewer。
3. `review-loop.md:7,13,47-49` 实际模型、独立性、可达失败路径、影响面与 finding 依据防止伪审查。保留冻结内容、coverage、pass不能有阻断等保证，只修停止信号和修复范围语义。
4. `adapters/project-rules.md:11-19,34` 明确不同宿主适用路径、selected/shadowed/manual/invalid，不把 AGENTS 作为其他宿主原生规则，不以 resolve 返回代替完整 inventory；`agent-rule-applicability.md:9` null 不推断适用。保留这种能改变规则选择的具体约束。
5. `adapters/ticket-selection.md:3-13` Ticket类型、依赖、认领、Spec lineage、用户显式选择不得静默替换、完成历史与补偿归属有明确故障防护。字段校验留 runtime，Skill只消费结果与处理缺口。
6. `adapters/specialized-review-session.md:9,20` 的 snapshot_path-only、content match、stale 重建能防止审错内容；安装级 host projection 将调用宏投影为 `$`/`/`，配置和文件清单校验留程序。无需以强模型会判断为由删除。
7. `testing-seams.md:3-9` 行为稳定边界、替身只在不可控系统边界、mock不证明抽象价值、边界语义保留有明确正确性用途。没有比较证据证明这些要求多余，保留按风险参考。
8. `humanizer.md:3` 已将润色保留手动、不是写入前强制动作；reader-first/final-state把过程从成品移除并保留Agent必要状态；目前看不到必须将它们纳入实施常驻的理由，保持按需。

## 全量归宿清单（39/39）

“保留”表示契约/归宿在 static 范围内成立，不表示已证明比强模型baseline更好。这里列出的合并/退役是 proposal，实施前追完调用者并把所需行为迁移到唯一来源。

| 对象 | 归宿/改动 | 读取/执行时机与证据 |
|---|---|---|
| `chatgpt/custom-instructions.md` | KEEP，独立用户设置，不进入开发协议 | 长工具任务进度；:7-13具体结果/60秒/最终边界符合监督需要，无行为比较结论 |
| `composition/manifest.json` | KEEP + TARGETED_FIX，同一组合权威 | 构建/安装执行；method/chain/handoff 保留；:47-57 implement调用tdd/review可追踪；确认条件语义从共享授权取，不按kind每次重问 |
| `resources/manifest.json` | KEEP + TARGETED_FIX，继续直接/派生consumer分离 | 构建分发；按需resources依赖闭包；:204-212 `policies`目录组改成细粒度source声明以配合唯一归宿，但不把目录复制当模型负担 |
| `resources/governance.json` | REDESIGN，区分packaging/mechanical/behavior | 检查/构建执行；目前:48-50等仅绑定文件存在测试，不能作语义保障；需要对行为政策明确semantic review或场景证据 |
| `policies/context-hygiene.md` | TARGETED_FIX + RELOCATE，主链按触发接入 | 容量/分支/职责切换或恢复；:3,7固定上下文拓扑删除，:5状态/引用/去密保留 |
| `policies/decision-taxonomy.md` | MERGE/RETIRE alias，保留wayfinder必要分工 | :3只有user-intervention指针、:5决定者代表自己；前者并入唯一授权，后者归wayfinder正文，不维护独立确认来源 |
| `policies/enterprise-safety.md` | MERGE，跨入口安全约束统一来源 | :3项目规则不授权、:4不外发敏感、:5原生skill边界保留；:6-7确认配置和完全禁止外部写与其他来源冲突，修正后按敏感操作加载 |
| `policies/merge-conflict-approval.md` | TARGETED_FIX，冲突方法按需 | 进行中的merge/rebase；:3,5从始终二次批准改为明确已有授权与实际语义分歧；危险Git操作不松绑 |
| `policies/project-discovery.md` | MERGE/RETIRE，setup/runtime单一契约 | 首次初始化/检测漂移；:3-9已有setup流程重复且Tracker等配置列与现setup不完全一致，保留探测证据/一次确认语义，不另发policy |
| `policies/project-storage.md` | MERGE，路径/归属交程序与storage adapter | :3-13 `.agent`归属/嵌套Git/目录固定；与storage/access/setup同一事实迁移唯一来源，产品知识仍按需 |
| `policies/write-boundaries.md` | MERGE，唯一授权+明确禁止操作 | :3指向唯一清单，:5危险Git/信息外发边界迁入安全约束；删除独立重复入口 |
| `resources/adapters/artifact-access.md` | KEEP，窄化为reader路径解析 | reader需要已有产物时；:3路径/归属引用storage唯一来源，:5写入侧内容归storage，不在reader重复写入控制 |
| `resources/adapters/artifact-review-session.md` | KEEP + TARGETED_FIX，runtime协议按需 | 综合产物审查；:3 content绑定、:7结果schema/轮次保留，JSON校验归runtime；不在Skill再抄schema长段 |
| `resources/adapters/artifact-storage.md` | KEEP + MERGE统一存储来源 | 生成本地工件时；:3-7安全路径/新增不覆盖/用户指定位置优先保留，事实规则统一消除project-storage副本 |
| `resources/adapters/assurance-levels.md` | TARGETED_FIX，风险选保证机制 | :5 quick边界方向正确；:7 quick不用Spec/Ticket但仍全六节自审与独占测试太重；:9 standard批次/独立审查保持，按风险触发深证据 |
| `resources/adapters/composition.md` | KEEP，简短调用契约 | 实际调用阶段；:3 method返回/chain连续，:5宿主宏投影/不要求用户切Skill；最终权限只由共享授权定义 |
| `resources/adapters/implementation-session.md` | KEEP + TARGETED_FIX，唯一生命周期接口 | 开工/恢复/收口；:3 runtime status/next_command保留，:5-9 batch/历史/基线界限保留；更新context恢复与证据契约，机械要求交runtime |
| `resources/adapters/project-rules.md` | KEEP，解析宿主与路径按需 | 计划采证/实施前/实际改动复核；:5执行Agent明确绑定、:19 inspect/resolve边界、:34 validate保留；解析字段和命令由程序返回 |
| `resources/adapters/specialized-review-session.md` | KEEP，冻结/匹配协议 | 专项只读审查；:9只读snapshot，:20 match/stale语义保留；路径排序/哈希生命周期由runtime，Skill消费 |
| `resources/adapters/ticket-selection.md` | KEEP + EXTERNALIZE机械字段 | Ticket选择/准入/恢复；:3-9歧义不猜/依赖环/不静默重选保留，字段类型/排序程序执行；Skill只保留用户决定与缺项处理 |
| `resources/adapters/work-scope.md` | TARGETED_FIX，范围契约 | :3删除旧Topic test/review及生命周期命令，指向implementation-session；:5历史补偿/未闭环不完成保留 |
| `resources/adapters/write-actions.md` | MERGE/RETIRE alias到唯一授权 | :3“确认后直接完成/先完成可审阅结果”保留到user-intervention，无需同一确认规则三套指针 |
| `resources/agent-rule-applicability.md` | KEEP，宿主规则判断方法 | 指令审查的目标路径/激活方式检查；:6-11 typed applicability保留，program返回状态避免模型猜 |
| `resources/artifact-finalization.md` | TARGETED_FIX，承重产物按风险四gate | :3只审承重内容值得保留；:17独立性实际记录、:27-29区分proposal/approved/evidence限制，避免未知一律禁止恢复 |
| `resources/document-rendering.md` | KEEP + TARGETED_FIX，渲染宿主专用 | 文档content/frontend/full；:5-7语义与渲染阶段边界保留，:28,32图示阈值适配用户；不进入普通开发常驻 |
| `resources/final-state-writing.md` | KEEP，最终文档按需 | :3-5有效状态/迁移例外，:9只读审查保留；不会因历史存在就删掉兼容依据 |
| `resources/first-principles-reasoning.md` | KEEP，承重选择按需参考 | :3,15,23明确不扩散到普通细节，因果/反事实/可证伪验收可用；缺比较证据不退役 |
| `resources/humanizer.md` | KEEP，手动/面向人审查按需 | :3不成为强制流程，:5硬约束保原义；不用作开发收口固定gate |
| `resources/instruction-authority.md` | KEEP + TARGETED_FIX，最小权威核心 | :3-5明确用户目标/项目路径/Spec层次有用；同步授权持续有效和实际runtime协议冲突的处理，避免低优先规则成为额外审批 |
| `resources/project-rule-review.md` | KEEP + TARGETED_FIX，按目标宿主专项 | :18,46-63作用域/证据分级保留；review预算从唯一loop；已做Inventory对象集不强迫完整三宿主重扫，不把当前资料缺口当效果证明 |
| `resources/reader-first-writing.md` | KEEP + TARGETED_FIX，写作/产物审查按需 | :3,9读者人与Agent区分保留，:15默认教学图示按用户理解成本改；不要求实现Agent先读整套writing |
| `resources/requirement-analysis.md` | KEEP，歧义/复杂请求按需 | :9快速通过、:13独立核对、:15真实fallback保留；不是每个任务加reviewer |
| `resources/requirement-reviewer-brief.md` | KEEP，独立需求审查专用包 | :3-16只原文/摘要/最小上下文，结论门槛完整；manifest直接consumer为空由requirement-analysis链接派生不算孤儿 |
| `resources/research-method.md` | KEEP + TARGETED_FIX，研究按需 | :8第一方来源、:10事实/推断/时效保留；:12写回确认沿用唯一授权，已明确授权研究写回不重复问 |
| `resources/review-loop.md` | TARGETED_FIX，审查唯一规则 | :7,13,47-49独立/事实/覆盖保留；:17补齐行为修复允许，:25-34几何信号改诊断，硬预算/当前证据 gate保留 |
| `resources/testing-seams.md` | KEEP，测试/设计按风险参考 | :3-9稳定边界、真实内部协作者、mock语义保留；只有扩大公开契约/范围的seam决定询问，普通seam继续 |
| `resources/user-intervention.md` | TARGETED_FIX，唯一授权/决策gate | :3自主方向保留，:8-11依据已有授权/实际新决定而非动作名每次问；对齐点不新增，已授权阶段直接继续 |
| `resources/visual-communication.md` | TARGETED_FIX，读者成本按需 | :3-13去默认图示硬门槛；:15,17,19关键文字、图可读、实现细节不入内容方法保留 |
| `resources/workflow-delivery.md` | TARGETED_FIX，证据与长期知识收口 | :3按需知识沉淀、:12不猜零、:21边界保留；:24独占测试改为逐验收可定位证据；quick摘要按风险精简，standard结构保持可解析 |

## 适合一直保留、按需读与交程序的内容

常驻的最小约束应只覆盖用户目标/范围/授权、真实状态、证据与完成边界和触发路由；宿主原生指令仍由宿主加载。不要把全部 resources 改成always，也不要由workflow复制用户全局规则。

按阶段/风险读取：需求核对在有承重歧义时；project-rules在实际影响路径选择时；seams在行为测试/接口边界时；独立design在持久化/并发/外部契约/兼容风险时；review-loop在审查/修复时；writing/rendering/humanizer仅产物适用时；context在容量/恢复/分支触发时。

程序执行：路径与命名安全、schema/依赖/认领/lineage、命令next_action、batch关闭条件、frozen content match、review计数、host projection、release/install hash与transaction。不要求模型手算或把程序已经可靠验证的字段全文重复进多个文档。

## 验证建议与边界

先用针对协议的 fixture 验证必需/可选命令、授权持续、真实pass收口、same-hunk合法修复、多验收多断言、恢复上下文、宿主路径选择。这只能证明确定性规则和安装闭包。

真实任务至少包含：可逆局部缺陷、跨模块API修复、持久化关闭/重开/恢复、并发或未知外部响应、Spec现状断言错、进行中merge冲突、长Topic被打断恢复。记录第一次完整交付的独立验收通过、完成后发现的P1/P2、用户裁决次数、返工原因、未验证项和耗时/token。相同模型、reasoning、原始请求、repo快照、权限下比较当前版本/候选，必要时加无workflow baseline；评估者只看原任务和最终可观察结果，不看预期问题名单。

本次没有证明所有规则净收益，更没有证明长文本一定有害。保留具体防故障机制，修订可定位契约冲突和机械假阳性，行为有效性留给真实任务证据。
