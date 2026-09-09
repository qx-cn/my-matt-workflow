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
python3 tools/workflow.py doctor
python3 tools/workflow.py build --release-id <release-id>
python3 tools/workflow.py install --target codex
python3 tools/workflow.py deploy --target codex
python3 tools/workflow.py prune-releases
python3 tools/workflow.py resolve-rules --repo <project> --agent codex
python3 tools/workflow.py validate-ticket <ticket-path>
python3 tools/workflow.py run-code-receipt --journal <run-journal>
python3 tools/workflow.py run-review-open --journal <run-journal>
python3 tools/workflow.py run-test-evidence --journal <run-journal> -- <declared test argv...>
python3 tools/workflow.py run-review-evidence --journal <run-journal> --snapshot-dir <review-snapshot-dir> -- <declared-review-command>
```

测试和审查命令分别来自项目 profile 的 `test_commands` 与 `review_commands`。runtime 只执行 work unit 建立时已冻结的精确 argv；审查命令从 `MY_MATT_REVIEW_ID`、`MY_MATT_REVIEW_SNAPSHOT`、`MY_MATT_CODE_CONTENT_ID` 读取当前审查单元，并在 stdout 输出结果 JSON。

`workflow.py check` 是源树的权威本地检查：它严格验证静态输入、可执行 eval 与冒烟注册表，运行完整单元测试；存在 `current.json` 时还会先校验 release 的校验和、缺失文件和额外文件，再比较其与源树是否一致。尚未构建首个 release 时会明确报告 release 验证不适用。

`workflow.py doctor` 是只读部署诊断：它分别报告源树、current release 与 Codex/Cursor/Claude 安装状态，明确区分 `valid`、`drift`、`invalid` 和 `not-installed`，不会自动安装或修复。

`build` 会先取得 byte-exact 源码快照；若复制期间工作树发生变化则重试，完整源树门禁与打包都只读取同一快照。它跳过旧 `current.json` 的一致性比较，因此可用新 release 替换已过期或损坏的 current release。`build` 仅构建并更新 current 指针；`deploy` 会在当前 release 完整且与源树一致时复用它，否则保留损坏 release 供排查、构建新 release 后再安装。

项目首次使用时手动运行 `/my-setup`。日常通过 `/my-ask-matt` 查询下一条命令，再手动调用推荐的 `/my-*`。

Codex 默认把 Skills 安装到 `${CODEX_HOME:-~/.codex}/skills`，把安装状态和版本化 runtime 保存到 `${CODEX_HOME:-~/.codex}/my-matt-workflow`。旧版安装状态仍指向 `.agents/skills` 时，下一次安装会在同一事务中迁移已托管的 `my-*` Skills。安装后的 `install-state.json` 会记录绝对 `runtime_entry`，因此项目内命令不依赖当前工作目录中存在本仓库的 `tools/`。
