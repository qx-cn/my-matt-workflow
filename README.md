# My Matt Workflow

个人使用的 Matt Pocock 工作流适配包。

## 原则

- Matt 原生 Skills 只用于升级比较，不作为运行时依赖。
- 所有 `my-*` Skills 都由用户手动调用。
- 项目固定规则只配置一次，保存在 `.agent/matt-workflow.md`；无 Git 项目同样使用 `.agent/` 保存文档与进度，Git 项目仅在安全时将其忽略。
- 没有外部 Tracker 时，Spec 和 Tickets 保存到 `.agent/work/`。
- 所有本地工作产物按 `.agent/work/<topic>/<type>/` 保存；交接由 `my-handoff` 写入 `handoffs/handoffs-<topic>-<time-or-sequence>.md` 并保留历史。
- 工作流源目录是唯一可编辑源；安装器可复制稳定 release 到 Codex、Cursor、Claude 或用户指定的 Skill 目录。

## 维护命令

在本目录运行：

```bash
python3 tools/workflow.py check
python3 tools/workflow.py doctor
python3 tools/workflow.py doctor --recommend
python3 tools/workflow.py recommend
python3 tools/workflow.py sync
python3 tools/workflow.py build --release-id <release-id>
python3 tools/workflow.py install --target codex
```

`workflow.py check` 是源树的权威本地门禁：它严格验证静态输入、可执行 eval 与冒烟注册表，运行完整单元测试，并在存在 `current.json` 时验证当前 release 与源树一致。尚未构建首个 release 时会明确报告 release 验证不适用；`build` 会在创建 release 前运行同一套完整门禁，只跳过旧 current release 的一致性比较，以便用新 release 替换已过期的旧 release。

项目首次使用时手动运行 `/my-setup`。日常通过 `/my-ask-matt` 查询下一条命令，再手动调用推荐的 `/my-*`。
