# 补偿 Ticket 15：证据消费契约

引用：Spec workflow-simplification r1；独立补审 CR02-C1、03-C1、IND04-S1；原 Ticket 02–04 保持 complete，不改写原审核与 receipt。

## 当前接口

- 配置：renderer 对全部字段采用 JSON 编码。reader 对已知字符串字段兼容旧 v2 裸标量字符串；JSON 对象和列表保留结构类型并由类型校验拒绝，schema_version 和列表字段保持结构解析及严格类型校验。Git 分支 null/true/数字均为字符串，Git 非法反斜线分支由 setup 原有校验拒绝。旧裸值与 JSON 字符串字面量本身歧义时，以既有 JSON 字符串语义为准；新 renderer 消除此歧义。
- 正式测试：`unit.test_run` 表示最近一次完整声明执行，包含批次 id、按声明顺序的 argv 和 completed；每条历史测试保存 run_id 与 command_index。completed 仅表示本批执行完毕，通过还需要每个位置的退出码为 0、内容 id 与当前一致。开始正式测试前先登记未完成批次；中断不会复用旧 pass。局部 progress 不替换正式批次。
- 兼容旧实施记录：历史 tests 保留；没有 test_run 完整性证明时 tests_passed=false，需要完整重测。不从最后一条同 argv 的成功推断整次通过。
- 审查：coverage_targets 从同一冻结 Spec 中同时提取数字编号和字母前缀的不变量，去重后沿用严格 coverage 校验。未覆盖不变量不能 pass，不适用必须说明原因。

## 后续 owner

Ticket 05 的 finish 应调用同一 tests_passed 判断，不能从原始 tests 再建 argv→最后成功映射。Ticket 06 的 reopen 清空测试/审查历史时应同时清除 test_run。Ticket 08 的迁移不应把缺失批次证明的历史测试恢复为完成资格。这些消费者仍由其原 Ticket 实施，本补偿 Ticket 不提前实现。

## 验证边界

公共 CLI 临时 Git 仓库验证配置往返、测试判定、中断重启、旧记录重测、coverage 缺失拒绝与完整提交；不构成宿主安装、其他项目迁移、生产运行或 Python 3.10 验证。最终测试与独立审查状态以 Ticket 15 的 runtime receipts 为准。
