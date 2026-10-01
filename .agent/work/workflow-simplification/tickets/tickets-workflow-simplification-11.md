---
id: "workflow-simplification-11"
title: "吸收上游五项方法改动"
ticket_kind: "implementation"
spec_id: "workflow-simplification"
spec_revision: 1
spec_ref: ".agent/work/workflow-simplification/specs/specs-workflow-simplification.md"
supersedes_ticket: []
compensates: []
status: complete
blocked_by: ["workflow-simplification-09"]
claimed_by:
tags: []
sequence: 11
test_commands: ["python3 -m unittest discover -s tests"]
rule_sources: [".agent/work/workflow-simplification/specs/specs-workflow-simplification.md", "resources/testing-seams.md"]
rule_scope: ["skills/**", "resources/**", "tests/**"]
rule_constraints: ["Spec 核心模型为状态与命令唯一权威；范围外工作不实施。", "验证仅断言可观察命令结果、状态、提交、归档和度量，不复刻内部算法。", "上游内容已自包含于 Spec，不引入其他上游变更；8 个冻结 Skill 不吸收方法改动。"]
rule_conflicts: []
review_probes: []
execution_agent: "auto"
---

# 11 — 吸收上游五项方法改动

**要构建什么：** TDD、指令写作、阶段路由、架构改进入口和 Spec 写作采用 Spec 已明确给出的上游方法，保持冻结 Skill 方法不变。

**被谁阻塞：** 09 — 按新 Skill 清单构建三种宿主安装件

## 适用规则与影响区域

- 规则来源：源 Spec revision 1（第 7 节吸收上游；AC-32）；共享测试 seam 约定。当前 Codex resolve-rules 未发现仓库原生规则；execution_agent 保持 auto，实施前按实际绑定 Agent 和修改路径重新解析。
- 影响区域：skills/**、resources/**、tests/**。
- 实施约束：上游内容已自包含于 Spec，不引入其他上游变更；8 个冻结 Skill 不吸收方法改动。 关键契约以源 Spec 原文为准；不推送、不建 MR、不写外部系统。
- 验证：逐项文本核对五项要求及 review-instructions 使用方法，配合资源链接与调用静态校验。
- 测试边界：以上 test_commands 为声明；与项目配置的匹配在新 runtime 生效后校验。旧 runtime 施工并非本 Spec 的必需条件，不能伪造实施 receipt。

## 验收标准

- [x] TDD 红绿循环不含重构，重构只作为审查建议；相关调用与资源不保留旧循环要求。
- [x] writing-for-agents 面向 Skill、AGENTS、CLAUDE，默认删除；包含指针触发、两类负担、信息分层、可判定完成条件、熟悉关键词与正向目标、剪枝和调用方式的全部要求。
- [x] review-instructions 采用 writing-for-agents 方法，以宿主参数处理差异；合并后保留必要审查目标。
- [x] ask-matt 在阶段边界按 Spec 五条顺序取首个成立项，除继续外说明原始信息损失，压缩时说明保留内容。
- [x] architecture 用户未指定方向先查约 20 个提交的反复热点，分散时才扩大；数字注明项目选择；to-spec 删除 PRD 别称。
