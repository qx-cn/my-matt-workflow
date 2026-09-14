# Workflow baseline/candidate comparative runbook

状态：planned / not-recorded。本轮没有调用高成本模型，也不把此计划计作 fresh-agent 执行证据。

## 目标

在相同模型、reasoning effort、宿主、权限、输入项目和时间预算下，对比基线工作流与候选工作流，判断新增流程成本是否换来更高的完成可靠性。

## 固定变量

- 同一个隔离项目快照与验收条件。
- 同一模型、reasoning effort、宿主版本、工具权限和最大轮次。
- 基线与候选各从 fresh session 启动；执行 Agent 不参与工作流实现。
- 预先冻结 release id、输入 prompt、判分 rubric 和失败分类。

## 观测指标

- 验收完成率与错误通过率。
- 从开始到可验证终态的时间和交互轮次。
- 生成 artifact 数、重复信息量与人工澄清次数。
- 中断恢复成功率、证据可追溯率、越权写入次数。
- token/调用成本；该指标只描述代价，不单独决定优劣。

## 判定

至少覆盖 quick、standard、audited 各一个代表场景。每组保存原始输出及机器可读判分；任何缺失、环境不一致或 rubric 无法判定都记为 inconclusive，不补写为 pass。候选方案只有在可靠性收益与额外成本均有证据时，才据此扩大默认适用范围。
