# R1/R3 状态修复接管核对

已完成，无 push/install。接管后核对旧作者现有实现，未改生产文件；新增一条 R3 过期 pass 不释放几何停止的 CLI 回归。

R1：活动 batch 汇总旧 complete Ticket 的 blocking/spec-challenge，普通 pass 不能消解；blocking 必须有点名 target 的实际 batch repair、当前测试与审查；challenge 必须点名 accept 或定义修订 reopen。mixed accept 不能一并豁免未修 correctness。close 记录 resolution 后，已发起可选整分支审查的 manifest 按同 content_id 下已关闭 batch 的处置过滤，因此 topic complete 能继续。合法处置保留原 Ticket implementation 历史字节。

R3：status 与 load 共用 effective_state；只有当前有效 pass 才解除旧几何停止，缺失或过期 pass 保持阻断，恢复依据被保存。

验证：
- /tmp/outcome-state-sol-tests.log：7 CLI 用例通过，28.279s。
- /tmp/outcome-state-sol-stale-pass.log：新增过期 pass 回归通过，3.684s。合计 8 个当前状态回归用例。
- /tmp/outcome-state-sol-legacy-cli.log：5 个恢复用例通过，21.855s，其中4个使用真实旧基线 CLI 创建 blocking/challenge/mixed 历史，第5个是额外 optional branch review fixture。
- /tmp/outcome-state-sol-geometry.log：真实旧基线 CLI 触发 needs-user 几何停止，候选 status 输出 topic complete，建议命令执行 exit 0，最终 complete。

公开 CLI 仅在临时合成项目验证程序合同；合成 review pass 不是业务正确性或独立生产审查证据。未跑完整 suite；主 Agent 在集成冻结后负责。未改 compare 区域，R2作者可继续改该区。

文件 SHA256（交付时当前快照；batches.py 仍可能被R2作者修改，主Agent须最终重算）：
- tools/workflow_lib/batches.py: `59c662248ff16742d469a08e55416faf9c16cfe75b12f31127d39bf3a8af57c5`
- tools/workflow_lib/branch_review.py: `12d4fc4c11f05ac5c3312442a4840408fd0b5163a2b37216cad7f9eb19527382`
- tools/workflow_lib/topic_service.py: `393e1a62a998d28f42a2b5075170da922f4c43db766bc2e21f1e5048861a6fb8`
- tests/test_holistic_state_repairs.py: `e4b82e59dd432dd821c10e4e1178d98187203e4a50db677c2a1f86aa23d72834`
