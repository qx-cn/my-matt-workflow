---
id: "workflow-simplification-02"
title: "创建配置 v2 与可完成的 quick Topic"
ticket_kind: "implementation"
spec_id: "workflow-simplification"
spec_revision: 1
spec_ref: ".agent/work/workflow-simplification/specs/specs-workflow-simplification.md"
supersedes_ticket: []
compensates: []
status: "ready-for-agent"
blocked_by: ["workflow-simplification-01"]
claimed_by:
tags: []
sequence: 2
test_commands: ["python3 -m unittest discover -s tests"]
rule_sources: [".agent/work/workflow-simplification/specs/specs-workflow-simplification.md", "resources/testing-seams.md"]
rule_scope: ["tools/**", "tests/**"]
rule_constraints: ["Spec 核心模型为状态与命令唯一权威；范围外工作不实施。", "验证仅断言可观察命令结果、状态、提交、归档和度量，不复刻内部算法。", "先在临时仓库验证新配置；本仓库配置留到最终收尾转换；quick 摘要逐条映射验收与不同测试，由 Skill 在后续接入。"]
rule_conflicts: []
review_probes: ["recovery"]
execution_agent: "auto"
---

# 02 — 创建配置 v2 与可完成的 quick Topic

**要构建什么：** 用户可预览 setup、写入新配置，在干净内容上启动 quick Topic，测试并提交、归档；同一套定位规则可以只读查看多个 Topic。

**被谁阻塞：** 01 — 保存施工前样例与文本量基线

## 适用规则与影响区域

- 规则来源：源 Spec revision 1（M1、M2、M5 quick/文档、M6、M7；第 2、5、6 节；AC-04、05、06 显式启动、14 Topic 定位、25 显式启动与文档）；共享测试 seam 约定。当前 Codex resolve-rules 未发现仓库原生规则；execution_agent 保持 auto，实施前按实际绑定 Agent 和修改路径重新解析。
- 影响区域：tools/**、tests/**。
- 实施约束：先在临时仓库验证新配置；本仓库配置留到最终收尾转换；quick 摘要逐条映射验收与不同测试，由 Skill 在后续接入。 关键契约以源 Spec 原文为准；不推送、不建 MR、不写外部系统。
- 验证：子进程 CLI 用例验证 setup 零写入、分支三种状态、quick 成功和缺陷注入、shared/private 归档与提交。
- 测试边界：以上 test_commands 为声明；与项目配置的匹配在新 runtime 生效后校验。旧 runtime 施工并非本 Spec 的必需条件，不能伪造实施 receipt。

## 验收标准

- [ ] setup 默认只探测和展示，apply 才写入 schema_version 2 的九个配置键；private 沿用嵌套 git 初始化。非法值指出字段，旧配置和 audited 提示 migrate，检测失败零写入。
- [ ] topic start 必须选择 Topic，检查内容干净、归档重名和现有状态；standard 启动要求至少一条无星号全量测试；quick 在默认分支按 M2 创建或切换分支，在其他分支不切换。
- [ ] 多个活动 Topic 时省略 topic 的相关操作拒绝；一个活动 Topic 可省略；归档 Topic 只读。work-overview 正确区分活动、待补建与文档 Topic。
- [ ] quick complete 校验全部摘要章节和验收对照；全量测试失败则拒绝，空集合标记未配置测试；成功时最多一次代码提交、归档和 kind quick 度量，没有实施记录。
- [ ] 文档 Topic 可直接 complete，记录 kind topic 且不可观察字段为 null；同名归档不覆盖；待补建不能直接 complete，无 Ticket 的 standard 拒绝完成。
- [ ] quick/文档完成满足 I-A1、I-A2；内容与 agent 改动的提交边界正确，任何流程不推送、不写外部系统。
