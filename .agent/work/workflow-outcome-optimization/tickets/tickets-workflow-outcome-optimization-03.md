---
id: workflow-outcome-optimization-03
title: Skill、规则、调用及按需加载统一
ticket_kind: implementation
spec_id: workflow-outcome-optimization
spec_revision: 2
spec_ref: .agent/work/workflow-outcome-optimization/specs/specs-workflow-outcome-optimization-02.md
status: ready-for-agent
blocked_by: []
claimed_by:
execution_agent: codex
sequence: 3
supersedes_ticket: []
compensates: []
tags: [outcome-optimization]
test_commands: ["python3 -m unittest discover -s tests"]
review_probes: []
touchpoints: ["skills", "resources", "policies", "composition/manifest.json", "tests/test_composition.py", "tests/test_resources.py", "tests/test_workflow_texts_v2.py", "tests/test_design_contract.py", "tests/test_teach_quality.py"]
---

# 03 — Skill、规则、调用及按需加载统一

## 要构建什么

统一授权与生命周期，补triage血缘，允许多对多证据与持久化验证，风险触发加载；修排障和写作冲突，保留需求与审查有效机制。

## 施工与授权

用户已接受 Spec 方向，要求“做好任务分工协调，进行并行施工”。本票处于该范围内。子 Agent 在隔离 worktree 准备变更，主 Agent 串行集成、绑定证据和收口；不新增 runtime 并行 lane。Spec revision 2 原文保留。发布、真实宿主安装和模型效果对照属另行授权阶段；临时目录的发布/安装fixture属于验证。

## 适用规则与验证

执行 Agent 为 Codex；runtime 开工按实际影响路径解析。用户 AGENTS 要求表达按信息类型/目标读者选择，Agent合同显式低歧义；改动不以减字数为目标。定向命令验证本票，完整 suite 与独立审查在集成批次执行。

## 验收标准

- [ ] AC04 — 已配置 local 项目首次 triage 新 Bug、没有 Spec 时能从 confirmed brief 形成有事实来源的 Spec，再到合法 Ticket；有匹配 Spec 时复用。既有需求不重复访谈，风险设计关口不重复。
- [ ] AC05 — 用户“只出 Spec”时停于 Spec；明确批准范围内开发时继续完成。授权同一具体外部动作后不重复询问；未授权目的地或 scope 变化仍请求恰当决定。宿主权限保持有效。
- [ ] AC06 — 一项生命周期测试有分别可定位的断言时可覆盖多个验收；单项验收需多种证据时不得被一个测试替代。缺失验收必须暴露。
- [ ] AC07 — 写入数据约束/脱敏、事务及 close/reopen 的独立存储验证被允许；同一有缺陷的读写接口不能作为唯一正确性 oracle。正式路由/adapter 接入遗漏能被相应案例检出。
- [ ] AC08 — 新抽象不会只因“生产 + 测试”两个 adapter 被要求增设；已有边界可注入替身，不强迫改公开接口。
- [ ] AC10 — 为已批准行为增加负向回归测试不触发新增需求门禁；新增产品行为或改变验收仍交用户决定。
- [ ] AC11 — 新上下文与 self 的来源可核实；同会话自审不能被标 independent，用户指定独立性和模型/成本限制得到遵守。
- [ ] AC12 — 核心调用路径没有旧 Topic test/review 硬要求；源文本、组合/分发与三宿主投影一致，所有声明路径可达。每个审查对象有唯一 inventory 行和明确处置。
- [ ] AC13 — quick 不强制空六节和完整标准摘要，仍可重建各验收、实际验证、关键风险与缺口。standard 仍覆盖六类风险，允许引用证据而非复制。
- [ ] AC14 — 换宿主必须交接时不被“空间足够”分支吞掉；跨上下文恢复能重建目标、授权、定义、状态、证据与下一步，不要求模型遗忘或保留无限上下文。
- [ ] AC15 — 简单教学结构可以有理由地选择文字；复杂图保留必要文字定义。项目既有术语不受统一禁词影响。
- [ ] AC23 — 慢恢复、间歇故障、必须先读调用链才能造复现三类案例都能推进调查；不因秒级、完全最小或固定假设数量硬停。证据不足的 root cause 保持假设，原场景未验证保持缺口；有效修复用原症状及能区分原因的回归验证。
- [ ] AC24 — 对有决定性歧义的请求，需求和验收能区分影响交付的解释，并回溯用户材料或标记假设；明确请求不重复访谈。跨 Ticket 集成的用户结果有验收归属，内部契约通过但违背上游目的的案例能进入 Spec 挑战，不能计正确交付。
- [ ] AC25 — 选取面向 Agent 的 Spec 与面向人的说明各一份，独立读者仅凭有效正文能识别当前规则、必要前提、下一步及限制；无相互冲突的修订补丁。事实/推断/未知可区分，缺来源不杜撰，简单内容无需强制图示或润色工序。另给仅有测试代码、无运行日志的任务：准确提取静态输入/断言与替身边界，设计动机未知且不宣称通过；补充失败日志后明确报告失败。能力效果另按第 8 节测量，不能把格式检查当写作水平证明。
