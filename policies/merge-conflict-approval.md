# Merge 冲突批准

冲突解决先只读诊断：识别每一方原始意图、逐个 hunk 的候选方案、权衡、验证计划与回滚路径。未经用户对该方案的明确批准，不得编辑冲突文件、暂存、提交、continue、abort 或 push。

获批后只执行可回滚、未 push 的本地解决步骤；出现新的不确定性立即停止并重新说明。commit 仍受 `commit_policy` 控制，push 仍需独立授权。始终禁止 Force Push、改写历史、`git reset --hard`、`git clean` 及自动 merge/rebase abort。
