# 本批实施契约：05–07

用户于本会话明确选择 05–07，并要求自动推进、单 Ticket 自审、批末统一独立审核、随后修复至无有效问题。模式采用 full-auto，保持 standard/local/shared；外部写入仍 confirm，未授权推送或安装。模型与思考配置继承，不能升级。

- 批次基线：9e24d381a00c51d0df286ccb7ac89f6083963b4f。
- 固定范围：scope-workflow-simplification-05-07.json，按依赖串行；不同时认领有依赖或重叠 scope 的 Ticket。
- 每张：runtime journal→实现→声明测试→冻结增强 self review→提交/关闭→next-ticket 读取同一 scope。
- 批末：在固定批次基线到最终代码的冻结单元上派新上下文独立 reviewer；覆盖 05–07 验收并检查集成影响，不读实施总结。
- 审查 finding：保留已完成 Ticket 与 self 记录。若需要补偿改动，使用引用真实 findings 的新补偿工作单元及单独固定修复范围；不改写本批原始 scope，不重开历史 journal，不靠新 session 重置同一批的修复额度。
- 施工 runtime full-auto 上限五次修复，同根因重复正式停止；本批 ledger 连续记录审核与修复，不因重新派审清零。出现正式阻断时保留证据，不宣称无问题。新产品的四轮规则依 Spec 由 06/07 实现，与施工 runtime 的计数不同。
