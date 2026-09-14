# 开发保证等级

`assurance_level` 与自治、写入和连续 Ticket 策略正交。它只决定完成当前工程任务需要多少持久产物与可恢复证据；更自动不代表可以降低保证，更严格的确认策略也不强制审计级流程。

## quick

只适用于单会话、影响局部、可逆、没有外部副作用，且不涉及安全边界、公开接口、数据语义、持久状态、迁移或兼容承诺的工作。以当前对话中的可追溯需求摘要作为 work unit，完成针对性测试和同会话代码自审；不强制版本化 Spec、Ticket 或 implementation journal。

任一排除条件成立时至少升级为 `standard`。Agent 不得为了省步骤把未知风险分类为 quick。

## standard

默认等级。保留版本化 Spec；单一、单会话切片可直接实施并保存测试与 review 证据，多切片、跨上下文或有依赖图时必须生成 Ticket。存在 Ticket 时使用 implementation journal；没有 Ticket 时不得伪造 journal receipt，只报告实际运行证据。

涉及公开接口、不可逆数据、安全/权限、持久恢复、外部副作用的未知响应、迁移或明确审计要求时升级为 `audited`。

## audited

使用完整 Spec/Ticket 血缘、规则解析、implementation journal、冻结代码与审查输入、runtime test/review/code receipts、受管 repair plan、submit/close 和恢复门禁。沿用现有 implementation session 合同。

## 共同完成标准

三个等级都必须满足当前范围的验收、运行必要测试、如实报告未验证项并完成代码审查。等级改变的是证据持久性和恢复强度，不降低正确性、安全性或用户授权边界。选择结果和升级原因写入当前 Spec、Ticket 或最终证据摘要；不得把同会话自审称为独立评审。
