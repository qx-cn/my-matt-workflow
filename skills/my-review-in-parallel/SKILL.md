---
name: my-review-in-parallel
description: 对同一冻结产物并行执行全部共享规则 reviewer，并把证据合并成一份只读审查结果。
disable-model-invocation: true
---

# 并行规则审查

对用户指定的同一产物运行全部适用的共享规则 review。只读审查；不修改、重写或格式化原产物。

先通过安装状态记录的 `runtime_entry` 运行：

```text
parallel-review-plan --artifact <path> [--artifact <path> ...]
```

该命令冻结产物的路径、大小和 SHA-256，并从 `references/shared/governance.json` 对应的治理清单发现全部 `reviewable-rule`。以返回的 `content_id` 和 lanes 为准；不得手写固定 reviewer 清单，也不得让不同 reviewer 读取不同版本。

为每条 lane 启动一个独立只读任务，调用 lane 指定的 review Skill。优先使用当前宿主已经提供的并行 Agent 能力：Cursor 可用 Subagents 或 `/multitask`，Codex 使用 collaboration/subagent，Claude 使用 parallel subagents。不要假装调用不存在的命令。宿主不支持并行时按 lanes 顺序串行执行，并在结果中写明 `execution: serial-fallback`。

每个 reviewer 只返回：规则、结论、证据位置、影响和最小修订方向。执行失败或没有拿到完整产物时返回 `inconclusive`，不得当作通过。

汇总时按根因去重；同一根因触犯多条规则时保留全部规则归属。只接纳能定位到冻结产物的 finding。所有 reviewer 都没有合格 finding 时输出 `No findings.`，并同时列出任何 `inconclusive` lane。

汇总前再次计算产物摘要；与 `content_id` 不一致时整批结果标记 `stale`，不要把旧结论用于当前产物。
