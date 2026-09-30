# Ticket 04 → 05 审查接口交接

Handoff-Status: ready

## 材料与提交

`tools/workflow_lib/ticket_review.py` 提供 open_review、submit_review 和 review；公开 CLI 是 `implement review --ticket <id> --reviewer-model <宿主实际模型>` 与 `implement review --ticket <id> --submit <结果文件>`。定位沿用 03；仅 implementing 可开或提交审查。

开放命令返回 `snapshot_dir`、`manifest`、可编辑 `result_file`。manifest 冻结 `unit_id`、`content_id`、`round`、当前 Ticket 验收、probes、直接下游验收、全部改变文件的 baseline/current 副本与 mode/sha256/size，以及规则、Spec、已决清单和审查循环文本。外部 result_file 是预填模板，只填 status、reviewer、coverage、findings；六项冻结字段须原样保留。`coverage_targets` 给出必须覆盖的验收、探针和 Spec 中明确标为 **I-<字母><数字>** 的不变量。not-applicable 必须说明原因。

项目根 .agent/.git 排除；嵌套测试 fixture 的 .agent 是项目内容，不能删去。忽略的未跟踪文件排除。范围外改变只列 outside_scope，仍附完整基线与最终字节；不读实现总结或简报计划。符号链接冻结链接目标文本，不解引用外部文件。非 blob Git 条目、非常规文件无法取得完整证据时拒绝，不能冒充已审查。

submit 检查冻结材料完整性、当前内容、定义、配置、适用规则、已决事项和下游验收；变化时拒绝，提示重审。格式错误保留当前单元可重试；相同已接受结果重复提交可恢复；同单元不同结论拒绝覆盖。

## 结果与来源

实施记录新增 `implementation_session_id`（runtime 标识）、`active_review`（manifest/hash、材料目录、模板路径、定义/配置快照）、`reviews`（每个开放轮次和接受记录）。接受记录保存于 `reviews/accepted-<unit_id>.json`，entry 包含 unit_id、content_id、round、status、reviewer、原始 result。

只有 advisory 的 findings 归一化为 entry.status=pass；原始 result.status 仍如实保留 findings。05 的 finish 必须消费归一化 entry.status，同时核验当前内容和材料绑定，不能仅看原始 result.status，也不能只凭历史 pass 越过重测/复审。topic status 累计显示已登记 advisory。

宿主在开放时声明实际模型，runtime 不选择模型。未传 reviewer-session-id 时冻结 self；确实派出不同上下文时宿主才传其独立 session 标识，runtime 将该声明和模型固定后校验结果。单独把结果 reviewer.provenance 改成 independent 被拒绝。该边界保证声明一致，不提供对宿主进程或隐藏上下文的外部证明。10 接入真实宿主派发时必须如实映射；本轮施工审查是 self。

## 后续 owner

05 拥有五步 finish、内容改变失效、notes 与单张 Ticket 的提交归档。06 拥有四轮上限、停止信号、needs-user 投影和 reopen；本轮记录轮次，但未兑现这些门禁。07 扩展到整分支对象。

当前审查循环文本在 ticket_review.REVIEW_LOOP_RULES 单处定义并冻结到材料，用户项目 Spec 不需复制工作流规则。09 的结构改造和10 的统一共享规则接入需要协调此定义，最终13 的 tools 裁剪应读取共享权威而移除重复正文。不要把此阶段暂存实现当成最终 Skill 分发形态。

仓库自身配置仍 schema 1；施工使用安装 runtime，不用正在重构的源入口管理施工。未安装新源码到宿主。

04 已登记 completed、close=ready-for-integration、single-ticket transition=complete，完成历史校验通过。
