# My Matt Workflow

个人使用的 Matt Pocock 工作流适配包。

支持 Python 3.10+。

## 原则

- Matt 原生 Skills 只用于升级比较，不作为运行时依赖。
- 所有 `my-*` Skills 都由用户手动调用。
- 项目固定规则只配置一次，保存在 `.agent/matt-workflow.md`；`agent_directory_mode: private`（默认）使用无 remote 的嵌套 Git，`shared` 则由主仓库跟踪、提交和推送 `.agent/`。无 Git 项目同样使用 `.agent/` 保存文档与进度。
- 没有外部 Tracker 时，Spec 和 Tickets 保存到 `.agent/work/`。
- 所有本地工作产物按 `.agent/work/<topic>/<type>/` 保存；交接由 `my-handoff` 写入 `handoffs/handoffs-<topic>-<time-or-sequence>.md` 并保留历史。
- 工作流源目录是唯一可编辑源；安装器可复制稳定 release 到 Codex、Cursor、Claude 或用户指定的 Skill 目录。

## 维护命令

在本目录运行：

```bash
python3 tools/workflow.py setup --repo <project>
python3 tools/workflow.py validate
python3 tools/workflow.py validate-evals
python3 tools/workflow.py smoke
python3 tools/workflow.py check
python3 tools/workflow.py build --release-id <release-id>
python3 tools/workflow.py install --target codex
python3 tools/workflow.py deploy --target codex
python3 tools/workflow.py prune-releases
python3 tools/workflow.py resolve-rules --repo <project> --agent codex
python3 tools/workflow.py validate-ticket <ticket-path>
```

`workflow.py check` 是源树的权威本地检查：它严格验证静态输入、可执行 eval 与冒烟注册表，运行完整单元测试；存在 `current.json` 时还会先校验 release 的校验和、缺失文件和额外文件，再比较其与源树是否一致。尚未构建首个 release 时会明确报告 release 验证不适用。

`build` 与 `deploy` 都会先运行同一套完整源树门禁，但跳过旧 `current.json` 的一致性比较，因此可用新 release 替换已过期或损坏的 current release。`build` 仅构建并更新 current 指针；`deploy` 会在当前 release 完整且与源树一致时复用它，否则保留损坏 release 供排查、构建新 release 后再安装。

项目首次使用时手动运行 `/my-setup`。日常通过 `/my-ask-matt` 查询下一条命令，再手动调用推荐的 `/my-*`。

Codex 默认把 Skills 安装到 `~/.agents/skills`，把安装状态和版本化 runtime 保存到 `${CODEX_HOME:-~/.codex}/my-matt-workflow`。安装后的 `install-state.json` 会记录绝对 `runtime_entry`，因此项目内命令不依赖当前工作目录中存在本仓库的 `tools/`。
