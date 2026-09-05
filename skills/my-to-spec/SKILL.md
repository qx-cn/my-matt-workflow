---
name: my-to-spec
description: 将当前对话整理为 Spec，并按项目配置保存或发布；不重新访谈，只综合已有讨论。
disable-model-invocation: true
---

本 Skill 从当前对话上下文和对代码库的理解中产出 Spec（也可称 PRD）。**不要重新访谈用户**；先按[最终态写作](references/shared/final-state-writing.md)收束当前有效内容。

读取 `.agent/matt-workflow.md`；其中定义任务后端、文档来源、外部写入确认策略与生效的 `humanizer_policy`。配置不存在时先运行 `/my-setup`。写入团队文档或外部 Tracker 前遵循[写操作 Gate](references/shared/adapters/write-actions.md)。

## 过程

1. 确定 Spec 血缘。首次产出分配稳定的 `spec_id` 与 `revision: 1`；修订时沿用 `spec_id`、递增 `revision`，并让 `supersedes` 指向上一版。每版新建文件，不覆盖历史版本；正文只写当前有效状态。

2. 若尚未探索，先探索仓库以理解当前代码状态。整个 Spec 使用项目领域术语，并遵守所触及区域的 ADR。输出前按 [项目规则解析](references/shared/adapters/project-rules.md) 为 `execution_agent` 解析规则；每个承重实施决策必须给出影响区域、规则、约束和验证。普通、可逆的实现细节留给实施阶段。

3. 从已确认讨论中提取目标、范围外、外部可观察行为、不变量、验收标准和未知。用户故事只在角色差异会改变行为或验收时使用，不为“全面”而枚举同义场景。

4. 描述验证策略：优先复用现有测试 seam，并选择能证明外部行为的最高层验证。只有新增 seam 会改变架构、公开接口或测试投入时才作为承重决定交给用户；不要预设全项目必须收敛为一个 seam。

5. 使用下列模板撰写 Spec。

6. **写入前最终校验**：按[产物最终校验](references/shared/artifact-finalization.md)依次通过来源账本、内部一致性、读者重建和事实正确性 gate。承重未知或矛盾未解除时不写入、不发布；本 Skill 不重新访谈，只报告需要回到上游确认的具体缺口。四项通过后，再按 [humanizer](references/shared/humanizer.md) 服从 `humanizer_policy`；润色若改变事实、结论或未知，重新校验。

7. **写入**：根据 `task_backend` 保存：
   - `local`：写入 `.agent/work/<feature-slug>/specs/specs-<feature-slug>-<time-or-sequence>.md`；
   - `project-docs`：先展示补丁，确认后写入配置的项目文档位置；
   - `external`：先展示完整预览，确认后发布到配置的 Tracker；
   - `none`：只在当前会话输出。

   对 external 后端，只有项目配置允许并在本次得到明确确认后，才添加项目配置的 agent-ready 标签；不得猜测 `ready-for-agent` 等标签名称。

<spec-template>

```yaml
---
spec_id: <稳定 feature id>
revision: <正整数>
supersedes: <上一版路径、URL 或空>
status: current
---
```

## 问题陈述

从用户视角描述其面对的问题。

## 目标结果

从用户视角描述完成后能观察到的结果，以及如何判断目标达成。

## 范围边界

列出范围内与范围外。只保留能阻止误实现的边界。

## 行为与验收

按风险列出外部可观察行为及其验收标准。角色差异确实改变行为时，可使用简短用户故事；否则直接描述行为。

## 不变量与失败边界

列出正常流程、失败路径、状态变化、数据或兼容性不能被破坏的条件。无相关风险时省略。

## 已确认的承重决策

只列会改变架构、公开接口、数据语义、兼容方式、测试投入或风险承担的已确认决定。普通可逆实现细节不进入 Spec。

- 要构建或修改的模块；
- 要修改的模块接口；
- 开发者做出的技术澄清；
- 架构决策；
- Schema 变更；
- API 契约；
- 具体交互。

**不要**写具体文件路径或代码片段；它们很快会过期。

每项决策应说明适用规则和影响区域；影响区域可使用模块、目录或 glob，不将具体文件路径写成不可变承诺。

例外：若原型产出了比文字更精确地编码决策的片段（状态机、reducer、schema、类型形状），可内嵌到相应决策，并简要说明来自原型。只保留含决策的信息，不要粘贴可运行 demo。

## 验证策略

说明需要证明什么、可复用的现有 seam 与证据类型。新增 seam 仅在必要时描述，不锁死具体测试代码。

- 什么构成好测试（只测试外部行为，而非实现）；
- 将测试哪些模块；
- 测试的先例（即代码库内相似测试）。

## 执行环境

- execution_agent：
- 未解决规则冲突：

## 依据与未知

只列会影响目标、范围、接口、数据语义、验收或风险的来源、假设与未知；可定位到用户确认、仓库材料、外部一手来源或实际执行证据。无承重未知时明确写“无”。

## 补充说明

与该功能有关的其他说明。

</spec-template>
