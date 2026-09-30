# workflow-simplification-15 — 证据完整性补偿修复

Spec: workflow-simplification r1。补偿 02、03、04，不改写历史验收和审核。runtime 已登记 completed/ready-for-integration；single-ticket transition=complete。本地提交状态以 Git 为准。

## 改动概述

- 正式测试通过依据为最近一次完整声明批次，结果绑定批次和声明位置；重复/等价 argv 的后一次成功不能掩盖失败。开始执行先持久化未完成标记；中断、部分执行、旧记录无证明均要求重测；progress 不替换正式证据。
- 配置统一 JSON 编码；旧裸 null/true/数字字符串保留拼写；JSON 对象/列表不强制转字符串，维持类型拒绝。合法引用字符串（包括分支名 {}）可往返。
- 同一冻结 Spec 的数字和字母前缀不变量均进入唯一 coverage_targets，遗漏拒绝，完整声明可提交，不适用须理由。

## 测试结果

50 项公共 CLI 针对性测试通过；runtime 执行声明全量 `python3 -m unittest discover -s tests` 最终退出 0/pass，回执 5161bfc110098b47db35bffc784d0aba68115d98953f5415795cb067943e2d3f，绑定最终 code_content_id 944f13f24d48d6afddc4136c95e0b30ddc0557283f83ac17259f1ec8df6af7ea。

独立 reviewer 另运行同一三模块 50 项及 13 项 CLI 探针，实际退出码与证据见 final-verification。主 Agent 的全量回执与 reviewer 的投影测试是不同证据，不混为同一范围。

## 审查发现与修复

原 CR02-C1、03-C1、IND04-S1 三项映射到本补偿 Ticket。首次独立审查发现兼容解析把裸 JSON 对象转成字符串的 P1；runtime 登记 finding→冻结修复方案→设计增强自审 pass→修复→重测→新冻结单元→另一新上下文独立复审。最终 Code/Spec 均无 findings，runtime review pass receipt fb6126bbb0b03d97906ef0afcba0f01c0b10c5a6e2f19720e6c0841c324503df。

审查者继承模型和思考配置，精确模型不可观察；safe session id 与实际 canonical task name 映射见 completion.json。设计方案检查为主 Agent 自审，未称独立；代码两轮审查均独立。

## 建议

无新增审核建议。后续 05/06/08 消费测试资格的约束见新增 handoff，保持单一通过判定。

## 已知问题

本补偿范围无未解决阻断。剩余主计划 Ticket 05–14 保持其原 owner 与状态，不因本次修复宣称完成。

## 长期知识沉淀

证据必须保留类型、声明身份与批次完成性；不能用词法推断或最后成功记录替代整体证明。旧记录缺少证明时保留历史并要求重测。

## 用户介入记录

用户明确要求系统性修复，沿用本会话 Topic 内自动授权与独立审核要求。没有升级模型、推送、安装或其他项目迁移。

## 未验证项

未验证 Python 3.10、真实宿主安装、外部项目迁移或生产运行。完整仓库测试是在当前本地 Python 上执行。

## 验收对照

A1：字符串往返、对象/列表拒绝及零写入；A2：重复/等价声明批次、失败及 progress 不能掩盖、完整重测恢复；A3：强杀/重启、部分批次与旧证据、内容绑定；A4：I-1…11、I-K1/I-T1、漏项拒绝与不适用理由；A5：50 项针对性、全量 runtime 测试、独立审核、关闭与 single-ticket transition 均完成。证据索引见 reviews/review-workflow-simplification-15-completion.json。
