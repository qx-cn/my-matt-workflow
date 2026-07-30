---
name: my-improve-codebase-architecture
description: 发现并比较能提升模块深度、局部性和可测试性的架构机会
disable-model-invocation: true
---

# My Improve Codebase Architecture

1. 读取项目配置、领域来源、ADR 和近期变更热点。
2. `composition_policy: automatic` 时读取并遵守 [my-codebase-design](references/composed/my-codebase-design/SKILL.md)，再围绕用户指定区域或高频变更区域探索理解摩擦；`manual` 时输出下一条显式调用并停止：Cursor / Claude 使用 `/my-codebase-design`，Codex 使用 `$my-codebase-design`。
   - 一个概念是否散落在许多浅 Module；
   - Interface 是否接近 Implementation 的复杂度；
   - 变更和测试是否缺少 Locality；
   - 是否存在真正值得建立的 Seam。
3. 对候选项应用删除测试，并标注 `Strong`、`Worth exploring` 或 `Speculative`。
4. 在 `.agent/work/<topic>/architecture-reports/architecture-reports-<topic>-<time-or-sequence>.html` 生成完全离线、自包含的 HTML 报告；使用内联 CSS/SVG，不加载 CDN，不外传代码信息。
5. 每个候选包含文件、问题、方案、收益、前后关系图和与 ADR 的冲突。
6. 只推荐候选，不直接重构。用户选择候选且当前已批准流程包含下一阶段时，`automatic` 读取并遵守 [my-grill-with-docs](references/composed/my-grill-with-docs/SKILL.md)；`manual` 输出下一条显式调用并停止：Cursor / Claude 使用 `/my-grill-with-docs`，Codex 使用 `$my-grill-with-docs`。当前流程未批准下一阶段时只建议，不扩展范围。

> 项目策略优先：读取 `.agent/matt-workflow.md` 的已解析生效策略；缺键或空值按 `strict-control`。本 Skill 中要求询问、确认、停止或限制后续工作的表述，除绝对安全底线外，均服从该生效策略。绝对安全底线始终不变：不得 Force Push、改写 Git 历史、执行破坏性 Git 操作，或向外部服务发送敏感信息。
