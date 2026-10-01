---
name: my-ask-matt
description: 判断当前情境适合哪个个人 Matt Skill 或工作流。
disable-model-invocation: true
---

# 询问 Matt

这是个人 Skill 的路由索引。读取 `.agent/matt-workflow.md` 的 `assurance_level`、[开发保证等级](references/shared/adapters/assurance-levels.md)与[组合调用](references/shared/adapters/composition.md)，选出一个下一跳，输出其 `{{skill-call:...}}` 调用并停止；不要在本 Skill 内执行目标正文。源码只保留可移植宏，安装投影分别为 Cursor / Claude 与 Codex 生成宿主语法。

## 主流程

多数工程工作沿以下阶段推进：

1. 有代码库的想法用 `{{skill-call:my-grill-with-docs}}`；没有代码库用 `{{skill-call:my-grill-me}}`。两者共享内部访谈方法，需要澄清领域语言时使用 `{{skill-call:my-domain-modeling}}`。
2. 纸面讨论无法回答逻辑或界面问题时，用 `{{skill-call:my-handoff}}` 跨会话保存上下文，再用 `{{skill-call:my-prototype}}` 得出可运行证据。
3. `quick` 且通过低风险准入时，可从已确认需求摘要直接用 `{{skill-call:my-implement}}`；`standard` 依次用 `{{skill-call:my-to-spec}}` 和 `{{skill-call:my-to-tickets}}`，合并对齐后逐张实施。实施阶段统一由 `{{skill-call:my-implement}}` 在当前已批准范围内实施。明确只要求 TDD 方法教学或单独循环时可进入 `{{skill-call:my-tdd}}`。
4. 交付需要证据报告时，以 `{{skill-call:my-test-report}}` 收束需求、改动、测试与缺口。它是按需尾段，不把未执行测试写成通过。

## 阶段边界

按顺序判断，第一个成立项就是选择；多个条件同时成立也只取首项：

1. 下一阶段需要原始上下文，或者空间还够 → 继续。
2. 上下文对后续已经没用 → 清空。
3. 要换宿主、换目录或仓库、交给同事、分出支线任务 → 交接。
4. 任务不需要人干预就能完成 → 交给子 Agent。
5. 以上都不是 → 压缩上下文，并说明要保留什么。

除继续外，其他选择都损失一部分原始信息，应说明哪些原始信息会丢失；压缩时明确保留目标、已确认决定、证据位置、未知和下一步中仍有用的内容。这里给出阶段选择，不在路由入口启动目标任务。

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
- 需要固定快照、跨质量维度检查或正式交付结论：`{{skill-call:my-review-artifact}}`；设计产物使用 `artifact_kind=design`，专项方法包括 `[共享方法](references/shared/reader-first-writing.md)`、`[共享方法](references/shared/final-state-writing.md)`、`[共享方法](references/shared/visual-communication.md)`、`{{skill-call:my-humanizer}}` 和 `[共享方法](references/shared/artifact-finalization.md)`。
- Codex、Cursor 或 Claude 项目规则的存在价值、作用域、权威与冲突审查：`{{skill-call:my-review-instructions}}`。
- Skill 组合、职责或文本审查：`{{skill-call:my-review-instructions}}`；编写方法参考 `{{skill-call:my-writing-for-agents}}`。
- 代码库健康巡检：`{{skill-call:my-improve-codebase-architecture}}`；模块形状与 seam 词汇参考 `{{skill-call:my-codebase-design}}`。

## 独立工具

- 有来源约束的阅读与综合：`{{skill-call:my-research}}`。
- 围绕有状态学习工作区学习概念：`{{skill-call:my-teach}}`。

- 安装或更新个人工作流：`{{skill-call:my-install}}`。
- 编写技术方案：`{{skill-call:my-tech-design}}`。
- 在访谈阶段执行追问方法：`{{skill-call:my-grilling}}`。
