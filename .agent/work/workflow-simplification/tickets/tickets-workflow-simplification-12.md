---
id: "workflow-simplification-12"
title: "让技术方案保留契约并可独立阅读"
ticket_kind: "implementation"
spec_id: "workflow-simplification"
spec_revision: 1
spec_ref: ".agent/work/workflow-simplification/specs/specs-workflow-simplification.md"
supersedes_ticket: []
compensates: []
status: "ready-for-agent"
blocked_by: ["workflow-simplification-10"]
claimed_by:
tags: []
sequence: 12
test_commands: ["python3 -m unittest discover -s tests"]
rule_sources: [".agent/work/workflow-simplification/specs/specs-workflow-simplification.md", "resources/testing-seams.md"]
rule_scope: ["skills/my-tech-design/**", "resources/**", "tests/**"]
rule_constraints: ["Spec 核心模型为状态与命令唯一权威；范围外工作不实施。", "验证仅断言可观察命令结果、状态、提交、归档和度量，不复刻内部算法。", "本 Ticket 只交付 Skill 契约与可核对材料，不执行外部写入，不声称飞书已实测。"]
rule_conflicts: []
review_probes: []
execution_agent: "auto"
---

# 12 — 让技术方案保留契约并可独立阅读

**要构建什么：** 技术方案读者获得契约、接口原文、上线与回滚边界；有参考文档时沿用其体例，交付前按统一循环完成自检。

**被谁阻塞：** 10 — 接通两个对齐点与统一审查收尾

## 适用规则与影响区域

- 规则来源：源 Spec revision 1（第 8 节；AC-33）；共享测试 seam 约定。当前 Codex resolve-rules 未发现仓库原生规则；execution_agent 保持 auto，实施前按实际绑定 Agent 和修改路径重新解析。
- 影响区域：skills/my-tech-design/**、resources/**、tests/**。
- 实施约束：本 Ticket 只交付 Skill 契约与可核对材料，不执行外部写入，不声称飞书已实测。 关键契约以源 Spec 原文为准；不推送、不建 MR、不写外部系统。
- 验证：审查者逐条对照第 8 节，检查本地引用、固定章节和完成条件；不以模板测试代替质量核对。
- 测试边界：以上 test_commands 为声明；与项目配置的匹配在新 runtime 生效后校验。旧 runtime 施工并非本 Spec 的必需条件，不能伪造实施 receipt。

## 验收标准

- [ ] 正文不包含 Spec 禁止的实现清单，删除四处覆盖要求；保留数据与接口变更、上线顺序、回滚、待确认项四个固定章节。
- [ ] 数据章节逐项列 Proto、RPC/HTTP、库表、SQL、MQ、配置，有变更贴实际 DDL/DML/proto，无则写无，原文只出现一次。
- [ ] 实现约定留 Spec，读者可访问则链接，不可访问则方案自包含；被否方案/推翻条件默认只在语义工件，必要时正文一句。
- [ ] 参考文档可选，提供后遵从章节结构和大致篇幅，表格单元格通常一两句；草稿仅存 Topic designs。
- [ ] 完成条件含最终态自检与悬空引用检查，遵守文档审查日志、轮数与停止条件。
- [ ] 可选 feishu 阶段仅读语义工件，缺内容返回 blocked-by-content；按宿主工具、wiki 目录和有评论时仅更新变更章节的规则说明执行，并标未实测；没有工具明确停下。
