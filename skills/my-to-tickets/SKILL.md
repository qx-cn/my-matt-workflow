---
name: my-to-tickets
description: 在 my-to-spec、my-triage 流程中作为指定阶段的工作单元被调用。
---

遵循[指令权威](references/shared/instruction-authority.md)。

# 拆分 Ticket

从当前有效 Spec 形成 tracer-bullet 纵向切片，每张穿过必要层次的完整路径、可独立演示验收、能在新上下文完成。声明真正阻塞边，不为顺序造依赖；机械大范围重构保留 expand–contract 例外：先兼容扩展、分批迁移、最后集成删除。

先读 `.agent/matt-workflow.md`、源 Spec 血缘、[项目规则解析](references/shared/adapters/project-rules.md)和代码，按[最终态写作](references/shared/final-state-writing.md)处理有效要求。建立 acceptance coverage：源验收各有明确owner，Ticket验收可回指要求，避免遗漏或未授权重复；承重切片按[第一性原理推理](references/shared/first-principles-reasoning.md)核对必要贡献。

## 对齐点2

与 Spec 一起呈现逐张标题、要实现的行为、依赖、影响区域、规则、test_commands 和测试边界。按[找用户的条件](references/shared/user-intervention.md)取得用户对整份 Spec/拆分的确认；不要把 Spec 已确认误当第二对齐点已通过，也不让用户逐段手动调用。

按[Ticket 格式](TICKET-FORMATS.md)保存 local 文件，填写 spec_id、spec_revision、spec_ref。先为每张 Ticket 确定 `execution_agent`：用户或已批准材料明确分配时沿用，否则沿用项目的 default_execution_agent；auto 到开工才绑定实际宿主。Spec 要求持久化恢复或外部副作用未知响应时，review_probes 分别声明 recovery 或 unknown-response，其他保持空列表。测试断言可观察结果，不复刻内部算法。修订只更新受影响未完成工作，已完成Ticket保持历史；需要改变已完成结果时另建补偿或迁移。

确认后直接调用 {{skill-call:my-implement}} 按依赖逐张完成。全部完成后多 Ticket 跑 Topic test/review，再依[交付规则](references/shared/workflow-delivery.md)收尾。quick 不进入本Skill。对外发布按共同确认条件；不修改父Issue。
