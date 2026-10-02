---
name: my-to-tickets
description: 在 my-to-spec、my-triage 流程中作为指定阶段的工作单元被调用。
---

遵循[指令权威](references/shared/instruction-authority.md)。

# 拆分 Ticket

只负责切分和覆盖，不执行设计审查。拆分发现设计问题时退回 Spec 修订，不在 Ticket 正文补设计。每张 Ticket 完成后系统必须一致、可发布；明知留下可达缺陷等后续修复，仅在对齐点2明确确认且中间状态有开关或其他隔离手段时允许。正文不写死非契约性内部函数名、局部算法步骤。

从当前有效 Spec 形成 tracer-bullet 纵向切片，每张穿过必要层次的完整路径、可独立演示验收、能在新上下文完成。声明真正阻塞边，不为顺序造依赖；机械大范围重构保留 expand–contract 例外：先兼容扩展、分批迁移、最后集成删除。

先读 `.agent/matt-workflow.md`、源 Spec 血缘、[项目规则解析](references/shared/adapters/project-rules.md)和代码，按[最终态写作](references/shared/final-state-writing.md)处理有效要求。建立 acceptance coverage：源验收各有明确 owner，Ticket验收可回指用户要求及来源，避免遗漏或未授权重复；跨 Ticket 才能证明的用户结果明确由集成 Ticket 或批次验证承接，内部契约通过却违背上游目的时进入 Spec 挑战；承重切片按[第一性原理推理](references/shared/first-principles-reasoning.md)核对必要贡献。

默认整个 Topic 一个批次；仅天然集成边界或超过保守启发式（预计超过 8 张 Ticket 或 20 个改动文件）时拆批次。阈值是方法内可调整启发式，不是用户配置，尚无实测依据。

## 对齐点2

与 Spec 一起呈现批次划分和理由、逐张标题、要实现的行为、依赖、影响区域、规则、test_commands 和测试边界。按[找用户的条件](references/shared/user-intervention.md)取得用户对整份 Spec/拆分的确认；不要把 Spec 已确认误当第二对齐点已通过，也不让用户逐段手动调用。

按[Ticket 格式](TICKET-FORMATS.md)保存 local 文件，填写 spec_id、spec_revision、spec_ref。先为每张 Ticket 确定 `execution_agent`：用户或已批准材料明确分配时沿用，否则沿用项目的 default_execution_agent；auto 到开工才绑定实际宿主。Spec 要求持久化恢复或外部副作用未知响应时，review_probes 分别声明 recovery 或 unknown-response，其他保持空列表。测试断言可观察结果，不复刻内部算法。修订只更新受影响未完成工作，批次收口后批次已收口的 Ticket 保持历史；需要改变已完成结果时另建补偿或迁移。

用户确认后用 batch plan 将划分及理由写入 Topic 持久状态。用户只要求拆分时交付 Ticket 并停止；开发阶段已获确认则直接调用 {{skill-call:my-implement}} 按依赖逐张完成。逐张定向测试、增强自审和本地提交，批次末 batch test/review/close；全部批次收口后，再依[交付规则](references/shared/workflow-delivery.md)收尾。quick 不进入本Skill。对外发布按共同确认条件；不修改父Issue。
