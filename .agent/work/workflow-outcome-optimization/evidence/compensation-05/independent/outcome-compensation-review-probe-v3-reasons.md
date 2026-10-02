# 独立复审探针修订理由

原探针 /tmp/outcome-compensation-review-probe.py 保留，不覆盖。派生探针 /tmp/outcome-compensation-review-probe-v3.py。

1. R2 dynamic(loader=True) 的修复原为模块顶层 assert，没有 TestCase。Python 3.14 unittest discover 可返回 exit 5 / NO TESTS RAN。修复夹具改为真实 PluginBehavior.test_selected_plugin_api，使用 json.loads 的实际行为 oracle；额外要求 exit 0 与 Ran 1 test，不能让 no-tests 静默通过。
2. R2 direct_loader_startup 原要求 unavailable=true，依赖已被否定的 wrapper 启动推断。新断言要求 loader_not_unavailable、same_known、unverified、exit非零（非 current pass）、无 new failure，以及实际 close 成功。此处证明既有诊断比较合同，不证明业务已通过。
3. 其他既有场景与公共 CLI 日志记录保留。新增 controls 将单独记录，最终候选收到前未运行。

4. optional branch 初始控制使用单 Ticket，真实 CLI 按既有合同拒绝（topic review 只用于多 Ticket standard），不构成产品缺陷。只将该夹具修正为两张实际 completed Ticket，记录两票历史 bytes；保留 initial controls 脚本与首轮 log/json，并用 REVIEW_CASES 只重跑该控制。
