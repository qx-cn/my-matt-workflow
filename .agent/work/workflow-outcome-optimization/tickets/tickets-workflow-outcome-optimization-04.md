---
id: workflow-outcome-optimization-04
title: 集成交付、完整变更索引与效果验证说明
ticket_kind: implementation
spec_id: workflow-outcome-optimization
spec_revision: 2
spec_ref: .agent/work/workflow-outcome-optimization/specs/specs-workflow-outcome-optimization-02.md
status: completed
completion_source: direct-engineering
blocked_by: ["workflow-outcome-optimization-01", "workflow-outcome-optimization-02", "workflow-outcome-optimization-03"]
claimed_by: direct-engineering-team
execution_agent: codex
sequence: 4
supersedes_ticket: []
compensates: []
tags: [outcome-optimization]
test_commands: ["python3 -m unittest discover -s tests"]
review_probes: []
touchpoints: ["README.md", ".agent/work/workflow-outcome-optimization", "tests/test_final_integration.py", "tests/test_workflow.py", "tests/test_portfolio.py", "resources/governance.json"]
---

# 04 — 集成交付、完整变更索引与效果验证说明

## 要构建什么

集成前三组，交完整可替换源码、对象归宿/AC证据和真实任务评估说明，完成独立审查；源码验证不冒充能力效果。

## 施工与授权

用户已接受 Spec 方向，要求“做好任务分工协调，进行并行施工”。本票处于该范围内。子 Agent 在隔离 worktree 准备变更，主 Agent 串行集成并核对实际工程证据；不新增 runtime 并行 lane。Spec revision 2 原文保留。发布、真实宿主安装和模型效果对照属另行授权阶段；临时目录的发布/安装fixture属于验证。

## 适用规则与验证

执行 Agent 为 Codex；实际改动按路径核对项目规则；施工不由被测runtime管理。用户 AGENTS 要求表达按信息类型/目标读者选择，Agent合同显式低歧义；改动不以减字数为目标。定向命令验证本票，完整 suite 与普通独立代码审查在集成后执行。

用户补充禁止自托管施工：不调用本workflow自身Skill或runtime管理进度，不产生自签完成回执；direct-engineering实际证据决定状态。

## 验收标准

- [x] AC16 — 交付一套可直接替换的完整源码/发布包，包含所有受影响正文、辅助文件、清单、runtime、测试和使用说明；明确删除/合并项及兼容限制，不仅交零散新条款。发布和每个宿主安装仅在分别授权后执行。
- [x] AC17 — 验证报告区分文本/机械契约、最小行为探针、历史实用证据和同条件模型对照；没有对照结果时不声称提升成功率或一次做对率。
- [x] AC26 — 七项能力各有明确机制、代表任务、可观察指标和限制；正确交付分母包含全部已分配任务，blocked/超时/环境失败不静默剔除。首次独立验收、修复后最终正确、错误完成声明分开记录；未授权行为列为自动化失败而非成功。没有试验结果时只报告待验证预期。

## 普通工程完成证据

本票按 direct-engineering 完成。最终 338 项完整 unittest 退出 0；限定独立审查发现已修复，未解阻塞 0。实际证据与边界见 `../evidence/acceptance-evidence-02.json`、`../evidence/independent-review-provenance.json` 和 `../deliveries/deliveries-workflow-outcome-optimization-02.md`。这不是产品 runtime 的完成回执；未发布或安装真实宿主，未做模型效果对照。
