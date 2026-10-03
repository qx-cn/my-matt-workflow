---
name: my-grill-with-docs
description: 通过高强度访谈澄清设计决定，并在过程中建立 ADR 与术语表。
disable-model-invocation: true
---

# 从需求到交付

已有确认摘要直接复用；只有未决需求会改变交付时调用 {{skill-call:my-grilling}}，只有承重领域术语含义未清时调用 {{skill-call:my-domain-modeling}}，分别按需处理；方法完成后返回本流程。复杂或类比请求在摘要形成前读取[需求核对](references/shared/requirement-analysis.md)。共同遵循[找用户的条件](references/shared/user-intervention.md)。

没有代码库时采用 my-grill-me 的访谈用途，只产需求摘要，停止主链；不创建 Topic、Spec 或 Ticket。

## 对齐点1

输出目标、范围、约束、可观察验收与“待在代码中核实的现状假设”（能直接查到的先查证，不问用户），逐项注明来自用户原文、仓库事实或待确认推断；按[保证等级](references/shared/adapters/assurance-levels.md)提议 quick/standard 及理由。按[产物存储](references/shared/adapters/artifact-storage.md)保存 `requirements/requirements-<topic>-01.md`。用户确认后执行 topic start；配置缺失时先完成 setup。

quick 直接实施和自审，不创建 Spec/Ticket；遵循[实施适配](references/shared/adapters/implementation-session.md)与[交付规则](references/shared/workflow-delivery.md)，完成 Topic。

standard 在授权阶段内直接调用 {{skill-call:my-to-spec}}，用户只要求当前摘要时交付并停止；由它继续 to-tickets；两者合并呈现对齐点2。用户确认后按依赖逐张实施。逐张定向测试、自审、本地提交；批次末 batch test/review/close。整分支审查可选、不能替代批次审查；全部批次收口后沉淀长期知识、写摘要，再 topic complete。中间直接调用已确认阶段，用户无需手动切换 Skill。
