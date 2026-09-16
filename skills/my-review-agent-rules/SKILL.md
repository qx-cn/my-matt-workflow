---
name: my-review-agent-rules
description: 对项目中的 Codex、Cursor 与 Claude Agent 指令做根本性只读审查；检查存在价值、宿主作用域、权威冲突、归宿和可执行性。
disable-model-invocation: true
---

# 根本性审查 Agent 项目规则

只读审查项目级 Agent 指令，不修改规则，也不把“优化现有文字”预设为答案。普通代码、设计产物和 Skill 分别交给对应 review；个人全局规则只有在用户明确指定时才作为外部证据纳入。

## 选择模式

- **Rule Set Survey**：用户给出仓库或规则目录时，分别对 `codex`、`cursor`、`claude` 运行 inventory，盘点 Codex `AGENTS*`、Cursor `.cursorrules` 与 `.cursor/rules/**/*.mdc`、Claude `CLAUDE.md` 与 `.claude/rules/**/*.md`，以及会约束它们的共享标准。按源路径去重，但保留每个宿主的作用域关系。只报告集合级根因并给出 Deep Review 队列，不替每条规则下 Verdict。
- **Deep Review**：用户给出单条规则或紧密耦合规则组时，审查目标以及会改变其行为的上级、下级、共享标准、引用材料、重叠规则和确定性机制。

Survey 只有在每个范围内规则源恰好进入一次 inventory，且其宿主、激活方式、声明作用域、覆盖关系与证据缺口均已记录时才是 `COMPLETE`。每个 Deep Review 候选必须有可定位的影响路径；否则 Survey 为 `INCONCLUSIVE`。

## Deep Review

### 1. 固定审查对象

先按[项目规则解析](references/shared/adapters/project-rules.md)确定目标宿主。运行 `python3 <runtime_entry> inspect-rules --repo <repo> --agent <agent>`；有目标路径时逐项传入 `--path`。inventory 结果负责发现候选，不替代语义判断。多个目标路径分别检查适用性，不能把其中一个路径上的 `selected` 当作所有路径都生效。

把目标、所有重叠或有 precedence 关系的规则、引用材料和相关确定性机制按[专项只读审查会话](references/shared/adapters/specialized-review-session.md)固定为一个 snapshot。完成条件：每个已解析行为依赖恰好映射到一个 snapshot 条目，或逐项标为 Evidence Gap。

### 2. 重建 Rule Contract

从真实请求、目标路径、规则消费者和行为证据重建：“在 X 情境中，该规则改变 Agent 的 Y 决定，从而产生 Z 可观察结果。”规则正文只是证据之一。无法建立契约时形成契约缺失 finding，不进入措辞审查。

### 3. 判断存在价值与归宿

对承重规则应用[第一性原理推理](references/shared/first-principles-reasoning.md)，依次检验：强 Agent 默认能力是否足够；内容是否只是知识参考；是否与另一规则重复；要求能否由 script、schema、CI 或 runtime 机械强制；是否确实属于 Agent 项目指令。主要机制必须能解释用户价值，每项承重职责只能有一个合理归宿。

Deep Review Verdict：

- `KEEP`：目标、归宿、作用域和机制成立，没有实质 finding。
- `TARGETED_FIX`：仍属于当前归宿，只需局部修复作用域、行为或文字。
- `REDESIGN`：目标成立，但规则机制或耦合结构需要根本重做。
- `MERGE`：与其他规则职责重复，应合并到一个权威来源。
- `RELOCATE`：仍是 Agent 指令，但宿主、目录或 precedence 层错误。
- `EXTERNALIZE`：内容是知识或参考，不应作为行为指令加载。
- `REPLACE_WITH_RUNTIME`：要求应由 script、schema、CI 或 runtime 机械强制。
- `RETIRE`：规则过时、无增量行为或净影响有害。
- `INCONCLUSIVE`：证据缺口会实质改变上述归宿判断。

每种候选 Verdict 都要有接受或排除依据。

### 4. 检查宿主适用性与权威

按[指令权威](references/shared/instruction-authority.md)消解冲突，不把项目规则当成授权来源：

- Cursor 的 `alwaysApply` 与合法 `globs` 可机械判断；`description` 必须记录相关性依据；无三种激活字段的是 `manual`，只有显式引用时适用；无效 metadata 不得静默丢弃。
- Codex 必须区分 `selected`、`shadowed` 与 `candidate`，并按目录 precedence 判断目标路径。
- Claude 的合法 `paths` 可机械判断；有效且无 `paths` 的规则为 always；无效 frontmatter 不得退化为 always。
- `target_match: null` 表示需要语义判断或显式引用，不表示适用，也不表示不适用。

完成条件：目标规则的每种激活方式、覆盖边和权威冲突都已闭合为事实、finding 或会限制 Verdict 的 Evidence Gap。

### 5. 走查并分级证据

至少走查一个目标路径、非目标路径、冲突路径和失败路径。每个实际分支都映射到 case 与证据等级，或标为 Evidence Gap；未映射路径阻止受影响的 Verdict。

- **static**：由文本、宿主语义或依赖推出；
- **observed**：有真实运行或失败记录；
- **comparative**：相同模型、reasoning、请求、snapshot 和权限下比较 baseline、当前规则与必要时的候选修订。

只有 comparative 能证明规则相对 baseline 的行为增益。只有观察证据冲突，或增值争议会实质改变 Verdict 时，才能说明争议命题、影响、最小案例与成本，并在用户明确授权后运行 comparative。

### 6. 最后检查指令设计

只有存在性 Gate 得出 `KEEP` 或 `TARGETED_FIX` 时，才逐句检查相关性、无效操作、重复、冲突、过度限定、不可执行要求和模糊完成条件。其他 Verdict 抑制会随归宿变化而消失的措辞建议。

## Finding Gate 与输出

finding 必须同时满足：存在可证明的失败路径或不变量；影响调用、作用域、权限、正确性、完成度或维护成本；位于固定审查单元内；指向可行动根因；不是普通偏好、无影响 style nit 或工具已可靠处理的问题；作者知道后大概率会修改。

按 `FOUNDATIONAL`、`APPLICABILITY`、`BEHAVIORAL`、`INSTRUCTIONAL` 分类。同一失败链只保留最接近根因的一项；存在 `FOUNDATIONAL` finding 时抑制派生的作用域和措辞建议。

按专项审查会话验证 snapshot 后再报告。Deep Review 先写 `Review-Unit`、`Target-Host`、`Evidence-Level` 与一个 Verdict；每个 finding 说明根因、失败路径、证据、影响和最小干预方向。Survey 只写 `COMPLETE | INCONCLUSIVE`、集合级 findings 和 Deep Review 队列。没有合格 finding 写 `No findings.`，不得把 static 通过写成行为有效。
