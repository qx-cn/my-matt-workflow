# Ticket 05 handoff

## 实现

`ticket_completion.finish` 验证当前完整测试批次、冻结审查登记、稳定定义和全部复选框。共享模式合并内容/元数据提交；私有模式先提交内容，并保留成功提交以重试元数据失败。完成后追加 ticket/complete 度量，并选择真正可准入的下一票。单票 standard 支持八章节摘要门及归档。

## 验证

`tests/test_implement_finish.py` 五项 CLI 测试通过，覆盖五步/归档、缺少审查/未勾选/过期内容、私有元数据 hook 失败重试、无内容提交/下一票、修复 notes 正文。已有 implementation/review 链路覆盖声明测试失败、ignored/agent 内容绑定和仅建议归一化。

## 后续 owner

06 负责四轮计数、停止信号、needs-user、accept/reopen；可复用 `require_pass` 和完成提交实现。07 接入多票 Topic 测试、整分支审查及收尾。

## 证据边界

本票同会话增强自审，批次 05–07 全部完成后另做独立审核。全量测试和正式关闭以 runtime journal 的实际 receipt 为准。没有推送或安装。
