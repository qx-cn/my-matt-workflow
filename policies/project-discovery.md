# 项目发现策略

首次初始化时检查以下证据：

- `AGENTS.md`、`CLAUDE.md`、`.cursorrules`、`.cursor/rules/**/*.mdc`、README 和贡献文档；
- Issue/PR 模板、任务引用和文档目录；
- Git remote、默认分支、测试命令和已跟踪工具目录。

发现结果只是候选证据。Tracker、文档位置、测试命令、Git 策略和补充的 standards sources 必须由用户确认一次，再保存到 `.agent/matt-workflow.md`。后续直接读取配置；但每次计划、实施或审查仍必须重新解析仓库规则的作用范围，尤其是带 glob 的 `.cursor/rules`；只有用户执行 `--refresh` 或检测到规则漂移时才重新确认配置本身。
