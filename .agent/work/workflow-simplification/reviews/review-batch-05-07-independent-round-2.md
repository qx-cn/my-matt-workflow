Review-Snapshot: 6448d6ae5092bea8b8070fd11e072b48740ba6033dee3ec5bc01ef851e0c3cdd
Base: ad6a89cf9696c2e7e8bd2f9c7d49ef2669b627c2
Head: ad6a89cf9696c2e7e8bd2f9c7d49ef2669b627c2（另含冻结修复差分）
Review-Scope: change-only；批次 05–07，round 2/4；仅修复差分及影响路径
Reviewer: independent_session / batch05-07-independent-round2

## Code

No findings.

已按组合代码审查方法完成 Code pass，再进行 Spec pass。唯一本轮输入是冻结 inventory 中的 snapshot_path；对比冻结 baseline 与 current 的三份变更：test_review_resolution.py、test_topic_branch.py、ticket_completion.py。只读检查了 metric、Ticket accept/finish、branch accept、Topic complete 的调用和提交恢复路径。

原 P1 `batch05-07-open-review-accept` 已修复。/var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/my-matt-review-snapshots/my-matt-review-6448d6ae5092-c65p528_/154-ticket_completion.py:23 对没有 submit 的 open entry 返回 reviewer_provenance=null；:52 在 Ticket 状态、实施记录、度量写入和 private 代码提交之前计算度量。已 submit 的 entry 仍读取其登记 reviewer，不从开启审查时的宿主声明推断结论。共享 metric 也覆盖 /var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/my-matt-review-snapshots/my-matt-review-6448d6ae5092-c65p528_/160-topic_service.py:420 的 branch 路径。

临时执行目录 /var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/batch05-07-r2-review-8wyo_zgn 的 tools/tests/resources 均从冻结 inventory 复制。以下是实际运行 argv 和最终退出码；模块内部调用公开 CLI `python3 tools/workflow.py … --repo <临时 Git 仓库>`，不直接调用生产内部函数断言行为。

| cwd | argv | 结果 |
|---|---|---|
| /var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/batch05-07-r2-review-8wyo_zgn | python3 -m unittest discover -s tests -p test_review_resolution.py -v | exit 0；12 tests，32.544s |
| /var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/batch05-07-r2-review-8wyo_zgn | python3 -m unittest discover -s tests -p test_topic_branch.py -v | exit 0；10 tests，63.809s |
| /var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/batch05-07-r2-review-8wyo_zgn | python3 -m unittest discover -s tests -p test_implement_finish.py -v | exit 0；5 tests，11.802s |
| /var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/batch05-07-r2-baseline-j8mt4vcd | PYTHONPATH=tests python3 -m unittest test_review_resolution.ResolutionTests.test_accept_unsubmitted_reviews_recovers_in_both_modes test_topic_branch.BranchTests.test_accept_unsubmitted_branch_reviews_in_both_modes -v | exit 1；2 tests / 4 mode failures，16.502s；预期负对照 |

负对照仅把复制树的 ticket_completion.py 换成冻结正式基线 /var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/my-matt-review-snapshots/my-matt-review-6448d6ae5092-c65p528_/002-ticket_completion.py；采用相同当前回归测试。shared/private Ticket 在提交钩子失败处仍变 complete；shared/private branch accept 均产生 KeyError: reviewer。当前冻结修复树同一回归通过，证明修复对应原根因。

当前回归实际覆盖：四次 review 未 submit、第五次进入 needs-user；测试未通过拒绝 Ticket accept；shared/private 中断接受完成；Ticket 元数据提交失败保持 needs-user 并可重试，原因仅登记一次；未 submit 度量的 provenance 为 null、轮数为四；已 submit self/independent provenance 保留；Ticket 与 branch 终点 metadata 干净；branch 收尾测试失败或改变内容时拒绝归档；正常 finish 和 private 内容提交后元数据失败重试不重复代码提交。公开 CLI 用例的预期拒绝均断言非零退出。

## Spec

No findings.

重新以冻结 Spec /var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/my-matt-review-snapshots/my-matt-review-6448d6ae5092-c65p528_/005-specs-workflow-simplification.md 和 Tickets 05/06/07 验收建立本轮映射，未以 Code 候选清单作为输入。Spec M4/M5 的 needs-user 接受契约、I-K1 当前测试门、I-A1/I-A2 提交终点和 Spec :759 的未知字段为 null，与本次修复及实际回归一致；对应当前 owner 为 06#A3、07#A4，正常完成影响路径仍满足 05 的提交与状态保证。

Ticket16 冻结验收与 scope 作为补偿边界读取，其施工闭合记录不作为本轮产品缺陷。08–14 的迁移、安装件、Skill 主链、上游方法、技术方案、全量集成和使用文档维持其冻结未来 owner；本轮未要求提前完成这些能力。

Code P0/P1/P2=0/0/0，blocker=none；Spec P0/P1/P2=0/0/0，blocker=none。

限制：这是修复后复审，不重启首轮 exhaustive review，也不重置四轮预算。仅运行上述三个相关模块共 27 tests 与负对照；未运行全量 suite、未做安装或跨版本 Python 验证，不推断这些状态。报告通过旧 runtime review-result schema 校验；快照 finalize 由主 Agent 另行完成。
