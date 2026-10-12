# my-matt-workflow v2

四个自包含 Skill、一份个人通用规则、一个软链同步脚本。

| Skill | 什么时候用 | 调用方式 |
| --- | --- | --- |
| my-grill | 澄清目标、范围、术语和设计决定 | 手动 |
| my-to-spec | 把已有讨论、PRD 和代码事实整理成 Spec | 手动 |
| my-tech-design | 写供工程师判断方案是否成立的 HTML 技术方案 | 手动 |
| my-review | 审查代码改动或文档，按必须修和建议分级报告 | 手动或 Agent 自动调用 |

决定、Spec 和 HTML 方案分别放在 `.agent/work/<主题>/decided.md`、`spec.md` 和 `design.html`。

每台机器首次迁移，在本仓库运行（需要 Bash、Python 3 和 Git）：

```bash
git pull
scripts/sync.sh --migrate-v1
scripts/sync.sh --check
```

以后升级只需 `git pull`；增删 Skill 时再跑一次 `scripts/sync.sh`。
`--dry-run` 打印动作，`--check` 只读检查，有问题时返回非零状态。

Skill 软链到 `~/.agents/skills/` 和 `~/.claude/skills/`。
全局规则软链到 `~/.cursor/rules/my-global.mdc`、`~/.claude/CLAUDE.md` 和 `${CODEX_HOME:-~/.codex}/AGENTS.md`。
迁移前先运行 `scripts/sync.sh --migrate-v1 --dry-run` 查看将删除的内容。

只在 [global.md](rules/global.md) 列出的四种情况下提议往仓库 AGENTS.md 加规则：同一错误第二次出现、评审发现本该知道的仓库知识、同一纠正说了第二遍、新同事也需要知道。确认后再写。

查旧版内容：`git show 16c03b5:<路径>`。
