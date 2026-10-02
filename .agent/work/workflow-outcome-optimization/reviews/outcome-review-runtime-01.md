# Runtime 普通独立工程审查（冻结报告）

结论：**存在 5 个 blocking：2 个 P1、3 个 P2；不能据当前候选版认定 AC01–03/18/19 与 quick 摘要 AC13 全部满足。** AC09 的指定几何停止修正与本次检查到的快照策略保留未发现阻塞。下述结论来自源码调用链及隔离 fixture 实际结果，不由测试通过推导。

## 输入、身份与执行边界

- 唯一被审源码：`/tmp/outcome-review-code-01`。所有读源命令采用绝对路径，所有 exec 均为 `login:false`。
- `/tmp/outcome-review-code-01/source-manifest.json` SHA256：`2bb61d48e58af1aef97d9491445a3ab5d1848a9d1d4312a38bbc9ad451506d5b`，与指定值一致。283 个 manifest 文件逐字节匹配，无 symlink；清单外只有 manifest 本身与 `changes.patch`。
- `/tmp/outcome-review-code-01/changes.patch` SHA256：`3138b77474177a89aed72f3a26316bd7efaf9a31fc59bff7d597465ba7f797ed`。18 个文件的 unified diff 新侧 hunk 均与冻结源码对应位置一致。
- Spec：`/tmp/outcome-review-code-01/.agent/work/workflow-outcome-optimization/specs/specs-workflow-outcome-optimization-02.md`，SHA256 `efd7c71b787657623b1d5d58a817330cdbf32b5f532b5d55192db2c3cbe72d13`。本次限定 AC01–03/09/18/19 和 AC13 的 quick 摘要。
- 未调用任何 my-matt-workflow Skill 或施工 runtime；产品 CLI 只对临时新建 Git fixture 使用显式 `--repo`。普通 Python 探针导入冻结模块，禁止写 pycache。未编辑主仓、冻结源码或真实 Topic，未执行安装、部署、迁移、发布或真实宿主切换。
- 主检查对象为 evidence、batches、ticket_implementation/completion/resolution/review、review_loop、topic_service、branch_review、artifact_review；为理解调用链只补读对应 CLI、tests、quality_metrics、README。没有扩展安装子系统审查。

## Blocking

### R1 — P1：非标准 runner 的真实部分执行失败仍被环境缺口吞掉

**触发路径：** fixture 的基线 `python3 -B full.py` 在启动时缺依赖；当前同一命令先用子 Python 执行 `assert 1 == 2`，真实退出 1 并产生 `AssertionError: actual behavior regression`，之后另一阶段报 `ModuleNotFoundError`。这些是当前候选 CLI 实际执行生成的观察，未手改测试 receipt。

**实际结果：** `batch test` 返回该行 `exit_code=1`、非空 `failures`、`unavailable=true`，却给出 `new_failures=[]`，只列基线 `unverified`；提交 fixture 的合法审查 pass 后，普通 `batch close` 返回退出码 0、`state=已收口`。失败断言始终未修复。

**行证据：** [evidence.py:14](/tmp/outcome-review-code-01/tools/workflow_lib/evidence.py:14)（14–20）只识别 unittest/pytest/Go 的少数文本标志；[evidence.py:36](/tmp/outcome-review-code-01/tools/workflow_lib/evidence.py:36) 将含缺依赖文本且未匹配这些标志的整个命令记为不可运行；[batches.py:242](/tmp/outcome-review-code-01/tools/workflow_lib/batches.py:242)（242–246）在基线不可运行时忽略 `now.unavailable=true` 的全部失败；[batches.py:284](/tmp/outcome-review-code-01/tools/workflow_lib/batches.py:284) 和 [batches.py:351](/tmp/outcome-review-code-01/tools/workflow_lib/batches.py:351) 最终允许收口。

**影响/要求：** AC01、AC19；Spec 111–123 明确要求部分失败与环境缺口分别保留。继承的有限 runner 分类仍留下此失败路径，本报告不声称分类器全部是本 patch 新引入。应保守保留已观察的行为失败，不能仅因另一阶段的 import 错误吞掉整个命令。不要求建设通用语义日志分析平台。

**复现证据：** `/tmp/outcome-review-probes-01.py` 的 `partial`；`/tmp/outcome-review-probes-01.log` 的 `PARTIAL_BATCH_TEST`、`PARTIAL_BATCH_CLOSE`。

### R2 — P1：定义 reopen 无条件排除全部旧自审发现，且旧单条记录被删除

**触发路径 A：** 记录 correctness blocking `unfixed`，`finish` 确实拒绝；仅在 Spec 添加无关说明、通过 `resolve --reopen --reason` 批准这项说明修订，产品代码保持 `wrong`。重跑原声明测试、提交 `self-review --no-findings` 后，`finish` 成功。

**实际结果 A：** 没有针对 blocking 的修复、接受、defer/decline 或逐项处置；`self_review_epoch_start=2` 令原 finding 不再参与门禁。这里的 reopen 理由只批准无关说明，不是接受代码缺陷。历史虽然仍在数组中，当前完成判断已经漏掉它。

**触发路径 B（旧活动记录）：** 旧记录只有 `self_review`，没有 `self_reviews`，含 blocking `legacy-bug`。重开前 `pending_self_findings` 能读到它；同样做无关说明修订并 reopen 后，原 `self_review` 被 pop，`self_reviews` 仍不存在，`past_reviews=[]`。发现及自审证据从保存记录中彻底消失。

**行证据：** [ticket_resolution.py:47](/tmp/outcome-review-code-01/tools/workflow_lib/ticket_resolution.py:47)（47–50）只要求任何稳定定义变化；[ticket_resolution.py:64](/tmp/outcome-review-code-01/tools/workflow_lib/ticket_resolution.py:64)（64–65）整体推进 epoch 并删除 singleton；[batches.py:116](/tmp/outcome-review-code-01/tools/workflow_lib/batches.py:116) 从 epoch 后开始恢复；[batches.py:190](/tmp/outcome-review-code-01/tools/workflow_lib/batches.py:190) 仅检查恢复后的 pending；[quality_metrics.py:72](/tmp/outcome-review-code-01/tools/workflow_lib/quality_metrics.py:72) 的 preserve_history 只保留 reviews，没有补存 singleton 自审。

**影响/要求：** AC02、AC18、AC19；Spec 89–92 要求未解 blocking 阻断、发现与处置历史可追溯，不能只改字段逃逸。定义裁决应处置相应挑战，不应默认消解其他 correctness blocking 或待处理 advisory；旧 singleton 应先归档保存，再重评。合法定义修订后确已解决的挑战应能继续，但需留下可追溯处置。

**复现证据：** `/tmp/outcome-review-probes-01.py` 的 `reopen` 与对应日志；`/tmp/outcome-review-boundary-probes-01.py` 的 `singleton_history`，日志 `LEGACY_BEFORE`/`LEGACY_AFTER`。

### R3 — P2：合法简短 quick 摘要在无测试配置时无法收尾

**触发路径：** quick fixture 未配置自动测试，摘要只有非空“验收证据”“影响与风险”“未验证项”，明确人工验证结果与未配置测试的边界。该摘要满足新校验，不含“测试结果”。

**实际结果：** `topic complete` 抛出未处理 `StopIteration`，Topic 仍 active；status 继续建议同一会失败的 complete。

**行证据：** [topic_service.py:396](/tmp/outcome-review-code-01/tools/workflow_lib/topic_service.py:396)（396–399）允许上述三组章节；[topic_service.py:522](/tmp/outcome-review-code-01/tools/workflow_lib/topic_service.py:522)（522–527）无测试时仍用 `next(...)` 强制查找“测试结果”。

**影响/要求：** AC13、AC03、AC19。已允许的简短摘要不能在后续 mutation 隐式恢复标准章节要求；应在现有验证/缺口章节披露“未配置测试”，或安全新增披露位置。

**复现证据：** `/tmp/outcome-review-probes-01.log` 的 `QUICK_NO_TESTS` 与 traceback，冻结源码行 525。

### R4 — P2：当前审查 pass 后发生内容漂移，next action 指向不可执行的 repair

**触发路径：** Ticket 全部 finish，批次全量测试与审查合法 pass，结果无 findings；批次尚未收口时出现新未提交内容。

**实际结果：** `batch status` 返回 `batch repair --notes-file ...`，输入要求“包含待修复发现 id”；任何 notes 都无法通过，因为本批次没有 findings。执行该动作报“修复说明必须引用全部待修复发现 id”。close 也拒绝并指回 batch repair。新内容没有被错误放行，但机械路由形成死路。

**行证据：** [batches.py:312](/tmp/outcome-review-code-01/tools/workflow_lib/batches.py:312)（312–313）仅凭 dirty+reviewing 无条件建议 repair；[batches.py:326](/tmp/outcome-review-code-01/tools/workflow_lib/batches.py:326)（326–331）repair 硬要求非空 findings；[batches.py:350](/tmp/outcome-review-code-01/tools/workflow_lib/batches.py:350) close 同样指向该动作。

**影响/要求：** AC03、AC19、Spec 79/160。应依据有无真实待修复发现选择能执行的测试/复审/内容处置路径，或明确需要恢复内容等外部输入，不应要求提供不存在的 finding id。

**复现证据：** `/tmp/outcome-review-boundary-probes-01.log` 的 `DIRTY_STATUS`、`DIRTY_NEXT_MUTATION`、`DIRTY_CLOSE`。

### R5 — P2：接受整分支挑战并收口后，Topic status 仍要求重复裁决

**触发路径：** 两张 Ticket 的最后批次测试与审查 pass；用户选择额外整分支审查，结果包含 spec-challenge；随后以非空理由 `batch accept` 接受并收口。

**实际结果：** 成功 mutation 的 `next_command` 是 `topic complete`，并且该动作确实成功；同一状态的 `topic status` 却仍显示挑战待裁决，建议 `resolve --branch --accept`。执行 status 的命令返回“没有待收口批次”。

**行证据：** [batches.py:361](/tmp/outcome-review-code-01/tools/workflow_lib/batches.py:361)（361–365）已保存 branch acceptance；[branch_review.py:147](/tmp/outcome-review-code-01/tools/workflow_lib/branch_review.py:147)（147–149）已有当前 HEAD/content 的接受判断；[topic_service.py:339](/tmp/outcome-review-code-01/tools/workflow_lib/topic_service.py:339)（339–342）只看 needs-user，没有复用接受判断；[branch_review.py:38](/tmp/outcome-review-code-01/tools/workflow_lib/branch_review.py:38)（38–41）resolve/load 又要求存在活动批次。原 status 分支仍留下此契约缺陷，不把其所有代码归为新引入。

**影响/要求：** AC03、AC19。状态与 mutation 必须共享当前接受语义；有效接受仍保留 known_issues，但不应再次生成同一裁决，也不能建议已经无法加载的动作。

**复现证据：** `/tmp/outcome-review-routing-probes-01.log` 的四个 `BRANCH_ACCEPT_*` 结果。

## Advisory（不作为阻塞计数）

### A1：definition drift 的 accept 路径与 reopen 提示存在差异，需明确例外语义

隔离探针先登记 self spec-challenge，随后修改 Spec，重跑声明测试并重登记当前自审。status 显示 `definition_changed=true`、建议 reopen，但直接 `resolve --accept` 仍成功，实施记录的 definition 没有重开更新。证据为 [ticket_resolution.py:20](/tmp/outcome-review-code-01/tools/workflow_lib/ticket_resolution.py:20)（20–44）、[ticket_completion.py:31](/tmp/outcome-review-code-01/tools/workflow_lib/ticket_completion.py:31) 与 `/tmp/outcome-review-probes-01.log` 的 `DRIFT_STATUS`/`DRIFT_ACCEPT`。

这是已观察的路径差异；accept 本身是显式用户裁决，探针也重采了当前证据，不能不加区分地宣称“没有授权或伪造完成”。建议明确接受例外能否包含修订定义，并使 status/记录绑定一致；若要求任何定义变化都必须 reopen，则应在 accept 分支重检。该语义解释不计入上述 5 个 blocking。

### A2：差异材料不包含共享 helper 的文件 diff

manifest 包含完整 `tools/workflow_lib/evidence.py`，本次已按当前全文件审核；`changes.patch` 没有该文件的 diff。当前快照完整性没有因此失败，但仅凭 patch 无法判断 helper 是已有文件还是新增、以及相对基线的精确变化。若 patch 用作交付差异，建议补充该文件的新增/修改 diff 或明确既存状态。本报告不擅自把整文件认定为新增，也不延伸安装子系统范围。

## 按 Spec 排除的假风险

- **advisory downgrade：** Spec 91 允许 defer/decline；`validate_result` 在冻结 `/tmp/outcome-review-code-01/tools/workflow_lib/ticket_review.py` 243–249 要求 defer 有 owner、decline 有 reason。已有 fix-in-batch advisory 被明确改成有归属/理由的处置，不等同 blocking 降级逃逸。blocking/spec-challenge 的遗漏或降级已有 batches 160–166 与 123–125 保护；本报告没有将合法 advisory 处置列为问题。R2 是 reopen 无条件跳过历史而没有逐项处置，性质不同。
- **旧 unavailable 标志：** 不能仅凭旧 `new_failures=[]` 使用成功。batches 278–285 缺 completed/environment 等必要字段会拒绝；Ticket 312–320 缺完整执行/环境记录也拒绝，需重采。已完成历史不因此重开。旧 unavailable 标志是否准确应通过有效原始事实或重采确认，不能以手造 completed/environment 的旧 receipt 制造逃逸。R1 完全使用候选 CLI 当场产生的新 receipt。
- **几何停止：** review_loop 88–100 已去掉位置重叠/体积的单独硬停止，仍保留 spec-challenge、证据不足、矛盾与预算；107–121 只在当前有效 pass 的条件下恢复旧几何停止。本次未发现 AC09 的阻塞。

## 已核查保护与测试边界

1. Ticket/branch 都使用 evidence.frozen_manifest 核验 manifest 及 inputs/changes 字节；repository 文件也被加入 inputs。最小 fixture 的完整快照可读取，改变冻结字节后被 `TopicError: snapshot...` 拒绝。
2. Ticket 的当前内容、Ticket/Spec/config、规则、decided、下游验收检查仍在 ticket_review 294–307，未被共享 helper 删除。相应正式 CLI fixture 包括 staged/unstaged/untracked、二进制/模式/链接、规则及下游变更拒绝。
3. branch 的 HEAD 检查仍在 129–130。额外探针用空提交保持源码字节不变，batch close 仍拒绝“HEAD 已变化”。
4. artifact 仍保留 ownership/inventory/size 校验、源路径参与 content_id 与释放生命周期；独立探针用同字节不同路径提交 scope，返回 stale，而不是 match。artifact 的改动仅替换 byte hash 比较为共用 helper，未把 Ticket/branch 身份套用到 artifact。
5. formal Ticket run 在执行前持久化 completed=false；batch test 在执行前写入无效记录。对应中断 fixture 拒绝旧成功；内容变化后的通过记录也被拒绝。本次没有执行跨进程写竞争或真实宿主恢复实验，不据此宣称全部并发路径正确。
6. 普通 unittest 运行了以下 7 个冻结测试模块：test_batches、test_review_resolution、test_topic_lifecycle、test_implement_review、test_implement_finish、test_implement_lifecycle、test_topic_branch。实际结果 **104 tests，258.780s，OK，进程退出码 0**；日志 `/tmp/outcome-review-focused-tests-01.log`。这些通过不消解上述实际反例，尤其原 tests 的 partial 用例只覆盖有标准 runner 标志的情形，reopen 用例只覆盖所修订的挑战。
7. 额外探针及输出保存在 `/tmp/outcome-review-probes-01.py/.log`、`/tmp/outcome-review-boundary-probes-01.py/.log`、`/tmp/outcome-review-routing-probes-01.py/.log`。fixture 使用真实临时 Git repo/产品 CLI，审查 result 的 pass 仅是构造合法状态用于验证门禁，不是对 toy 产品正确性的独立保证。
8. README 97 已声明旧 writer 不混写、切换前盘点参与宿主、未知重采及完成历史不重开。本次未盘点真实宿主、实施切换或判断其他未随快照提供的切换计划；该部分 AC18 仅核查声明，不冒充升级验证。
9. 未运行仓库自身 Skill/施工命令、validate/check 全库入口或未改子系统穷举。检查结论只覆盖所列源码路径与已执行 fixture；没有同条件模型对照或真实环境能力提升结论。

## AC 判定

| AC | 本次结论 |
|---|---|
| AC01 | R1 阻塞；普通当前失败已有保护，但真实非标准 partial failure 仍可逃逸 |
| AC02 | R2 阻塞；直接 blocking/spec-challenge 门禁有效，reopen 历史逃逸未守住 |
| AC03 | R3–R5 阻塞；最后 Ticket 的正常批次下一步已有覆盖，异常/接受恢复路由不一致 |
| AC09 | 指定几何停止与当前 pass 恢复的检查范围内未发现阻塞；不作全流程正确性证明 |
| AC13 quick | R3 阻塞；有配置测试的简短摘要用例通过，无配置分支失败 |
| AC18 | R2 阻塞；旧成功缺字段会重采，旧单条自审在 reopen 丢失；真实切换未评估 |
| AC19 | R1–R5 涉及成功语义/部分失败/历史/路由；快照字节、Ticket 下游、branch HEAD、artifact scope 的已查策略保留 |

结束时再次核验：manifest SHA256 未变化，283 个清单文件仍全部匹配，未出现清单外新源文件。报告随后设为只读；摘要存于 `/tmp/outcome-review-runtime-01.md.sha256`。
