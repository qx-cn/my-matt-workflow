# Ticket 06 handoff

## 实现

`review_loop` 对冻结差异计数，最多四轮；第四轮阻断、耗尽后通过失效、设计/证据结论及四种停止信号进入 needs-user。相邻修复比较前一差异 new 与后一差异 old，两者都属于中间快照，不混用工作树行号。

`ticket_resolution` 提供有理由的 accept/reopen。接受需要当前完整声明测试，保留已知问题并复用完成提交；reopen 只接受 Ticket 稳定定义或 Spec 变化，重新验证测试 argv，保留基线与代码，清空测试/审查及停止信号。裁决历史保留。

## 验证

10 项独立 CLI 用例覆盖四轮通过后失效、四轮阻断、inconclusive/blocked-by-design、四种停止信号、重开定义门、修订测试及私有接受提交。13 项 review 基础回归通过。全量状态以 journal 的实际 receipt 为准。

## 后续 owner

07 可复用 review_loop、冻结文件/结果校验和测试批次绑定，整分支对象必须有独立轮数与定义快照。不得借用已完成 Ticket 的审查通过作为分支通过。

## 证据边界

本票增强自审；05–07 最终统一独立审核。仅本地开发与提交，无推送或安装。
