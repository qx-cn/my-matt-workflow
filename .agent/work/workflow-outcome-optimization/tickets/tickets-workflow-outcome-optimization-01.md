---
id: workflow-outcome-optimization-01
title: runtime 正确完成、证据与恢复收敛
ticket_kind: implementation
spec_id: workflow-outcome-optimization
spec_revision: 2
spec_ref: .agent/work/workflow-outcome-optimization/specs/specs-workflow-outcome-optimization-02.md
status: completed
completion_source: direct-engineering
blocked_by: []
claimed_by: direct-engineering-team
execution_agent: codex
sequence: 1
supersedes_ticket: []
compensates: []
tags: [outcome-optimization]
test_commands: ["python3 -m unittest discover -s tests"]
review_probes: [recovery]
touchpoints: ["tools/workflow_lib", "tests/test_batches.py", "tests/test_implement_finish.py", "tests/test_implement_lifecycle.py", "tests/test_implement_review.py", "tests/test_review_resolution.py", "tests/test_review_snapshot.py", "tests/test_topic_branch.py", "tests/test_topic_lifecycle.py"]
---

# 01 — runtime 正确完成、证据与恢复收敛

## 要构建什么

共用状态/证据判定，当前失败、未解发现与内容中断控制完成；恢复保留历史、来源与不同审查scope。

## 施工与授权

用户已接受 Spec 方向，要求“做好任务分工协调，进行并行施工”。本票处于该范围内。子 Agent 在隔离 worktree 准备变更，主 Agent 串行集成并核对实际工程证据；不新增 runtime 并行 lane。Spec revision 2 原文保留。发布、真实宿主安装和模型效果对照属另行授权阶段；临时目录的发布/安装fixture属于验证。

## 适用规则与验证

执行 Agent 为 Codex；实际改动按路径核对项目规则；施工不由被测runtime管理。用户 AGENTS 要求表达按信息类型/目标读者选择，Agent合同显式低歧义；改动不以减字数为目标。定向命令验证本票，完整 suite 与普通独立代码审查在集成后执行。

用户补充禁止自托管施工：不调用本workflow自身Skill或runtime管理进度，不产生自签完成回执；direct-engineering实际证据决定状态。

## 验收标准

- [x] AC01 — 基线不可运行、当前实际失败时，公共 CLI 明确返回当前失败与比较缺口，普通 batch close 拒绝收口；当前通过时保留通过及基线缺口。已知失败、部分执行和跨包同名失败原有正确行为不退化。
- [x] AC02 — 自审含未解决 blocking 时不能 finish；spec-challenge 进入裁决路径，不能继续依赖争议定义的实现。修复后重新登记绑定当前内容的证据可继续，旧发现仍可追溯。
- [x] AC03 — 最后一张 Ticket finish 后返回当前可执行的批次步骤；恢复、批次修复、可选 Topic review 与 Topic complete 的 status/next_command 一致。
- [x] AC09 — 两次修复触及相同行且当前审查 pass 时正常通过；体积越阈值不单独硬停。预算耗尽、真实 spec-challenge 或证据不足仍遵循既有停止路径。
- [x] AC18 — 候选 runtime 恢复旧活动记录时重评当前失败、未解决发现和停止状态，未知字段不补成功。升级前已合法完成的历史不重开；旧 writer 混写限制与参与宿主切换方案明确披露，未经授权不安装/迁移。
- [x] AC19 — runtime 共用逻辑后 Ticket、batch、quick 的成功语义不混淆；执行中断、内容变化、部分失败不能借旧记录通过。status 与 mutation 的下一步一致，状态在两者之间变化时写入重检并拒绝失效动作。Ticket 下游定义、branch HEAD、artifact scope 校验各自保留。

## 普通工程完成证据

本票按 direct-engineering 完成。最终 338 项完整 unittest 退出 0；限定独立审查发现已修复，未解阻塞 0。实际证据与边界见 `../evidence/acceptance-evidence-02.json`、`../evidence/independent-review-provenance.json` 和 `../deliveries/deliveries-workflow-outcome-optimization-02.md`。这不是产品 runtime 的完成回执；未发布或安装真实宿主，未做模型效果对照。
