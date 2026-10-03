---
name: my-install
description: 安装、查询或回滚个人 My Matt Workflow release
disable-model-invocation: true
---

# My Install

先定位绝对 runtime 入口。已安装环境从目标 Agent 根目录下 `my-matt-workflow/install-state.json` 读取并校验绝对 `runtime_entry`；源码开发环境使用 workflow source root 下的 `tools/workflow.py`。安装、查询与回滚可在任意项目 cwd 执行，不把当前目录当作 workflow 源码。

1. 安装当前已发布版：`python3 <absolute-runtime-entry> install --target <codex|cursor|claude>`；也可用 `--agent-home <path>` 指定自定义 Agent 根目录。
2. 从本地 Skills 构建并安装：先确认当前目录就是包含 `skills/`、`tools/workflow.py` 与 package manifests 的 workflow source root，再运行 `python3 tools/workflow.py deploy --target <codex|cursor|claude>`。`deploy` 不适用于普通目标项目目录。
3. 回滚：`python3 <absolute-runtime-entry> install --release <release-id>`。
4. 清理历史 release：用同一绝对 runtime 先运行 `prune-releases` 预览；确认候选仅为未被 Agent 安装状态引用的 release 后，再运行 `prune-releases --apply`。若有自定义 Agent 根目录，附加每个 `--agent-home <path>`。
5. 报告 release ID、所选 Agent 根目录中 `my-matt-workflow/install-state.json` 的安装状态、`runtime_entry` 与 `installed_agent`；它是项目 setup 的默认执行环境候选。

install state 缺失、损坏或 `runtime_entry` 不存在时停止，并要求用户提供 workflow source root 或重新安装；不要回退到目标项目中的相对 `tools/workflow.py`。安装器只管理 manifest 中列出的 `my-*` Skills，不删除其他个人 Skills。校验失败时停止，不覆盖现有安装。
