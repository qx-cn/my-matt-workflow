# Runtime session bridge

本文件集中定义领域 Skill 与项目 runtime 的 session 接口；Skill 只消费工作单元并返回语义结果，不自行复制调度、快照、恢复或写入流程。

## 实施 session

先从当前 Agent 的 `my-matt-workflow/install-state.json` 读取绝对 `runtime_entry`；不要假设目标仓库内存在本工作流的 `tools/`。然后运行：

```sh
python3 <runtime_entry> implementation-open --repo <repo> --ticket <ticket> --base <fixed-point> [--agent <agent>] [--path <path> ...]
```

默认是串行且只接受一张 Ticket；串行时可用 `--path` 提供实际影响路径。只有用户明确要求并行时才传 `--parallel` 和多次 `--ticket`，且不传共享 `--path`；runtime 会用各 Ticket 的 `rule_scope` 解析规则，并仅在 Ticket 均已解除阻塞、属于同一 topic、具有具体且可证明互不重叠的写入范围时返回多个 lane，否则拒绝并行。宿主还必须能隔离 lane 的写入、构建和测试状态，才可并发执行 `lanes[*].work_unit`；无法证明隔离时按 lane 串行执行，不能假称并行。

每个 lane 结束时，把下面的 JSON 保存为文件并提交：

```json
{"outcome":"completed|blocked-by-design|blocked-by-evidence","test_receipt":null,"review_receipt":null,"blocker":null}
```

```sh
python3 <runtime_entry> implementation-submit --journal <journal> --result-file <json>
```

`completed` 必须提供非空测试与审查 receipt；阻塞结果必须提供 blocker。runtime 会重新校验 Ticket 与 Spec 的内容 receipt。所有 lane 都提交后运行：

```sh
python3 <runtime_entry> implementation-close --journal <journal> [--journal <journal> ...]
```

只有全部 lane 都是 `completed` 才返回 `ready-for-integration`；这表示可进入集成，不表示集成已经发生。

## 产物审查 session

开始前运行：

```sh
python3 <runtime_entry> artifact-review-open --artifact <path> [--artifact <path> ...] [--parallel]
```

默认串行。只有用户明确要求并行时才传 `--parallel`；runtime 返回共享同一 `content_id` 的方法 lane，宿主负责按 `dispatch` 执行。结果 JSON 必须完整覆盖 `review_unit.required_checks`：

```json
{"content_id":"<id>","checks":{"<method>":{"status":"pass|finding|inconclusive|not-applicable","reason":null}},"findings":[],"inconclusive":[]}
```

`not-applicable` 必须提供非空 `reason`。每个 `finding` 或 `inconclusive` 项以 `checks` 数组标明它解释的方法；一个合并项可覆盖多个方法。提交并释放快照：

```sh
python3 <runtime_entry> artifact-review-submit --artifact <path> [--artifact <path> ...] --snapshot-dir <dir> --result-file <json>
```

runtime 会拒绝缺失方法、无解释的 finding/inconclusive，或已变化的源内容。直接调用 Skill 而宿主没有接入这些命令时，必须明确说明缺少 runtime session；不能虚构工作单元、固定快照或闭合结果。
