---
id: "workflow-simplification-01"
title: "保存施工前样例与文本量基线"
ticket_kind: "implementation"
spec_id: "workflow-simplification"
spec_revision: 1
spec_ref: ".agent/work/workflow-simplification/specs/specs-workflow-simplification.md"
supersedes_ticket: []
compensates: []
status: complete
blocked_by: []
claimed_by: 
tags: []
sequence: 1
test_commands: ["python3 -m unittest discover -s tests"]
rule_sources: [".agent/work/workflow-simplification/specs/specs-workflow-simplification.md", "resources/testing-seams.md"]
rule_scope: ["tools/**", "tests/**", "evals/fixtures/**", ".agent/matt-workflow.md"]
rule_constraints: ["Spec 核心模型为状态与命令唯一权威；范围外工作不实施。", "验证仅断言可观察命令结果、状态、提交、归档和度量，不复刻内部算法。", "先完成本 Ticket 再修改旧版格式或删除功能；不部署、不安装、不在其他项目迁移。"]
rule_conflicts: []
review_probes: []
execution_agent: "auto"
---

# 01 — 保存施工前样例与文本量基线

**要构建什么：** 在旧版行为仍可运行时，生成迁移将使用的真实旧格式样例，并记录可重复测量的主链文本量。后续施工可验证历史产物，而不靠手写猜测旧格式。

**被谁阻塞：** 无——可立即开始

## 适用规则与影响区域

- 规则来源：源 Spec revision 1（施工顺序第 1 步；第 9、10 节；AC-34 基线、AC-35 样例来源）；共享测试 seam 约定。当前 Codex resolve-rules 未发现仓库原生规则；execution_agent 保持 auto，实施前按实际绑定 Agent 和修改路径重新解析。
- 影响区域：tools/**、tests/**、evals/fixtures/**；另含用户在本会话授权提前修改的项目测试配置，限于加入现有 unittest 命令，不改变其他策略。
- 实施约束：先完成本 Ticket 再修改旧版格式或删除功能；不部署、不安装、不在其他项目迁移。 关键契约以源 Spec 原文为准；不推送、不建 MR、不写外部系统。
- 验证：基线生成与样例完整性核对，加 unittest 回归；本 Ticket 只承诺基线可复现，不承诺新迁移行为。
- 测试边界：以上 test_commands 为声明；与项目配置的匹配在新 runtime 生效后校验。旧 runtime 施工并非本 Spec 的必需条件，不能伪造实施 receipt。

## 验收标准

- [x] 使用施工开始前的旧版 runtime 生成 AC-35 的 A–E Topic、旧配置和分片术语样例；保存生成方式、旧版提交、基线提交及期望转换结果。样例不含宿主秘密或真实用户项目内容。
- [x] 将未完成实施会话 fixture 复制到测试 fixtures；保留迁移所需旧记录和基线，复制完成前不删除 evals。
- [x] 按第 9 节的 Cursor 安装件、相对 Markdown 链接传递闭包和内容去重口径测量旧 release；包含旧 requirement-analysis，保存精确字符数、release 标识和复现方式。
- [x] 样例可在临时 git 仓库加载；A、B、C 的进行中记录均有可用基线，E 确实违反 I-T3；全量测试可以读取样例而不写回样例。
