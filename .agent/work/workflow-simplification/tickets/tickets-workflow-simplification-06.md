---
id: "workflow-simplification-06"
title: "限制审查轮数并处理 Ticket 裁决"
ticket_kind: "implementation"
spec_id: "workflow-simplification"
spec_revision: 1
spec_ref: ".agent/work/workflow-simplification/specs/specs-workflow-simplification.md"
supersedes_ticket: []
compensates: []
status: complete
blocked_by: ["workflow-simplification-05"]
claimed_by: 
tags: []
sequence: 6
test_commands: ["python3 -m unittest discover -s tests"]
rule_sources: [".agent/work/workflow-simplification/specs/specs-workflow-simplification.md", "resources/testing-seams.md"]
rule_scope: ["tools/**", "tests/**"]
rule_constraints: ["Spec 核心模型为状态与命令唯一权威；范围外工作不实施。", "验证仅断言可观察命令结果、状态、提交、归档和度量，不复刻内部算法。", "只 reopen 能重置 runtime 轮数；不因同会话重复派审重置；接受不能绕过测试。"]
rule_conflicts: []
review_probes: ["recovery"]
execution_agent: "auto"
---

# 06 — 限制审查轮数并处理 Ticket 裁决

**要构建什么：** 审查遇到上限、停止信号或设计问题时停止；用户接受可完成 Ticket，修订定义后重开可继续实施。

**被谁阻塞：** 05 — 按五步完成并提交单张 Ticket

## 适用规则与影响区域

- 规则来源：源 Spec revision 1（M3 定义变化、M4、M5 Ticket accept；第 4 节；AC-17、18、19）；共享测试 seam 约定。当前 Codex resolve-rules 未发现仓库原生规则；execution_agent 保持 auto，实施前按实际绑定 Agent 和修改路径重新解析。
- 影响区域：tools/**、tests/**。
- 实施约束：只 reopen 能重置 runtime 轮数；不因同会话重复派审重置；接受不能绕过测试。 关键契约以源 Spec 原文为准；不推送、不建 MR、不写外部系统。
- 验证：CLI 测试覆盖四轮边界、四种信号、行号换算、accept 正反例和 reopen 前后状态。
- 测试边界：以上 test_commands 为声明；与项目配置的匹配在新 runtime 生效后校验。旧 runtime 施工并非本 Spec 的必需条件，不能伪造实施 receipt。

## 验收标准

- [x] 最多四轮，pass 后内容变化仍消耗下一轮；第四轮阻断或第四轮通过后失效再申请审查均置 needs-user，拒绝第五轮。blocked-by-design/inconclusive 同样立即停止。
- [x] 四个停止信号各有可达用例：连续复审阻断落在前次修复内、相邻修复在中间快照行号重叠、contradicts 指向旧问题、基线增删行超过第一轮的 1.5 倍；原因可见。
- [x] needs-user 拒绝继续开轮，但可运行测试；accept 必须测试在当前内容通过且满足 I-K1，有内容才提交，complete 和 accepted 度量同步，剩余阻断作为已知问题。
- [x] reopen 从 implementing/needs-user 均可执行，但仅 status、claimed_by、复选框变化时拒绝；Ticket 定义或 Spec 改变后重读校验，保留代码与基线，测试/审查记录作废，轮数和信号归零。
- [x] 修订后的测试声明重新按 I-K2 校验并生效；每条裁决理由保存；重启 CLI 后轮数、停止原因和定义快照仍有效。
