# Artifact review session

本文件定义产物审查 Skill 与项目 runtime 的 session 接口；Skill 只消费固定审查单元并返回语义结果，不自行复制调度、快照或验证流程。

开始前从当前 Agent 的 `my-matt-workflow/install-state.json` 读取绝对 `runtime_entry`，然后运行：

```sh
python3 <runtime_entry> artifact-review-open --artifact <path> [--artifact <path> ...] [--kind general|design] [--parallel]
```

`--kind` 默认为 `general`；技术方案、架构说明或设计文档使用 `design`，runtime 只在这种审查单元中加入 `my-review-design`。默认串行。只有用户明确要求并行时才传 `--parallel`；runtime 返回共享同一 `content_id` 的方法 lane，宿主负责按 `dispatch` 执行。结果 JSON 必须完整覆盖 `review_unit.required_checks`：

```json
{"content_id":"<id>","checks":{"<method>":{"status":"pass|finding|inconclusive|not-applicable","reason":null}},"findings":[],"inconclusive":[]}
```

`not-applicable` 必须提供非空 `reason`。每个 `finding` 或 `inconclusive` 项以 `checks` 数组标明它解释的方法；一个合并项可覆盖多个方法。提交并释放快照：

```sh
python3 <runtime_entry> artifact-review-submit --artifact <path> [--artifact <path> ...] --snapshot-dir <dir> --result-file <json>
```

runtime 会拒绝缺失方法、无解释的 finding/inconclusive，或已变化的源内容。直接调用 Skill 而宿主没有接入这些命令时，必须明确说明缺少 runtime session；不能虚构工作单元、固定快照或闭合结果。
