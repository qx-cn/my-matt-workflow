---
name: my-work-artifacts
description: 只读列出、定位和读取本地忽略的工作产物。
disable-model-invocation: true
---

# My Work Artifacts

使用本 Skill 读取 `.agent/work/` 下的本地工作产物。它只执行只读命令；不得迁移、覆盖、删除或写入产物。

1. 列出某个 topic/type 的产物：

   ```sh
   python3 tools/workflow.py work-list --repo . --topic <topic> --type <type>
   ```

2. 定位一个产物；`<selector>` 可以是 `latest`、序号或精确文件名：

   ```sh
   python3 tools/workflow.py work-resolve --repo . --topic <topic> --type <type> --selector <selector>
   ```

3. 读取一个已定位的 UTF-8 Markdown 产物：

   ```sh
   python3 tools/workflow.py work-read --repo . --topic <topic> --type <type> --selector <selector>
   ```

路径越界、歧义、symlink escape、HTML、非 UTF-8 内容和超过大小上限的文件都会失败。`domain` type 包含其 `adr/` 子目录。该方案不承诺默认 `@` 下拉框显示 `.agent/` 产物；需要时显式调用本 Skill。
