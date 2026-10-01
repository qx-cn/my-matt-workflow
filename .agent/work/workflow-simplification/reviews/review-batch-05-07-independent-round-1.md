Review-Snapshot: 30a78d5963739b3e64848e30d132bd8a0561f18569dc19419d6895bbe521bb45
Review-ID: e06fc286807d4f7d9183fec19f4224c4
Base: 9e24d381a00c51d0df286ccb7ac89f6083963b4f
Head: ad6a89cf9696c2e7e8bd2f9c7d49ef2669b627c2
Review-Scope: change-only
Reviewer: independent_session / batch05-07-independent-round1
Round: 1

## Code

[P1][high] 接受未交回结果的审查会崩溃并留下半完成 Ticket — /var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/my-matt-review-snapshots/my-matt-review-30a78d596373-d4obhrme/154-ticket_completion.py:21

`review` 每次开启即占一轮，公开命令允许在上一轮未 submit 时再次开启。审查者退出、会话中断或结果未交回后，四个 open 轮次耗尽预算；第五次请求正确登记 needs-user。此时在当前内容上测试通过后，用户可以按 M5 接受现状，但 Ticket/branch accept 都将最后的 open 记录当成已完成 verdict，`metric()` 读取不存在的 `reviewer`，退出码 1、`KeyError: 'reviewer'`。Ticket 路径先在 `154-ticket_completion.py:61-66` 写 complete 和 outcome，再发生异常；`:75` 只捕获 TopicError/OSError，没有恢复 Ticket，导致没有提交/accepted 度量，后续 accept 又被 complete 状态拒绝。branch 路径在 `160-topic_service.py:420` 同样崩溃，不能归档。来源真实状态由 `157-ticket_review.py:168` 和 `128-branch_review.py:200` 正常登记，不需要篡改 JSON。修复应明确支持预算耗尽但最后一轮尚无结果的接受路径，在写状态前形成安全的度量值，并保证失败回滚；不要将未知审查来源伪造为通过。

基线可达性：复制 manifest 中五个正式 base 副本，结合未变模块组装临时 base CLI，运行 setup/start/test/review×4（全部退出 0）；保留项目原状态改用最终 frozen CLI，第五次 review 退出 1 并置 needs-user；accept 退出 1、KeyError，Ticket 已 complete。shared 与 private 均复现。另在最终 frozen CLI 中完成两张 Ticket，topic test，topic review×4，不 submit，第五次停止后 branch accept 同样 KeyError。此问题由本批新增预算/accept/metric 链引入，非未提交施工 schema 间迁移。

关联验收：workflow-simplification-06#A3、workflow-simplification-07#A4。Spec 冻结文件 `006-specs-workflow-simplification.md:157-176,212-222,232-236` 定义每次开启计轮、预算耗尽可进入 needs-user 及接受的前置条件；没有要求最后一轮必须 submit。

## Spec

No findings.

重新按同一冻结 Spec 和 Tickets 05–07 的全部验收建立映射，没有发现独立于上述 Code 根因的遗漏、错误行为或范围蔓延；同一失败链不重复列项。08–14 的迁移、安装件、主链文本、命令删除、全量集成验证与 README/config 由未来 owner 负责，不作为本批 blocker。follow_ons=[]，design_gap=null。

下表记录要求覆盖和证据边界。代码文件均以本报告所列 snapshot directory 内对应 frozen artifact 为证据；测试仅从 manifest 的 snapshot_path 复制到 `/tmp/independent-batch057` 执行。

| 当前验收 | 实现与实际验证 |
|---|---|
| 05#A1 | `154-ticket_completion.py` finish gates；test_five_steps_finish_commits_once_and_archives_single_ticket、test_finish_rejects_missing_review_unchecked_and_stale_content；13 个 review 用例验证判断字段和内容绑定。 |
| 05#A2 | require_pass/current_manifest 与 tests_passed；stale content/status 测试、review 材料失效用例；test_implement_lifecycle 的失败及 agent/ignored 内容边界。 |
| 05#A3 | commit_completion 的 shared/private 提交、notes；finish 五步标题/次数、无内容、修复 notes 正反例；private metadata hook 失败重试和额外 shared hook 重试。 |
| 05#A4 | complete 状态、metric、next_start_command；no-content preserves next ticket、私有提交重试度量唯一、真实五步下一命令。 |
| 05#A5 | `160-topic_service.py` standard 单 Ticket complete；双方模式单 Ticket 归档、pending 自动补建、缺摘要拒绝和 I-A1/I-A2/I-3 检查。 |
| 06#A1 | `157-ticket_review.py` 上限与 `146-review_loop.py` stop；四轮 pass 失效、四轮阻断、blocked-by-design/inconclusive 及第五轮持久拒绝。 |
| 06#A2 | `146-review_loop.py` delta/inside/signals；同根因、插入后中间快照行号重叠、contradicts 正反例、体积 >1.5 的各 CLI 用例。 |
| 06#A3 | accept 当前测试与 I-K1 gate；失败测试拒绝、needs-user 测试可运行、accepted 度量/known issues、双方提交。另有本报告 P1：open 末轮接受失败。 |
| 06#A4 | `156-ticket_resolution.py` definition diff 与重新 validate；checkbox-only 拒绝、implementing/needs-user reopen、保留 baseline/code、旧 tests/reviews 清空。 |
| 06#A5 | revised_test_argv_revalidates_and_becomes_effective；restartable CLI 状态、裁决原因与停止原因持久；未声明配置命令 reopen 拒绝。 |
| 07#A1 | `128-branch_review.py` full_tests/test/load；空 full-test 集合、失败退出码7、失败后继续第二命令、单 Ticket review 拒绝、缺当前测试 review 拒绝。 |
| 07#A2 | branch material 与 Topic baseline/acceptance 并集断言；独立四轮、needs-user complete 拒绝；contradicts 用例及额外 root/overlap/volume 三种 branch 信号探针。 |
| 07#A3 | multi complete 再执行 full tests、require_pass、check_summary、收尾提交/归档；双方含一次 branch 修复完整流程、关尾测试失败保持活动、归档重名拒绝。 |
| 07#A4 | branch needs-user accept、current full-test 与 closing test、定义 reopen；双方正常接受、原因/known issues/accepted 度量、私有提交失败后一次收尾提交、测试改内容拒绝。另有本报告 P1：open 末轮接受失败。 |
| 07#A5 | abandon 双方模式原样保留 dirty 内容、dirty_content 输出、overview 不显示、归档 Ticket start 拒绝；topic lifecycle 归档不能覆盖。 |
| 07#A6 | 双方 single/multi-with-repair/branch accept/abandon，以及 shared/private Ticket accept 测试；额外 private 无内容 accept 不创建主仓代码提交；正常终点 agent clean、private 主仓不跟踪 agent、代码提交次数断言。 |

实际运行检查：Python 3.14.4、Git 2.54.0，6 个模块共 74 tests 全部通过，各命令退出码 0：`test_implement_finish.py` 5、`test_review_resolution.py` 10、`test_topic_branch.py` 9、`test_implement_review.py` 13、`test_implement_lifecycle.py` 19、`test_topic_lifecycle.py` 18。命令形式为 `python3 -m unittest discover -s tests -p '<module>'`。探针 driver `/tmp/independent-batch057/probes.py`、`probes_extra.py`、`probe_baseline.py` 合计 9 个场景：final Ticket/branch open-budget accept 2；branch 三停止信号 3；shared completion rollback/retry 1；private no-content accept 1；正式 base→final shared/private accept 2。driver 退出 0 表示它们成功断言预期现象，失败的 accept CLI 子进程真实退出 1，并非接受通过。

证据局限：未运行缺少其他冻结源码资源的仓库全部测试、Python 3.10 或真实宿主安装；未把未来 owner 的完成能力算入本批验收。运行只写临时项目与报告，不读取实施总结/briefing/journal，不修改 live 或 frozen 代码。snapshot finalize/status:match 由主 Agent 后续执行，本报告不声称已经完成核验。

可重复执行的公开 CLI 复现脚本已保存为 `review-batch-05-07-independent-round-1-repro.py`；它读取冻结 manifest、校验 artifact SHA256、仅在临时目录组装 base/final 和测试项目。运行 `python3 <script>` 即可。已复跑退出码 0，逐条 CLI argv/stdout/stderr/exit_code 和三场景状态保存在 `review-batch-05-07-independent-round-1-repro-evidence.json`：shared/private 正式基线→最终 Ticket accept 与最终 branch accept 子命令均退出 1；两个 Ticket 已 complete、metrics 空、agent dirty，branch 仍 active 未归档。driver 退出 0 仅表示缺陷复现断言成立。

Code: P0=0 / P1=1 / P2=0，blocker=1。Spec: P0=0 / P1=0 / P2=0，blocker=0。
