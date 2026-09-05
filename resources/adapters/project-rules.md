# 项目规则解析适配

规则的权力边界与冲突处理遵循[指令权威](../instruction-authority.md)。

规则解析以当前计划或 Ticket 的 `execution_agent` 为输入；优先级是本次显式指定、项目 `default_execution_agent`、安装状态的 `installed_agent`。三者都无法确定时停止，不得混读多个 Agent 的专属规则。

共享标准来自贡献规范、编码规范与相关 ADR。跨 Agent 约束若维护在 `AGENTS.md`，非 Codex Agent 只能把它作为 workflow 约定读取；这不改变各宿主自身的原生规则发现方式。

先从当前 Agent 的 `my-matt-workflow/install-state.json` 读取绝对路径 `runtime_entry`：Codex 状态根为 `${CODEX_HOME:-~/.codex}`，Cursor 为 `~/.cursor`，Claude 为 `~/.claude`；自定义安装则使用安装时指定的 Agent 根目录。使用 `python3 <runtime_entry> resolve-rules --repo <repo> --agent <codex|cursor|claude> --path <影响路径>` 获取规则证据。不得假设当前项目中存在本工作流仓库的 `tools/`。解析器只读取该目标 Agent 的来源：

- `codex`：贡献/编码标准，以及从仓库根到每个影响路径父目录的原生 `AGENTS*` 指令；每层只选择首个非空的 `AGENTS.override.md`、`AGENTS.md` 或已配置 fallback，越靠近影响路径的规则 `precedence_index` 越大；自定义 fallback 以 `--codex-fallback <文件名>` 传入；
- `cursor`：`AGENTS.md` 跨 Agent 约定、贡献/编码标准、`.cursorrules`、`.cursor/rules/**/*.mdc`；
- `claude`：`AGENTS.md` 跨 Agent 约定、贡献/编码标准、`CLAUDE.md`、`.claude/CLAUDE.md`、`.claude/rules/**/*.md`。

`.agent/rules/**/*` 不是 Codex 原生项目指令，不得把它冒充 `AGENTS.md` 证据。个人全局 `~/.codex/AGENTS*` 只属于当前运行环境，不写入可共享 Ticket。

Cursor 规则必须按原生语义处理：`alwaysApply: true` 全局适用；`globs` 只匹配目标路径；只有 `description` 的规则需要相关性判断；无三者的规则仅在显式手动引用时适用。Claude 的 `paths` 规则也只在匹配路径时适用。

## 计划输出

访谈结束、Spec 或 Ticket 输出前解析规则。计划顶部只记录执行 Agent 与未解决冲突数；不要写冗长规则综述。每个计划项固定写四项：

- **影响区域**：模块、目录或 glob；
- **规则**：来源及匹配依据；
- **约束**：由规则推出的可执行设计或测试要求；
- **验证**：证明该项满足约束的测试、检查或人工验证。

相关规则未读取、存在未解决冲突，或计划项缺少上述四项时，不得生成 `ready-for-agent` Ticket。

## 实施与审查

开始每个 Ticket 前，按真实将修改的路径重新执行 `resolve-rules`，再运行 `python3 <runtime_entry> validate-ticket <ticket-path>`。新规则若改变架构、接口、范围或验收，回到计划确认；审查发现必须引用规则来源与匹配依据。
