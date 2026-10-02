# Runtime 整体独立只读审查

结论：确认 2 条 P1 未补齐的完成门禁漏洞，以及 1 条 P2 旧状态恢复路由不一致。不能据当前候选版宣称 AC01、AC18、AC19 全部完成；共享逻辑有实际收敛，但 runtime 精简不等于交付或模型能力提升。

## 范围与证据

- 最终冻结源码：`/tmp/outcome-holistic-608b72b`；基线：`/tmp/outcome-holistic-base-7947cb2`。
- 开始核对 manifest SHA256 为 `0f7c4296a473ec1df31e3e61f87d8a861aa2ef6eaaa904a46c4c85ae4ecd3eb1`。结束同摘要，并逐项核对 281 文件 hashes，零不匹配。
- 只读两个冻结目录；未读取主仓可变生产源码，未修改源码/真实宿主，未调用 workflow Skill 治理。全部反例在独立临时 Git fixture 运行公共 CLI。
- 已读 Spec revision 2 及 evidence、batch、Ticket implementation/completion/resolution/review、review_loop、branch/artifact review、Topic/status 路由差异与相关上下文。没有运行全量 suite。
- `/tmp/outcome-holistic-runtime-probe.py` 与 `.json`：旧协议发现遗失、真实动态导入失败。
- `/tmp/outcome-holistic-runtime-geometry.py` 与 `.json`：旧几何停止的 status/mutation 分歧。
- 探针复用最终测试目录的临时 Git/CLI 建仓 seam；额外行为和判定独立编写。fixture 和程序写入的 review pass 均为 synthetic，仅用于检验 runtime 门禁是否接收，不是实际 reviewer 已判定业务正确，更不是独立模型验收或真实项目效果证据。

## R1 — P1：恢复旧活动 batch 时遗漏已提交 Ticket 的未解决自审阻断

最终位置：`/tmp/outcome-holistic-608b72b/tools/workflow_lib/branch_review.py:108-110`。关联 `batches.py:312-315`、`batches.py:370-401`、`ticket_implementation.py:292-300`。

触发条件：旧 runtime 在活动 Topic 中登记 blocking 或 spec-challenge 自审，利用旧 finish 漏洞把该 Ticket 标 complete；该 batch 仍 open，尚未完成交付。切换候选 runtime 后重采 batch test 和 batch review。

实证：脚本用 **基线 CLI 实际产生** 这两种旧记录，没有伪造实现状态。候选 `batch status` 的 `decisions_needed=[]`，新 manifest 的 `self_findings=[]`。提供针对 manifest 全部 targets 的 synthetic pass 后，候选普通 `batch close` 返回 `state=已收口`；原实现记录仍保存 `persisted-old-blocker`，且没有处置/裁决。

原因：`pending_self_findings()` 本身识别旧 blocking/challenge，但 `materials()` 只把 `disposition=fix-in-batch` 放入 batch/branch 材料；普通 blocking 无该字段，spec-challenge 也无需这个 disposition。恢复 Ticket 的 gate 仅在加载 implementing/needs-user Ticket 时调用，complete Ticket 直接进入 batch 路径。这不是要求重开已合法完成的历史，而是**尚未关闭的活动 batch 必须处理旧 runtime 非法漏过的发现**；可以保留完成 Ticket 历史，用现有裁决或补偿路径处置。

预期：旧活动 batch 的未解决 blocking 应阻止普通收口；spec-challenge 必须进入裁决，不能靠 reviewer 看不到发现的普通 pass 消除。应将这些历史发现带入当前门禁/材料并要求明确处置，而不只迁移 advisory。

基线关系：旧 runtime 已存在 finish 漏洞；候选修好新 Ticket finish，却遗漏旧活动 batch 的恢复路径，属于 Spec 要求的修复未闭合，不是声称新引入旧漏洞。

Spec：§3 活动记录重评、§4.3 自审发现控制行为、AC02、AC18、AC19。

## R2 — P1：运行中的动态导入错误仍被当成纯启动环境缺口

最终位置：`/tmp/outcome-holistic-608b72b/tools/workflow_lib/evidence.py:132-137`（决定性分支在 136）；关联 `evidence.py:110-119,173-187` 与 `batches.py:248-255`。

触发条件：baseline 因缺测试依赖不能执行；当前自定义行为 probe 已进入被测逻辑，但其真实错误为 ModuleNotFoundError，且 stdout 没有 unittest/pytest/Go 执行标记。

实证：临时 fixture 的当前 `full.py` 调用 `selected_plugin()`，返回拼错的标准库插件名 `json_typo_regression`，继而真实 `importlib.import_module()` 抛异常。先写 `.agent/behavior-executed` 标记，内容 `selected_plugin invoked`；异常 traceback 来自 Python 本身，没有打印伪装 traceback 或伪造测试结果。候选结果同时为 `exit_code=1`、`unavailable=true`、`execution_observed=false`、`new_failures=[]`，仅列 `unverified=['python3 -B full.py']`；synthetic review pass 后普通 close 成功。原始 traceback、执行环境和比较输出均留在 JSON。

原因：完整 ModuleNotFoundError traceback 只证明异常类型，不能证明错误发生在解释器/测试框架启动前。`environment_only_failure()` 无条件接受 `module_missing_diagnostic()`；`execution_observed()` 只识别若干测试框架文案，不能为普通脚本的实际执行作否定证明。随后不可比 baseline 分支跳过当前失败。

预期：无法证明为纯启动依赖缺口的非零退出保持实际/未知失败；缺少可信可比 baseline 时须修复或取得既有失败证据，不能普通收口。收紧异常文案还不够，应绑定能证明启动阶段的结构或显式 runner 事实。无需把所有 ModuleNotFoundError 永远当产品问题，但本例不能仅凭异常类型批准收口。

基线关系：旧 `batches.run_full()` 的关键词判定也会吞此案例；候选显著缩小误判范围，但该核心路径仍残留。不是新回归；与原 AC01 的修复目标直接相关。

Spec：§4.5 表中“基线不可运行、当前实际执行失败”及“部分执行”两行，AC01、AC18、AC19。

## R3 — P2：旧 branch 几何停止的 status 提示会被建议的 mutation 自己拒绝

最终位置：`/tmp/outcome-holistic-608b72b/tools/workflow_lib/topic_service.py:333-344`；关联新 `branch_review.py:49-51` 与 `branch_review.resolve()` 的 needs-user 前置条件。

触发条件：旧非 batch 多 Ticket 协议中，branch 第 1 轮有阻断，修复后第 2 轮已经有效 pass，但旧 runtime 因 diff 体积超过 1.5 倍写 needs-user。当前内容/HEAD/定义及冻结 pass 均有效。

实证：基线公共 CLI 实际执行两轮审查形成几何停止；旧协议 fixture 复用仓库既有 legacy seam。候选 `topic status` 仍返回 `branch_review.status=needs-user` 并建议 `resolve --branch --accept --reason '<理由>'`。照建议执行时 `branch_review.load()` 先成功恢复几何停止，把状态持久化为 reviewing；紧接着 accept 报 `branch accept 只接受 needs-user`，退出 1。再次 status 已变成 reviewing / topic complete。整个恢复既不需要用户裁决，也不应以一次失败 mutation 才完成。

预期：status 和 mutation 应共享同一恢复后视图，status 能显示恢复依据并路由当前合法步骤；不能要求用户提供无必要的风险接受再拒绝它。

基线关系：旧 status 要求 accept 与旧几何停止政策一致；候选新增 mutation 自动恢复后，status 未接入该共同判定，产生新的跨入口不一致。

Spec：§4.2、§4.6、AC03、AC09、AC18、AC19。

## 收敛收益与维护成本

有直接代码证据的收益：

- Ticket、quick、batch 通过 `evidence.execute()` 共用 subprocess 调用、真实退出码、环境、输出截断事实和运行期间内容漂移观测；scope 特有的成功策略仍由调用者决定。branch 全量测试继续复用 Ticket run/test predicates。这部分抽取有实际消费者，不是只有生产/测试两个 adapter。
- Ticket 与 branch 的冻结 manifest/hash 检查收敛；artifact 仅共用 `bytes_match`，仍保留其目录范围和 size 约束，没有用一个通用 helper 抹掉 scope 差异。
- 正常 batch 路由经 `next_start_command -> batches.status` 共用，最后 Ticket finish 直接返回 batch test；完整性检查、运行前失效标记、环境/内容绑定降低旧成功 receipt 被误复用的风险。
- 几何启发式不再直接硬停，保留矛盾、Spec 挑战、证据状态与轮数预算。当前有效 pass 可解除若干旧停止。

当前维护代价：

- evidence 模块新增约 200 行，其中相当部分为 unittest 文本语法、loader 身份和旧输出截断的兼容推断；比原重复 subprocess 代码复杂。R2 说明集中后仍须约束推断能力，不能用 parser 集中代替事实证明。
- `pending_self_findings` 已集中，但其消费者自己过滤 findings；几何恢复分散在 Ticket load、batch active、branch load，而 Topic status 直接读 JSON。R1/R3 是规则局部共享、入口未完全收敛的实际后果。
- batch 状态仍同时存在 plan 与 per-batch 文件，旧/新证据同时支持；Spec 明确本轮不强制存储迁移，因此这里只记维护成本，不提出额外门禁或扩大重构范围。
- 每命令前后 content_id 与环境绑定增加计算；这是证据保护的成本，本审查未量化吞吐/耗时，不能声称 runtime 整体提速。

不能据这些机械改进推定任务完成率、准确率、需求理解、写作、代码实现、排障或自动化净收益提升；仍须 Spec §8 的同模型/权限/预算受控任务对照。本审查只确认具体改进路径和上述反例。

## 验证边界

定向正例测试选择：新 blocking 自审修复/历史保留；不可用 baseline 当前失败与旧 receipt 重评；最后 Ticket 完成路由；旧 Ticket 几何停止解除。结果单独留存 `/tmp/outcome-holistic-runtime-focused-tests.log`。通过只证明对应样例；不能消解上述独立反例。

未验证：真实宿主安装、真实模型 reviewer 行为、生产任务效果、全量 suite、所有可能测试框架文本、任意依赖环境变化。未发现证据支持 artifact byte-helper 抽取破坏其原 scope 约束；这是本次有限读码结果，不是全面无缺陷结论。
