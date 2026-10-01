---
name: my-to-spec
description: 在 my-grill-with-docs、my-wayfinder 流程中作为指定阶段的工作单元被调用。
---

遵循[指令权威](references/shared/instruction-authority.md)。

# 整理 Spec

从已确认需求和代码库事实整理版本化 Spec，不重新访谈。不为 Spec 分配执行 Agent。先读取[最终态写作](references/shared/final-state-writing.md)、[项目规则解析](references/shared/adapters/project-rules.md)与既有 ADR；找用户按[共同条件](references/shared/user-intervention.md)。

首次分配 spec_id/revision1；修订递增 revision，用 supersedes 指前版，每版新增 Topic 内文件，阅读全文比较有效行为并记修订索引。Topic Spec 是实施边界，不读取或发布长期 Spec。承重决定用[第一性原理推理](references/shared/first-principles-reasoning.md)连接目标、事实、机制、真实替代与可证伪验收；可逆实现细节留给实施。

写清目标、范围、行为、不变量、验证策略及影响结果的未知。必要时调用 {{skill-call:my-review-design}}，遵循[审查循环](references/shared/review-loop.md)。来源与事实按[产物最终校验](references/shared/artifact-finalization.md)核对，承重未知保持可定位，不润色成确定结论。

按[产物存储](references/shared/adapters/artifact-storage.md)保存 Topic specs，再直接调用 {{skill-call:my-to-tickets}}。Spec 与逐 Ticket 行为、依赖、测试命令和边界合并呈现对齐点2；用户确认前不实施，确认后由 to-tickets 直接继续 implement。

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

每项承重决策还应引用它服务的目标或验收，说明可定位的事实与约束、采用机制、被排除的最小替代方案，以及什么观察会推翻该选择、由哪项验证捕获。没有真实替代成本时省略替代方案，不为模板完整制造内容。

例外：若原型产出了比文字更精确地编码决策的片段（状态机、reducer、schema、类型形状），可内嵌到相应决策，并简要说明来自原型。只保留含决策的信息，不要粘贴可运行 demo。

## 验证策略

说明需要证明什么、可复用的现有 seam 与证据类型。新增 seam 仅在必要时描述，不锁死具体测试代码。

- 什么构成好测试（只测试外部行为，而非实现）；
- 将测试哪些模块；
- 测试的先例（即代码库内相似测试）。

## 依据与未知

只列会影响目标、范围、接口、数据语义、验收或风险的来源、假设与未知；可定位到用户确认、仓库材料、外部一手来源或实际执行证据。无承重未知时明确写“无”。

## 补充说明

与该功能有关的其他说明。

## 本次修订索引（仅修订版）

这是评审与影响分析的导航，不增加、覆盖或恢复规范正文中的要求。按外部可观察行为列出本次新增、修改、移除项；每项指向本版最终条款或说明其已移除，标明前版依据及受影响验收。没有行为变化时只写“无外部行为变化”，不造空表。索引只引用旧版，不重复已废止的旧要求；迁移、兼容或安全边界确需保留的旧状态应写入规范正文的相应位置。后续 Ticket 影响映射仍由 `my-to-tickets` 负责。

</spec-template>
