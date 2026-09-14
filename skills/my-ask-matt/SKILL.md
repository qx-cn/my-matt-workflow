---
name: my-ask-matt
description: 判断当前情境适合哪个个人 Matt Skill 或工作流。
disable-model-invocation: true
---

# 询问 Matt

这是 portfolio 的路由索引。读取 `.agent/matt-workflow.md` 的 `composition_policy`、`assurance_level`、[开发保证等级](references/shared/adapters/assurance-levels.md)与[组合调用](references/shared/adapters/composition.md)，选出一个下一跳，输出其 `{{skill-call:...}}` 调用并停止；不要在本 Skill 内执行目标正文。源码只保留可移植宏，安装投影分别为 Cursor / Claude 与 Codex 生成宿主语法。

## 主流程

多数工程工作沿以下阶段推进：

1. 有代码库的想法用 `{{skill-call:my-grill-with-docs}}`；没有代码库用 `{{skill-call:my-grill-me}}`。两者共享内部访谈方法，需要澄清领域语言时使用 `{{skill-call:my-domain-modeling}}`。
2. 纸面讨论无法回答逻辑或界面问题时，用 `{{skill-call:my-handoff}}` 跨会话保存上下文，再用 `{{skill-call:my-prototype}}` 得出可运行证据。
3. `quick` 且通过低风险准入时，可从已确认需求摘要直接用 `{{skill-call:my-implement}}`；`standard` 先用 `{{skill-call:my-to-spec}}`，仅在多切片、跨上下文或存在依赖图时再用 `{{skill-call:my-to-tickets}}`；`audited` 依次使用 Spec、Tickets 和完整 implementation session。实施阶段统一由 `{{skill-call:my-implement}}` 在当前已批准范围内实施。明确只要求 TDD 方法教学或单独循环时可进入 `{{skill-call:my-tdd}}`。
4. 交付需要证据报告时，以 `{{skill-call:my-test-report}}` 收束需求、改动、测试与缺口。它是按需尾段，不把未执行测试写成通过。

阶段边界遵循[上下文卫生](references/policies/context-hygiene.md)。上下文接近限制时用 `{{skill-call:my-handoff}}`，在新会话继续。

## 情境入口

- 外部 Bug、需求或外部 PR 堆积：`{{skill-call:my-triage}}`。
- 难解、间歇性或回归故障：`{{skill-call:my-diagnosing-bugs}}`；若根因是缺少稳定 seam，转到 `{{skill-call:my-improve-codebase-architecture}}`。
- merge 或 rebase 冲突：`{{skill-call:my-resolving-merge-conflicts}}`。
- 答案只掌握在外部知情人手中：`{{skill-call:my-to-questionnaire}}`。
- 需要人工完成第三方配置或一次性迁移：`{{skill-call:my-wizard}}`。
- 重组或润色文章：`{{skill-call:my-edit-article}}`；只去除 AI 写作痕迹时用 `{{skill-call:my-humanizer}}`。
- 巨大且迷雾重重、超出单会话的工作：`{{skill-call:my-wayfinder}}`。地图完成后交接到 Spec，不直接跳到实现。
- 首次使用工程流程：`{{skill-call:my-setup}}`。

## 评审与维护

- 固定基线的代码审查：`{{skill-call:my-code-review}}`。
- 只判断已形成方案的逻辑、承重决策、状态和责任边界是否闭环：`{{skill-call:my-review-design}}`。
- 需要固定快照、跨质量维度检查或正式交付结论：`{{skill-call:my-review-artifact}}`；设计产物使用 `artifact_kind=design`，专项方法包括 `{{skill-call:my-reader-first-writing}}`、`{{skill-call:my-final-state-writing}}`、`{{skill-call:my-visual-communication}}`、`{{skill-call:my-humanizer}}` 和 `{{skill-call:my-artifact-finalization}}`。
- Skill 组合、职责或文本审查：`{{skill-call:my-review-skill}}`；编写方法参考 `{{skill-call:my-writing-great-skills}}`。
- 代码库健康巡检：`{{skill-call:my-improve-codebase-architecture}}`；模块形状与 seam 词汇参考 `{{skill-call:my-codebase-design}}`。

## 独立工具

- 有来源约束的阅读与综合：`{{skill-call:my-research}}`。
- 围绕有状态学习工作区学习概念：`{{skill-call:my-teach}}`。

portfolio 还明确保留三个非路由入口：`my-install` 是行政入口，`my-requirement-analysis` 与 `my-tech-design` 是仅在用户明确选择时使用的 specialist。它们不会由本路由器暗中跳转。
