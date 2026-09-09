---
name: my-code-review
description: 从固定基线开始，沿 Code 与 Spec 两个顺序独立的审查 pass 检查代码变更。
disable-model-invocation: true
---

# 代码审查

只读审查用户指定的变更并返回作者会实际修复的发现；不修改文件、提交代码或发布评论。输出前按[面向读者写作](references/shared/reader-first-writing.md)确定实现者和合并决策者要据此做什么。

本 Skill 有两个输入入口：独立调用时从用户指定的固定点创建 review snapshot；作为 `my-implement` 方法时，只消费 runtime `run-review-open` 提供且 `method=my-code-review` 的只读审查单元。组合模式不得另建 snapshot、另选基线或生成第二份未绑定的审查结论。

对固定点与当前完整工作树之间的同一内容快照做两个顺序独立的审查 pass：

- **Code**——实现本身是否正确、稳健、安全、高效、兼容、可测试且易维护，并符合仓库 Standards？
- **Spec**——实现是否完整、准确地满足原始 Issue、PRD 或 Spec，且没有范围蔓延？

在同一次调用中依次完成 Code pass 与 Spec pass。第二遍重新从同一快照和必要来源建立候选，不把第一遍的候选清单或结论作为输入；这是一种顺序复核，不声称上下文隔离。完成后并列汇总。它们是一次 review 的内部方法，不是新 Skill 入口：`composition_policy` 为 `manual` 或 `automatic` 都必须在同一次调用中完成。

## 审查对象

独立调用时，用户说的固定点就是基线：Commit SHA、分支、tag、`main`、`HEAD~5` 等。若没有指定，优先使用实施开始记录的 `HEAD`。仍无法确定时，把选择审查基线分类为 `consequential`，按[指令权威与决策 Gate](references/shared/instruction-authority.md)运行 `decision-gate`：`allow` 时采用 profile 的 `default_base_branch` 并记录依据，`confirm` 时询问固定点，`pause` 时停止。组合模式直接采用审查单元中已固定的代码范围和 `code_content_id`，不运行这项基线选择。

独立调用时，用户显式指定的任何 fixed-point（包括 commit、tag、分支或其他 ref）都保持权威，不得替换。仅在用户未指定而采用默认基线分支时，若其 configured upstream 存在并领先本地分支，则以上游 ref 比较；否则使用本地分支。将解析后的 ref 交给安装状态记录的 `runtime_entry`：`review-snapshot --repo <repo> --base <fixed-point>`。记录 `resolved_fixed_point`、`merge_base`、`head`、`content_id`、`change_sources` 和 `changes`。组合模式改为验证审查单元的 `method`、`review_id`、`code_content_id` 与 artifacts，并从只读 snapshot 取证。

快照必须覆盖 committed、staged、unstaged 与 untracked 内容：以 `git diff --binary <merge_base>` 读取所有 tracked 最终内容，以 `git log <merge_base>..HEAD --oneline` 读取 Commit 上下文，并读取 `change_sources.untracked` 中每个路径的完整内容。二进制或无法直接阅读的文件记录类型、大小与可用检查结果，不得静默跳过。

两个维度必须使用同一 `content_id` 和 `changes` 路径集合。坏 ref 或 `status: empty` 在此失败；任何内容变化都要重建快照并重跑两个维度，旧 receipt 立即失效。

## 范围与来源

调用者可指定 `review_scope=change-only|touched-context`。默认 `change-only`，只报告本次变更新引入或实质放大的问题；`touched-context` 还可报告变更调用路径上直接相关的重要既有问题，但必须标记“既有/非本次引入”。无关旧问题始终不报告。

按 [项目规则解析](references/shared/adapters/project-rules.md) 发现并按实际变更路径匹配 Standards；存在 run context 时使用其中已固定的 `execution_agent`。

按以下顺序找 Spec：

1. Commit 信息中的 Issue 引用（`#123`、`Closes #45`、GitLab `!67` 等）；按项目配置的 Tracker 工作流获取；
2. 用户传入的路径；
3. 与分支或功能匹配的 `.agent/work/`、`docs/`、`specs/` 下的 PRD/Spec；
4. 若都没有，将 Spec 标记为“未评估：未找到可用 Spec”，无需确认，也不得暂停或缩减 Code 审查。

读取 `.agent/work/` 产物时遵循[工作产物访问](references/shared/adapters/artifact-access.md)。没有 Spec 时只跳过 Spec；Code 仍完整执行。

## 双遍审查

**Code pass** 从完整快照、Commit 上下文和规则地图开始。检查完整 diff 及理解变更所需的周边代码、调用方和测试；发现首个问题后继续检查全部变更。系统检查逻辑正确性、边界条件、错误处理、资源生命周期、并发与一致性、安全、性能、兼容性、测试充分性、代码设计与可维护性，同时检查仓库 Standards、Fowler code smells、函数/变量/类型命名和注释。仓库 Standards 优先；smell、命名或注释只有造成可观察风险时才报告。注释还要与代码行为一致，并按 [humanizer](references/shared/humanizer.md) 服从 `humanizer_policy`，保留简短领域用语。

**Spec pass** 重新从同一 `content_id` 的完整快照、Commit 上下文和 Spec 开始，不读取 Code pass 的候选清单或结论。先在内部把每条规范性要求映射到实现与测试证据；缺少或冲突的证据成为候选 finding，但不输出这份检查清单。由此检查遗漏、部分实现、错误行为和范围蔓延；每项引用 Spec 位置，并检查注释是否与 Spec、ADR 或相关文档一致。

高风险变更按实际风险加深对应检查；低风险变更不为并行而增加 reviewer。

## Finding 准入与归类

候选问题只有同时满足以下条件才进入报告：

- 对正确性、安全、性能、兼容性或可维护性有实质影响，或构成明确需求偏差；
- 是离散、可行动且位于 `review_scope` 内的问题；
- 失败场景、调用路径或违反的不变量能由代码、测试、命令结果或 Spec 证明；
- 不是猜测、无影响的 style nit、工具已覆盖事项或明确的有意行为；
- 作者知道后大概率会修复。

`change-only` finding 还必须证明失败场景能从 review unit 的正式 `base_sha` 到当前快照到达；不得把同一未提交工作树的中间 schema、临时迁移或已被替换的施工状态当作受支持来源。无法证明正式基线可达时降为 `inconclusive`，不下 blocker 结论。

严重度使用 `P0`（安全越权、数据丢失或破坏、不可恢复故障或核心路径普遍失败）、`P1`（合并前应修复的真实 Bug 或需求偏差）、`P2`（值得修复的局部缺陷或维护/测试风险）；P0/P1 是 blocker。置信度只用 `high` / `medium`，低置信度候选不进入 findings；仅当证据缺口影响合并判断时，才在结尾写简短 residual risk。

双遍审查完成后按主要原因归类：没有 Spec 也成立的实现或工程问题归 Code；必须依据 Spec 才成立的遗漏、错误需求行为或范围蔓延归 Spec。同一失败链只保留最接近根因的一项，另一维不重复。

## 输出

报告开头写 `Review-Snapshot: <content_id>`、基线、`head` 和 `Review-Scope: <scope>`。只固定输出 `## Code` 与 `## Spec`；无内容的注释、命名或统计子节不生成。每维按严重度再按位置排列 findings：

```text
## Code
[P1][high] 可行动标题 — path/to/file:line
一个短段落，包含失败场景或不变量、证据、影响及最小验证方式。

## Spec
[P1][medium] 可行动标题 — path/to/file:line
一个短段落，包含失败场景或不变量、Spec 证据、影响及最小验证方式。
```

无合格发现写 `No findings.`；无 Spec 写“未评估：未找到可用 Spec”，不伪造通过结论或 P0/P1/P2 零计数。作为 `my-implement` 方法时，同时返回 runtime 要求的结构化条目：稳定 `id`、根因、severity、摘要与正式基线可达性；证据不足项使用 `inconclusive`。最后用一行汇总：Code 始终列出 P0/P1/P2 数量与 blocker；Spec 已评估时列出对应数量与 blocker，未评估时只写状态。只在必要时追加 residual risk。不要复述审查过程、输出逐项通过清单、无影响建议、重复证据、完整命令流水或未经请求的修复代码。不得为缩短报告而截断通过准入的真实发现。
