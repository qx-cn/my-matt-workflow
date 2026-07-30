---
name: my-doctor
description: 检查 Matt 上游 Skills 是否发生影响个人工作流的变化
disable-model-invocation: true
---

# My Doctor

日常上游漂移检查运行 `python3 tools/workflow.py doctor`；需要审阅未采用上游 Skill 的候选时，运行 `python3 tools/workflow.py doctor --recommend`（或单独运行 `python3 tools/workflow.py recommend`）。

- 退出码 `0`：已适配的上游 Skills 未变化，简短报告兼容。
- 退出码 `2`：展示变化文件和受影响的 `my-*` Skills。
- 只暂停受影响流程；不阻止无关 Skills 使用。
- `--recommend` 不改变退出码：即使存在推荐项，退出码仍为 `0`；它按 `recommend`、`consider`、`covered`、`defer` 分类展示通用性、建议的 `my-*` 名称和本地化注意事项。
- 不自动修改个人 Skill，不自动更新上游基线，也不自动采纳推荐。

若用户确认要处理已采用 Skill 的变化或审阅候选，且当前已批准流程包含同步阶段：`composition_policy: automatic` 时读取并遵守 [my-sync](references/composed/my-sync/SKILL.md)；`manual` 时输出下一条显式调用并停止，Cursor / Claude 使用 `/my-sync`，Codex 使用 `$my-sync`。当前流程未批准同步时只建议，不扩展范围；推荐仅在用户逐项明确决定采用后，才进入迁移工作。

> 项目策略优先：读取 `.agent/matt-workflow.md` 的已解析生效策略；缺键或空值按 `strict-control`。本 Skill 中要求询问、确认、停止或限制后续工作的表述，除绝对安全底线外，均服从该生效策略。绝对安全底线始终不变：不得 Force Push、改写 Git 历史、执行破坏性 Git 操作，或向外部服务发送敏感信息。
