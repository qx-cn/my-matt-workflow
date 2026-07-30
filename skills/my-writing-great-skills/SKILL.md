---
name: my-writing-great-skills
description: 为任意 Agent 编写或改进可预测、精简且可验证的个人 Skill
disable-model-invocation: true
---

# My Writing Great Skills

Skill 的根本质量是 **predictability**：每次采取相同过程，而不是生成相同文本。

## 设计

1. 明确触发场景、目标行为、自由度和完成条件。
2. 个人 Skill 放在当前 Agent 配置的 Skill 根目录 `<skills-home>/<skill-name>/`，不得放入内部管理目录。
3. 默认使用 `disable-model-invocation: true`；只有确需自动发现时才省略。
4. `SKILL.md` 保留每次运行都需要的步骤；重型参考通过一级 context pointer 拆出。
5. 每个含义只有一个 source of truth，删除 duplication、sediment 和 no-op。
6. 用稳定的 leading words 压缩重复解释。

## 验证

- 先用基线场景观察没有 Skill 时的失败；
- 编写能修复该失败的最小 Skill；
- 用同一场景验证；
- 纪律型 Skill 再加入压力，寻找新的合理化路径；
- 检查 Frontmatter、名称、引用、行数和实际发现行为。

不要为项目专属规则创建全局 Skill；把它们放到项目配置。

> 项目策略优先：读取 `.agent/matt-workflow.md` 的已解析生效策略；缺键或空值按 `strict-control`。本 Skill 中要求询问、确认、停止或限制后续工作的表述，除绝对安全底线外，均服从该生效策略。绝对安全底线始终不变：不得 Force Push、改写 Git 历史、执行破坏性 Git 操作，或向外部服务发送敏感信息。
