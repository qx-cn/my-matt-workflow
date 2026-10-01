# 项目个人存储策略

默认个人目录为 `<repo>/.agent/`：

- `matt-workflow.md`：项目配置；
- `work/<topic>/<type>/`：所有本地工作产物；文件名使用 `<type>-<topic>-<time-or-sequence>.<extension>`。
- `CONTEXT.md`：项目术语；`adr/NNNN-<slug>.md`：难以撤回的决定，不按 Topic 分片。
- `work/<topic>/handoffs/`：交接；由 `my-handoff` 只新增、不覆盖历史文件。
- `work/<topic>/prototypes/`、`researches/`、`learning/` 与 `architecture-reports/`：隔离原型、研究、项目学习、离线架构报告。

非项目交接写入系统临时目录。非项目学习内容写入安装配置指定的个人学习目录；未配置时使用当前工作目录。

`.agent/` 的 Git 归属由 `matt-workflow.md` 的 `agent_directory_mode` 决定：默认 `private` 使用无 remote 的嵌套 Git，主仓库不跟踪它；`shared` 由主仓库跟踪，随主仓库的远端推送。两种模式下，工作流都不得修改主仓库的忽略规则。
