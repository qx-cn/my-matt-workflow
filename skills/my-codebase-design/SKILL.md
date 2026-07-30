---
name: my-codebase-design
description: 设计更深、更易测试且更具局部性的模块接口
disable-model-invocation: true
---

# My Codebase Design

使用统一词汇：

- **Module**：具有 Interface 和 Implementation 的单元；
- **Interface**：调用者正确使用 Module 必须知道的全部事实；
- **Seam**：可在不修改调用点的情况下改变行为的位置；
- **Adapter**：在 Seam 上满足 Interface 的具体实现；
- **Depth**：小 Interface 后隐藏大量行为带来的杠杆；
- **Locality**：知识、变更、Bug 和验证集中在一个地方。

设计时：

1. 先确定 Seam，再设计 Interface。
2. 用删除测试判断 Module 是否真正隐藏复杂度。
3. Interface 同时是调用面和测试面。
4. 只有存在至少两个真实 Adapter 时才引入可替换 Seam。
5. 比较至少两种有实质差异的方案，按 Depth、Locality、迁移成本和测试面选择。
6. 遵守项目现有架构决策，不做无关重构。

> 项目策略优先：读取 `.agent/matt-workflow.md` 的已解析生效策略；缺键或空值按 `strict-control`。本 Skill 中要求询问、确认、停止或限制后续工作的表述，除绝对安全底线外，均服从该生效策略。绝对安全底线始终不变：不得 Force Push、改写 Git 历史、执行破坏性 Git 操作，或向外部服务发送敏感信息。
