# 项目规则解析适配

规则解析以当前计划或 Ticket 的 `execution_agent` 为输入；优先级是本次显式指定、项目 `default_execution_agent`、安装状态的 `installed_agent`。三者都无法确定时停止，不得混读多个 Agent 的专属规则。

共享规范来自 `AGENTS.md`、`AGENTS.override.md`、贡献规范、编码规范与相关 ADR。跨 Agent 的强制约束应只维护在 `AGENTS.md`；Agent 专属文件只放该 Agent 的触发方式或专属能力。

使用 `python3 tools/workflow.py resolve-rules --repo <repo> --agent <codex|cursor|claude> --path <影响路径>` 获取规则证据。解析器只读取该目标 Agent 的专属来源：

- `codex`：共享规范与 Codex 的 `AGENTS*` 指令；
- `cursor`：共享规范、`.cursorrules`、`.cursor/rules/**/*.mdc`；
- `claude`：共享规范、`CLAUDE.md`、`.claude/CLAUDE.md`、`.claude/rules/**/*.md`。

Cursor 规则必须按原生语义处理：`alwaysApply: true` 全局适用；`globs` 只匹配目标路径；只有 `description` 的规则需要相关性判断；无三者的规则仅在显式手动引用时适用。Claude 的 `paths` 规则也只在匹配路径时适用。

## 计划输出

访谈结束、Spec 或 Ticket 输出前解析规则。计划顶部只记录执行 Agent 与未解决冲突数；不要写冗长规则综述。每个计划项固定写四项：

- **影响区域**：模块、目录或 glob；
- **规则**：来源及匹配依据；
- **约束**：由规则推出的可执行设计或测试要求；
- **验证**：证明该项满足约束的测试、检查或人工验证。

相关规则未读取、存在未解决冲突，或计划项缺少上述四项时，不得生成 `ready-for-agent` Ticket。

## 实施与审查

开始每个 Ticket 前，按真实将修改的路径重新执行 `resolve-rules`，再运行 `python3 tools/workflow.py validate-ticket <ticket-path>`。新规则若改变架构、接口、范围或验收，回到计划确认；审查发现必须引用规则来源与匹配依据。
