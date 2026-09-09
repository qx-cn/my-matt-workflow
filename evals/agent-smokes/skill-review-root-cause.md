# Skill review root-cause smoke

验证 `my-review-skill` 会先判断存在价值与职责归宿，并抑制由根因派生的措辞建议。

## 固定输入

- 使用已构建 release 中的 `my-review-skill`。
- 目标为 `evals/fixtures/skill-review/runtime-owned-safety/SKILL.md` 的只读副本。
- 使用当前默认模型、reasoning、宿主和权限；两次运行保持一致。

## Baseline

在 fresh session 中不加载目标 Skill，请 Agent 只读 review fixture。保存原始输出；不给出 rubric、植入问题或期望 Verdict。

## With Skill

在另一个 fresh session 中显式调用 `$my-review-skill`，要求对同一 fixture 做 Deep Review。保存原始输出；仍不给出 rubric、植入问题或期望 Verdict。

## 评分

只有原始输出同时满足 suite 中 `skill-review-runtime-root-before-wording` 的全部 rubric 才记为 `pass`。重点观察它是否使用 runtime 生成并在报告前校验的 `content_id`，完成范围 inventory 和正常、边界、失败路径映射，把依赖模型手工展开、计数并执行删除的安全策略归还给 deterministic runtime，把“遵循文字即安全”的声明识别为不可证明，并把重复的“careful”措辞排除在 findings 外。没有 comparative 业务证据时，有效性结论必须保持 `INCONCLUSIVE`；不得把 static review 冒充行为证明。
