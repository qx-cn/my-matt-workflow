---
name: my-resolving-merge-conflicts
description: 在用户批准的前提下，安全审阅并解决进行中的 Git merge 或 rebase 冲突
disable-model-invocation: true
---

# 安全解决冲突

用于正在进行的 merge 或 rebase 冲突。批准前不得修改冲突文件、暂存、提交或 push；批准、可执行操作和固定禁止项遵循 [Merge 冲突批准](references/policies/merge-conflict-approval.md)。

1. 读取 `git status`、冲突文件、相关提交、PR/Issue 或本地 Ticket，说明每一方变更的原始意图。
2. 按 hunk 给出解决方案：保留哪些意图、不能兼容时选择什么、对应权衡、验证计划与可执行回滚路径。不得凭空增加行为。
3. 取得明确批准后，按已批准方案执行、验证并报告证据和回滚方式；出现新的不确定性时停止并重新说明。
