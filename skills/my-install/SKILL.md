---
name: my-install
description: 安装、查询或回滚个人 My Matt Workflow release
disable-model-invocation: true
---

# My Install

1. 需要把当前已发布最新版安装到 Agent 时，运行 `python3 tools/workflow.py install --target <codex|cursor|claude>`；也可用 `--agent-home <path>` 指定自定义 Agent 根目录。
2. 需要从本地 Skills 更新发布并安装时，运行 `python3 tools/workflow.py deploy --target <codex|cursor|claude>`。它会校验内容；没有变化时复用当前 release，有变化时才构建新 release。
3. 回滚时运行 `python3 tools/workflow.py install --release <release-id>`。
4. 清理历史 release 时，先运行 `python3 tools/workflow.py prune-releases` 预览；确认候选仅为未被 Agent 安装状态引用的 release 后，再运行 `python3 tools/workflow.py prune-releases --apply`。若有自定义 Agent 根目录，附加每个 `--agent-home <path>`。
5. 报告 release ID 和所选 Agent 根目录中 `my-matt-workflow/install-state.json` 的安装状态。

安装器只管理 manifest 中列出的 `my-*` Skills，不删除其他个人 Skills。校验失败时停止，不覆盖现有安装。

> 项目策略优先：读取 `.agent/matt-workflow.md` 的已解析生效策略；缺键或空值按 `strict-control`。本 Skill 中要求询问、确认、停止或限制后续工作的表述，除绝对安全底线外，均服从该生效策略。绝对安全底线始终不变：不得 Force Push、改写 Git 历史、执行破坏性 Git 操作，或向外部服务发送敏感信息。
