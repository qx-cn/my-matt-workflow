# 实施适配

从宿主 install-state.json 读取绝对 runtime_entry。开工/恢复先读 status 与 next_command，核对当前定义和证据；不手算哈希、不凭旧总结跳阶段。需要 checkpoint/压缩或换上下文时读取[上下文与恢复](../../policies/context-hygiene.md)。

standard 用 batch plan 保存确认的分组及理由，默认 Topic 一个批次。依依赖执行 implement start/test/self-review/finish：定向验证，六类风险自审可引用可定位证据，逐张本地提交。高风险 Ticket 的额外 implement review 不能替代批次审查。可跨会话恢复，不要求整个批次保留在无限上下文。

全部提交后 batch test/review；宿主派真实新上下文并提交绑定当前内容的结果。修复登记发现 id，再测试、复审、batch close。可运行基线与当前结果比较；基线不可运行不掩盖当前实际失败，当前通过只证明当前命令通过，不能宣称无回归。观察到的失败、未解决阻断、spec-challenge和已选 fix-in-batch 未修复不得普通收口；缺执行证据明确未知，按 runtime 返回条件处理，不虚构 receipt。

多批次最后收口前可选 topic review，执行了则必须有当前有效通过记录；未执行不阻断。所有批次收口后 topic complete。批次收口后历史保留，另建补偿/迁移；整分支修复落最后批次。审查预算、来源和停止只由[审查循环](../review-loop.md)定义。

quick 不建 Spec/Ticket，直接实施、定向验证及简洁自审，摘要按[交付规则](../workflow-delivery.md)。旧版活动工作按 runtime recovery 补采必要证据并重评当前条件，不编造旧记录；已完成历史不因缺新增字段回写。
