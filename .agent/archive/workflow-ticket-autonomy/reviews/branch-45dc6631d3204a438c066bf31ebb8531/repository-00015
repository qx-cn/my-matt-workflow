# 专项只读审查会话

专项 review Skill 先解析所有会改变目标行为的文件，并把绝对路径去重、稳定排序。随后从当前 Agent 的 `my-matt-workflow/install-state.json` 读取绝对 `runtime_entry`，将每个文件作为重复的 `--artifact` 参数运行：

```sh
python3 <runtime_entry> artifact-review-snapshot --artifact <path> [--artifact <path> ...]
```

只有返回 `status: ready` 才能开始审查。后续证据只读取 `review_unit` 中的 `snapshot_path`；`content_id`、快照路径或哈希不得由 Skill 自行拼接。无法纳入快照的外部状态逐项记录为 Evidence Gap。

报告前使用完全相同且顺序稳定的文件列表运行：

```sh
python3 <runtime_entry> artifact-review-finalize \
  --artifact <path> [--artifact <path> ...] \
  --expect-content-id <content-id> \
  --snapshot-dir <snapshot-dir>
```

只有 `status: match` 且快照已释放时才能发送结论。`stale` 表示审查对象已经变化：丢弃旧结论，重新建立快照并重审；不能把旧 findings 搬到新内容上。
