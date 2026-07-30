# diagnosing-bugs audit evidence

## Pinned source and file accounting

- Pinned commit: `2ab958093e83e0ec752e6c1c5932da465bf23e0c`
- Canonical source path: `skills/engineering/diagnosing-bugs`
- Local counterpart: `skills/my-diagnosing-bugs`

| File | Source SHA-256 | Local SHA-256 |
| --- | --- | --- |
| `SKILL.md` | `7a0779480f323a66d109404646bcc1a14bf0232b45b3e3ea93b652a035718acb` | `e32fe1da4a59a7e39c79d3cad1ed974b1c44b0fe633940eaaa90a763e9166402` |
| `agents/openai.yaml` | `3e430dbe4334a87597488c060cb3dc3786bb00c9182877d6f5ec41f62490e90b` | `aeffa835f10b859e8a77d73d632c6c133f0123377302ff722204b84a047e7ce8` |
| `scripts/hitl-loop.template.sh` | `b2932630950e5210075bcd6f850e5accf30c101c5367b29eac3a29b4dd8084c8` | `b23d8dfc8c25bdd98f199252f20ed89d5bb946eaef2397b42c3f60c648781eb6` |

## Section/source-local mapping

The audited source sections and their local counterparts are:

| Pinned upstream section | Local counterpart |
| --- | --- |
| `SKILL.md#Diagnosing Bugs` | `SKILL.md#My Diagnosing Bugs` |
| `SKILL.md#Phase 1 — Build a feedback loop` | `SKILL.md#阶段 1 —— 建立反馈循环` |
| `SKILL.md#Ways to construct one — try them in roughly this order` | `SKILL.md#构造方式——大致按以下顺序尝试` |
| `SKILL.md#Tighten the loop` | `SKILL.md#收紧循环` |
| `SKILL.md#Non-deterministic bugs` | `SKILL.md#非确定性 Bug` |
| `SKILL.md#When you genuinely cannot build a loop` | `SKILL.md#确实无法建立循环时` |
| `SKILL.md#Completion criterion — a tight loop that goes red` | `SKILL.md#完成条件——能变红的紧凑循环` |
| `SKILL.md#Phase 2 — Reproduce + minimise` | `SKILL.md#阶段 2 —— 复现并最小化` |
| `SKILL.md#Minimise` | `SKILL.md#最小化` |
| `SKILL.md#Phase 3 — Hypothesise` | `SKILL.md#阶段 3 —— 提出假设` |
| `SKILL.md#Phase 4 — Instrument` | `SKILL.md#阶段 4 —— 埋点` |
| `SKILL.md#Phase 5 — Fix + regression test` | `SKILL.md#阶段 5 —— 修复与回归测试` |
| `SKILL.md#Phase 6 — Cleanup + post-mortem` | `SKILL.md#阶段 6 —— 清理与复盘` |
| `agents/openai.yaml#interface` | `agents/openai.yaml#interface` |
| `scripts/hitl-loop.template.sh#Human-in-the-loop reproduction loop.` | `scripts/hitl-loop.template.sh#人在回路的复现循环。` |
| `scripts/hitl-loop.template.sh#Copy this file, edit the steps below, and run it.` | `scripts/hitl-loop.template.sh#复制本文件、编辑以下步骤，然后运行。` |
| `scripts/hitl-loop.template.sh#The agent runs the script; the user follows prompts in their terminal.` | `scripts/hitl-loop.template.sh#Agent 运行脚本；用户在终端中遵循提示操作。` |
| `scripts/hitl-loop.template.sh## Usage:` | `scripts/hitl-loop.template.sh## 用法：` |
| `scripts/hitl-loop.template.sh#bash hitl-loop.template.sh` | `scripts/hitl-loop.template.sh#bash hitl-loop.template.sh` |
| `scripts/hitl-loop.template.sh## Two helpers:` | `scripts/hitl-loop.template.sh## 两个辅助函数：` |
| `scripts/hitl-loop.template.sh#step "<instruction>"          → show instruction, wait for Enter` | `scripts/hitl-loop.template.sh#step "<instruction>"          → 显示说明，等待 Enter` |
| `scripts/hitl-loop.template.sh#capture VAR "<question>"      → show question, read response into VAR` | `scripts/hitl-loop.template.sh#capture VAR "<question>"      → 显示问题，将响应读入 VAR` |
| `scripts/hitl-loop.template.sh## At the end, captured values are printed as KEY=VALUE for the agent to parse.` | `scripts/hitl-loop.template.sh## 最后会以 KEY=VALUE 输出捕获值，供 Agent 解析。` |
| `scripts/hitl-loop.template.sh#--- edit below ---------------------------------------------------------` | `scripts/hitl-loop.template.sh#--- 在下方编辑 ---------------------------------------------------------` |
| `scripts/hitl-loop.template.sh#--- edit above ---------------------------------------------------------` | `scripts/hitl-loop.template.sh#--- 在上方编辑 ---------------------------------------------------------` |

The source body was compared section-by-section, including examples, ordering, constraints, stop conditions, frontmatter/runtime metadata, and all listed support files. Metadata interface fields are accounted for separately from local policy metadata.

## Delta, allowed adaptation, and conclusion

- Allowed local adaptation: a renamed manual-invocation Skill may retain repository-specific metadata only when it does not alter the upstream method.
- Material delta: The local autonomous limited-evidence mode permits work after the upstream hard no-loop stop condition, so the adapter must be bounded.
- Conclusion: **adapter-rework-required**.
- Exact follow-up queue: **Plan 2 — `my-diagnosing-bugs` adapter rework**; this audit does not restore or refactor the Skill.

## Retrieval/application scenario

`tests/fixtures/task_12_application.json` defines `diagnosing-bugs-application`. It retrieves `SKILL.md#确实无法建立循环时`, verifies `没有紧凑、可变红的命令，就不得进入常规假设阶段` within that exact heading, and independently derives `stop-before-hypothesis` only when the retrieved constraint is present.
