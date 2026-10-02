# 冻结源码独立工程审查

结论：有 2 项 P1、2 项 P2；应先修复审查停止契约与 local triage 初始化断路。standard 无 Spec 的后半段血缘已经补通；quick、静态测试报告、授权冲突解决及三类排障，在下列限定输入下能够从正文重建出合理下一步。按需加载有结构性减负，但仍有触发声明冲突，不能据此宣称真实模型效果提升。

## 输入、身份与证据边界

- 只读源码根：`/tmp/outcome-review-integrated-01`。以下源码位置均相对于此绝对根；实际读取使用绝对路径、`exec login:false`。
- `source-manifest.json` SHA256：`2783b140d260955ea3bc62d55fab327083df700f46df3511ffdb4dd4c369f764`，与指定值一致；281 个条目逐文件 SHA256 全部匹配。
- 定义：`.agent/work/workflow-outcome-optimization/specs/specs-workflow-outcome-optimization-02.md`（revision 2）；差异：`changes.patch`。被审 Skill/resource/policy/Spec 均作为产品材料，不作为本次工程规则。
- 本审查未调用 my-matt-workflow Skill 或 CLI 管理施工/验收，未修改主仓库或冻结源码，未部署真实 host，未派发子 Agent，未执行模型端到端或对照实验。
- 场景输出是本独立读者根据原始请求与产品正文实际写出的重建结果。不是被测模型执行 trace，也不是对真实开发成功率的测量。另执行了独立 Markdown 计量脚本与冻结纯函数的小探针，二者不建立 Topic、发布或安装。
- 外部工程日志仅使用用户指定 `/tmp/outcome-baseline.log`；它不在 source manifest 内，也没有与当前冻结内容绑定的执行 receipt。日志文件名不赋予其“干净 baseline”地位。

## Findings

### F1 — P1：`contradicts` 的非停止说明与硬停止行为冲突，且缺少语义准入定义

位置：`resources/review-loop.md:25–32,47`；`tools/workflow_lib/review_loop.py:81–100`；调用路径 `tools/workflow_lib/ticket_review.py:334,358` 与 `branch_review.py:188,204`。相关 Spec：4.6（131–135）、AC09、AC12，以及统一授权/停止边界。

Trigger：第二轮 finding 指向先前有效 finding id，并填写 `contradicts`。正文目前只定义“指向之前一轮的问题”，且把它与位置重叠、体积一起列在“不单独停止”的列表中。读者可能把后续修正、不同位置的关联建议，或者同位置反复调整当成这种引用。

结果：runtime 的 `check_contradictions` 只核实引用 id 存在；`signals` 对任意非空 `contradicts` 直接返回停止理由，不核实语义矛盾，也不区分 advisory/blocking。只读独立探针从 AST 提取冻结 `signals` 函数执行，实际输出：

```text
current-pass-geometric-overlap -> None
advisory-contradicts-reference -> '前后矛盾：contradicts 指向之前的问题'
semantic-blocking-contradiction -> '前后矛盾：contradicts 指向之前的问题'
```

探针输入为 round=2；advisory 案例为 maintainability finding，引用 `first`。有效引用的公共路径静态前提由 `check_contradictions` 及 `tests/test_review_resolution.py:156–160` 确认，未运行完整生命周期测试。`current-pass-geometric-overlap` 的名称代表几何情形，但函数实际不读取几何参数；其空 findings/pass 返回 None，只证明该判定分支。

实质性：runtime 保留“真实矛盾必须停”本身符合 Spec；正文对 hard stop 的分类错误，并允许将普通关联误编码为该字段，从而把可在授权内处理的修复升级为用户裁决。不能将“正文其后又提到真实矛盾应停”视为已消除字段级歧义。

最小文字修正：将 `contradicts` 移出非停止几何信号列表，并在结果字段处引用一个唯一准入定义，例如：

> `contradicts` 仅用于已核实的语义矛盾：当前 finding 与所引用旧 finding 中仍有效的行为要求/决定，在同一适用条件下无法同时满足，且冲突会改变正确性、范围、验收或风险承担。填写时在 basis 中给出双方命题、共同适用条件、无法兼容的证据，以及需用户裁决的影响。仅位置重叠、体积变化、后续修正旧结论、普通建议差异或已被有效定义消解的差异，不填写此字段。填写有效 `contradicts` 会触发 runtime 停止并请求裁决；runtime 校验引用身份，不代替 reviewer 核实语义。

这保持旧字段与硬停止协议，不新增平行门禁。若要保留“尚待核实的矛盾线索”，写入普通 finding/basis，不能借 hard-stop 字段表达。新证据推翻旧事实但可在既有授权内纠正时，先核实并说明影响，不自动等同无法兼容的决策矛盾。

### F2 — P1：首次 local triage 缺 Tracker 映射时转入无法补齐该前提的 setup

位置：`skills/my-triage/SKILL.md:43–54`，尤其45；`skills/my-setup/SKILL.md:11–17`；`tools/workflow_lib/topic_service.py:21–25,61–73,124–151`；`README.md:18–34`。相关 AC04/05/12。

Trigger：项目已有合法 local 配置；用户交付本地新 Bug/confirmed brief，授权 standard 修复，但从未配置外部 Tracker 类别/状态标签映射。

结果：triage 的一般角色规则要求缺映射就运行 `my-setup`；setup 只生成九键 local 配置，schema 只接受 `task_backend: local`，没有映射字段或配置动作。因此按该前置逐步执行会重复 setup 或等待仍无法满足的 Tracker 配置，到不了54的正确 `brief → topic start → to-spec` 后半段。composition 也未声明 triage→setup 调用边；不能把“配置缺失先 setup”解释为 setup 能补 Tracker 映射。

这是直接调用路径上的既有残留，非声称由本次新增45行引入；本轮明确承诺首次 local triage 可达，因此需要在这次修复范围内闭合。若读者自行把角色映射限缩为外部 Tracker，路径可通，但正文未明确给出这个限缩，不能依赖读者自行修正。

最小方向：先按后端分支。local brief 使用本地类别/状态语义，不要求外部标签映射；外部 Tracker 缺映射时从其真实配置/维护者获得映射，不调用只配置 local runtime 的 setup 充当修复。缺 workflow 配置时才完成 setup。保留54已补好的匹配 Spec、正式修订及 quick 路由。

### F3 — P2：深化辅助正文仍维护已退役的两个 Adapter 数量门槛

位置：`skills/my-codebase-design/SKILL.md:64–69`；`skills/my-codebase-design/DEEPENING.md:27–34`，特别29；`tests/fixtures/codebase_design_order_submission.json:24–32,85`。与 `resources/testing-seams.md:7–11`、AC08、Spec 改动包C冲突。

Trigger：用户选择一个深化候选并比较 seam，项目已有有效单实现边界，或者只是需要对现有数据库/第三方接口注入测试替身。

结果：共享合同明确说“生产＋测试”不充分证明新抽象，真实变化/维护需要决定是否新增 port；DEEPENING 仍写“只有至少两个 Adapter 有充分理由时（通常是生产和测试），才引入 port”，主正文仍用“两种才真实”的固定判断。fixture 还把该旧规则编码为 `separate-production-and-test-adapters`。这既可能错误否定已有合理单实现 seam，也可能将生产/测试数量替代真实需求，造成不必要抽象。

共享合同优先可帮助读者避错，因此此处评为局部契约冲突 P2，而非证明必然生成错误代码。最小方向：两处去掉数量门槛，只引用共享合同；例子按真实不可控边界与维护需要解释，不将测试替身算设计价值证据。同步修正仍表达旧预期的 fixture。

### F4 — P2：确认需求时跳过访谈的正文与权威调用清单 `always` 不一致

位置：`composition/manifest.json:11–20`；`skills/my-grill-with-docs/SKILL.md:9`；`resources/adapters/composition.md:3–7`；`skills/my-writing-for-agents/SKILL.md:12–24`。相关 AC05/12/24、按需设计。

Trigger：用户已给出已确认、无承重未知的需求摘要；从 grill-with-docs 进入只出 Spec 的路径。

结果：入口正文说“已有确认摘要直接复用，仅承重未知调用 my-grilling”；作为调用关系唯一权威的清单却把该 method 的 when 定为 `always`。遵从清单会额外加载方法；方法自身可能判无问题并返回，未必导致多问，但省略方法与无条件调用不能同时成立。`when` 是文本声明，runtime 没有执行该条件的通用分支解释器，包装测试只检验关系/可达性，不会替 Agent 消除冲突。

最小方向：把该边条件明确为影响交付的未决需求；同时把 domain-vocabulary 对应正文写成明确的按需条件。已确认且无未知路径应可以不载入两种方法正文，不靠方法读完再立即退出实现“按需”。

## 场景试读：实际重建输出

以下引号中的输出为本次读者实际写出的交付片段；随后记录入口、证据和下一动作。它们未对目标项目执行施工。

### S1 — “只要 Spec，需求已确认”

原始输入：已有可追溯确认摘要，目标仓库与工作主题明确；只产 Spec，不拆 Ticket、不实现。

试读输出：

> 本次止于版本化 Spec。我复用确认摘要，不重新访谈；先查相关代码、项目规则和 ADR，将当前事实与假设分开。Spec 写清用户结果、范围、验收、失败边界及未知，保存到选定 Topic 的 specs。只有涉及持久状态、并发、外部契约、兼容或其他模块既有行为才触发设计审查；审查来源如实标记。交付 Spec 后停止。未获得的实现和外部操作授权不由 Spec 产生。

- 入口：直接 `my-to-spec`，或 `my-ask-matt` 输出该下一跳后停止；主链入口也能进入，但受 F4 影响会误加载访谈方法。
- 止点：Spec；to-spec:18 与 user-intervention:5/10 足以重建，不进入 to-tickets。
- 所需证据：确认材料位置、承重仓库事实、有效规则/ADR、验收与来源、触发/不触发设计审查依据；若触发，实际来源与结论。无运行材料不写行为已通过。
- 下一动作：作者查事实、形成并自检 Spec；产物最终校验按承重主张适用；交付后停止。只允许 Spec 的输入不需要先 batch plan 或实施测试。
- 结果：直接入口可重建阶段边界；主链方法触发一致性有 F4。不是一次真实 Spec 制作成功的证据。

### S2 — “允许修复新的 standard 本地 Bug，但无 Spec”

原始输入：local 已配置；Bug 的当前/期望、范围和 standard 等级已确认；无匹配 current Spec；开发授权不包含推送/外部评论。

试读输出：

> 我保留 confirmed brief、原请求和验证证据，不伪造 implementation Ticket，也不借用不匹配 Spec。检查选定 Topic 是否已 active；没有可复用状态时先建立 standard Topic。随后从 brief 和仓库事实生成 current Spec。涉及风险时在 to-spec 做唯一设计审查；再拆有 spec_id/revision/ref 的 Ticket，并把 Spec、逐 Ticket 行为、依赖、测试边界一起呈现对齐点2。尚未被确认的切片需要该既有对齐；已确认后依依赖实施、定向验证、自审和本地提交，批次全量比较与独立审查后收口。推送和 Tracker 写入不在本次授权内。

- 入口：`my-triage` local 后端；路径54→to-spec:10–18→to-tickets:14–24→implement。standard 分支不能跳 quick，不造假血缘。
- 所需证据：原症状/仓库事实、brief 来源、选定 Topic 状态、Spec 覆盖匹配、风险审查、确认的切分及测试命令、真实实施/批次结果。
- 下一动作：已有明确 Topic 时核对状态/建立状态并进入 to-spec；未明确多个候选 Topic 时说明分歧，不自行侵入另一 Topic。
- 结果：54之后的链可重建；从首次 local 入口严格依序读取时被45的 Tracker 映射前置截断，见 F2。上述输出采用明确 local 分支，不能当成无条件全路径通过。
- 授权边界：开发授权不等于尚未知的 Ticket 划分已经确认；对齐点2是保留的原关口，不是新增加的逐张批准。方法选择、普通修复、补负向回归不新增批准。

### S3 — “只有测试代码、无执行日志，写测试报告”

所选源码：`tests/test_install_simplification.py:17–31,52–66` 的 `test_changed_deploy_runs_one_gate_on_packaged_snapshot`，含 `patch.object(module, '_run_all_up_gate', side_effect=gate)`。只读取；未运行 deploy。

试读报告实际输出：

> **总体结论：**当前只能描述静态测试设计，不能确认该用例执行通过，也不能确认完整 suite、真实 host 安装或性能收益。
>
> **静态输入/前置状态：**测试创建临时 repo，只有 my-demo Skill，元数据 name=my-demo、description=test、disable-model-invocation=true；载入 CLI 模块并将 ROOT 指向临时 repo，AGENT_STATE_HOMES 置空。部署参数为 release_id=v1、upstream_id=local、target=auto，agent_home 指向临时 home。
>
> **替身：**完整检查入口 `_run_all_up_gate` 被替换为本地 gate。gate 记录调用 root、比较原 Skill 与检查位置的 Skill 字节，并返回 status=valid。这不是实际完整 suite 的执行结果。
>
> **可定位断言：**52–66行设计为断言检查入口只调用一次；检查所见 Skill 字节与源 fixture 一致；检查 root 不等于源 root。静态代码只给出了这些判定，不能扩大成所有 runtime/资源文件完整绑定证明。
>
> **边界与未知：**临时 fixture 和替换检查入口限定了覆盖范围。作者设计动机未提供，保持未知；从断言推断“意在防止活源树重复检查或快照错误”只能标为分析判断。执行命令、退出码、实际观测和真实 host 状态均缺失，当前不填通过。

- 入口：`my-test-report`；止点：正式报告，不自动跑测试/部署。
- 所需证据：当前代码的具体输入、前置状态、mock 与断言；只有存在与当前内容相符的运行记录才能写执行通过。
- 下一动作：生成报告并标静态证据/未执行；需要实际执行结论时取得对应运行记录。固定矩阵保留“设计理由未知”，不为填字段杜撰动机。
- 结果：test-report:76/85/99 能准确区分静态设计、替身边界与执行事实。此输出是读者重建探针。

#### S3b — 补充真实工程失败日志后，实际报告增补

外部输入：`/tmp/outcome-baseline.log`。定位336/361/386/408行是四个 ERROR；358/383/405/430行均报 README 对 runbook 的链接缺失；433/435行是 `Ran 286 tests in 311.094s` 与 `FAILED (errors=4)`。

试读增补输出：

> **实际工程预检查：失败。**提供的 unittest 日志记录286项测试、耗时311.094秒，最终4 errors。四个错误发生在 ReleaseTests 的 router/adapter/shared-resource/policy 打包场景，均在 preflight Markdown 校验时报 README 引用的 outcome-evaluation-runbook.md 缺失。它们是实际执行错误，不能降为“无日志”“仅未验证”或用其余 ok 淡化。
>
> 此文件是工程预检查失败记录，不是已证明干净、可比较的业务 baseline。日志没有绑定本冻结 manifest，不能据此说当前冻结源码仍有四个错误，也不能说当前版本已无回归。日志不提供所选新 mock 用例的可靠当前运行结果；该用例仍是静态设计、动机未知。后续修后 pass 是另一时点/范围的证据，不改写这个失败记录。

原始日志未附 shell receipt，故退出码具体数值未知；测试 runner 的 FAILED 是明确失败观察。没有把其他文件名含 pass 的日志读成这次失败已不存在。下一动作是保留该工程失败及内容绑定缺口，若要确认修复后当前状态，取得修后对应内容/命令结果；本次无需执行。

### S4 — “用户已经授权解决本次冲突”

原始输入：正在 merge/rebase；已授权解决此次冲突、保留双方意图并继续该操作；没有强推授权。

试读输出：

> 我先读 Git 状态、两侧提交和要求，给每个冲突说明双方意图与合并方式。在既有授权内完成可逆解决并验证，不逐 hunk 再问。若两方产品语义无法同时保留，先给具体取舍与影响，由用户裁决。验证后继续已授权的 merge/rebase，并报告实际结果；推送到未授权目标或危险 Git 不从本次授权推导。

- 入口：`my-resolving-merge-conflicts`→merge-conflict-approval→user-intervention；止点为本次已授权冲突操作及验证。
- 所需证据：状态、双方意图、解决后的内容、相应测试/审查与回滚依据；continue 的授权与验证前提。
- 下一动作：读实际冲突并执行兼容双方语义的解决；普通不确定性自行查证。单一授权来源未要求每个 hunk 重批。
- 结果：9–13与policy:3–7能重建合理路径。是否成功合并依真实仓库证据，本次没有运行。

### S5 — quick 局部 Bug 可行性

原始输入：已确认需求与 quick，当前分支明确，局部可回滚、不改变持久结构/权限/外部API；预计单会话完成。

试读输出：

> 保存必要 brief，核对 Topic/等级和原准入后直接进入 my-implement；不建 Spec/Ticket或 standard 实施记录。保留各验收、关键失败路径和影响的短计划，复用已有覆盖或选择合理 red/green；跑针对性验证，简洁自审，摘要写验收证据、影响风险与缺口后完成 Topic。若实际风险超过准入，在既有对齐点说明升级原因。

依据triage:54、assurance-levels:5–7、implement:10/14、implementation-session:11、workflow-delivery:24–26。runtime topic_service:244–270静态显示quick启动要求干净且有分支，默认基线分支上可能创建/切换 Topic 分支；不能将quick解释为无任何Git前提。报告不是实际quick收口的验证。

### S6 — 慢恢复排障

原始输入：“重启后恢复需20分钟，偶尔遗漏最后一条状态；先诊断，别操作生产。”

试读输出：

> 先记录版本、原持久状态、恢复时间线与准确遗漏，读日志/配置/恢复调用链。保留完整恢复条件，用本地代表场景或已有checkpoint按阶段观察，不因无法秒级运行拒绝调查。下一探针围绕最后一条状态何时提交/消费，选择能区分未落盘、未重放和消费接线遗漏的观察。只诊断，不扩大到生产修复。20分钟原场景未跑完时记录验证缺口；局部探针不能证明原故障消失。

入口diagnosing-bugs；证据为原状态/日志/阶段时序/持久化与消费入口；下一动作只读取证，或授权内隔离探针；止点诊断结论及未知。正文15–25、31、35–39及feedback-methods:9允许推进，不存在速度硬门槛。

### S7 — 间歇故障排障

原始输入：“约100次才出现一次重复消费，最近10次没失败。”

试读输出：

> 不把10次未失败算已修复。保存触发条件、总试次和实际失败样本，读时序/并发/历史证据，提出能被证伪的重复消费候选。选择保留真实竞争条件的重复采样或代表性集成实验，避免为了确定性消除竞争。一次主要改变一个变量；修复若获授权，用能区分原因的回归和原场景重复观察验证，报告样本与不确定性。

入口diagnosing-bugs；证据为条件、试次、失败比例、时序和可区分预测；下一动作按信息收益做实验；缺样本时继续取证，root cause保持假设。正文23/29/31/39与feedback-methods:9–11足以推进，无最低复现率或固定假设数量。

### S8 — 必须先读调用链才能构造复现

原始输入：“线上日志显示恢复到一半丢事件，没有现成red命令；只能先读调用链。”

试读输出：

> 先读取恢复入口、状态写入与事件消费调用链，以及配置/历史/已有测试，标出可达路径和缺失输入，再构造与日志症状一致的隔离回放。日志观察、静态缺陷判断和原环境复现分开；不把可达路径写成原环境已重现。当前只有一个可信候选也可直接检验，不补造3–5个假设。无法重现时继续授权内只读取证与可回滚探针；必要验收缺失不称完成。

入口diagnosing-bugs；证据为日志、相关条件与静态路径、复现输入和判别预测；下一动作读代码而非等待先有red；止点由诊断/修复授权限定。正文15/19/29/35–39解除旧互相冲突门槛。三类推演都只证明规则允许合理调查，不证明真实Bug已定位或修复。

## 仅正文独立重建：Agent Spec 与人类 README

本节只以两份有效正文为输入，不借历史讨论补足规则。读者为本独立审查者；未再派第二读者，因此不声称额外新上下文A/B读者实验。

### R1 — Agent Spec revision 2

读者任务：“判断这份文档现在授权什么，并重建候选施工/验证边界。”实际输出：

> 当前文件唯一current，revision2替代revision1；目前交付止于审核与Spec，implementation_status为not-started，方向接受不等于开工批准。候选范围覆盖32Skills、共享材料、组合、runtime和安装内部优化，但排除模型升级、真实账户/生产、自动push/安装/迁移和重写完成历史。
>
> 后续实施获准后，quick不建Spec/Ticket；standard从current Spec产生有血缘Ticket，逐张验证自审提交，批次全量比较和独立审查再收口。当前真实失败、未解blocking或依赖争议定义不能借旧成功字段通过。语义矛盾/预算/必要证据不足仍停；行重叠和体积不单独硬停。
>
> 我需要真实用户来源、仓库事实与当前内容绑定的测试/审查，而不是测试名字或字段齐全；持久契约可独立查存储与close/reopen，并核验真实消费入口。真实效果试点是另一个待授权阶段，正确交付分母包含全部分配任务，不能删blocked/超时/环境失败。缺对照不能宣称七项能力提升。
>
> 下一动作是交付本Spec并停止；若用户另行批准施工，才进入相应实施阶段与明确验证。各参与宿主不能混用旧/新writer写同一活动Topic；安装迁移分别遵授权。

定位：frontmatter/12；45–60；64–105；127–154；218–249；251–298。规则、前提、动作、限制可重建；基线SHA/宿主版本与历史审查content_id是Spec的来源陈述，本阅读探针没有独立验证其历史正确性。正文最终态与当前止点没有被“候选将做什么”覆盖。该输出不能当作AC全部工程完成。

### R2 — 人类 README

读者任务：“在已安装的项目开始工作，并判断哪些结果可以对外声称。”实际输出：

> 首次项目先setup并确认具体配置；现有配置不用重建。先确认所需产物和quick/standard，standard再确认Spec与Ticket划分。已确认材料直接复用，只出Spec就停，授权开发就完成授权范围内实施/验证/本地提交。
>
> 项目调用从所用宿主install-state读取绝对runtime_entry，不假设目标项目拥有本包tools目录。quick无Spec/Ticket但有准入和验收风险说明；standard逐Ticket定向测试/自审/提交，批次全量比较和独立审查后收口，再topic complete。
>
> 当前实际失败不能被缺基线吞掉；当前通过但基线不可比不能称无回归。修复和review内容变化使旧通过失效。源码检查、release与每个host状态分别说明；安装发布不自动授权。旧writer混写和历史记录限制公开，未知不补成功。
>
> 下一动作按项目是否已配置、用户阶段和当前status选择；安装后的工程用绝对runtime，给人展示human状态。真实效果尚需同条件任务对照，机械测试不能证明成功率提升。需要效果方案时读取源码中的runbook；README并没有证明它已执行。

定位README:7–14/18–44/81–105/138–163。前提与常见动作可重建；安装包不等于源码仓库，163已称runbook在“源码仓库”，不能假设所有host项目均携带该文件。独立读者仍会在triage具体入口遇到F2，README总览不能消除入口冲突。

## 按需加载与字数复核

独立脚本 `/tmp/outcome-review-loading-probe.py` 仅读取冻结Markdown及resource release_path，在内存建立Cursor宏投影与Markdown链接闭包；不执行候选打包/安装器。结果保存 `/tmp/outcome-review-loading-probe.json`。

| 指标 | 实际结果 | 含义 |
|---|---:|---|
| 原baseline记录 | 58,213字符 | fixtures中既有原始测量，不是本次重新执行旧安装 |
| 当前主链全部可达按需分支 | 37,849字符 | 94文件路径、34种不同正文，按内容去重；链接缺失0 |
| 差额 | 20,364字符 | 约35.0%累计文本减少，不是token、载入量、性能或效果收益 |
| to-spec入口正文 | 2,561字符 | 全可达资源闭包13,072；不应每次递归全读 |
| triage入口正文 | 4,371字符 | 全可达资源闭包19,413；不含其他Skill正文自动内联 |
| test-report入口正文 | 3,030字符 | 全可达资源闭包10,019 |
| diagnosing入口正文 | 1,628字符 | 全可达资源闭包9,605 |

`tests/test_text_measurement.py:12–24`已将门禁改为原58213记录，明确包括全部可选分支，不再要求35k。独立数值与用户给定37849相符。脚本给每个虚拟Skill提供声明资源路径以遍历；它不单独证明实际consumer分发正确，不能替代三宿主投影测试。当前值低于基准不以省略关键规则解释，下面按场景核对其承重规则仍有位置。

按需的实质路径：S1不需要to-tickets/implement/TDD/码审正文；S3不需要开发、设计审查、humanizer（未请求润色）；S4只需冲突与授权安全分支；S6–8按反馈方法/临时HITL需要读局部辅助文件。composition method/chain/handoff表示不同阶段，release.py:429拒绝composed正文副本；resource_consumer_maps:269–274仍将可达资源打包给caller，这保证可达，不表示要求模型读取。安装资源总量与上下文消费不可混同。

仍有限制：F4权威always声明会误加载访谈；triage:84将grilling与domain-modeling一起触发于“需要充实请求”，没有把领域词汇未知单独写成条件。共享来源中带链接也不自动等于需要递归加载所有目标，例如最终校验的新读者gate不能因为碰到一个例子就任意新增独立审查轮次。未采集实际host材料读取trace，因此只能判定“存在可跳过的阶段/风险分支及正文精简”，不能判定模型实际少读了多少。不得为了再压字符删除授权、语义停止、测试oracle、未知或恢复规则。

## 范围覆盖与交付证据

32个入口正文均纳入阅读；辅助文件按与上述AC的真实影响路径定向展开，而非声称所有示例/assets均完成逐字深审。

| Skill | 本次核对的消费者/风险 |
|---|---|
| my-ask-matt | 单下一跳路由、阶段止点、换宿主优先 |
| my-grill-me | 无代码库止于摘要 |
| my-grill-with-docs | 确认复用、方法触发、quick/standard |
| my-grilling | 只解决承重歧义、来源与返回 |
| my-domain-modeling | 术语/ADR与授权、长期知识 |
| my-to-spec | brief→Spec、唯一设计关口、阶段止点 |
| my-to-tickets | 血缘、跨Ticket结果owner、确认与批次 |
| my-implement | 六类风险、quick例外、证据/发现约束 |
| my-tdd | seam、独立oracle、多验收、合理例外 |
| my-code-review | 固定点、完整影响面、独立性/Spec挑战 |
| my-review-design | 承重事实、独立性与预算 |
| my-review-artifact | 按需维度、内容绑定、证据不足 |
| my-review-instructions | 单对象/集合、事实/效果边界、按需索引 |
| my-writing-for-agents | 指针条件、单一来源与完成规则 |
| my-codebase-design | seam门槛/术语、DEEPENING残留 |
| my-improve-codebase-architecture | content/frontend止点、候选选择后深化 |
| my-triage | local/Tracker、血缘、初始化与误加载 |
| my-wayfinder | 决策而非实施授权、交接与会话边界 |
| my-prototype | 隔离、证据外推边界、吸收授权 |
| my-diagnosing-bugs | 三种排障推演、原症状/因果/未知 |
| my-test-report | 静态mock用例与实际工程失败日志 |
| my-resolving-merge-conflicts | 已授权冲突解决、语义取舍 |
| my-humanizer | 冻结面、已授权原地改写、非固定工序 |
| my-edit-article | 可逆重排不重批、事实立场边界 |
| my-teach | none合法、学生正文/内部工件与质量边界 |
| my-tech-design | content/frontend/feishu、来源与未实测 |
| my-handoff | 状态来源、范围授权与证据恢复 |
| my-install | 绝对入口、目标/安装证据、损坏停止 |
| my-setup | 九键local配置、预览与有效配置复用 |
| my-research | 一手来源、事实推断与写回授权 |
| my-to-questionnaire | 外部知识缺口、保存不等于发送 |
| my-wizard | 人工脚本、秘密路径与静态验证，不真实执行 |

当前有27份resource Markdown、3份policy，resource manifest声明30项（包含这3项policy）。旧7份policy中的decision-taxonomy/project-discovery/project-storage/write-boundaries在patch中删除；write-actions适配也删除，相关职责转到统一授权/访问/存储等来源。治理manifest给当前共享对象分类，composition给调用/路由，resources给分发；它们不等于Spec 5.2要求的完整变更处置inventory。

| AC | 本次结论与边界 |
|---|---|
| 04 | 无Spec血缘后段已补；首次local前置仍有F2 |
| 05 | 直接Spec止点、已授权冲突与同目标写入可重建；方法触发F4需同步 |
| 06–07 | implement/tdd/tests/testing-seams支持多对多与独立存储oracle、真实router；示例不等于本项目行为已运行 |
| 08 | 共享规则改善；深化辅助正文残留F3 |
| 10 | review-loop:17允许批准行为的负向回归，不当新增需求 |
| 11 | 真新上下文/self缺口、实际模型/成本限制明确；未验证真实host派发 |
| 12 | 有调用/分发清单及完整冻结文件；F1/F2/F4为契约不一致；未见逐对象归宿/触发/处置理由的产品变更inventory |
| 13 | quick不造空六节，standard六类风险可引用证据；S5仅静态可行性 |
| 14 | ask-matt及context-hygiene明确换宿主先checkpoint，恢复目标/授权/定义/状态/证据/下一步 |
| 15 | teach CONTENT与visual规则允许none且关键文字保留；既有术语准许；不评价实际成品教学质量 |
| 16 | 输入包含完整候选源码而不只是零散条款；删除项可从patch核对。未提供正式release身份/替换包验证receipt或完整处置索引，不宣称发布/安装已完成 |
| 17 | README、Spec和runbook分清机械/探针/历史/对照；本报告进一步区分静态代码与实际失败日志 |
| 23 | S6–8三种路径均可推进，证据不足不写根因/原症状修复；未进行真实排障 |
| 24 | 用户来源/假设/决定性歧义有规则；to-tickets跨Ticket结果owner与spec-challenge明确；真实隐藏场景满足仍待试点 |
| 25 | R1/R2及S3/S3b给实际正文重建输出；不能当多名读者统计或写作普遍提升 |
| 26 | runbook具有七项机制/任务/指标/限制、全部任务分母和首验/最终/错误完成分别记录；无试验结果，未知外部动作仅有部分入口规则，见下段 |

## 未知外部结果与其余限制

短推演输入：“已授权向Tracker发布brief，工具超时，没有返回是否成功；仍在同一上下文。”正确可接受的读者输出应为：

> 结果未知。先查目标Issue的评论/状态，核对原操作是否已生效；查不到可靠结果就保持未知，继续不依赖该结果的授权工作，不能盲目再发同一brief。相同目标授权持续有效，但不等于授权重复副作用。

Spec:282与runbook:34明确支持该输出；context-hygiene:7也要求恢复不重复未知结果的副作用。不过user-intervention:8只处理写入授权，triage的context-hygiene指针在54限于跨会话保存恢复包，wizard外部写入也未给通用“结果未知先查原状态”处理。因此同会话外部写入路径的规则触达未完整闭合，不能将“统一授权”算作已证明未知结果自动恢复。此处作为AC26覆盖缺口，不声称本次观察到实际重复写入，也不以假设风险增设通用审批门禁；最小补验证是针对原具体外部操作读者短推演，必要时在已有共享授权/副作用规则中补状态核对条件。

本报告未替施工方签验收，未用候选workflow证明自身有效。修复优先顺序：F1停止字段契约、F2local初始化，再同步F3/F4；普通工程修复后按修改范围验证。当前证据只支持所列静态机制、计量和纯函数观察，真实host、全部AC完成、效果提升和历史baseline回归结论均未建立。
