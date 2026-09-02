# 工作产物访问适配

工作产物位于 `.agent/work/<topic>/<type>/`。`.agent/` 的归属由 `matt-workflow.md` 的 `agent_directory_mode` 决定：`private` 是个人嵌套 Git 工作区，`shared` 由主仓库跟踪；两种模式下主仓库都不应为它修改 `.gitignore`。reader Skill 直接读这些路径，不要在写入侧复制访问逻辑。

写入前只确认目标 topic、type 与文件名约定；不要把临时访谈、未确认草稿或运行时策略复制进上游核心流程。
