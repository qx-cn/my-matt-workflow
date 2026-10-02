# Runtime、测试与效果证据诊断

审查对象：原固定 review unit；来源路径/hash索引现存 `../evidence/source-manifest.json`（retained manifest，不是原 runtime metadata schema）。源码与本仓库历史文档只读取映射后的 `snapshot_path`；没有读取可变源码来补充结论，没有修改源码。主 Agent 统一 finalize。本报告是诊断及 SPEC 输入，不是实施结果。

证据等级：A 为当前快照代码加实际公共 CLI 探针；B 为当前快照代码或精确函数探针；C 为本仓库既有审查/执行记录；D 为外部历史记忆，用来选择验证任务，不证明现版仍有缺陷。下面的行号均对应映射的 `source_path` 文本行号。

## 1. 已观测到的自审阻断发现仍可提交，定义挑战没有进入裁决路径

影响：高。等级 A，当前可复现。

原文：现行 Spec `specs-workflow-review-2026q4-01.md:129` 要求“发现与代码不符时，按 M2 的 `spec-challenge` 处理”；同文 `:120` 要求“`spec-challenge` 一律不由 Agent 自行裁决：批次进入 `needs-user`”。`resources/review-loop.md:49` 也规定 Spec 挑战交用户决定。

当前代码：`tools/workflow_lib/batches.py:108–138` 的 `self_review` 校验六节结构和 finding schema，但只将 findings 记入 `unit['self_review']`。`:141–147` 的 `require_self` 只要求内容/定义绑定和章节完整。`tools/workflow_lib/ticket_completion.py:28–45` 的 `finish` 在批次 Ticket 没有独立高风险 review 时，不检查自审 findings 是否仍有 blocking、fix-in-batch 或 spec-challenge。正式 review 的挑战分流在 `ticket_review.py:338–365`，自审路径没有等效分流。

实际探针：定向测试通过；登记带完整字段的 `blocking/correctness` 或 `blocking/spec-challenge` 自审发现；Ticket 验收勾选；`implement status` 仍建议 finish，`implement finish` 成功提交且返回 `status: complete`。该探针不包含真实缺陷实现，仅证明运行时对自己已知的结构化阻断记录没有执行阻断。记录见 `../evidence/my-matt-quality-cli-self-findings.json`；综合复现见 `../evidence/my-matt-quality-runtime-reproduced.json`。

预期失败：Agent 已承认实现/定义冲突，却被下一命令提示推进本地完成；后续批次可能修复，但这使已知故障和错误前提继续进入下游实现。要求 Agent 再读规则自行记住停止，不能替代运行时对已登记 finding 的状态处理。

修改方向：自审与正式 review 共用 finding 处置函数。当前未处理 blocking/fix-in-batch 禁止 Ticket finish；在既有 Ticket 范围内修复、重测、重新自审即可，无需增加新用户确认。spec-challenge 从自审记录即时进入已有 needs-user 路径并携带发现，用户裁决后按既有定义修订/接受路径恢复。已解决与未解决必须可区分，不以“后来写一份无发现文本”隐式丢失历史。

验收建议：两个公共 CLI 反例均先拒绝 finish；blocking 本范围修好后可 finish；spec-challenge 未裁决时不推进，用户已有明确授权可作为裁决证据，不能重复问已决问题。只对机器已知的 findings 执行语义门禁，不让 runtime 评判自由文本质量。

## 2. 不可比较的测试基线会隐藏当前已执行的失败

影响：高。等级 A，当前可复现。不是“所有历史失败都必须修好”的建议。

原文：Spec `:239`：“基线已失败、现在仍失败的用例不阻断……新增失败阻断”；`:240`：“某条全量命令在基线上根本无法运行（环境缺失）……‘无法验证’，不阻断收口”。`resources/adapters/implementation-session.md:7` 复述全量相对首次基线无新增失败才可收口。

当前代码：`batches.py:199–216` 的 `compare` 在 `old['unavailable']` 且未观测到测试执行时，`:203–204` 无条件 `unverified.append(...); continue`，不看当前命令是否已经正常执行且报告失败。`:230–234` 的 `tests_passed` 只要求当前内容绑定、命令一致与 `not new_failures`；`:279–320` 的 close 据此放行，并将 `known_failures` 与 `unverified` 加入摘要。

公共 CLI 实际路径：在临时 Git 仓库，首次 `python3 full.py` 因缺依赖没有真正执行测试，记 unavailable；实现阶段将该命令恢复为真正运行的 unittest，其 `test_behavior` 返回 assertion failure，退出 1；定向测试通过；用仓库自身 `BatchTests.review` 夹具提交合法格式的 pass 回执。`batch test` 返回 `new_failures=[]`、`known_failures=[]`、`unverified=["python3 full.py"]`；`batch close` 返回“已收口”。自动摘要的“已知问题”是 `[]`，只在“未验证项”列命令，遗漏当前已经观测到的真实失败。该 pass 是明确脚本测试夹具，不是真独立模型审查，不证明 LLM 会忽视此故障。

证据：`../evidence/my-matt-quality-cli-baseline-recovery.json` 保存 baseline/current 原始尾部、退出码、收口与摘要；`../evidence/my-matt-quality-runtime-reproduced.json` 为复现脚本结果。

严格结论：缺少可执行基线，不能证明当前失败新增于本次改动；同样不能把当前已执行且失败的命令仅当成“无法验证”。故障是事实输出和结果可解释性缺失，不应靠推测将其归因为新引入。

修改方向：分开记录当前执行状态与可比较性，至少 distinguish `passed / failed / unavailable` 加 `comparable_baseline / no_comparable_baseline`。原 unavailable 而当前 passed 可报告当前通过、历史对照未知；原 unavailable 而当前 failed 必须报告当前 failure 及缺少对照，受该检查支撑的必要验收不能计通过。阻断范围按验收必要性和可达影响判断；不要求修复所有无关存量失败，也不让不存在的基线豁免当前事实。

关联证据粒度限制：`:207–215` 以失败 case ID 的集合差判断新失败。同一个 unittest case 的 assertion 原因从历史 fixture 错误变为本次行为错误时，结果仍是 known failure，且不会标不确定。这是已知失败豁免的政策/粒度限制，不是已证明的生产错误。建议为改动触及的历史失败增加定向差异探针或明确风险评估；不要承诺通用 stdout 哈希可以稳定识别所有失败根因。

## 3. 审查已经通过仍因文本形状/修复位置硬停

影响：中高。等级 B，精确快照函数探针；未观察到现版真实项目触发频率。

原文：`resources/review-loop.md:27–30` 将“同一处连续修改”和“体积膨胀：……第一轮的1.5倍”列为停止信号；`:23–32` 要求需要用户处理状态拒绝继续。

当前代码：`review_loop.py:96–107` 在收到每轮结果后，先判断相邻两次修复 hunk 是否重叠及总 diff 体积是否超过首次 1.5 倍，未要求当前仍有阻断发现。`ticket_review.py:361–365` 调用 signals 后 stop。精确函数探针传入 `status=pass, findings=[]`，同一行合法第二次修复会返回“同一处连续修改”，修复扩大到 2 倍会返回“体积膨胀”。

证据：`../evidence/my-matt-quality-review-stop-probes.json`；综合脚本也重现。只有纯函数执行，未跑整个 review 提交/状态迁移 CLI，此处不能宣称已完成端到端验证。

行为影响：位置重叠可能是准确修正，diff 增大可能是补必要的边界处理；有效 pass 仍被迫找用户。它把成本/循环风险代理量提升成正确性判断，可能削弱已授权范围内持续修复。

修改方向：保留有上限的成本预算和真正未解决的定义冲突、不确定结论；将重复位置和体积增长作为复查/缩小方案的信号，不能单凭它们拒绝当前有效 pass。若仍有阻断、两轮没有新的可验证进展，再停止并说明根因与已尝试路径。预算固定边界与用户授权如何相互作用需明确；不要通过扩大范围/修订状态无限重置预算。

## 4. Ticket 完成回执的下一命令跳过尚未完成的批次

影响：中。等级 A，当前复现。更适合与统一状态/下一动作来源一起处理。

当前代码：`ticket_implementation.py:389–397` 的 `next_start_command` 寻找 next ready Ticket，找不到就直接返回 `topic complete`。`ticket_completion.py:100–101` 的 finish 回执调用它，未查询 batch test/review/close 是否完成。`topic_service.py:433–438` 又会正确拒绝未收口批次。

实际路径：上面的单 Ticket batch 两种自审探针，finish 成功回执均指向 `topic complete`，但该批次还没有任何 batch test/review/close。遵循回执会撞到下一道机械门禁，再回头查询 batch status。机械保护仍有效；问题是流程导航矛盾，不能表述成已经绕过 Topic 完成门禁。

修改方向：所有 finish/close/status 返回的 next action 由一个 runtime 判定函数产生，包含当前 Topic 协议、Ticket/批次状态、当前证据、用户裁决状态；完成最后 Ticket 后返回 batch test，测试后返回 batch review，当前通过后返回 batch close，所有批次收口才 Topic complete。不是通过再加一段“如果命令失败读别处”的提示解决。

## 5. 已有度量证明保存了记录，尚未证明默认策略提高真实一次交付质量

影响：对优化判断高。等级 B/C。不是对现有代码有效性的否定。

做得好的原文：`evidence-effectiveness-assessment-01.md:7–9` 区分“真实项目同状态观察”“真实材料的只读试写”“源码与确定性门禁”，明确 `execution_evidence.status = not-recorded`；`:15–17` 分别指出新视图、修订索引与减少行数不能推出实际质量提升；`:23–28` 继续收集效果而非推广不可证的收益。`comparative-runbook-01.md:3` 明确 planned/not-recorded，`:7–26` 已提出同模型、同权限、冻结输入、fresh session、固定 rubric 的对照。这些证据边界应保留。

现版 schema：`quality_metrics.py:53–65,80–101,104–134` 保存按视角/来源/严重度发现数、审查子 Agent session 数、高风险审查与整分支执行情况；`:137–162` 支持归档后登记逃逸缺陷、合法归属和 design_review 未知。`tests/test_quality_metrics.py` 是记录/校验/汇总回归，不能证明审查真的看出了一个缺陷。登记数没有任务暴露量分母和观察窗口；`record_escape` 没绑定缺陷引入的 workflow release、模型/档位、输入任务及独立 oracle，也没有风险/严重度标签；`design_status` 根据 Topic 中任一对应设计记录推断执行状态，不证明缺陷所属 revision/定义曾获得相应审查。

预期误判：找出更多 advisory 会显得“发现数增加”，但最终重要逃逸缺陷可能没变；观察更久、使用更多会“逃逸数增加”；未登记不能当零。没有同条件候选/基线真任务运行，无法支持“默认六节增强自审+批次审查比旧策略更可靠”或“流程减短导致一次做对”。

修改方向：优先补小规模真实对照，不先建庞大 metrics 平台。冻结 release/commit、模型/档位、任务输入、环境、权限、验收 oracle、风险级别、可用于首次交付的测试范围；保留每次完整原始轨迹与结论依据。主指标是独立验收/隐藏生命周期 oracle 的完成率、错误完成率和重要逃逸缺陷；同时看中断恢复、用户纠正轮次、耗时与成本。登记缺陷附引入版本、发现窗口和证据，未知保留未知。小样本结果按任务类型报告，不外推总体提升。

## 明确应保留及已修复机制

- 当前定向测试回执绑定 content_id，整套声明 command list、run_id、completed 和每条退出码，见 `ticket_implementation.py:300–311,325–352`。中途崩溃先持久化 completed=false，旧逐条成功不能虚构完整通过。能够直接防住中断后错误完成。
- 当前自审绑定定义快照和内容，见 `batches.py:134–147`；当前审查绑定 immutable 文件、身份及当前定义，schema 校验 coverage 与 findings，pass 不含 blocking 或 spec-challenge，见 `ticket_review.py:183–284,287–325`。应修缺失的路由，不能为减规则删掉这些证据门禁。
- 批次关闭后当前内容变化不能直接归档，历史批次/Ticket 用补偿处理，见 `topic_service.py:433–438`；复审内容绑定和归档历史保护值得保留。
- self/independent 来源区分、无法派新上下文时如实披露缺口，是已授权默认策略，见 `resources/review-loop.md:7` 与 `implementation-session.md:9`。当前 schema 以宿主声明 session_id 判定来源，不能把 CLI 测试里注入 distinct ID 当成真正隔离 Agent 行为证据。不建议未经真实比较把所有 self fallback 强制阻断。
- quick 可未配置测试但摘要披露，见 `topic_service.py:469–519`，这是显式降级路径。应让实际未运行的必要验收保持未验证，不把 quick 的有意许可硬改成所有轻任务都必须建 Ticket。
- 既有 `workflow-review-2026q4/reviews/whole.md:7–19` 的 Go 包身份、partial import 错误分类、unittest summary 误报三个 bug 已在当前 `batches.py:150–216` 修复。本轮精确函数探针确认包 B 同名 case 可成为新增失败、partial 基线仍比较已执行测试、修掉一个历史 unittest 失败不误报新增。不能将这些旧缺陷再列现版问题。
- 历史 whole 审查记录明确 274 项通过后仍发现 3 个实际 parser 问题，后续定向/完整及独立探针补证；这支持选择真正生产形状的探针作为 reviewer 工作方式，不支持把通过 case 总数作为模型效果。

## 本轮执行与复现

已执行：5 个精确快照 `batches.failures/execution_observed/compare` 函数探针；1 个 unavailable→可执行失败的完整 batch close 公共 CLI 探针；2 个含自审 blocking 的 start/test/self-review/finish 公共 CLI 探针；2 个 pass 仍触发停止的 signals 函数探针。综合脚本已实际重跑，退出 0，用时约 5.5 秒。

复现：`PYTHONDONTWRITEBYTECODE=1 python3 ../evidence/runtime-probe.py`。原始探针只从固定 snapshot materialize 精确文件；归档复现脚本从自身目录的 retained-source.zip/manifest 校验 hash 后复制到自己拥有的 `/tmp` 目录；目标项目由仓库已有 unittest 夹具创建临时 Git 仓库；review pass 是合成 fixture；完成后清理临时目标，不改工作区。脚本与 JSON 记录不是外部审批、不是独立模型审查，更不是新版本效果证明。

未执行：全套 tests、当前源码 validate/check/deploy/install、真实模型候选/基线运行、真实生产或外部服务、完整 review stop CLI 链路。没有理由为只读诊断先花几分钟再跑同一全套；本轮回归证据只覆盖已明确的有限机制。

文件：`../evidence/runtime-probe.py`；`../evidence/my-matt-quality-runtime-reproduced.json`；`../evidence/my-matt-quality-runtime-probes.json`；`../evidence/my-matt-quality-cli-baseline-recovery.json`；`../evidence/my-matt-quality-cli-self-findings.json`；`../evidence/my-matt-quality-review-stop-probes.json`。

## 真实任务验证设计

第一批选 6 类真实开发任务，每类冻结两个相似实例，旧/新 release 随机分配、同模型/档位/宿主/权限和预算，执行 Agent 不看隐藏 oracle，每个 run 独立会话。复杂任务沿用户真实已授权范围执行，外部副作用用本地模拟器或测试环境；这不授权部署/交易。

1. 简单且低风险的展示/配置修改：衡量轻路径是否减少仪式文档、交互与耗时，验收仍完整，不能强迫为展示修改构造无关测试。
2. 含一个真实未决业务语义的需求：衡量是否先查证可查事实，仅把实质未决项交用户，已决问题不再问；同时给简单已明确任务，检测澄清是否过度。
3. 多 Ticket 共享 helper/配置/错误语义变化：隐藏一个未改消费者，oracle 检查调用方与跨 Ticket 集成，防止 Ticket 各自通过而整体行为错。
4. 持久状态、重启与恢复：覆盖完整写入→关闭→重开→生产 router/adapter 再接入；提供 unit pass 但 lifecycle 缺陷，观察是否查到真实可达路径。这来自旧 Trader 实际失误的任务类别，不能拿旧版失误预设现版一定失败。
5. 历史红测试/不可执行命令：既有无关失败必须被披露且不拖死范围；恢复执行后当前失败必须保留；同 case 名不同失败原因不当已验证通过。隐藏 oracle 独立判断本次变更的验收。
6. 中断接续/定义更新/两次同处修复：首轮修复后中断，fresh Agent 查 runtime 继续；给必要的第二次精确同处修复和无发现 pass，检测是否错误硬停、使用旧通过或将批次未关闭误为 Topic 完成。

独立评分：首次宣称可交付时锁定结果，oracle 判断全部明确必要验收、实际可达行为与授权边界；记录错误宣称完成，即使后续修好也不能回写首次成功。复核者尽量只拿需求、代码与原始执行结果，不知道 baseline/candidate 标签。

主报告：每类“首次完整正确 / 不能完成 / 错误完成 / 不可判定”，重要逃逸缺陷以及用户纠正次数；副指标为调用/token、墙钟时间、文档量、恢复时间。至少记录设计审查到底覆盖哪个 Spec revision、批次范围及独立来源。不能为了得到‘新版本更优’将环境不可比的失败、未跑任务或派出但未返回结果补成 pass。样本少时只说哪些失败在该组下降/未下降，保留不确定性。

外部记忆的个案未纳入本报告的结论依据；主诊断以已核原会话和当前探针为准。
