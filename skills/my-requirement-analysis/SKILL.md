---
name: my-requirement-analysis
description: 在复杂或显式请求时验证 AI 对用户需求的理解，并在制定 Plan 前识别偏差、遗漏和关键歧义。
disable-model-invocation: true
---

# Requirement Analysis

仅在用户明确调用 `{{skill-call:my-requirement-analysis}}`，或当前请求复杂、隐含、类比驱动并由[开发保证等级](references/shared/adapters/assurance-levels.md)要求增强需求核对时运行；这不意味着每次都要启动独立 reviewer。普通 grill 已产生可追溯需求摘要时，不重复完整访谈。它验证“理解是否正确”，不评判方案优劣。

先形成主 Agent 摘要：目标、范围、用户明确约束和可观察验收标准。每一项都标出来自用户原文、仓库事实还是尚未确认的推断。

## 快速通过

简单请求若目标、范围、约束和验收都能逐项直接对应用户原文，且没有会改变结果的第二种合理理解，记录 `PASS` 并进入 Plan。不要为了启动 reviewer 而扩大简单请求。

## 独立审查

只有复杂、隐含、类比驱动，或确有会改变结果的第二种合理理解时，才读取[独立需求 Reviewer Brief](references/reviewer-brief.md)，让一个未参与主摘要的 reviewer 独立对比原始输入与摘要。Reviewer 可读取用户点名的最小仓库上下文，但不能看到主 Agent 的疑点或预期答案。

没有 sub-agent 能力时，主 Agent 仍完成四维自检并继续，但必须把结果标记为 `independence evidence gap`；不得把串行自审写成独立审查。

## 处理结果

- `PASS`：保留确认后的摘要，进入 Plan。
- `NEEDS_CLARIFICATION`：只向用户提出会改变目标、范围、约束或验收的最小问题，收到回答后更新摘要。
- `MISUNDERSTANDING`：按证据修正摘要；目标或范围发生实质变化时再做一次独立审查，否则记录修正后进入 Plan。

完成条件：最终摘要的四类信息均可追溯；未解决的承重歧义已交给用户；独立性证据的实际状态被如实记录。
