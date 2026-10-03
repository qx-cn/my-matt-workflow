---
name: my-code-review
description: 在 my-implement 流程中作为指定阶段的方法被调用。
---

遵循[审查循环](references/shared/review-loop.md)，包括独立性、覆盖、建议归属、修复与停止；需用户处理时按[找用户的条件](references/shared/user-intervention.md)。

遵循[指令权威](references/shared/instruction-authority.md)。

# 代码审查

只读审查用户指定的变更并返回作者会实际修复的发现；不修改文件、提交代码或发布评论。输出前按[面向读者写作](references/shared/reader-first-writing.md)确定实现者和合并决策者要据此做什么。

本 Skill 有两个输入入口：独立调用时从用户指定的固定点创建 review snapshot；作为 `my-implement` 方法时，只消费 runtime batch review、按需 implement review 或 topic review 提供的只读材料包。组合模式不得另建 snapshot、另选基线或生成第二份未绑定的审查结论。

## 审查对象

独立调用时，用户说的固定点就是基线：Commit SHA、分支、tag、`main`、`HEAD~5` 等。若没有指定，优先使用实施开始记录的 `HEAD`。仍无法确定时使用配置的 default_base_branch 并记录依据；会改变目标范围的分歧依共同确认条件处理。组合模式直接采用审查单元中已固定的代码范围和 `content_id`，不运行这项基线选择。

独立调用时，用户显式指定的任何 fixed-point（包括 commit、tag、分支或其他 ref）都保持权威，不得替换。仅在用户未指定而采用默认基线分支时，若其 configured upstream 存在并领先本地分支，则以上游 ref 比较；否则使用本地分支。将解析后的 ref 交给安装状态记录的 `runtime_entry`：`review-snapshot --repo <repo> --base <fixed-point>`。记录 `resolved_fixed_point`、`merge_base`、`head`、`content_id`、`change_sources` 和 `changes`。组合模式改为验证审查单元的 `unit_id`、`content_id`、`acceptance`、`probes`、`downstream_tickets` 与冻结材料，并从只读 snapshot 取证。

快照必须覆盖 committed、staged、unstaged 与 untracked 内容：以 `git diff --binary <merge_base>` 读取所有 tracked 最终内容，以 `git log <merge_base>..HEAD --oneline` 读取 Commit 上下文，并读取 `change_sources.untracked` 中每个路径的完整内容。父仓未跟踪的嵌套 Git 工作树会在 receipt 中展开为逐文件路径，包括没有 HEAD 的 private workspace；只读取这些展开路径，不把目录占位或嵌套仓 HEAD 当成文件内容。二进制或无法直接阅读的文件记录类型、大小与可用检查结果，不得静默跳过。

全部视角必须使用同一 `content_id` 和 `changes` 路径集合。坏 ref 或 `status: empty` 在此失败；任何内容变化都要重建快照，旧 receipt 立即失效。复审范围遵循共享审查循环。

## 范围与来源

调用者可指定 `review_scope=change-only|touched-context`。默认 `touched-context`，报告本次引入、放大及直接调用路径上相关的重要既有问题；`change-only` 只报告本次引入或实质放大的问题，但必须标记“既有/非本次引入”。无关旧问题始终不报告。

按 [项目规则解析](references/shared/adapters/project-rules.md) 发现并按实际变更路径匹配 Standards；存在 run context 时使用其中已固定的 `execution_agent`。

按以下顺序找 Spec：

1. Commit 信息中的 Issue 引用（`#123`、`Closes #45`、GitLab `!67` 等）；按项目配置的 Tracker 工作流获取；
2. 用户传入的路径；
3. 与分支或功能匹配的 `.agent/work/`、`docs/`、`specs/` 下的 PRD/Spec；
4. 若都没有，将 Spec 标记为“未评估：未找到可用 Spec”，无需确认，也不得暂停或缩减 Code 审查。

读取 `.agent/work/` 产物时遵循[工作产物访问](references/shared/adapters/artifact-access.md)。没有 Spec 时标明 spec 未评估，其他视角仍完整执行。

## 五个视角

审查者按风险组织一次审查，不要求固定两遍仪式。第一轮穷尽固定范围，读取完整仓库的调用方、消费者、测试与项目规则；复审范围遵循共享规则。

- correctness：逻辑、边界、错误处理、资源生命周期、并发、一致性、安全与性能。
- impact：必查影响面。独立寻找改动契约的调用方与消费者，检查存量数据、发布和回滚期间新旧版本并存、锁与配置键、权限、性能及跨 Ticket 集成与遗留代码。实施者声明与理由不能替代核实或降低严重度。
- spec：验收映射到代码与测试，输出每条验收覆盖。覆盖只是本视角的一部分，不是发现准入门槛。
- spec-challenge：修复必须改变已确认目标、外部行为、验收语义、明确限制或风险承诺的产品挑战。技术事实错误、实现漏项归普通 spec/correctness，作者直接修复与同步定义；不得以“Spec 要求如此”为由放行可达故障，已决事项不凭偏好重开。
- maintainability：项目分层、命名、重复实现、推测性代码与测试质量；只报告有实质影响或违反项目规则的问题。

## Finding 准入与归类

候选问题只有同时满足以下条件才进入报告：

- 对正确性、安全、性能、兼容性或可维护性有实质影响，或构成明确需求偏差；
- 是离散、可行动且位于 `review_scope` 内的问题；
- 失败场景、调用路径或违反的不变量能由代码、测试、命令结果或 Spec 证明；
- 不是猜测、无影响的 style nit、工具已覆盖事项或明确的有意行为；
- 作者知道后大概率会修复。

`change-only` finding 还必须证明失败场景能从 review unit 的正式 `base_sha` 到当前快照到达；不得把同一未提交工作树的中间 schema、临时迁移或已被替换的施工状态当作受支持来源。无法证明正式基线可达时降为 `inconclusive`，不下 blocker 结论。

严重度使用 `P0`（安全越权、数据丢失或破坏、不可恢复故障或核心路径普遍失败）、`P1`（合并前应修复的真实 Bug 或需求偏差）、`P2`（值得修复的局部缺陷或维护/测试风险）；P0/P1 是 blocker，映射为结果骨架的 blocking；P2 映射为 advisory。置信度只用 `high` / `medium`，低置信度候选不进入 findings；仅当证据缺口影响合并判断时，才在结尾写简短 residual risk。

同一失败链保留最接近根因的一项，标注主要视角。每条发现给出位置（文件与行区间或可定位契约）、视角、依据（正式基线可达路径或明确规则）和 blocking/advisory 严重度。无需验收编号；有编号可以保留 anchor。advisory 必须选择 fix-in-batch、defer（建议归属）或 decline（理由）。当前可达故障不能因为后续 Ticket 的归属降为建议。

## 输出

独立调用报告 content_id、基线、HEAD、范围，按五个视角组织发现，并附验收覆盖。既有问题标注“既有/非本次引入”；无合格发现写“无发现”，无 Spec 写“未评估：未找到可用 Spec”。每条发现用具体失败场景说明证据、影响和验证方式，不报猜测与纯风格意见。组合模式使用 runtime 预填骨架，不手改身份或内容字段，如实记录模型、来源与独立性缺口。spec-challenge 用平实中文说明用户需要决定什么。不得截断真实发现。
