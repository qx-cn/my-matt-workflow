---
name: my-final-state-writing
description: 审查、撰写或修订文档，使正文只保留当前有效状态。
disable-model-invocation: true
---

# 最终态写作

用于只读审查、撰写或修订交付文档、设计说明、实施计划、报告和用户可见的总结，使正文准确反映当前已确认的状态。

撰写前先按[面向读者写作](references/shared/reader-first-writing.md)确定人类读者的决定或动作，再阅读并遵循[最终态写作规则](references/shared/final-state-writing.md)。该共享规则是唯一权威来源；不要在本 Skill 或产物中重复维护规则文本。若产物将进入实施、评审或跨会话交接，写入前再执行[产物最终校验](references/shared/artifact-finalization.md)。

## Review 模式

用户要求 review、检查或审查已有产物时，只读评审，不修改或重写原文。逐项核对正文中的目标、设计、约束和待确认项是否仍是当前有效状态；只有旧状态影响迁移、兼容、回滚、安全边界或 ADR 取舍时才允许保留。

只报告有明确文本依据的问题，并给出位置、违反的规则、对读者决定或后续实施的影响，以及最小修订方向；同一过期决定造成的多个表象合并为一项。没有合格发现时写 `No findings.`。
