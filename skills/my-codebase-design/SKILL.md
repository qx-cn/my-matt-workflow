---
name: my-codebase-design
description: 用于设计深模块的共享词汇。当用户想设计或改进模块接口、寻找深化机会、确定 Seam 位置、让代码更易测试或更便于 AI 导航，或其他 Skill 需要深模块词汇时使用。
disable-model-invocation: true
---

# 代码库设计

设计**深模块**：把大量行为置于小接口之后，放在清晰的 Seam 上，并通过该接口测试。无论何时设计或重构代码，都使用这套语言和原则。目标是让调用者获得杠杆，让维护者获得局部性，并让所有人都能测试。

## 术语表

严格使用这些术语——不要用“组件”、“服务”、“API”或“边界”替代它们。一致的语言正是关键所在。

**Module（模块）**——任何具有 Interface 和 Implementation 的事物。刻意不限定规模：可以是函数、类、包，或跨层切片。*避免使用*：unit、component、service。

**Interface（接口）**——调用者正确使用 Module 必须知道的一切：类型签名，也包括不变量、顺序约束、错误模式、必需配置和性能特征。*避免使用*：API、signature（过于狭窄——它们只指类型层面的表面）。

**Implementation（实现）**——Module 内部的内容，即代码主体。它不同于 **Adapter**：一个事物可以是小 Adapter 却有很大的 Implementation（例如 Postgres 仓储），也可以是大 Adapter 却有很小的 Implementation（例如内存 fake）。当话题是 Seam 时使用“Adapter”；其他情形使用“Implementation”。

**Depth（深度）**——接口上的杠杆：调用者（或测试）每学习一单位接口所能驱动的行为量。当大量行为位于小接口之后时，Module 是**深的**；当 Interface 几乎和 Implementation 一样复杂时，Module 是**浅的**。

**Seam（接缝）**（Michael Feathers）——无需在该处编辑就能改变行为的位置；也就是 Module 的 Interface 所在的*位置*。Seam 放在哪里本身是一个设计决策，和其后放置什么不同。*避免使用*：boundary（它与 DDD 的 bounded context 含义重叠）。

**Adapter（适配器）**——在 Seam 处满足 Interface 的具体事物。它描述的是*角色*（填补哪个槽位），而不是实体（内部是什么）。

**Leverage（杠杆）**——调用者从 Depth 获得的收益：他们每学习一单位 Interface 就得到更多能力。一次 Implementation 投入，会在 N 个调用点和 M 个测试中回报。

**Locality（局部性）**——维护者从 Depth 获得的收益：变更、Bug、知识和验证集中在一个地方，而不是散布到各个调用者。修复一次，处处修复。

## 深模块与浅模块

**深模块** = 小 Interface + 大量 Implementation：

```
┌─────────────────────┐
│      小 Interface    │  ← 少量方法，简单参数
├─────────────────────┤
│                     │
│   深 Implementation  │  ← 隐藏复杂逻辑
│                     │
└─────────────────────┘
```

**浅模块** = 大 Interface + 少量 Implementation（应避免）：

```
┌─────────────────────────────────┐
│          大 Interface             │  ← 许多方法，复杂参数
├─────────────────────────────────┤
│      薄 Implementation            │  ← 只是直通
└─────────────────────────────────┘
```

设计 Interface 时，问自己：

- 我能减少方法数量吗？
- 我能简化参数吗？
- 我能把更多复杂度隐藏在内部吗？

## 原则

- **Depth 是 Interface 的属性，不是 Implementation 的属性。** 深 Module 的内部可以由小型、可 mock、可替换的部件组成——只是它们不属于 Interface。Module 可以同时具有**内部 Seam**（仅供 Implementation 私有使用，并由其自身测试使用）和位于 Interface 上的**外部 Seam**。
- **删除测试。** 想象删掉这个 Module。若复杂度随之消失，它只是直通；若复杂度在 N 个调用者中重新出现，它就在创造价值。
- **Interface 就是测试面。** 调用者和测试跨越同一个 Seam。若你想测试*越过* Interface 的内容，这个 Module 的形状很可能不对。
- **一个 Adapter 只意味着假设的 Seam；两个 Adapter 才意味着真实的 Seam。** 除非确有事物在 Seam 两侧变化，否则不要引入 Seam。

## 为可测试性而设计

好的 Interface 会让测试自然发生：

1. **接受依赖，而不是创建依赖。**

   ```typescript
   // 可测试
   function processOrder(order, paymentGateway) {}

   // 难以测试
   function processOrder(order) {
     const gateway = new StripeGateway();
   }
   ```

2. **返回结果，而不是产生副作用。**

   ```typescript
   // 可测试
   function calculateDiscount(cart): Discount {}

   // 难以测试
   function applyDiscount(cart): void {
     cart.total -= discount;
   }
   ```

3. **小的表面积。** 方法越少，需要的测试越少。参数越少，测试准备越简单。

## 关系

- 一个 **Module** 恰有一个 **Interface**（它呈现给调用者和测试的表面）。
- **Depth** 是 **Module** 的属性，依据其 **Interface** 衡量。
- **Seam** 是 **Module** 的 **Interface** 所在之处。
- **Adapter** 位于 **Seam**，并满足 **Interface**。
- **Depth** 为调用者带来 **Leverage**，为维护者带来 **Locality**。

## 被否决的表述

- **Depth 是 Implementation 行数与 Interface 行数的比率**（Ousterhout）：这会鼓励给 Implementation 注水。我们改用“Depth 即 Leverage”。
- **“Interface”是 TypeScript 的 `interface` 关键字或类的 public methods**：过于狭窄——这里的 Interface 包含调用者必须知道的每一项事实。
- **“Boundary”**：与 DDD 的 bounded context 含义重叠。请说 **Seam** 或 **Interface**。

## 继续深入

- **在给定依赖条件下深化一组模块**——见 [DEEPENING.md](DEEPENING.md)：依赖类别、Seam 纪律，以及“替换而不是叠加”的测试。
- **探索备选 Interface**——见 [DESIGN-IT-TWICE.md](DESIGN-IT-TWICE.md)：并行启动子代理，以多种根本不同的方式设计 Interface，然后按 Depth、Locality 和 Seam 位置比较。

> 项目策略优先：本仓库的已解析生效策略优先于本 Skill；缺省按 strict-control；它不改变上述上游设计方法。
