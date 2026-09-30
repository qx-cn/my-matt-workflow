---
id: "workflow-simplification-14"
title: "更新使用文档与本仓库配置"
ticket_kind: "implementation"
spec_id: "workflow-simplification"
spec_revision: 1
spec_ref: ".agent/work/workflow-simplification/specs/specs-workflow-simplification.md"
supersedes_ticket: []
compensates: []
status: "ready-for-agent"
blocked_by: ["workflow-simplification-13"]
claimed_by:
tags: []
sequence: 14
test_commands: ["python3 -m unittest discover -s tests"]
rule_sources: [".agent/work/workflow-simplification/specs/specs-workflow-simplification.md", "resources/testing-seams.md"]
rule_scope: ["README.md", ".agent/matt-workflow.md", "tests/**"]
rule_constraints: ["Spec 核心模型为状态与命令唯一权威；范围外工作不实施。", "验证仅断言可观察命令结果、状态、提交、归档和度量，不复刻内部算法。", "本次仅本地起草 Ticket；实际写 README/配置属于实施范围。施工可按 Spec 直接实施，不强制使用将被替换的工作流 runtime/Skill。"]
rule_conflicts: []
review_probes: []
execution_agent: "auto"
---

# 14 — 更新使用文档与本仓库配置

**要构建什么：** README 按最终工作流说明用法，本仓库采用新配置；维护者清楚何时可以新增门禁以及提交如何记录触发来源。

**被谁阻塞：** 13 — 完成命令收缩与全量行为验证

## 适用规则与影响区域

- 规则来源：源 Spec revision 1（第 6、10、11 节；AC-27 本仓库新配置、41；范围边界）；共享测试 seam 约定。当前 Codex resolve-rules 未发现仓库原生规则；execution_agent 保持 auto，实施前按实际绑定 Agent 和修改路径重新解析。
- 影响区域：README.md、.agent/matt-workflow.md、tests/**。
- 实施约束：本次仅本地起草 Ticket；实际写 README/配置属于实施范围。施工可按 Spec 直接实施，不强制使用将被替换的工作流 runtime/Skill。 关键契约以源 Spec 原文为准；不推送、不建 MR、不写外部系统。
- 验证：对照最终 help/config 核对 README，运行最终 check；检查变更范围不含既有 work 文档和真实宿主路径。
- 测试边界：以上 test_commands 为声明；与项目配置的匹配在新 runtime 生效后校验。旧 runtime 施工并非本 Spec 的必需条件，不能伪造实施 receipt。

## 验收标准

- [ ] README 描述两个对齐点、quick/standard、新配置与实际命令；删掉长期 Spec、预设、旧审计/门禁、eval 和其他已移除功能的使用说明。
- [ ] 维护章节明确修改工作流提交需有一行 Trigger，说明哪个项目的什么问题触发；度量证明必要前不新增门禁。
- [ ] 本仓库配置改为 schema 2 九键，保留 local/shared/main/auto 和有效标准/领域来源；设置匹配全部 Ticket 声明的非空全量 unittest 命令，不保留预设正文。
- [ ] 本仓库既有 work 文档及本次 Spec/Ticket 全文不转换、不归档；不操作宿主安装及其他项目迁移；最终 check 后被跟踪文件仍零变化。
