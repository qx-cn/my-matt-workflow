# my-matt-workflow v2

四个自包含 Skill、一份个人通用规则、一个软链同步脚本。

| Skill | 用途 | 调用方式 |
| --- | --- | --- |
| `my-grill` | 澄清目标、范围、术语和设计决定 | 手动 |
| `my-to-spec` | 把已有讨论、PRD 和代码事实整理成 Spec | 手动 |
| `my-tech-design` | 写技术方案或发布文档（飞书云文档或本地 HTML） | 手动 |
| `my-review` | 审查代码改动或文档，按“必须修”和“建议”分级报告 | 手动或 Agent 自动调用 |

## 使用方式

Cursor 和 Claude Code 用 `/my-grill`，Codex 用 `$my-grill`。外部参考、决定、Spec 和本地 HTML 方案分别放在 `.agent/work/<主题>/` 下的 `refs/`、`decided.md`、`spec.md` 和 `design.html`；含内部信息的 `refs/` 仅留本地（已由 `.gitignore` 忽略，不提交外部同步源）。

- **小改动、范围清楚**：直接让 Agent 做，不调用 Skill。
- **需求不清楚或改动面大**：
  1. 用 `my-grill` 问清需求，外部参考文档归档至 `refs/`，决定写进 `decided.md`。
  2. 需要书面方案时，用 `my-to-spec` 写 `spec.md`。
  3. 开一个新会话，让 Agent “按 `.agent/work/<主题>/spec.md` 实施”。
  4. 改动涉及存量数据、并发与锁、对外契约、鉴权与权限、敏感数据或发布回滚兼容时，Agent 会调用 `my-review`；未调用时可手动调用。只处理“必须修”，“建议”自己决定。
- **已有 PRD**：直接用 `my-to-spec`；PRD 有含糊处，先用 `my-grill`。
- **方案评审或上线准备**：用 `my-tech-design` 写技术方案或发布文档（会先询问输出到飞书还是本地 HTML），可用 `my-review` 审文档。若前序访谈或排查会话较长，建议新开会话或由 Skill 派干净上下文的子 Agent 基于需求/PRD 或已有的 `.agent/work/<主题>/spec.md`、`decided.md`、`refs/` 生成初稿，避免长对话噪音稀释排版与表达规则。
- **审自己或别人的分支**：用 `my-review`，可指定基准分支。
- **沉淀仓库知识**：Agent 只在 [global.md](rules/global.md) 列出的四种情况下提议往仓库 `AGENTS.md` 加条目（同一错误第二次出现、评审发现本该知道的仓库知识、同一纠正说了第二遍、新同事也需要知道），看过确认后再写。

日常使用注意以下边界：

- **按需选用**：不把四个 Skill 机械串跑一遍。
- **控制审查范围**：不让 Agent 反复修“建议”。
- **保留工程结构**：不对工程 Spec 或技术方案调用通用 `humanizer`（会抹平加粗列表并增加丢约束风险）。
- **单文件维护 Spec**：`spec.md` 只保留一份原地更新；业务或方案改动原因记入 `decided.md`（被推翻的旧决定标 `[已废止，见 YYYY-MM-DD]`，纯文字微调不记）。

## 安装与同步

同步脚本需要 Bash、Python 3 和 Git，按机器状态执行首次安装或迁移：

- **全新机器首次安装**：克隆本仓库后在仓库根目录运行 `./scripts/sync.sh` 建立软链，再运行 `./scripts/sync.sh --check` 校验。
- **曾安装过 v1 的机器首次迁移**：在本仓库先运行 `./scripts/sync.sh --migrate-v1 --dry-run` 预览将删除的旧文件，确认后运行 `./scripts/sync.sh --migrate-v1` 与 `./scripts/sync.sh --check`。

`my-tech-design` 输出本地 HTML 时仅依赖 Python 3（运行 `check_html.py`）；输出**飞书云文档与内嵌画板**时，依赖宿主机已安装并登录飞书开放平台工具链：

- **外部 Skill**：`lark-doc`、`lark-whiteboard`、`lark-wiki`、`lark-shared`
- **外部 CLI**：`lark-cli`（需已完成 `lark-cli auth login`）与 Node.js `@larksuite/whiteboard-cli`（用于将画板 JSON DSL 编译为飞书原生画板节点）

日常升级与同步约定如下：

- **常规升级**：只需 `git pull`；增删或重命名 Skill 时再跑一次 `./scripts/sync.sh`（`--dry-run` 打印动作，`--check` 只读检查并在异常时返回非零状态）。
- **软链目标**：Skill 软链到 `~/.agents/skills/` 和 `~/.claude/skills/`；全局规则软链到 `~/.claude/CLAUDE.md` 和 `${CODEX_HOME:-~/.codex}/AGENTS.md`。
- **Cursor 个人规则**：Cursor 不读取软链过去的全局规则，`~/.cursor/rules` 也不是官方用户规则位置。Cursor 改用个人规则（Customize → Rules → User）中名为“个人通用规则”的一条，内容与 `rules/global.md` 一致；修改 `rules/global.md` 后在 Cursor 里通过个人规则接口更新或手动粘贴。
- **历史基线**：查 v1 旧版内容用 `git show 16c03b5:<路径>`。
