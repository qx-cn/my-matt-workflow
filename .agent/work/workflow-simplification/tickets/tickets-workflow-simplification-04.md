---
id: "workflow-simplification-04"
title: "冻结完整审查材料并校验结果"
ticket_kind: "implementation"
spec_id: "workflow-simplification"
spec_revision: 1
spec_ref: ".agent/work/workflow-simplification/specs/specs-workflow-simplification.md"
supersedes_ticket: []
compensates: []
status: "ready-for-agent"
blocked_by: ["workflow-simplification-03"]
claimed_by:
tags: []
sequence: 4
test_commands: ["python3 -m unittest discover -s tests"]
rule_sources: [".agent/work/workflow-simplification/specs/specs-workflow-simplification.md", "resources/testing-seams.md"]
rule_scope: ["tools/**", "tests/**"]
rule_constraints: ["Spec 核心模型为状态与命令唯一权威；范围外工作不实施。", "验证仅断言可观察命令结果、状态、提交、归档和度量，不复刻内部算法。", "runtime 不决定宿主模型，不把自审冒充独立；循环规则文字接入由后续 Ticket 完成，本阶段提供材料与结果边界。"]
rule_conflicts: []
review_probes: ["recovery"]
execution_agent: "auto"
---

# 04 — 冻结完整审查材料并校验结果

**要构建什么：** 审查者获得与当前内容绑定的材料包和预填结果骨架；只填写判断字段即可提交，格式错误明确指出字段。

**被谁阻塞：** 03 — 从 Ticket 启动实施并登记真实测试

## 适用规则与影响区域

- 规则来源：源 Spec revision 1（M4 材料与结果、M5 绑定；第 3、4 节；AC-11、13、16、21）；共享测试 seam 约定。当前 Codex resolve-rules 未发现仓库原生规则；execution_agent 保持 auto，实施前按实际绑定 Agent 和修改路径重新解析。
- 影响区域：tools/**、tests/**。
- 实施约束：runtime 不决定宿主模型，不把自审冒充独立；循环规则文字接入由后续 Ticket 完成，本阶段提供材料与结果边界。 关键契约以源 Spec 原文为准；不推送、不建 MR、不写外部系统。
- 验证：CLI 子进程覆盖冻结输入、预填篡改、非法字段、建议通过及 scope 外文件；不依赖实际派发外部审查者。
- 测试边界：以上 test_commands 为声明；与项目配置的匹配在新 runtime 生效后校验。旧 runtime 施工并非本 Spec 的必需条件，不能伪造实施 receipt。

## 验收标准

- [ ] implement review 冻结 Ticket 基线以来全部内容差异，排除 agent、git 和被忽略文件；rule_scope 之外的文件单列，不能从审查差异中删去。
- [ ] 材料包含冻结改动、稳定验收编号、probes、下游 Ticket、已决事项、循环规则与骨架；排除实施者总结和简报的实施计划。
- [ ] 骨架预填 unit_id、content_id、round、acceptance、probes、downstream_tickets；submit 比较当前冻结单元，任何不一致或必填缺失指出具体字段。
- [ ] 校验 reviewer 来源与实际模型、coverage、四类 status 和两类 severity；blocking 必填锚定对象、位置、出错路径和可达性；pass 含阻断问题拒绝。
- [ ] 仅 advisory 的结果登记为通过，建议出现在 topic status；审查来源如实保存，self 不能被标为 independent。
