# 工作产物访问适配

工作产物位于 `.agent/work/<topic>/<type>/`。`.agent/` 保持 Git 忽略，默认 `@` 补全不承担发现或读取这些产物的职责；需要读取时显式调用 `my-work-artifacts`，不要在 reader Skill 中复制其 CLI 用法。

写入前只确认目标 topic、type 与文件名约定；不要把临时访谈、未确认草稿或运行时策略复制进上游核心流程。
