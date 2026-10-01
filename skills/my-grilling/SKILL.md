---
name: my-grilling
description: 在 my-grill-me、my-grill-with-docs、my-triage、my-wayfinder、my-improve-codebase-architecture 流程中作为指定阶段的方法被调用。
---

# 访谈方法

围绕会改变目标、范围、约束或验收的承重未知追问。先查证环境中可获得的事实；用户需决定的事项遵循[找用户的条件](references/shared/user-intervention.md)。

每轮列出所有互不依赖的问题，每题附推荐答案和取舍依据；用户可全部采纳或只改几项。依赖其他答案的留下一轮，会大幅影响其他问题的单独问。例如先确定服务对象，再问依赖它的成功指标；部署路径与已有测试可独立核对时同轮问。

用户以具体方案或类比描述目标时，先分清目标与手段；复杂、隐含或类比请求在形成摘要前按[需求核对](references/shared/requirement-analysis.md)检查理解。只有会改变结果的歧义继续追问。

结束需求摘要新增“待在代码中核实的现状假设”，供 Spec 现状事实逐条核实；能在访谈阶段查到的事实当场查证，不问用户。

目标、范围、明确约束、可观察验收均可追溯且承重未知已解决时完成；按[最终态写作](references/shared/final-state-writing.md)收束决定，返回调用方，不因普通实现细节继续访谈。
