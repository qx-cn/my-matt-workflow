# 实施适配

从宿主 install-state.json 读绝对 runtime_entry。恢复先读 status，按 next_command 继续；不用手写哈希或内容 id。

standard 的已确认划分用 `batch plan --groups-file <JSON数组> --reason <理由>` 保存；默认整个 Topic 一个批次。一个会话依依赖顺序执行 implement start/test/self-review/finish：定向命令，六节增强自审传 notes-file，逐张本地提交，已提交 Ticket 等批次收口。高风险 Ticket 可额外 implement review --reason <触发理由> --reviewer-model <实际模型>；不能替代批次审查。

全部提交后 batch test/review（宿主派新上下文，提交预填结果骨架），修复用 batch repair --notes-file 引用发现 id，然后重新测试、复审、batch close。全量测试相对首次基线没有新增失败才可收口；基线已有失败与无法运行命令进入摘要。内容或 HEAD 变化需要复审。批次收口后历史不可改写，另建补偿或迁移；可选整分支修复落最后批次。

多批次最后收口前可 topic review --initiated-by user|agent --reason <理由>，以 Topic 基线到当前提交审查。未执行不阻断完成；执行了需当前通过记录。所有批次收口后 topic complete。不具备新上下文时如实记 self 并披露独立性缺口。规则只在[审查循环](../review-loop.md)定义。

quick 不建 Spec/Ticket，直接实施、定向测试和同会话六节自审，写[交付摘要](../workflow-delivery.md)；归档仍由 runtime 完成。旧版已有实施历史可恢复原 Ticket 协议，不虚构新的批次审查记录。
