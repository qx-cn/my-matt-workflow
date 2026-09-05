---
name: my-improve-codebase-architecture
description: 扫描代码库中的深化机会，分阶段生成候选内容与 HTML 报告，并深挖用户选择的候选项；内容与前端可使用不同模型。
disable-model-invocation: true
---

# 改进代码库架构

找出能把浅模块变为深模块的架构机会，帮助维护者按证据、收益、成本和风险选择值得深入的候选项。

先读取[面向读者写作](references/shared/reader-first-writing.md)与[内容/前端交接](references/shared/document-rendering.md)，再选择阶段：

- 未指定阶段：执行 `content`，读取 [CONTENT.md](CONTENT.md)，将 `architecture-review-<timestamp>.content.md` 写入操作系统临时目录，报告绝对路径与 `/my-improve-codebase-architecture frontend <artifact>` 后停止。
- `frontend <artifact>`：只读取语义工件、[FRONTEND.md](FRONTEND.md)和 [HTML-REPORT.md](HTML-REPORT.md)，渲染同名 `.html`；不得重新扫描代码库或改变候选结论。
- `full`：顺序完成内容与前端，保留中间工件，并说明没有形成模型隔离证据。
- `deepen <candidate>`：用户选定候选后进入下述深化循环，不重新生成候选报告。

内容与前端阶段可由不同模型独立运行；前端发现内容缺口时返回 `blocked-by-content`。

## 深化循环

用户选择候选后，读取 `.agent/matt-workflow.md` 的 `composition_policy`，按[组合调用](references/shared/adapters/composition.md)将 `my-grill-with-docs` 与 `my-codebase-design` 作为内部方法：读取当前所需的 [my-grill-with-docs 正文](references/composed/my-grill-with-docs/COMPOSED.md) 或 [my-codebase-design 正文](references/composed/my-codebase-design/COMPOSED.md)，执行后返回宿主，不输出另一条 Skill 调用。

- 用访谈确认约束、依赖、深化模块形状、接缝内外和能存活的测试。
- 新领域概念或澄清后的术语更新到项目配置指定的领域模型；承重拒绝理由确实值得未来避免重提时，才建议记录 ADR。
- 需要比较深化模块接口时，执行 `my-codebase-design` 的设计两次方法。

未经用户选择，不先提出候选模块的具体接口，也不进入实现。
