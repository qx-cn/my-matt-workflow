---
name: my-domain-modeling
description: 在 my-grill-with-docs、my-triage、my-wayfinder、my-improve-codebase-architecture 流程中作为指定阶段的方法被调用。
---

遵循[指令权威](references/shared/instruction-authority.md)。

# 项目领域模型

先读取 `.agent/CONTEXT.md`、`.agent/adr/`、配置列出的领域来源及相关代码，遵循[产物访问](references/shared/adapters/artifact-access.md)。主动质疑冲突术语，用具体边缘场景区分概念，并将用户描述与代码交叉验证；涉及用户决定时遵循[找用户的条件](references/shared/user-intervention.md)。

术语解决后按 [CONTEXT-FORMAT.md](CONTEXT-FORMAT.md) 更新项目级 `.agent/CONTEXT.md`；只写项目词汇、定义和边界，不存实现细节。多上下文在同一文件按领域分节；不按 Topic 分片。未来维护者需要据此理解和判断，按[面向读者写作](references/shared/reader-first-writing.md)表达。

难以撤回、缺少背景会让未来维护者意外、且有真实替代权衡的决定，按 [ADR-FORMAT.md](ADR-FORMAT.md) 写 `.agent/adr/NNNN-<slug>.md`。三项缺一就不写。先扫描已有编号与决定，保留依据及被拒替代方案；不是模板填充。

Topic 收尾再核对哪些已确认知识值得长期保留，依[交付规则](references/shared/workflow-delivery.md)记录新增及依据。修改既有项目文档按共同确认条件处理。
