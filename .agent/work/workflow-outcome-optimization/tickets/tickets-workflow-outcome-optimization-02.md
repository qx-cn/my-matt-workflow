---
id: workflow-outcome-optimization-02
title: 安装升级去重、等价投影与无变化短路
ticket_kind: implementation
spec_id: workflow-outcome-optimization
spec_revision: 2
spec_ref: .agent/work/workflow-outcome-optimization/specs/specs-workflow-outcome-optimization-02.md
status: ready-for-agent
blocked_by: []
claimed_by:
execution_agent: codex
sequence: 2
supersedes_ticket: []
compensates: []
tags: [outcome-optimization]
test_commands: ["python3 -m unittest discover -s tests"]
review_probes: [recovery]
touchpoints: ["tools/workflow.py", "tools/workflow_lib/installer.py", "tools/workflow_lib/release.py", "tools/workflow_lib/doctor.py", "tools/workflow_lib/projection.py", "tests/test_skill_packaging_v2.py", "tests/test_security_hardening.py", "tests/test_doctor.py"]
---

# 02 — 安装升级去重、等价投影与无变化短路

## 要构建什么

一次稳定快照完整检查；同操作受保护验证复用；投影清单字节等价，无变化免临时打包和重写而不省必需检查。

## 施工与授权

用户已接受 Spec 方向，要求“做好任务分工协调，进行并行施工”。本票处于该范围内。子 Agent 在隔离 worktree 准备变更，主 Agent 串行集成、绑定证据和收口；不新增 runtime 并行 lane。Spec revision 2 原文保留。发布、真实宿主安装和模型效果对照属另行授权阶段；临时目录的发布/安装fixture属于验证。

## 适用规则与验证

执行 Agent 为 Codex；runtime 开工按实际影响路径解析。用户 AGENTS 要求表达按信息类型/目标读者选择，Agent合同显式低歧义；改动不以减字数为目标。定向命令验证本票，完整 suite 与独立审查在集成批次执行。

## 验收标准

- [ ] AC20 — 正常稳定的源码变化 deploy 仅在最终打包快照上执行一轮完整 suite；失败不发布，漂移拒绝或重新取快照。同操作对受保护的同内容 release 复用验证；不同旧包、新包及漂移后对象不混用。记录实际 suite 与验证次数，不仅检查输出文案。
- [ ] AC21 — 构建输入不变且 release/目标实际内容正确时，无变化 deploy 返回 current，不临时打包或重写目标；它仍可运行一轮 check。release 或已安装内容篡改能被发现，不能误报 current；旧摘要缺失回退有效校验。源码、测试/配置、构建/投影器和 upstream 参数变化走相应重新校验路径，不能误用产物身份代替测试身份。
- [ ] AC22 — 所有支持宿主的新投影清单与原物理投影逐字节等价；路径/链接保护、非托管同名目录、安装中断回滚、并发写、最终目标校验不退化。安装已有 release 不额外运行源码完整 suite；多宿主结果分别呈现。验证重复减少须附计数与阶段耗时，性能收益不预填百分比。
