# 主工作流隔离行为 Smoke

- 日期：2026-09-05
- 用例：`evals/agent-smokes/main-workflow-fresh-context.md`
- release：`workflow-opt-validation-layers-v1`
- 隔离仓库：`/tmp/my-matt-fresh-smoke.cKVppt`
- 基线：`1953a83f3d2156e6c261779307c936a063bd853f`
- 结果提交：`ecc71b64ad367df98290a3a16c6386df4e1d83e9`
- 执行身份：独立评估代理 `Lovelace` 生成 Spec、Ticket、实现、测试和测试报告；模型标识未由宿主暴露。该代理因账户用量上限在最终审查/提交前中断，由主代理完成收口。
- 证据定性：主链行为用例通过；完整的“独立代理端到端通过”未获得，状态为 `inconclusive`，不得把本记录写成这一更强结论。

## 结果

| Rubric | 结果 | 证据 |
| --- | --- | --- |
| 版本化 Spec | 通过 | `spec_id: normalized-greeting-cli`、`revision: 1`、`supersedes:`、`status: current`。 |
| Ticket 血缘与准入 | 通过 | Ticket 含 `spec_id/spec_revision/spec_ref`；`validate-ticket` 在 ready 状态通过，实施状态迁移 gate 允许完成。 |
| 实现与实际测试 | 通过 | `python3 -m unittest -v` 退出 0，6 个测试全部 `ok`。 |
| 完整工作树 review | 通过 | 提交前快照含 2 个 unstaged 代码文件与 4 个 untracked 工作产物，不依赖 `HEAD`。 |
| 证据型测试报告 | 通过 | 报告分别说明需求、实际执行、未测试项、结论与证据边界。 |
| 最终工件与限制 | 通过 | Spec、Ticket、测试报告路径完整；本记录明确独立评估中断与未覆盖访谈质量。 |

## 关键原始证据

实际测试输出：

```text
Ran 6 tests in 0.061s

OK
```

提交前最终快照：

```json
{"status":"ready","content_id":"3722b267e5ef0eedd9659e442a2647964a69239049c911b179d51804effb7dfe","change_sources":{"committed":[],"staged":[],"unstaged":["app.py","test_app.py"],"untracked":[".agent/matt-workflow.md",".agent/work/normalized-greeting/specs/specs-normalized-greeting-01.md",".agent/work/normalized-greeting/tests/test-report.md",".agent/work/normalized-greeting/tickets/tickets-normalized-greeting-01.md"]}}
```

提交后等价性：

```json
{"status":"match","clean":true,"content_id":"3722b267e5ef0eedd9659e442a2647964a69239049c911b179d51804effb7dfe","head":"ecc71b64ad367df98290a3a16c6386df4e1d83e9"}
```

单 Ticket 收口：

```json
{"reason":"single-ticket","status":"complete"}
```

## 观测到的失败与修复

独立代理最初使用普通 YAML 块列表生成 Ticket，runtime 报错：

```text
无效 Ticket 配置行：  - requirements.md
```

代理改成行内列表后继续工作。源树随后为 `frontmatter()` 增加块列表支持并补回归测试；这属于 smoke 直接发现的兼容性问题。

## 证据边界与清理状态

- 交互式 `my-grill-with-docs` 由已确认的 `requirements.md` 替代，本用例不评价访谈质量。
- 这不是用户真实业务项目 smoke，不证明对大型仓库、外部 Tracker 或多 Ticket 计划的效果。
- 独立代理未返回最终自然语言答复；其落盘工件保留为原始输出，主代理只完成验收勾选、最终审查记录、状态完成与提交等价性验证。
- 隔离仓库暂不清理，便于复核；所有写入均位于上述 `/tmp` 目录。
