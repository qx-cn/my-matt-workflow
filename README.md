# my-matt-workflow v2

四个自包含 Skill、一份个人通用规则、一个软链同步脚本。

| Skill | 什么时候用 | 调用方式 |
| --- | --- | --- |
| my-grill | 澄清目标、范围、术语和设计决定 | 手动 |
| my-to-spec | 把已有讨论、PRD 和代码事实整理成 Spec | 手动 |
| my-tech-design | 写技术方案或发布文档（飞书云文档或本地 HTML） | 手动 |
| my-review | 审查代码改动或文档，按必须修和建议分级报告 | 手动或 Agent 自动调用 |

## 怎么用

Cursor 和 Claude Code 用 `/my-grill`，Codex 用 `$my-grill`。产物放在 `.agent/work/<主题>/`。

- 小改动、范围清楚：直接让 Agent 做，不调用 Skill。
- 需求不清楚或改动面大：
  1. 用 my-grill 问清需求，决定写进 `decided.md`。
  2. 需要书面方案时，用 my-to-spec 写 `spec.md`。
  3. 开一个新会话，让 Agent "按 `.agent/work/<主题>/spec.md` 实施"。
  4. 改动涉及存量数据、并发、对外契约、鉴权与权限、敏感数据或发布回滚时，Agent 会调用 my-review；没调用时可以手动调用。只处理"必须修"，"建议"自己决定。
- 已有 PRD：直接用 my-to-spec；PRD 有含糊处，先用 my-grill。
- 方案评审或上线准备：用 my-tech-design 写技术方案或发布文档（会先询问输出到飞书还是本地 HTML），可用 my-review 审文档。
- 审自己或别人的分支：用 my-review，可以指定基准分支。
- 交付时 Agent 提议往仓库 AGENTS.md 加条目：看过再同意。

不要每个任务都把四个 Skill 串一遍；不要让 Agent 反复修"建议"；Spec 只保留一份，改动原因写进 `decided.md`。

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
全局规则软链到 `~/.claude/CLAUDE.md` 和 `${CODEX_HOME:-~/.codex}/AGENTS.md`。
迁移前先运行 `scripts/sync.sh --migrate-v1 --dry-run` 查看将删除的内容。

Cursor 不读取软链过去的全局规则，`~/.cursor/rules` 也不是官方的用户规则位置。Cursor 改用个人规则（Customize → Rules → User）中名为'个人通用规则'的一条，内容与 `rules/global.md` 一致。`global.md` 修改后，在 Cursor 里让 Agent 用个人规则接口更新这一条，或手动粘贴。

只在 [global.md](rules/global.md) 列出的四种情况下提议往仓库 AGENTS.md 加规则：同一错误第二次出现、评审发现本该知道的仓库知识、同一纠正说了第二遍、新同事也需要知道。确认后再写。

查旧版内容：`git show 16c03b5:<路径>`。
