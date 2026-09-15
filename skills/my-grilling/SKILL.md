---
name: my-grilling
description: 对计划、决策或想法进行高强度逐项访谈。
disable-model-invocation: true
---

围绕会改变目标、范围、约束或验收的承重未知进行高强度访谈。沿决策树逐支前进，一次解决一个决定及其依赖；每个问题都给出推荐答案。

每次只问一个问题，等待反馈后再继续。一次问多个问题会令人无所适从。

能通过探索环境（文件系统、工具等）找到的**事实**，应自行查证而非提问。按[指令权威与决策 Gate](references/shared/instruction-authority.md)区分决定：已批准范围内普通、可逆的 `routine` 细节由 Agent 继续；`consequential` 只在 gate 返回 `confirm` 时询问；产品取舍、成功指标、优先级或不可逆承诺等 `user-exclusive` 决定必须由用户回答。

当目标、范围、明确约束和可观察验收均可追溯，且没有未处理的 `consequential` 或 `user-exclusive` 未知时，访谈完成。需要用户回答的决定尚未解决前不得执行该事项；不要为了“覆盖所有方面”继续询问普通实现细节。

确认后按[最终态写作](references/shared/final-state-writing.md)收束当前有效决定，供后续产物使用。
