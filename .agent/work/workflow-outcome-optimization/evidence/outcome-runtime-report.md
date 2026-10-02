# Runtime 施工交接

源码仅在 `/tmp/my-matt-outcome-runtime` 修改。未调用本 workflow 的施工 Skill，未用 runtime 管理真实施工，未 commit、发布、安装；CLI 仅在临时 Git fixture 验证候选。

补丁 `/tmp/outcome-runtime.patch`，SHA256 `22325162cfc4a02804562e673b58f3b5542b1abf015b926d6499df3921ab7f18`。源码 SHA256 清单 `/tmp/outcome-runtime-source-manifest.json`。13 文件，新增 `tools/workflow_lib/evidence.py`；未碰共享 `tests/test_workflow.py`、`tests/test_portfolio.py`。

## AC 与行为证据

- AC01：不可执行基线下当前真实失败记录为 `new_failures` 并带 `comparison=baseline-unavailable`，同时披露比较缺口；当前通过可继续但不证明无回归。关闭时从原始结果重新比较，不信旧 `new_failures=[]`；结果/命令数不完整不得比较。现有 partial execution、Go package identity、known failure 回归保留。
- AC02：self blocking 阻 finish；Spec challenge 进入现有 `needs-user`/resolve。省略 findings 不能消解旧问题，同内容仅删/降级 blocking 被拒绝；代码/定义改变后明确新结果才能登记 resolution。history 不删除，Spec 修订 reopen 仅切换当前自审 epoch。self fix-in-batch 进入批次冻结材料及 coverage target，关闭保存对应 review resolution。
- AC03：finish 与 close 回执通过同一 serial next-action 判断；最后一张 Ticket 返回 batch test/review/close。未完成 optional whole-branch 审查返回其恢复命令，不错误建议 close；必要 reviewer/修复说明/未勾验收输入显式提示。
- AC09：位置相近和体积增长不作为根因证明或独立硬停止；真实矛盾、Spec challenge、inconclusive/design blocking、四轮预算保留。公共 CLI 修复重叠后的 pass 正常继续。
- AC18：重算原始批次失败；旧自审 history 的 missing/downgraded findings 不补零；旧几何 stop 只有当前内容/定义/快照/accepted receipt 有效 pass 才解除，保存恢复依据。完成历史没有重开；缺新执行完整性/环境记录要求重跑。混写/宿主切换说明由 README 组负责。
- AC19：`evidence.execute` 共享命令、退出码、环境、内容变化事实，Ticket/batch/quick 成功语义仍独立。batch 在执行前持久化 incomplete，崩溃不能沿用旧 success。Ticket 各命令实际内容绑定与正式 run 完整性保留，quick 在关闭内重跑并记录实际结果。冻结字节和 accepted receipt 校验共享；Ticket downstream/definition/rules、branch HEAD/definition/rules、artifact ownership/lifecycle 检查仍在各调用层。
- 配合 AC13：quick 摘要仅验证三类非空证据，兼容验收证据/验收对照/测试结果，影响与风险/影响面/对抗检查，未验证项/已知缺口；standard 原有八摘要、六自审不变。格式校验不声称证明语义充分。

## 验证

- `/tmp/outcome-runtime-red.log`：原版公共 CLI 4 项 regression 失败，分别为 baseline failure、self blocking、self challenge、last Ticket routing。
- `/tmp/outcome-runtime-final-batches.log`：23 tests，98.843s，OK。
- `/tmp/outcome-runtime-lifecycle-green2.log`：19 tests，20.787s，OK（后续仅状态输入提示与历史恢复扩展，由完整 suite 再验证）。
- `/tmp/outcome-runtime-resolution-green2.log`：13 tests，26.729s，OK（后续 history 扩展由完整 suite 再验证）。
- `/tmp/outcome-runtime-full-suite.log`：中间完整 suite 295 tests，379.943s，OK。此轮启动后补了 history 回归，不作为最终绑定证据。
- `/tmp/outcome-runtime-final-full-suite.log`：最终固定源码完整 suite：296 tests，326.110s，OK；进程退出码 0。
- compileall 与 `git diff --check` 通过，最终源码匹配上述 manifest。

## 边界

未做真实宿主迁移/安装、模型效果 A/B、生产 Bug 验证。自审与审查内容充分性仍需要语义审查，runtime 只执行可解析的证据/状态保护。本次不改变失败身份粒度、不引入通用环境缓存或状态平台。没有实现新的 legacy 全量迁移；既有独立 migration/adapter 和公开 alias 保留。
