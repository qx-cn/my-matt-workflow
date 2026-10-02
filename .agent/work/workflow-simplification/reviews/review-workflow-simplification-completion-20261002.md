# workflow-simplification 历史完成审查

审查者：独立只读子 Agent，继承宿主模型与推理档位，未升级或降级。第一轮完整审查，未修改用户仓库、冻结历史工件、登记 runtime 或发布。按当前 my-code-review 的 correctness、impact、spec、spec-challenge、maintainability 五视角执行；判断历史完成时使用旧 Spec revision 1，不用 Q4 新要求追溯否定旧验收。

历史范围：40e51af..c4809cc44a99def8433ec84ea47968038416de16；content_id=c75a9675ab5e0ef0f38980dd242658906e971d4a66e0b82effe940ae0440b76e。当前核查点：77246b4225a48c6d177ff830c7c00ffb07f7666d；content_id=21ac32239067a1dcdd7e8ae652b9532a1c44f36975a1ed40ad506ec1bbdc5f94。范围为 touched-context：实现、CLI 调用方、冻结材料消费者、规则文本、构建/安装/迁移及测试。

## 判断

历史端点的主干实现和普通临时 Git 仓库中的自动化验收已完成，独立全套 check 通过；不能据此称历史所有外部行为均满足。发现 2 个可复现 P1/blocking，另有 1 个历史 P2/advisory：状态查询隐藏 Ticket 裁决、Gitlink 仓库无法进入审查、共享审查规则另有硬编码副本。前两个问题在当前仍可达；第三个已由 Q4 修正。没有以新批次、六节自审、五视角输出、两轮文档预算等新要求追溯否定旧工作。

## correctness / impact

### H-F2 — P1/blocking：未修改的 Gitlink 使整个 standard 审查入口失败

位置：历史及当前 tools/workflow_lib/ticket_review.py:27–53，尤其 35–37；由 implement review、branch_review.review 和当前 batch review 共同消费。

正式基线可达路径：已有正常 Gitlink（Git submodule 在 ls-tree 中同样为 mode=160000、kind=commit）的仓库，创建 ordinary Ticket，只修改 code.txt，声明测试通过，执行 implement review。baseline_files 遍历整个基线而不是只枚举改动，遇到任何非 blob 即拒绝，报“无法冻结非 blob 内容：module”，exit 1。Gitlink 本身可以完全未改。当前新批次在 Ticket 本地完成后、batch test 通过，再执行 batch review 也报同样错误；当前高风险 implement review 及可选 topic review（batch test 前置已满足）同样失败。按同一根因合并为一项。

影响：正常包含子模块的仓库不能走完审查/完成链；并非低置信度的潜在风险。源 Spec 未排除子模块仓库；“全部内容改动”与五步完成契约存在边界缺口。旧版 review_snapshot.py:81–120 已专门支持 gitlink，因此也是新 runtime 替换时的影响面回归；旧 Topic 引入。

证据：/tmp/simplification_completion_probes.py 与 .json；/tmp/simplification_current_probes.py 与 .json；/tmp/simplification_current_more.py 与 .json。探针使用真实临时 Git 仓库、公开 CLI，包含实际 Gitlink 类型和未修改的子仓 HEAD。预置 pass/自审文本仅用于机械契约探针，不是假称真实独立语义审查。

当前状态：仍存在。新批次正常、高风险单票和可选整分支三条消费者路径都已实际确认。

## spec

### H-F1 — P1/blocking：topic status 隐藏需用户处理的 Ticket 并返回不可执行的收尾下一步

位置：历史 tools/workflow_lib/topic_service.py:254–285；当前同文件:254–307。

依据：旧核心模型 M6 明确要求 topic status 显示各 Ticket 状态、需用户处理的对象及原因、下一条完整命令。其遍历 implementations 只收集建议/已知问题，完全没有输出 Ticket 列表及 stop_reason；active 情况直接选择 topic complete，只有 branch needs-user 覆盖。

真实路径：implement start → implement test → implement review → submit inconclusive。此时 Ticket 文件为 needs-user，implement status 能看到对象和原因，但 topic status 仍只显示 active，branch_review=null，next_command=topic complete；跟随下一步只会因 Ticket 未 complete 而失败。用户依标准 Topic 状态入口恢复时不知道要裁决哪张 Ticket及为什么。

当前状态：对继续支持的既有 v2、未建立 batches 的实施记录，公开 CLI 仍复现同样错误，decisions_needed=[]、batch_status=null、next_command=topic complete。当前新批次正常 active 的 next_command 已由 batch_status 正确提供，实测为 implement finish，因此不能把该缺陷写成“所有当前 standard 都误指向 complete”。新批次列表是批次 ID 集合，非逐 Ticket 状态，但本报告阻断证据限定在真实支持的旧记录恢复路径。历史整分支建议不进入 topic status 的缺口由历史:272–282直接证明：advisories仅从implementations填充，branch分支只追加known_issues并处理needs-user。这违反未限定Ticket的AC-16，故AC-16判部分满足。当前源码:286–287已新增最新轮收集，本报告不计为仍存故障，也不新增第三个当前P1。

证据：/tmp/simplification_completion_probes.json 中 active_ticket_status、needs_user_ticket_status；/tmp/simplification_current_probes.json 的 supported_v2_existing_needs_user；/tmp/simplification_current_more.json 的 new_batch_active_topic_status。当前 legacy fixture 按当前测试约定模拟升级前已开始的 v2 session，不把人为删除 batches 当作新协议支持来源。

## maintainability

### H-F3 — P2/advisory：冻结材料里的审查循环仍来自第二份硬编码定义

位置：历史 tools/workflow_lib/ticket_review.py:73–96，及 resources/review-loop.md；前者的 loop_rules 返回常量，implement/branch review 将其写入 review-loop-rules.md。

依据：旧 Spec 第4节要求同一规则一处定义，AC-15要求共享审查循环覆盖并由六个 Skill引用。六个 Skill 确实引用共享资源，但公共 runtime 打包规则不读取它；注释写 Ticket09 将迁移，历史端点仍残留。结果是修改共享资源后安装 Skill 的规范与 runtime 材料可分叉。历史两份内容的主要规则接近，未发现端点因此产生的另一条独立可达故障，不提升到 P1。

当前状态：已修复；current ticket_review.py:73–74 直接读取 resources/review-loop.md。disposition=decline，reason=当前已完成共享来源修正，不需要再为历史端点施工。此项不计当前阻断。

## spec-challenge

无新增发现。旧阻断准入、下游建议和建议不修等已决设计由 Q4 明确替代，不能用当前规则追溯否定旧验收。本审查仍报告没有 AC 锚点的实际故障（H-F2），没有因旧 Spec 允许或没写到而放行。

## 独立运行与四项机械护栏

在 historical 冻结仓独立运行 python3 tools/workflow.py check：Python 3.14.4，exit 0，输出 status=valid；随后 git diff --exit-code exit 0、git status --porcelain 空。check 内部调用全套 unittest discover，并只在失败时输出测试日志；因此不猜测试数量。Python 3.10 未由本子 Agent 本地运行；主 Agent 提供当前历史 commit 的 CI run36924685542，3.10/3.14 两 job 的 check 与 git diff 步骤均 success，应作为独立 CI 来源单列。

- 测试失败：test_implement_lifecycle 的 declared_tests_progress_failure_and_definition_change、duplicate_commands、interrupted_formal_run 等真实 CLI 断言；finish/accept gate 拒绝无完整当前测试，确认有效。
- 审查后改动：test_implement_finish 的 stale_content、test_implement_review 的 stale/frozen_corruption、changed_rules_decisions_downstream；当前内容变化失效，.agent/与 ignored 修改例外已覆盖，确认有效。
- 越序：start_guards_dependencies_content_and_quick、needs_user_busy、依赖及同Topic单票约束，确认有效。
- 审查单元不匹配：submit_missing_changed_prefilled_fields、invalid_shapes、semantic_validation，预填身份/content/round/acceptance/probes/downstream不符拒绝，确认有效。

这些机械护栏有效不等于真实仓库边界已覆盖；H-F1/H-F2 正是全套绿灯之外的公开消费者故障。

历史 Cursor 主链复测：32,155 Python 字符，77 可达文件、31 去重内容；施工前 fixture 记录 58,213，满足35,000上限。没有为此操作真实宿主安装或外部系统。

## AC-01–41 覆盖

“满足”表示旧历史端点的明确条款有源码/文本及已运行测试证据；不是对未来模型效果、真实用户项目或全部 Git 形态作保证。“部分”表示有正常路径证据但本轮发现要求或支持边界缺口。

| AC | 历史判断 | 简要覆盖证据 |
|---|---|---|
| 01 | 满足 | my-grilling/my-grill-with-docs：批量问题、推荐与取舍、需求核对、来源摘要、等级提议。 |
| 02 | 满足 | grill-with-docs→to-spec→to-tickets→implement自动chain；user-intervention唯一人工条件资源；三宿主资源闭包测试。 |
| 03 | 满足 | implement_lifecycle existing_branch/nondefault/admission；finish五步真实CLI单提交，源码无push消费者。 |
| 04 | 满足 | topic_lifecycle invalid_and_legacy_setup；migration representative commands验证audited/非法字段。 |
| 05 | 满足 | topic_lifecycle quick dirty/summary/test failure/private+shared/无测试/commit retry。 |
| 06 | 满足 | standard_wildcards；pending_requires_full_tests，拒绝仅前缀测试配置。 |
| 07 | 部分，H-F2 | finish五步公共CLI测试通过；但未改Gitlink仓库无法进入review，真实探针反例。 |
| 08 | 满足 | declared_tests_progress_failure；finish_missing_review/stale，nonzero与命令/退出码记录。 |
| 09 | 满足 | content-bound lifecycle tests、finish_stale、ignored/agent例外、快照腐坏拒绝。 |
| 10 | 满足 | start_guards_dependencies_content_and_quick；needs_user_is_busy。 |
| 11 | 满足 | submit_reports_all_missing_and_changed_prefilled_fields，所有预填字段逐项拒绝。 |
| 12 | 满足 | admission_matching；declared_tests_progress_failure_and_definition_change；progress不作finish依据。 |
| 13 | 部分，H-F2 | review_freezes_all_changes、outside_scope、binary/link/mode、nested_agent_fixtures通过；gitlink全仓失败。 |
| 14 | 满足 | lifecycle topic_selection_and_cross_topic_ticket_rejection，两个Topic/指定Topic测试隔离。 |
| 15 | 部分，H-F3 | 六Skill均引用共享资源，review-loop文本覆盖预算/停止/日志；runtime另有常量副本。 |
| 16 | 部分 | review_pass_and_advisory_registered证实Ticket建议进入topic status；旧Spec未限定Ticket。历史topic_service.py:272–282只从implementations收集advisory，branch-review只收集known_issues/needs-user，因此整分支advisory遗漏；当前:286–287已增加最新分支轮次advisory收集，不计新的当前P1。 |
| 17 | 满足 | review_resolution fourth_pass_invalidation/four_blocking；fifth拒绝与needs-user持久化。 |
| 18 | 满足 | same_root_two_repairs、overlapping_repairs、contradiction、volume四种真实CLI停止测试。 |
| 19 | 满足 | resolution accept_keeps_known_issues、accept_unsubmitted、definition_reopen/new_commands、private accept。 |
| 20 | 满足 | topic_branch branch_needs_user_accept_definition_only_reopen；artifact_cli_retired_options。 |
| 21 | 满足 | review semantic_validation与invalid_shapes：必填字段、blocking证据、pass含blocking拒绝。 |
| 22 | 满足 | final_integration exact_commands_unknown_legacy；旧spec目录仅作迁移检测，不读取长期Spec内容。 |
| 23 | 满足 | topic_branch abandon_preserves_dirty_content(private/shared)，归档原因/度量/内容保留。 |
| 24 | 满足 | finish/private retry、resolution/private accept、topic_branch单/多票修复/branch accept/abandon两模式；提交数与.agent干净断言。 |
| 25 | 满足 | topic_lifecycle overview_document_pending_active_archive；standard无票/单票；自动补建与归档重名拒绝。 |
| 26 | 满足 | to-spec不发布长期Spec，domain-modeling CONTEXT/ADR，handoff只在换宿主目录人或Spec前保存。 |
| 27 | 满足 | setup9keys、新schema2；migration项目级代表性命令只读停机。 |
| 28 | 满足 | final_integration removed_names_absent扫描skills/resources/policies。 |
| 29 | 满足 | skill_packaging catalog32、resources_no_composed；源码compose删除正文机制。 |
| 30 | 满足 | catalog_invocation_graph与三宿主install权限测试；11被调用方名单与其余手动元数据。 |
| 31 | 满足 | 对正式基线8冻结Skill全目录diff核对：只有许可全局引用/元数据/研究移动，map参考仅同类替换。 |
| 32 | 满足 | TDD无refactor；writing-for-agents删除/指针/负担/分层/完成条件；ask-matt顺序；architecture约20commit；to-spec无PRD别称。 |
| 33 | 满足 | tech-design/SKILL+CONTENT：四固定节/原文唯一位置/Spec访问/参考/自检/路径/飞书未实测。 |
| 34 | 满足 | text_measurement函数/测试，实际32155≤35000，baseline注释与fixture58213。 |
| 35 | 满足 | migration由baseline.bundle旧runtimefixture A–E；preview/apply/backup/private/继续finish/accept/reopen/归档/第二次no-op。 |
| 36 | 满足 | migration project_and_topic_legacy_gates_are_read_only，代表性命令与局部旧Topic隔离。 |
| 37 | 满足 | 本子Agent3.14.4 check+diff独立通过；3.10/3.14 CI由主Agent另行核实；不声称本地运行3.10。 |
| 38 | 满足 | final_integration exact_public_commands_and_unknown_legacy_commands。 |
| 39 | 满足 | final_integration FIELDS完整、metrics CLI/topic汇总、unknown保持null、test failures非command error。 |
| 40 | 满足 | skill_packaging release retention current/previous/installed；Ticket17 custom home并发/registry/upgrade/corrupt专项。 |
| 41 | 满足 | README最终help/9keys用法，维护节Trigger与度量前不新增门禁；removed说明核对。 |

## 工程完成与历史 runtime 归档

17张 Ticket 均complete且验收已勾选；16张有最终旧施工run phase=complete，其中01/09/13另保留原阻塞attempt和后续完成attempt。原run阻塞不自动否定新完成attempt。Ticket14没有同名run，但其票据明确允许直接按Spec施工，不强制使用被替换runtime/Skill；Spec施工顺序末句也明确不需要使用自身runtime。其实际README/配置提交4009709、red/green日志、artifact方法receipt和完整check存在。可认定工程交付证据存在，来源明确self；不能伪造runtime闭环或独立审核。

尾部迁移补偿679cf9c有正式4009709基线、三文件快照、snapshot verify=status match、迁移red/green与全套check；completion明确reviewer_provenance=self、runtime_completion_receipt=null。因此它有工程修复与自审证据，不是独立整分支审核。Ticket17有raw run及test/review evidence与独立probe日志，但alias_mapping只说明别名映射，不是新上下文独立性的充分证据；需要宿主session/派发记录来确认历史独立来源。没有从“independent”文件名或别名猜独立性。

workflow-simplification目录仍位于.agent/work/，没有topic-state.json，不是runtime archived。Ticket14 A4和旧Spec范围边界明确本仓已有work不转换、不归档；当前显示pending不能据此算工程不完成，仍需将“本仓刻意保留历史工件”与“在新用户项目中的topic complete自动归档机制”分别陈述。自动归档机制由公共CLI临时仓测试确认，本仓历史Topic没有归档receipt是准确状态，不是这里发现的额外Bug。

历史审查来源残余边界：登记的pass能证明当时runtime接受该结果，不能仅凭报告别名证明每次确实新上下文。飞书、7个实际项目迁移、模型行为收益在原Spec边界之外或明确未验证；不将其纳入本轮blocking。真实宿主安装由主Agent单独核实：releases/20261002-004722与历史最终源码匹配，两宿主安装valid/32skills，当前drift相对Q4新源码；这不是旧Topic安装遗漏。本子Agent未操作宿主，相关证据由主Agent的historical-release-match.txt/external-verification.json支撑。
