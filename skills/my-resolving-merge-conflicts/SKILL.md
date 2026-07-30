---
name: my-resolving-merge-conflicts
description: 在用户批准的前提下，安全审阅并解决进行中的 Git merge 或 rebase 冲突
disable-model-invocation: true
---

# 安全解决冲突

用于正在进行的 merge 或 rebase 冲突。先诊断与说明，**批准前不得修改冲突文件、暂存、提交或 push**。

1. 读取 `git status`、冲突文件、相关提交、PR/Issue 或本地 Ticket，说明每一方变更的原始意图。
2. 按 hunk 给出解决方案：保留哪些意图、不能兼容时选择什么、对应权衡、验证计划与可执行回滚路径。不得凭空增加行为。
3. 等待用户明确批准该方案。用户可随时中止；批准前只能进行只读检查。
4. 批准后，逐项应用未 push 且可回滚的本地解决步骤，运行项目类型检查、测试与格式化。发现新的不确定性时停止并重新说明。
5. 仅在项目 `commit_policy` 允许时完成 merge/rebase 所需的 commit 或 continue；未经确认不得 push。

始终禁止 Force Push、改写 Git 历史、`git reset --hard`、`git clean`、自动 `merge --abort` 或 `rebase --abort` 等破坏性操作。完成时报告已解决项、验证证据和回滚方式。

> 项目策略优先：读取 `.agent/matt-workflow.md` 的已解析生效策略；缺键或空值按 `strict-control`。本 Skill 中要求询问、确认、停止或限制后续工作的表述，除绝对安全底线外，均服从该生效策略。绝对安全底线始终不变：不得 Force Push、改写 Git 历史、执行破坏性 Git 操作，或向外部服务发送敏感信息。
