# Implementation session

本文件定义实施 Skill 与项目 runtime 的 session 接口；Skill 只消费工作单元并返回语义结果，不自行复制调度、快照、恢复或写入流程。

先从当前 Agent 的 `my-matt-workflow/install-state.json` 读取绝对 `runtime_entry`；不要假设目标仓库内存在本工作流的 `tools/`。然后运行：

```sh
python3 <runtime_entry> implementation-open --repo <repo> --ticket <ticket> --base <fixed-point> [--agent <agent>] [--path <path> ...]
```

默认是串行且只接受一张 Ticket；串行时可用 `--path` 提供实际影响路径。只有用户明确要求并行时才传 `--parallel` 和多次 `--ticket`，且不传共享 `--path`；runtime 会用各 Ticket 的 `rule_scope` 解析规则，并仅在 Ticket 均已解除阻塞、属于同一 topic、具有具体且可证明互不重叠的写入范围时返回多个 lane，否则拒绝并行。宿主还必须能隔离 lane 的写入、构建和测试状态，才可并发执行 `lanes[*].work_unit`；无法证明隔离时按 lane 串行执行，不能假称并行。

`implementation-open` 会通过可恢复事务领取 Ticket，并把 journal 留在 `admitted`。按实际阶段推进同一 journal：开始实现前记录 `implementing`，进入审查时记录 `reviewing`，只有测试与审查都绑定到最终代码内容后才记录 `committing`。

每次恢复、CLI 校验错误或 repair-plan 审查通过后，先查询 runtime 的唯一粗粒度 gate；它只说明当前流程边界，不替 Agent 调度 TDD 切片：

```sh
python3 <runtime_entry> implementation-next-action --journal <journal>
```

```sh
python3 <runtime_entry> run-record <journal> --phase implementing
python3 <runtime_entry> run-record <journal> --phase reviewing
python3 <runtime_entry> run-code-receipt --journal <journal>
python3 <runtime_entry> run-review-open --journal <journal>
python3 <runtime_entry> run-test-evidence --journal <journal> -- <declared test argv...>
python3 <runtime_entry> run-review-submit --journal <journal> --snapshot-dir <review-snapshot-dir> --result-file <json>
# 或由已配置的独立执行适配器完成：
python3 <runtime_entry> run-review-evidence --journal <journal> --snapshot-dir <review-snapshot-dir> [--reviewer-session-id <new-session-id>] -- <declared-review-command>
python3 <runtime_entry> run-record <journal> --phase committing
```

`implementation-next-action` 是恢复和推进 session 的高层入口；旧 `implementation-status` 保留兼容，两者返回相同的 `next_action` 与 `next_gate`。`run-code-receipt` 对 Ticket 声明的 `rule_scope`（含 `**` 等 glob）生成结构化 code receipt。`run-test-evidence` 只执行 work unit 已声明的 test command，保存 argv、真实 exit code 与 stdout/stderr digest，并返回 runtime 登记的 evidence id。`run-review-open` 冻结同一 code scope 及其固定基线副本，以及当前 Ticket 验收、直接下游 owner 和按 Ticket 声明的风险探针；语义方法由 runtime 固定为 `my-code-review`，并返回随机 `review_id`、只读 snapshot 与 `code_content_id`；reviewer 必须读取该 snapshot。

宿主在同一次 `my-implement` 中自动应用组合的 `my-code-review` 方法，再用 `run-review-submit` 提交结果；无需用户再次手动调用 Skill。需要独立进程时可改用 profile 预先声明的 `review_commands` 与 `run-review-evidence`，后者通过 `MY_MATT_REVIEW_METHOD`、`MY_MATT_REVIEW_ID`、`MY_MATT_REVIEW_SNAPSHOT`、`MY_MATT_CODE_CONTENT_ID`、`MY_MATT_TICKET_BOUNDARY` 和 `MY_MATT_IMPLEMENTATION_SESSION_ID` 传递固定单元。传入 `--reviewer-session-id` 时，命令从只读 snapshot 目录运行，其中包含代码、基线、Spec、规则和 boundary manifest；结果必须使用同一不同的 ID 作为 `independent_session` provenance。两条路径使用相同结果协议：`status` 为 `pass | findings | inconclusive | blocked-by-design`。默认 `reviewer_provenance=self`，并覆盖当前 Ticket 每个验收与必需风险探针；finding 必须引用当前验收，follow-on 只能引用直接下游 owner，design gap 才使用 `blocked-by-design`。用户显式要求独立审查时才使用不同的 `independent_session` provenance；这证明 session 区分和冻结输入，不证明不存在其他隐藏上下文。

runtime 登记每轮结果。`findings` 进入受管 repair-plan：运行时冻结方案和审查前代码，方案只经 `my-review-design` 自审通过后才可返回 `implementing`，此时 `implementation-next-action` 返回 `fix-approved-findings`；修复后必须重新测试、开新 code-review snapshot 并复审。默认只允许一轮修复；最终复审出现新的有效 finding 时，runtime 以带 finding receipt、repair-plan receipt 和 profile limit 的 `review-boundary-exhausted` Critical 登记 `blocked-by-review`。`full-auto` 可按 profile 的 `max_repair_rounds`（上限 5）继续；连续两轮出现同一 `root_cause` 时返回 `blocked-by-design`，`inconclusive` 返回 `blocked-by-evidence`。只有 `pass` 生成可用于完成的 `review_receipt`。普通 review result JSON/coverage 校验失败保留同一受管 snapshot，并由 status 返回 `correct-review-result`；代码漂移废弃旧 snapshot 并返回 `open-review`；只有可验证的 snapshot 完整性或归属损坏才登记正式 Critical。

## 回合关闭

runtime 不能观察或拦截宿主发送的聊天 final；宿主必须自行把 final 视为实施会话的终止动作。journal 处于 `admitted`、`testing`、`implementing`、`reviewing`、`committing` 或 repair-plan 流程时，只能继续工作或以 commentary 汇报进度，不得发送 final。局部测试通过、当前正在施工、尚待 receipt 或“下一步继续”均不是终止结果。

只有以下任一条件成立才可发送 final：

- 已提交并关闭实施会话，且按 [work scope](work-scope.md) 的 `next-ticket` transition 返回 `complete`；`ready-frontier` 或 `approved-plan` 返回下一张 Ticket 时，在同一实施任务继续。
- runtime 已登记正式 blocked outcome；final 必须说明 blocker、已登记证据和最小恢复条件。
- 用户明确要求暂停或停止；保留 journal 并如实说明未完成状态和恢复入口。

`max_repair_rounds` 只限制同一审查 finding 的自动修复轮数，不限制正常 TDD 切片或 Ticket 推进。达到限制时登记 `blocked-by-review`，而不是以未提交的进度汇报结束回合。

仅当 `implementation-next-action` 返回 `submit-completed`，或 runtime 已登记正式 Critical 时，把下面的 JSON 保存为文件并提交：

```json
{"outcome":"completed|blocked-by-design|blocked-by-evidence","test_receipt":{"kind":"test","evidence_id":"<runtime evidence id>"},"review_receipt":{"kind":"review","evidence_id":"<runtime evidence id>"},"code_receipt":{"kind":"code","content_id":"<code-content-id>","sources":[]},"blocker":null}
```

```sh
python3 <runtime_entry> implementation-submit --journal <journal> --result-file <json>
```

`completed` 只能从 `committing` 提交，且 test/review receipt 必须引用该 journal 的 runtime evidence registry，并与当前 code receipt 绑定；旧字符串或调用者手拼的 pass dict 不能转换为完成证据。阻塞结果把三个 receipt 设为 `null` 并提供 blocker。runtime 会重新校验 Ticket definition、Spec lineage、profile、rules、standards/domain sources、review result、evidence records 与代码 receipt，并通过 WAL 协调 Ticket 和 journal 的终态投影。所有 lane 都提交后运行：

```sh
python3 <runtime_entry> implementation-close --journal <journal> [--journal <journal> ...]
```

只有全部 lane 都是 `completed` 才返回 `ready-for-integration`；这表示可进入集成，不表示集成已经发生。
