---
name: my-domain-modeling
description: 澄清领域术语、关系、边界和难以逆转的设计决策
disable-model-invocation: true
---

# My Domain Modeling

在设计过程中主动构建并收紧项目领域模型。这是一项**主动**的纪律：挑战术语、构造边缘场景，并在术语或决策结晶时立即记录。（其他 Skill 为取得词汇而阅读项目术语表不属于本 Skill；本 Skill 用于改变模型，而不仅是使用模型。）

## 文件结构

首先读取项目配置列出的正式术语表、ADR 和相关代码。项目正式文档位置因仓库而异，不假设根目录存在 `CONTEXT.md` 或固定 `docs/adr/`；项目配置未列出时，按当前 topic 使用下列个人目录：

```text
.agent/work/<topic>/domain/
├── domain-<topic>-glossary.md
└── adr/
    ├── domain-<topic>-0001-event-sourced-orders.md
    └── domain-<topic>-0002-postgres-for-write-model.md
```

按需创建文件：只有内容可写时才创建。首个术语解决后才创建 `.agent/work/<topic>/domain/domain-<topic>-glossary.md`；首次需要 ADR 才创建 `.agent/work/<topic>/domain/adr/`。若仓库存在多个领域上下文，以项目配置和目录边界确定术语及 ADR 的归属；不明确时，按 `decision_policy` 询问或在已批准的无人值守计划中记录假设。

## 会话期间

### 对照术语表提出质疑

当用户所用术语与既有语言冲突，立即指出：“术语表将‘取消’定义为 X，但你似乎在说 Y；究竟是哪一个？”

### 收紧模糊语言

当用户使用含糊或多义术语时，提出精确、规范的名称：“你说的是‘账户’，是 Customer 还是 User？它们不同。”

### 讨论具体场景

讨论领域关系时，用具体场景压测它们。构造探查边缘情况的场景，迫使概念之间的边界变得精确。

### 与代码交叉验证

用户说明某事如何工作时，检查代码是否一致。发现矛盾时明确展示，例如：“代码会取消整张 Order，但你刚说可以部分取消；哪个是正确行为？”

### 就地更新个人术语表

术语一经解决，立即按 [CONTEXT-FORMAT.md](CONTEXT-FORMAT.md) 的格式写入 `.agent/work/<topic>/domain/domain-<topic>-glossary.md`；不要批量积压。个人术语表必须完全不含实现细节，不得把它当作 Spec、草稿本或实现决策库；它只是一份词汇表。

正式团队术语文档是外部写入：按项目策略先预览、确认或依照已批准的无人值守计划写回。个人术语表先记录，避免丢失本次会话结论。

### 谨慎提出 ADR

只有同时满足以下三项才建议创建 ADR：

1. **难以逆转**：以后改变主意的成本很高。
2. **缺少背景会令人意外**：未来读者会问“他们为什么这样做？”
3. **源于真实权衡**：存在真实替代方案，并因具体原因选择其一。

缺任何一项就不写 ADR。使用 [ADR-FORMAT.md](ADR-FORMAT.md) 的格式先写个人候选；写回团队 ADR 目录前遵守项目写入策略。

> 项目策略优先：读取 `.agent/matt-workflow.md` 的已解析生效策略；缺键或空值按 `strict-control`。本 Skill 中要求询问、确认、停止或限制后续工作的表述，除绝对安全底线外，均服从该生效策略。绝对安全底线始终不变：不得 Force Push、改写 Git 历史、执行破坏性 Git 操作，或向外部服务发送敏感信息。
