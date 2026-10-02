# 深化

在给定依赖条件下，如何安全地深化一组浅模块。假定你已掌握 [SKILL.md](SKILL.md) 中的词汇——**Module**、**Interface**、**Seam**、**Adapter**。

## 依赖类别

评估一个深化候选项时，对其依赖进行分类。该类别决定如何跨越其 Seam 测试深化后的 Module。

### 1. 进程内

纯计算、内存状态、无 I/O。始终可以深化——合并这些 Module，并直接通过新的 Interface 测试。无需 Adapter。

### 2. 可本地替代

具有本地测试替身的依赖（Postgres 的 PGLite、内存文件系统）。若替身存在，即可深化。让替身在测试套件中运行，以测试深化后的 Module。Seam 是内部的；Module 的外部 Interface 上不设 port。

### 3. 远程但自有（Ports & Adapters）

网络边界另一侧的自有服务（微服务、内部 API）。优先复用既有传输边界；需要新 port 时按共享合同判断真实变化与维护价值，深 Module 拥有逻辑，传输层作为 Adapter 注入。测试替身保留 HTTP/gRPC/队列的必要边界语义，不以生产/测试各一个实现证明抽象价值。

表述应说明真实边界与选择依据；跨网络部署本身不要求新增一层公开接口。

### 4. 真正外部（Mock）

你无法控制的第三方服务（Stripe、Twilio 等）。优先通过项目已有稳定边界注入依赖/替身；确需新增 port 时按共享合同解释必要性，不因需要 mock 就新增公开接口。

## Seam 纪律

- 是否新增 port 或复用既有单实现边界，只按下文共享测试合同判断；测试替身不作为新生产抽象的价值证据。
- **内部 Seam 与外部 Seam。** 深 Module 可以有内部 Seam（其 Implementation 私有，供自身测试使用），也可以有位于其 Interface 的外部 Seam。不要仅因为测试使用内部 Seam，就通过 Interface 暴露它。

## 测试策略

测试面、内部/外部 seam、Adapter 与 mock 统一遵循[测试 Seam 合同](references/shared/testing-seams.md)。深化后只移除已被新测试面完整替代、且不再证明独立行为的旧测试；保留仍覆盖不同风险或契约的测试。
