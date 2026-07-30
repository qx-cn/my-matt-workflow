---
name: my-implement
description: 根据 Spec 或一组 Ticket 实施工作。
disable-model-invocation: true
---

实施用户在 Spec 或 Ticket 中描述的工作。

读取 `.agent/matt-workflow.md`、完整 Spec/Ticket 与仓库规则，记录开始时的 `HEAD`。始终遵守已批准 Spec/Ticket 的范围，不凭空扩展需求或做无关重构；但是否在当前 Ticket 后继续由已解析的 `work_scope_policy` 决定：`single-ticket` 在当前 Ticket 完成后停止；`ready-frontier` 可持续领取所有阻塞者已完成的 Ticket；`approved-plan` 可按依赖顺序完成同一已批准计划的所有 Ticket。用户说「继续 / 提交并继续」只表示在当前已生效策略下推进，不升档、不改写 `composition_policy` / `work_scope_policy` / `decision_policy`，也不等于放宽为全自动连做。

只有同时满足以下条件的 Ticket 才能进入实施：`ticket_kind: implementation`、`status: ready-for-agent`、所有 `blocked_by` 已完成、至少一条可验证验收标准，且不带任何 `wayfinder:*` 标记。`ticket_kind: wayfinder-decision` 或带 `wayfinder:*` 的 Ticket 永不进入实施；未解决的产品决定属于用户专属决定，`decision_policy: autonomous` 也不得代答。缺少类型的旧 Ticket 不自动猜测，按 `decision_policy` 请求确认、停止，或只在既有模板与明确状态能得出唯一结论时补记。

用户指定的 Ticket 不满足准入时，立即停止并说明具体不满足项；不得静默改选其他 Ticket。只有用户明确确认改选后，才可从可实施集合中按确定性顺序选择另一张。

在预先约定的 seam 上执行 TDD：

- `composition_policy: automatic` 时，进入 TDD 阶段才读取并遵守 [my-tdd](references/composed/my-tdd/SKILL.md)；
- `manual` 时，输出下一条显式调用并停止：Cursor / Claude 使用 `/my-tdd`，Codex 使用 `$my-tdd`。

定期运行类型检查和单个测试文件；结束时运行一次完整测试套件。

完成后执行代码审查：`automatic` 时到达 review 阶段才读取并遵守 [my-code-review](references/composed/my-code-review/SKILL.md)；`manual` 时输出下一条显式调用并停止，Cursor / Claude 使用 `/my-code-review`，Codex 使用 `$my-code-review`。审查必须覆盖 Standards 与 Spec 两个独立轴。

按项目的 `branch_policy`、`commit_policy`、`external_write_policy` 处理分支、提交、Push 和 PR/MR。`confirm` 时，展示最终 diff 与测试证据并取得本次明确确认；`allow` 时可在验证通过后自动执行；`deny` 时不得执行。`decision_policy: autonomous` 时记录每项自行判断及证据；`ask` 时询问，`halt` 时停止。

> 项目策略优先：读取 `.agent/matt-workflow.md` 的已解析生效策略；缺键或空值按 `strict-control`。本 Skill 中要求询问、确认、停止或限制后续工作的表述，除绝对安全底线外，均服从该生效策略。绝对安全底线始终不变：不得 Force Push、改写 Git 历史、执行破坏性 Git 操作，或向外部服务发送敏感信息。
