# 项目发现策略

首次初始化时检查以下证据：

- `AGENTS.md`、`CLAUDE.md`、README 和贡献文档；
- Issue/PR 模板、任务引用和文档目录；
- Git remote、默认分支、测试命令和已跟踪工具目录。

发现结果只是候选证据。Tracker、文档位置、测试命令和 Git 策略必须由用户确认一次，再保存到 `.agent/matt-workflow.md`。后续直接读取配置；只有用户执行 `--refresh` 或检测到规则漂移时才重新确认。
