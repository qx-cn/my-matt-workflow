Review-Snapshot: 6b9e9db162770c5f2065ce0954ea82469c58cd25fcb856659bc607ed2ee20c29
Baseline: dfc3532f96a442de6584770e945bee469f35b181
Head: runtime unit 未提供，未从 mutable repo 补读。
Review-Scope: change-only
Review-ID: f14f8f36725a12de1730460a2b1308b7

## Code

[P1][high] 保留配置对象值的类型拒绝 — tools/workflow_lib/topic_service.py:106-109

正常 v2 配置的 `default_base_branch` 被替换为 JSON 对象 `{}` 时，正式基线 `read_config` 会拒绝“必须为非空字符串”；当前代码跳过 JSON 解析，将该对象文本直接赋给字符串字段。公开 CLI `setup`、`work-overview`、`setup --apply` 实际全部退出 0，最后一个命令还把对象错误固化为字符串 `"{}"`。失败路径是配置文件 → `read_config` STRING_KEYS 分支 → `validate_config`（此时已成为 str）→ `setup` 的 Git ref 检查（`{}` 是合法 ref 文本）→ 配置写回，可能把类型错误的分支配置带入后续基线选择。位置正是本次新增分支，基线同输入明确拒绝，不依赖施工中的中间格式。锚定 Ticket A1。最小验证：生成正常 v2 配置，仅把该字段改为 `default_base_branch: {}`，运行上述三个命令；当前均通过，期望类型错误被拒绝。修正时区分裸标量兼容与 JSON 容器，不能把容器类型无条件文本化。

## Spec

No findings.

同一类型拒绝问题由 Code 根因覆盖，不重复计为 Spec finding。分别从冻结实现、测试和 Spec 建立要求映射；Spec M5 的内容绑定（186–195 行）、测试失败/进度命令约束（357–365 行）、首轮覆盖（388–390 行）与 Ticket A1–A4 对应行为均纳入验证。未扩展到下游能力。

| 当前验收/探针 | 核验结果和证据 |
|---|---|
| A1 | 字符串往返、旧裸 `null/true/123/1e3`、嵌入引号、非法 schema/反斜线拒绝的冻结测试通过；上述对象类型拒绝有 P1 发现。Git 分支中的反斜线本身非法，冻结测试按拒绝验证。 |
| A2 | `test_duplicate_commands_keep_failure_until_full_successful_rerun` 和 `test_declared_tests_progress_failure_and_definition_change` 通过，重复/等价 argv 按每个 command_index 保留失败，progress 不能替代完整批次，完整重测恢复。 |
| A3 | `test_interrupted_formal_run_invalidates_prior_success_and_can_recover` 与 `test_each_test_is_bound_to_its_actual_content` 通过；另经 CLI 先成功、再在第二命令中 SIGKILL（退出 -9），持久记录仅有一条新批次 entry、completed=false，重启 status 显示 tests_passed=false，重测退出 0 恢复。旧记录删除 test_run 后也必须重测。 |
| A4 | 冻结数字/字母编号测试通过；补充 CLI 探针对 I-1… I-11、I-K1、I-T1 逐项遗漏，13 次均退出 1；未声明、重复目标、无理由 NA 均退出 1，完整有理由 NA 退出 0。 |
| A5 | 仅对冻结提供的三模块投影执行 49 项测试，全部通过，退出 0（62.351s）。本次独立审核结果绑定当前内容，但结论为 findings，不能出具 pass receipt。原始复现/修复映射/历史完成保存及仓库声明全量回归不在该可读冻结单元内，未声称已验证。 |
| required probe: recovery | 部分批次持久化、进程中断、独立 CLI 重启判断和完整重测恢复实跑通过；退出码和状态载于 verification JSON。 |

50 条 current/review_inputs/固定依赖与 6 条 baseline 的 SHA 与 size 均核验，unit 核心字段与 snapshot_dir/.review-unit.json 一致；依赖 review_id、code_content_id、base_sha 与唯一 unit 绑定。未读取实施总结、计划、旧审核或 mutable 项目源码。测试仅在临时重建目录使用固定基线依赖，并由 runtime current artifacts 覆盖对应路径。verification JSON 保存命令、实际退出码和恢复状态。

实际模型精确标识不可观察，继承宿主配置，没有升档。可观察的宿主任务名为 `/root/independent_repair15`；未取得 session UUID，协议 safe session id `independent-repair15` 映射该任务，与 implementation_session_id 不同。

Code: P0=0/P1=1/P2=0，blocker=1；Spec: P0=0/P1=0/P2=0，blocker=0。
