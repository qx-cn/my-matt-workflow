---
name: my-tdd
description: 以 red-green-refactor 循环进行测试驱动开发。
disable-model-invocation: true
---

# 测试驱动开发

TDD 是 red → green → refactor 循环。本 Skill 只保留循环与完成门；测试形状见 [tests.md](tests.md)，seam、adapter 与 mock 的单一事实来源见[测试 Seam 合同](references/shared/testing-seams.md)。

探索代码库时，读取已有的项目领域术语与 ADR，使测试名称和接口词汇匹配项目语言，并尊重所涉及区域的 ADR。

读取本地术语表或 ADR 工作产物时，遵循 [工作产物访问](references/shared/adapters/artifact-access.md)。

## 好测试是什么

测试通过公共接口验证行为，而非实现细节。代码可以完全改变，测试不应随之改变。好测试读起来像规格：“用户可用有效购物车结账”准确说出能力；它不关心内部结构，因此可穿越重构。

参见 [tests.md](tests.md) 中的例子；需要替身时读取 [mocking.md](mocking.md)，它指向共享 seam 合同。

## Seam——测试放在哪里

按[测试 Seam 合同](references/shared/testing-seams.md)选择公共或模块内部 seam。**只在预先约定或可从 Ticket、计划和代码推断的 seam 测试。** 无法推断且会改变公开接口、范围或测试投资的关键 seam，交回宿主按[工作范围](references/shared/adapters/work-scope.md)暂停确认；普通、既有 seam 继续执行。

## 反模式

- **与实现耦合**——mock 内部协作者、测试私有方法，或从旁路验证（例如不经接口而查询数据库）。征兆是：行为没有改变，重构却让测试失败。
- **同义反复**——断言用与代码相同的方式重新计算预期值（`expect(add(a, b)).toBe(a + b)`、以同一方式手写的 snapshot、断言常量等于自身），因此天生通过、永远不能与代码分歧。预期值必须来自独立事实源：已知正确字面量、演算示例或 Spec。
- **水平切片**——先写全部测试，再写全部实现。批量测试验证的是**想象中的**行为：测试对象的**形状**而非面向用户行为，测试会对真实变更失去敏感度，并在理解实现前锁死测试结构。应做**纵向切片**：一个测试 → 一个实现 → 重复；每个测试都是会响应上一轮反馈的 **tracer bullet**。

## 循环规则

- **先 red，后 green。** 先写失败测试，再只写足以通过的代码。不要预判未来测试或加入推测性功能。
- **一次一个切片。** 每轮一个 seam、一个测试、一个最小实现。
- **再 refactor。** green 后在同一行为 seam 下消除重复、改善名称与内部结构；每次小步重跑测试，保持 green。重构不增加新行为，新行为回到下一轮 red。

完成条件：每项验收行为都经历可观察 red、最小 green 与保持 green 的必要 refactor；测试通过稳定 seam，且没有把未验证行为或推测性抽象带入当前切片。
