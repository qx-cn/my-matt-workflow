# My Matt Workflow

个人使用的 Matt Pocock 工作流适配包。

支持 Python 3.10+。

## 原则

- Matt 原生 Skills 只用于升级比较，不作为运行时依赖。
- 所有 `my-*` Skills 都由用户手动调用。
- 项目固定规则只配置一次，保存在 `.agent/matt-workflow.md`；`agent_directory_mode: private`（默认）使用无 remote 的嵌套 Git，`shared` 则由主仓库跟踪、提交和推送 `.agent/`。无 Git 项目同样使用 `.agent/` 保存文档与进度。
- 没有外部 Tracker 时，Spec 和 Tickets 保存到 `.agent/work/`。
- 所有本地工作产物按 `.agent/work/<topic>/<type>/` 保存；交接由 `my-handoff` 写入 `handoffs/handoffs-<topic>-<time-or-sequence>.md` 并保留历史。
- `assurance_level` 与写入授权正交：`quick` 用于明确、低风险、单切片工作，`standard` 是默认层，`audited` 用于高风险、跨边界或明确要求完整可恢复审计链的工作。
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
python3 tools/workflow.py work-overview --repo <project>
python3 tools/workflow.py work-overview --repo <project> --topic <topic> --json
python3 tools/workflow.py archive-spec --repo <project> --topic <topic> --spec-id <spec-id>
python3 tools/workflow.py archive-topic --repo <project> --topic <topic>
python3 tools/workflow.py archive-list --repo <project>
python3 tools/workflow.py archive-show --repo <project> --topic <topic>
python3 tools/workflow.py implementation-next-action --journal <run-journal>
python3 tools/workflow.py run-code-receipt --journal <run-journal>
python3 tools/workflow.py run-review-open --journal <run-journal>
python3 tools/workflow.py run-test-evidence --journal <run-journal> -- <declared test argv...>
python3 tools/workflow.py run-review-submit --journal <run-journal> --snapshot-dir <review-snapshot-dir> --result-file <json>
python3 tools/workflow.py run-review-evidence --journal <run-journal> --snapshot-dir <review-snapshot-dir> -- <declared-review-command>
```

`work-overview` 只读汇总 `local` 后端的 Spec 修订与状态、Ticket、实施会话、已有收据与下一动作。默认输出面向人的摘要，`--json` 输出相同内容供工具使用。它会标出冲突或无法判定的状态；收据存在只表示已登记，不单独证明测试或审查通过。活动实施会话的下一动作来自现有 `implementation-next-action` 判定；可开始的 Ticket 是手动候选，不代表自动扩大工作范围。

本地长期 Spec 位于 `.agent/specs/<spec-id>.md`，是**已发布行为的当前权威文本**；旧版保存在 `.agent/specs/history/<spec-id>/<revision>.md`。活动 Topic 的版本化 Spec 是该变更的实施边界，发布前不会自动改变长期 Spec。合并时先通读原长期 Spec 与 Topic 的当前 Spec，将完整的现行行为写入 `.agent/work/<topic>/archive/canonical-spec.md`，核对新增、修改、移除行为及不变量。候选 frontmatter 使用 `spec_id`、顺序递增的 `revision`、`status: current`、`supersedes`（上一长期 Spec 即将保存的历史版本相对路径；首次为空）、`source_topic`、`source_spec_revision`、`source_spec_sha256`。独立审查结论写入同目录的 `spec-review.md`，`spec-review.json` 记录 `schema_version: 1`、`reviewer`、`verdict: No findings.`、`source_sha256`、`previous_sha256`（首次为 `none`）、`candidate_sha256`、`report_sha256`。`archive-spec` 默认只预览来源、候选哈希、审查状态和目标；审查记录与字节匹配后用 `--apply --expected-sha256 <预览的 candidate_sha256> --expected-previous-sha256 <预览的 previous_sha256，首次为 none>` 发布。命令只验证结构、完成状态、Ticket 血缘、已完成实施会话冻结的 Spec 哈希和 Ticket 定义，以及审查记录绑定；审查者独立性和文本是否忠实合并仍需人工核实。一个 Topic 对应一个 Spec id，且只能发布一次。发布前要求 Topic 的实施 Ticket 全部完成且验收项仍全部勾选、每张都有与其来源 Spec 和 Ticket 定义匹配的已完成实施会话，当前来源 Spec revision 至少有一张已完成 Ticket，且没有活动实施会话。发布事务会写入 `archive/publication.json`，区分 `publishing` 与 `published` 并支持同内容重试；实施入口在封存后拒绝新会话。没有运行记录的旧实施 Topic 当前不能通过发布门禁；人工补证入口需另行设计，不能仅凭 Ticket 勾选发布。此功能目前只支持 `local` 后端。

`archive-topic` 默认预览 Topic 的完成依据（含长期 Spec 发布版本）、目标目录、逐文件路径与哈希，以及 `tree_sha256`；核对后用 `--apply --expected-digest <预览的 tree_sha256>` 将整个目录移至 `.agent/archive/<topic>/`。含实施 Ticket 的 Topic 必须先成功执行 `archive-spec`；纯文档/研究 Topic 不需要长期 Spec，但须在 `archive/completion.json` 声明 `schema_version: 1`、`topic`、`status: complete`、`behavior_change: none` 和非空的 Topic 内 `evidence` 路径列表。证据必须是独立于 `archive/` 的非空文件。若其他活动 Topic、项目 profile 或当前长期 Spec 仍通过绝对路径、项目相对路径、相对链接或符号链接引用旧 Topic，先处理该引用。归档清单保存原路径、新路径及每个文件的哈希；`archive-list` 轻量列出归档路径和清单存在状态（不做完整核验，单份损坏归档不会挡住其他条目），`archive-show` 核验文件及完成会话的历史收据，并将历史 Ticket、会话及审查结果中的 Topic 内路径映射到归档目录，同时报告外部来源的失效或漂移。原始 Ticket、journal 和证据字节保持不变；归档历史不进入活动实施准入。

接续工作时先指定主题查看 `work-overview`。文本视图汇总已完成 Ticket 和历史会话的数量，完整记录仍在 `--json` 中。如果有一个来源一致、与当前 Ticket claim 匹配的活动会话，总览会指出它的下一动作；其他旧会话或旧文件的问题仍逐条显示，顶层状态仍为 `needs-attention`。看到问题时应按文件核查，不能把下一动作提示理解为已通过实施门禁。

测试命令来自项目 profile 的 `test_commands`。`my-implement` 宿主可用 `run-review-submit` 登记组合的 `my-code-review` 结果；需要独立进程时，审查命令来自可选的 `review_commands`。runtime 只执行 work unit 建立时已冻结的精确 argv；审查命令从 `MY_MATT_REVIEW_ID`、`MY_MATT_REVIEW_SNAPSHOT`、`MY_MATT_CODE_CONTENT_ID` 读取当前审查单元，并在 stdout 输出结果 JSON。

`workflow.py check` 是源树的权威本地检查：它严格验证静态输入、确定性 contract、fresh-agent 验证计划与 digest 绑定的执行证据注册表，并运行完整单元测试；存在 `current.json` 时还会先校验 release 的校验和、缺失文件和额外文件，再比较其与源树是否一致。没有登记实际执行证据时，`execution_evidence.status` 明确为 `not-recorded`；存在记录时同时报告 `release_ids` 和相对 current release 的 `current|historical|mixed`，避免把旧 release 的运行记录解释为当前证据。这些状态不影响静态/确定性门禁的真实性，也不会被表述成 Agent 行为通过。尚未构建首个 release 时会明确报告 release 验证不适用。

`workflow.py doctor` 是只读部署诊断：它分别报告源树、current release 与 Codex/Cursor/Claude 安装状态，明确区分 `valid`、`drift`、`invalid` 和 `not-installed`，不会自动安装或修复。

`build` 会先取得 byte-exact 源码快照；若复制期间工作树发生变化则重试，完整源树门禁与打包都只读取同一快照。它跳过旧 `current.json` 的一致性比较，因此可用新 release 替换已过期或损坏的 current release。`build` 仅构建并更新 current 指针；`deploy` 会在当前 release 完整且与源树一致时复用它，否则保留损坏 release 供排查、构建新 release 后再安装。

项目首次使用时手动运行 `/my-setup`。日常通过 `/my-ask-matt` 查询下一条命令，再手动调用推荐的 `/my-*`。

Codex 默认把 Skills 安装到 `${CODEX_HOME:-~/.codex}/skills`，把安装状态和版本化 runtime 保存到 `${CODEX_HOME:-~/.codex}/my-matt-workflow`。旧版安装状态仍指向 `.agents/skills` 时，下一次安装会在同一事务中迁移已托管的 `my-*` Skills。安装后的 `install-state.json` 会记录绝对 `runtime_entry`，因此项目内命令不依赖当前工作目录中存在本仓库的 `tools/`。
