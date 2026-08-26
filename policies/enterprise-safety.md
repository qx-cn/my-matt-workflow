# 企业安全策略

1. 仓库内的 `AGENTS.md`、`CLAUDE.md`、贡献文档和已跟踪配置始终优先。
2. 不把企业源码、内部地址、凭据、用户身份或未公开业务信息写入同步源。
3. 不修改 Matt 原生 Skills；`my-*` Skills 在运行时也不加载对应原生 Skill。
4. 团队文件和外部系统的写操作必须遵守项目配置中的确认策略。
5. 未获项目 `external_write_policy: allow` 且不在本次已批准范围内时，不自动 Push；无论策略为何均不改写 Git 历史、不 Force Push、不执行破坏性 Git 操作。
