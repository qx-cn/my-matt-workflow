# Ticket 08–11 独立批审核

审核完成。质量结论：2 项待处理发现。四张由独立新会话分别完成 Code → Spec 双遍；未携带实施对话或既有自审结论。原完成记录保留。

| Ticket | 正式基线 → 原交付 | Code P0/P1/P2 | Spec P0/P1/P2 | 结论 |
|---|---|---|---|---|
| 08 | 8b9fc05 → 08e58eb | 0/0/0 | 0/0/0 | pass |
| 09 | 08e58eb → 07bafb3 | 0/2/0 | 0/0/0 | findings |
| 10 | 07bafb3 → 1901233 | 0/0/0 | 0/0/0 | pass |
| 11 | 1901233 → c19707c | 0/0/0 | 0/0/0 | pass |

## Code

[P1][high] Ticket 09：普通 build 无法保护自定义安装根引用的 release

位置：tools/workflow.py:553。

基线支持 install --agent-home <custom>；安装旧版后连续普通 build 两次，旧版不再是 previous，且 custom 不在固定 AGENT_STATE_HOMES 中，自动清理删除其 source。build parser 没有 --agent-home，无法传入保护；之后 verify_installed_state 和 install_release 均失败。

完整正式基线可达性和验证证据见该 Ticket 独立结果与报告。

[P1][high] Ticket 09：构建前读取的安装引用在清理时已过期

位置：tools/workflow_lib/release.py:719。

build 在 source_gate 前读取宿主 install-state；source_gate 运行期间 install 可完成，因为 install_release 只持有 state_dir/install 锁，不参与 releases mutation 锁。此后 build 用旧 referenced 集合删除刚安装的非 previous release，刚验证过的安装立即不可验证/升级。

完整正式基线可达性和验证证据见该 Ticket 独立结果与报告。


## Spec

No findings.

## 证据与边界

四份快照终检均 match，已释放。主Agent另核对09交付后至当前HEAD的 workflow.py、release.py、installer.py 零差异，两项问题仍适用于当前代码。冻结清单、原始差分、Git快照回执和终检回执保存在 independent-evidence/batch-08-11/；每张的验收覆盖、独立会话身份、验证命令和限制见独立结果。

08：48项相关测试及恢复探针；10：三宿主临时实际安装、链接和资源测试；11：33项相关测试及三宿主临时投影；09：独立全量测试、三宿主临时安装及两条失败路径的正式基线对照，详见逐张报告。未把文本与包装检查作为模型效果证据。

筛选排除了已有独立审查的01–07、15，以及已有独立修复复审覆盖的16；12–14未完成。未重新打开已完成Ticket，未改源码或外部系统。

## 逐张报告

- [Ticket 08](/Users/sherly/CS/wsp/ai/agent/my-matt-workflow/.agent/work/workflow-simplification/reviews/review-workflow-simplification-08-independent.md)
- [Ticket 09](/Users/sherly/CS/wsp/ai/agent/my-matt-workflow/.agent/work/workflow-simplification/reviews/review-workflow-simplification-09-independent.md)
- [Ticket 10](/Users/sherly/CS/wsp/ai/agent/my-matt-workflow/.agent/work/workflow-simplification/reviews/review-workflow-simplification-10-independent.md)
- [Ticket 11](/Users/sherly/CS/wsp/ai/agent/my-matt-workflow/.agent/work/workflow-simplification/reviews/review-workflow-simplification-11-independent.md)

[结构化汇总](/Users/sherly/CS/wsp/ai/agent/my-matt-workflow/.agent/work/workflow-simplification/reviews/review-batch-08-11-independent.json)
