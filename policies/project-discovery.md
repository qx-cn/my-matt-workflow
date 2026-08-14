# 项目发现策略

首次初始化时检查以下证据：

- `AGENTS.md`、README、贡献文档，以及目标 execution agent 的原生规则；
- Issue/PR 模板、任务引用和文档目录；
- Git remote、默认分支、测试命令和已跟踪工具目录。

发现结果只是候选证据。Tracker、文档位置、测试命令、Git 策略、默认 execution agent 和补充的 standards sources 必须由用户确认一次，再保存到 `.agent/matt-workflow.md`。后续直接读取配置；但每次计划、实施或审查仍必须按目标 Agent 与实际路径重新解析规则作用范围；只有用户执行 `--refresh` 或检测到规则漂移时才重新确认配置本身。
