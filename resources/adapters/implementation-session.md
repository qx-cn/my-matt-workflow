# 实施适配

从宿主 install-state.json 读取绝对 runtime_entry。开工/恢复先读 status 与 next_command，核对当前定义和证据；不手算哈希、不凭旧总结跳阶段。需要 checkpoint/压缩或换上下文时读取[上下文与恢复](../../policies/context-hygiene.md)。

standard 用 batch plan 保存确认的分组及理由，默认 Topic 一个批次。依依赖执行 implement start/test/self-review/finish：定向验证，六类风险自审可引用可定位证据，逐张本地提交。高风险 Ticket 的额外 implement review 不能替代批次审查。可跨会话恢复，不要求整个批次保留在无限上下文。

全部提交后 batch test/review；宿主派真实新上下文并提交绑定当前内容的结果。修复登记发现 id，再测试、复审、batch close。可运行基线与当前结果比较；基线不可运行不掩盖当前实际失败，当前通过只证明当前命令通过，不能宣称无回归。观察到的失败、未解决阻断、spec-challenge和已选 fix-in-batch 未修复不得普通收口；缺执行证据明确未知，按 runtime 返回条件处理，不虚构 receipt。

多批次最后收口前可选 topic review，执行了则必须有当前有效通过记录；未执行不阻断。所有批次收口后 topic complete。批次收口后历史保留，另建补偿/迁移；整分支修复落最后批次。审查预算、来源和停止只由[审查循环](../review-loop.md)定义。

quick 不建 Spec/Ticket，直接实施、定向验证及简洁自审，摘要按[交付规则](../workflow-delivery.md)。旧版活动工作按 runtime recovery 补采必要证据并重评当前条件，不编造旧记录；已完成历史不因缺新增字段回写。

## 技术刷新

为已确认目标纠正事实、补齐实现或调整技术方法，直接更新计划与受影响的未完成定义。记录原因、真实调用方与消费者、验收归属和验证，保持 Spec 版本血缘，不减少验收覆盖或隐藏失败。定义变化或点名处置已登记技术性 spec-challenge 后执行：

```sh
python3 <runtime_entry> resolve --repo <repo> --ticket <id> --refresh --reason '<技术理由>' --notes-file <依据.json>
python3 <runtime_entry> resolve --repo <repo> --branch --topic <topic> --refresh --reason '<技术理由>' --notes-file <依据.json>
python3 <runtime_entry> batch refresh --repo <repo> --topic <topic> --reason '<技术理由>' --notes-file <依据.json>
```

notes-file 是 JSON，字段必须恰为以下六项；没有发现处置用空 findings：

```json
{
  "kind": "technical",
  "adjustment": "调整依据、调用方与消费者、验收归属及可定位验证结果",
  "unchanged_behavior": "保持不变的已确认目标与预期外部行为",
  "unchanged_acceptance": "保持不变的验收语义、覆盖与用户限制、风险承诺",
  "evidence": [{"path": "repo/relative/file", "detail": "可定位位置、观测或命令结果"}],
  "findings": [{"unit_id": "审查单元的确切身份", "finding_id": "发现id", "basis": "为何属于技术事实纠正"}]
}
```

evidence 必须非空，path 为仓库内存在的非空文件，不能跨出仓库或经过符号链接；runtime 自动记录内容哈希。独立审查使用 result 的 unit_id，自审使用 `self:<ticket-id>`。Agent 负责技术与产品性质判断；runtime 校验材料、定义、身份和状态，不把格式通过当语义证明。

refresh 保留基线、原始结果、自审历史、同一 series 全部已开轮次、未解发现与剩余额度，更新相关 Ticket/批次/整分支定义，失效旧测试、自审与通过记录，要求重新验证。已开未提交仍计数，四轮耗尽不能开第五轮。仅追加处置明确点名的技术挑战；其他产品挑战、证据不足、语义矛盾和预算停止仍有效。重复同一刷新不重复计数，旧记录依据实际历史恢复预算，不批量改标签。真正改变用户约定仍请求决定，accept/reopen 保留用户裁决语义；完成历史由后续补偿工作承接。
