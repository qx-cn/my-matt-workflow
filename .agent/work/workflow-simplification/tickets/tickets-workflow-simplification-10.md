---
id: "workflow-simplification-10"
title: "接通两个对齐点与统一审查收尾"
ticket_kind: "implementation"
spec_id: "workflow-simplification"
spec_revision: 1
spec_ref: ".agent/work/workflow-simplification/specs/specs-workflow-simplification.md"
supersedes_ticket: []
compensates: []
status: "ready-for-agent"
blocked_by: ["workflow-simplification-09"]
claimed_by:
tags: []
sequence: 10
test_commands: ["python3 -m unittest discover -s tests"]
rule_sources: [".agent/work/workflow-simplification/specs/specs-workflow-simplification.md", "resources/testing-seams.md"]
rule_scope: ["skills/**", "resources/**", "policies/**", "tests/**"]
rule_constraints: ["Spec 核心模型为状态与命令唯一权威；范围外工作不实施。", "验证仅断言可观察命令结果、状态、提交、归档和度量，不复刻内部算法。", "runtime 已强制的规则从 Skill 正文删除；手动 humanizer 保留且不成为强制步骤；冻结入口只同步许可的全局调用与交接变化。"]
rule_conflicts: []
review_probes: []
execution_agent: "auto"
---

# 10 — 接通两个对齐点与统一审查收尾

**要构建什么：** 用户在需求与 Spec/Ticket 两处对齐后，主链自动逐张实施、独立审查并收尾；文档审查也按统一停止条件记录，长期知识归于项目。

**被谁阻塞：** 09 — 按新 Skill 清单构建三种宿主安装件

## 适用规则与影响区域

- 规则来源：源 Spec revision 1（第 1–6 节文本行为、第 9 节；AC-01、02、15、26）；共享测试 seam 约定。当前 Codex resolve-rules 未发现仓库原生规则；execution_agent 保持 auto，实施前按实际绑定 Agent 和修改路径重新解析。
- 影响区域：skills/**、resources/**、policies/**、tests/**。
- 实施约束：runtime 已强制的规则从 Skill 正文删除；手动 humanizer 保留且不成为强制步骤；冻结入口只同步许可的全局调用与交接变化。 关键契约以源 Spec 原文为准；不推送、不建 MR、不写外部系统。
- 验证：对照 Spec 核对主链、确认条件、六处引用、文档循环、知识与摘要；自动化验证可检查的引用/章节，不把文本存在等同实跑效果。
- 测试边界：以上 test_commands 为声明；与项目配置的匹配在新 runtime 生效后校验。旧 runtime 施工并非本 Spec 的必需条件，不能伪造实施 receipt。

## 验收标准

- [ ] grilling/grill-with-docs 按依赖批量提问并给推荐答案，复杂或类比请求先核对；摘要逐项标来源并提议 quick/standard，无代码库 grill-me 仅产摘要。
- [ ] 主链完成两次对齐后直接调用后续 Skill；对齐点 2 包括 Spec、逐 Ticket 行为、依赖、测试命令与边界；按顺序实施，不让用户逐段手动调用。
- [ ] 找用户完整条件只在一份共享资源定义，相关 Skill/权威资源引用；覆盖对齐、用户专属选择、审查停止、外部操作、范围外文档、setup/migrate、非主链 handoff 与环境阻塞。
- [ ] 审查循环规则在一份共享资源覆盖 M4 与第 4 节全部要点，指定六个 Skill 引用；第一轮穷尽 coverage、复审限定影响、建议不修复、下游归建议、修复仅改正删除收窄、同事实联动和单一规则定义。
- [ ] standard 派新上下文只读审查者，继承模型与思考档位并记实际模型；派不出时如实 self；文档最多四轮、记录产物与轮次等日志、不能通过扩范围重置，停止交用户裁决；已决清单不能重开。
- [ ] implement 在动手前补写实施计划并按 runtime 状态恢复；quick 摘要有逐条验收→不同测试→代码位置；收尾沉淀 CONTEXT/ADR、全部固定摘要节、建议/已知问题/介入/未验证项。
- [ ] to-spec 不依赖长期 Spec；domain-modeling 写项目级术语和 ADR；handoff 仅用于换宿主/目录/人或未成 Spec 的访谈，取消 ready/draft 与独立重建门槛。
