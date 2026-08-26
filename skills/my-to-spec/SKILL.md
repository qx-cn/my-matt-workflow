---
name: my-to-spec
description: 将当前对话整理为 Spec，并按项目配置保存或发布；不重新访谈，只综合已有讨论。
disable-model-invocation: true
---

本 Skill 从当前对话上下文和对代码库的理解中产出 Spec（也可称 PRD）。**不要重新访谈用户**；先按[最终态写作](references/shared/final-state-writing.md)收束当前有效内容。

读取 `.agent/matt-workflow.md`；其中定义任务后端、文档来源、外部写入确认策略与生效的 `humanizer_policy`。配置不存在时先运行 `/my-setup`。写入团队文档或外部 Tracker 前遵循[写操作 Gate](references/shared/adapters/write-actions.md)。

## 过程

1. 若尚未探索，先探索仓库以理解当前代码状态。整个 Spec 使用项目领域术语，并遵守所触及区域的 ADR。输出前按 [项目规则解析](references/shared/adapters/project-rules.md) 为 `execution_agent` 解析规则；每个实施决策必须给出影响区域、规则、约束和验证。

2. 勾勒将用于测试该功能的 seam。优先复用现有 seam，使用尽可能高的 seam；必须新增时，也应在可行的最高层提出。整个代码库的 seam 越少越好，理想数量是一个。

   与用户确认这些 seam 是否符合预期。

3. 使用下列模板撰写 Spec。

4. **写入前**：按 [humanizer](references/shared/humanizer.md) 服从 `humanizer_policy`，再根据 `task_backend` 保存：
   - `local`：写入 `.agent/work/<feature-slug>/specs/specs-<feature-slug>-<time-or-sequence>.md`；
   - `project-docs`：先展示补丁，确认后写入配置的项目文档位置；
   - `external`：先展示完整预览，确认后发布到配置的 Tracker；
   - `none`：只在当前会话输出。

   对 external 后端，只有项目配置允许并在本次得到明确确认后，才添加项目配置的 agent-ready 标签；不得猜测 `ready-for-agent` 等标签名称。

<spec-template>

## 问题陈述

从用户视角描述其面对的问题。

## 解决方案

从用户视角描述解决该问题的方案。

## 用户故事

写一份**很长、带编号**的用户故事清单。每个故事使用：

1. 作为一名 `<角色>`，我希望 `<功能>`，以便 `<收益>`。

<user-story-example>
1. 作为移动银行客户，我希望看到账户余额，以便更明智地决定如何消费。
</user-story-example>

清单必须非常全面，覆盖该功能的各个方面。

## 实施决策

列出已做出的实施决策，可以包括：

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

## 测试决策

列出已做出的测试决策，包括：

- 什么构成好测试（只测试外部行为，而非实现）；
- 将测试哪些模块；
- 测试的先例（即代码库内相似测试）。

## 执行环境

- execution_agent：
- 未解决规则冲突：

## 范围边界（仅在需要防止误实现时保留）

描述本 Spec 明确覆盖到哪里。

## 补充说明

与该功能有关的其他说明。

</spec-template>
