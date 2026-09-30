# Ticket 01–04 独立补审

四张 Ticket 的补审均已完成；01 通过，02–04 存在待修复发现。原完成记录、原 self-review 和源码均未改写。本次新增报告是历史交付的独立补审证据，不能解释为四张全部审核通过。

| Ticket | 独立结论 | 发现 |
| --- | --- | --- |
| 01 | pass | 无合格发现 |
| 02 | findings | P2：合法分支名 `null` 被读成 None |
| 03 | findings | P1：重复测试命令先失败后成功，status 误报全部通过 |
| 04 | findings | P1：coverage 漏掉 Spec 数字编号不变量，遗漏仍允许 pass |

## 待修复发现

1. **P1 / 03-C1**：`tools/workflow_lib/ticket_implementation.py:258–260`。合法 test_commands 中相同 argv 执行两次，退出码依次为 9、0；implement test 整体退出 1，但 status 选择最后一条成功记录，返回 tests_passed=true 并指向 review。违反 03#A4，失败证据被掩盖。
2. **P1 / IND04-S1**：`tools/workflow_lib/ticket_review.py:144–145`。coverage 目标提取遗漏 Spec 的 I-1… I-11，缺少这些判断仍可登记 pass；主动补 I-6 却以 target 未声明拒绝。属于 04#A4 当前 coverage 校验职责。
3. **P2 / CR02-C1**：`tools/workflow_lib/topic_service.py:104–107`。setup 接受合法 Git 分支名 null 并退出 0；新解析器把配置值转换为 None，后续 work-overview/topic start 拒绝配置。正式 baseline 同序列成功，交付 head 失败。

三项均有临时仓库公共 CLI 复现和真实退出码；当前 HEAD 的相关实现仍与发现对应冻结代码一致。补偿修复尚未开始，修复后须重新独立审核。

## 独立性与证据

每张 Ticket 使用一个新 reviewer agent，上下文不包含实施总结、handoff 或既有审核，仅消费固定 baseline→交付 commit 的冻结代码、Spec、Ticket、规则和审核方法。Code 和 Spec 在各 reviewer 内顺序审核，未声称两遍分别隔离。来源为 /root/independent_ticket01…04；模型设置继承，精确模型不可观察，未升级模型或思考档位。

针对性验证：01 的旧 Cursor 闭包独立实测 58,213 字符，原 eval 8 文件逐字节匹配；02 的 40 项回归和 6 项探针通过；03 的 35 项回归通过并复现失败误报；04 的 45 项回归通过并复现 coverage 缺口。针对性测试通过不等同于无缺陷，也不构成全量回归、宿主安装或外部环境验证。

四个主冻结单元共 647 个文件，01 的补充单元 445 个文件；逐项 SHA256 核验完成。五个单元经 runtime finalize 全部返回 match/released。冻结副本已按 runtime 生命周期释放；清单、hash、commit 端点、原始报告和复现脚本保存在本目录 independent-evidence，可按相同端点重建。脚本中的临时路径保留原样，重新运行前须重建对应投影。

## 逐张报告

- [Ticket 01](review-workflow-simplification-01-independent.md)
- [Ticket 02](review-workflow-simplification-02-independent.md)
- [Ticket 03](review-workflow-simplification-03-independent.md)
- [Ticket 04](review-workflow-simplification-04-independent.md)
- [结构化汇总](review-workflow-simplification-01-04-independent.json)
- [runtime 完整性回执](review-workflow-simplification-01-04-independent-finalization.json)
