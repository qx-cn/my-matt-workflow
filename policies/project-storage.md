# 项目个人存储策略

默认个人目录为 `<repo>/.agent/`：

- `matt-workflow.md`：项目配置；
- `work/<topic>/<type>/`：所有本地工作产物；文件名使用 `<type>-<topic>-<time-or-sequence>.<extension>`。
- `work/<topic>/handoffs/`：交接；由 `my-handoff` 只新增、不覆盖历史文件。
- `work/<topic>/prototypes/`、`researches/`、`learning/`、`domain/` 与 `architecture-reports/`：隔离原型、研究、项目学习、个人术语/ADR 候选和离线架构报告。

非项目交接写入系统临时目录。非项目学习内容写入安装配置指定的个人学习目录；未配置时使用当前工作目录。

`.agent/` 应被 Git 忽略。Agent 配置目录可能包含团队文件，工作流不得把它们加入仓库的忽略规则。
