---
name: my-review-artifact
description: 对一个固定版本的交付产物做综合只读审查，合并适用质量维度并输出有证据、低重复的 findings。
disable-model-invocation: true
---

遵循[审查循环](references/shared/review-loop.md)，包括独立性、覆盖、建议归属、修复与停止；需用户处理时按[找用户的条件](references/shared/user-intervention.md)。

# 综合审查产物

审查 runtime 提供的固定 `review_unit`，并把结论连同其 `content_id` 交回 runtime 验证。快照生命周期、过期检查和执行调度由 runtime 管理；本 Skill 只决定审查什么以及哪些问题值得报告。开始与交付遵循 [artifact review session](references/shared/adapters/artifact-review-session.md)。

打开审查单元时按产物用途声明 `artifact_kind=general|design`；只有技术方案、架构说明或设计文档使用 `design`。类型一经进入 `review_unit` 就保持固定，不由审查发现反向改写。

## 选择审查维度

先明确产物的目标读者、用途和承重决策，再只采用真正适用的方法：

- 最终交付物：[final-state-writing](references/shared/final-state-writing.md)
- 读者需要据此理解或行动：[reader-first-writing](references/shared/reader-first-writing.md)
- 复杂关系、流程或状态需要视觉表达：[visual-communication](references/shared/visual-communication.md)
- 面向人的成篇文本：[自然表达](references/shared/humanizer.md)
- 承重交付物需要来源、完整性与发布前检查：[artifact-finalization](references/shared/artifact-finalization.md)
- `review_unit.artifact_kind` 为 `design`：{{skill-call:my-review-design}}

逐项处理 `review_unit.required_checks`：适用时审查，不适用时标记 `not-applicable` 并给出简短理由；不要为了覆盖规则而制造 finding。多个维度指向同一根因时合并为一个 finding，并保留最能说明影响的证据。

## Finding 门槛

每个 finding 必须：

- 能定位到 `review_unit` 中的具体内容；
- 说明被违反的要求、对读者或决策的实际影响；
- 给出足以指导修订的最小方向，而不是替作者重写整份产物；
- 重要到作者知道后大概率会修复。

设计审查必须有承重断言核验表、审查发现、已考察但排除的风险、待用户确认的需求语义假设四部分，并在提交中附 design_report；缺节或“与现状不符”未关联发现不得将 review-design 记 pass。发现挑战/未决语义假设在下一个现有对齐点交用户，不自行裁决。

缺少必要证据时标记 `inconclusive`，不得伪造通过；普通偏好和无影响的风格建议不进入 findings。

## 输出

按影响排序输出去重后的 findings，并附 `content_id`。每个 required check 都必须闭合为 `pass`、`finding`、`inconclusive` 或 `not-applicable`；未全部闭合时不得输出 `No findings.`。没有达到门槛的问题时输出 `No findings.`；存在 `inconclusive` 时单独列出，不能用它代替确定结论。
