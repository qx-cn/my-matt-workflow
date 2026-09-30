---
id: "workflow-simplification-03"
title: "从 Ticket 启动实施并登记真实测试"
ticket_kind: "implementation"
spec_id: "workflow-simplification"
spec_revision: 1
spec_ref: ".agent/work/workflow-simplification/specs/specs-workflow-simplification.md"
supersedes_ticket: []
compensates: []
status: complete
blocked_by: ["workflow-simplification-02"]
claimed_by: 
tags: []
sequence: 3
test_commands: ["python3 -m unittest discover -s tests"]
rule_sources: [".agent/work/workflow-simplification/specs/specs-workflow-simplification.md", "resources/testing-seams.md"]
rule_scope: ["tools/**", "tests/**"]
rule_constraints: ["Spec 核心模型为状态与命令唯一权威；范围外工作不实施。", "验证仅断言可观察命令结果、状态、提交、归档和度量，不复刻内部算法。", "以外部 CLI 和内容状态测试，argv 不经过 shell；简报不进入 Spec 血缘。"]
rule_conflicts: []
review_probes: ["recovery"]
execution_agent: "auto"
---

# 03 — 从 Ticket 启动实施并登记真实测试

**要构建什么：** 用户选择合格 Ticket 后获得执行简报，并直接运行其声明的测试；失败和定义变化不会被误判为可以完成。

**被谁阻塞：** 02 — 创建配置 v2 与可完成的 quick Topic

## 适用规则与影响区域

- 规则来源：源 Spec revision 1（M1–M3、M5 记录绑定、M6；第 3 节；AC-06 自动补建、08、10、12、14 Ticket 定位、25 自动补建入口）；共享测试 seam 约定。当前 Codex resolve-rules 未发现仓库原生规则；execution_agent 保持 auto，实施前按实际绑定 Agent 和修改路径重新解析。
- 影响区域：tools/**、tests/**。
- 实施约束：以外部 CLI 和内容状态测试，argv 不经过 shell；简报不进入 Spec 血缘。 关键契约以源 Spec 原文为准；不推送、不建 MR、不写外部系统。
- 验证：真实临时 git 仓库覆盖准入、自动补建、前缀匹配、失败退出与多 Topic 隔离；不要求本阶段能 finish。
- 测试边界：以上 test_commands 为声明；与项目配置的匹配在新 runtime 生效后校验。旧 runtime 施工并非本 Spec 的必需条件，不能伪造实施 receipt。

## 验收标准

- [x] validate-ticket 接受 Spec 第 3 节字段，检查非空 test_commands、来源血缘、依赖和规则冲突；shlex argv 匹配支持配置前缀加零或多个参数，拒绝 unittestx 等伪前缀。
- [x] implement start 拒绝未完成依赖、脏内容、quick 和同 Topic 已有 implementing/needs-user；待补建自动成为 standard，基线取与默认分支分叉点，并再次校验全量测试非空。
- [x] 执行 M2 分支规则；记录 Ticket 基线及定义快照；生成包含 Ticket、Spec 验收、已完成前置提交与改动文件、适用规则和测试命令的简报，预留 Agent 实施计划。
- [x] implement test 不带 argv 时逐条执行声明测试并绑定当前内容；任一失败非零退出，显示失败命令、退出码和输出末尾；status 给出重测命令，不给 finish。
- [x] 带 argv 的匹配测试仅用于进度，不计入完成依据；在 implementing/needs-user 中 test_commands 偏离定义快照时拒绝，提示恢复或用户修订后 reopen。
- [x] ticket id 自带 Topic；省略 ticket 时只选择指定 Topic 唯一的实施中/needs-user Ticket，无候选则提示 topic status；topic A 的测试不能运行 topic B 的 Ticket。
