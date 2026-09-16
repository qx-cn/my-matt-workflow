# Agent rule review scope and authority smoke

验证 `my-review-agent-rules` 会先判断规则的存在价值、归宿、宿主作用域与权威，再检查措辞。

## 固定输入

- 使用已构建 release 中的 `my-review-agent-rules`。
- 目标为 `evals/fixtures/agent-rule-review/project/` 的只读副本。
- 使用当前默认模型、reasoning、宿主和权限；baseline 与 with-Skill 保持一致。

## Baseline

在 fresh session 中不加载目标 Skill，请 Agent 只读 review fixture 中的项目规则。保存原始输出；不给出 rubric、植入问题或期望 Verdict。

## With Skill

在另一个 fresh session 中显式调用 `$my-review-agent-rules`，对同一 fixture 做 Deep Review。保存原始输出；仍不给出 rubric、植入问题或期望 Verdict。

## 评分

只有原始输出同时满足 suite 中 `agent-rule-scope-and-authority` 的全部 rubric 才记为 `pass`。重点观察它是否固定审查单元，完整盘点 always、glob、manual 与 invalid 规则，区分目标路径和非目标路径，报告高权威冲突，把可机械执行的安全策略交还 runtime，并在报告前验证 snapshot。没有 comparative 证据时不得声称规则相对 baseline 有效。
