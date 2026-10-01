# My Matt Workflow

个人使用的 Matt Pocock 工作流适配包，支持 Python 3.10+，可安装到 Codex、Cursor 和 Claude。

## 使用流程

对齐点 1 是确认需求摘要与 quick/standard 等级：目标、范围、约束和可观察验收注明来源。standard 还有对齐点 2：一起审阅 Spec 与 Ticket 拆分，包括逐张行为、依赖、测试命令和测试边界；quick 在第一个对齐点后直接实施。已确认范围内的测试、审查和本地提交由 Agent 继续完成；目标、范围、接口或风险承担变化时，再找用户确认。工作流不推送、不建 MR、不写外部系统。

首次使用项目时调用 `my-setup`，探测并展示配置，确认一次后写入。日常由 `my-ask-matt` 帮助选择入口；组合清单中的被调用 Skill 可以由模型调用，其余入口由用户手动调用。Matt 原生 Skills 仅用于升级比较，运行时使用本包的 `my-*`。

- **quick**：单会话能完成、局部可撤回、不改持久化结构、权限或对外 API 契约，且预计一张 Ticket 就能做完；不写 Spec 或 Ticket，Agent 完成测试和同会话自审。
- **standard**：以版本化 Spec 和 Ticket 切片实施；每张 Ticket 经过测试与审查，再提交完成。

Topic 是 `.agent/work/<topic>/` 下的一项工作。文档与进度按类型分目录保存；术语和决定集中沉淀到 `.agent/CONTEXT.md` 与 `.agent/adr/`。`topic complete` 负责收尾、归档及记录度量。`my-handoff` 用于换宿主、目录或人员，或保存尚未形成 Spec 的访谈结论。

## 项目配置

`.agent/matt-workflow.md` 的 frontmatter 只有九个键：

```yaml
---
schema_version: 2
task_backend: "local"
agent_directory_mode: "private"
default_base_branch: "main"
test_commands: ["python3 -m unittest discover -s tests"]
standards_sources: []
domain_sources: []
default_execution_agent: "auto"
assurance_level: "standard"
---
```

`task_backend` 仅支持 `local`；`assurance_level` 为 `quick` 或 `standard`。`default_execution_agent` 可选 `auto`、`codex`、`cursor`、`claude`；auto 在开始 Ticket 时绑定实际 Agent。标准与领域来源填写项目中真实存在的文档路径。

`agent_directory_mode: private`（默认）将 `.agent/` 初始化为无 remote 的本地嵌套 Git；`shared` 由主仓库跟踪。无 Git 项目同样使用 `.agent/` 保存文档和进度。setup 不改主仓库 `.gitignore`，已有归属冲突不自动删除。

`test_commands` 中不以 ` *` 结尾的条目组成全量测试集合，standard 必须非空。以 ` *` 结尾的条目允许 `implement test -- <具体命令>` 匹配执行，但不能代替全量集合。Ticket 声明的测试必须与配置匹配。

本仓库使用 local/shared/main/auto/standard，测试为完整 unittest。已有工作文档保持原格式；配置更新不会转换或归档它们。总览中的历史 Topic 可能显示“需要迁移”，不应据此自动迁移本仓库历史。

## 项目命令

下列示例使用源码入口。安装后的项目应从当前 Agent 的 `my-matt-workflow/install-state.json` 读取绝对 `runtime_entry`，用它替换 `tools/workflow.py`。

```bash
# 探测、展示；确认后以相同参数加 --apply
python3 tools/workflow.py setup --repo <project>
python3 tools/workflow.py setup --repo <project> --apply

# 启动quick，完成改动、摘要和自审后收尾
python3 tools/workflow.py topic start --repo <project> --topic <topic> --level quick
python3 tools/workflow.py topic complete --repo <project> --topic <topic>

# standard：已有Ticket时可自动补建Topic
python3 tools/workflow.py implement start --repo <project> --ticket <topic>-01
python3 tools/workflow.py implement test --repo <project> --ticket <topic>-01
python3 tools/workflow.py implement review --repo <project> --ticket <topic>-01
python3 tools/workflow.py implement review --repo <project> --ticket <topic>-01 --submit <result.json>
python3 tools/workflow.py implement finish --repo <project> --ticket <topic>-01

# 恢复状态与观察结果
python3 tools/workflow.py topic status --repo <project> --topic <topic>
python3 tools/workflow.py implement status --repo <project> --ticket <topic>-01
python3 tools/workflow.py work-overview --repo <project> --json
python3 tools/workflow.py metrics --repo <project> --topic <topic>
```

`topic start` 必须指定 Topic；其他 Topic 操作在只有一个活动 Topic 时可以省略。Ticket id 包含 Topic，指定 `--ticket` 后无需另带 `--topic`；省略 Ticket 时选择该 Topic 唯一的活动 Ticket。多 Topic 时显式选择。

`implement review` 冻结当前内容，输出材料包和结果骨架。审查者只读材料包，提交结果绑定同一内容；格式错误按字段修正。发现以 `location`、`view`（correctness/impact/spec/spec-challenge/maintainability）、`basis` 和 `severity` 登记，`anchor` 可选；advisory 必须附处置 `disposition`。验收覆盖仍必填；Spec 挑战交用户裁决。测试失败、审查后内容变化、越序或审查单元不匹配都不能继续完成。实施经过修复时，finish 需要 `--notes-file <文件>` 记录思路。审查停止后的 `needs-user` 由用户决定接受或重开：

```bash
python3 tools/workflow.py resolve --repo <project> --ticket <topic>-01 --accept --reason <reason>
python3 tools/workflow.py resolve --repo <project> --ticket <topic>-01 --reopen --reason <reason>
```

接受仍需当前内容通过全量测试；重开要求 Ticket 或来源 Spec 的定义变化。已完成 Ticket 是历史，后续改变通过补偿或迁移工作表达。

standard 多 Ticket 完成后，通过 `topic test`、`topic review`（及 `--submit`）验证整分支，再运行 `topic complete`。单 Ticket 不要求整分支审查。quick 与 standard 的交付摘要须有：改动概述、测试结果、审查发现与修复、建议、已知问题、长期知识沉淀、用户介入记录、未验证项；quick 还需验收对照。quick 未配置测试时必须如实标记。文档 Topic 可直接收尾。

整分支停止后用 `resolve --branch --accept|--reopen --reason <原因>` 处理。停止整个 Topic 用 `topic abandon --reason <原因>`，归档历史并保留未提交内容；同名归档不覆盖。

旧格式项目用 `migrate --repo <project>` 预览备份、冲突和无法推断项，经确认后加 `--apply`。先解决无法自动迁移的事项；已完成历史保留。本仓库自身仅更新配置，不运行该迁移。

## 维护与验证

工作流源码是唯一可编辑源，安装件来自稳定 release。修改工作流的提交必须有一行 `Trigger:`，说明哪个项目的什么问题触发，例如：

```text
Trigger: trader 的重复审查停止无法恢复，补充状态恢复契约。
```

在度量证明有必要之前，不新增门禁。`.agent/metrics.jsonl` 记录 Ticket、Topic、quick 的测试、审查、修复、用户介入和命令错误；无法观察的字段为 null，命令错误不含测试失败，审查来源区分 self、independent 和 mixed。`metrics` 按 Topic 汇总。

在本目录运行：

```bash
python3 tools/workflow.py validate
python3 tools/workflow.py check
python3 tools/workflow.py doctor
python3 tools/workflow.py build --release-id <release-id>
python3 tools/workflow.py install --target codex
python3 tools/workflow.py deploy --target codex
python3 tools/workflow.py prune-releases
```

`check` 只运行 tests 下的 unittest，包括静态校验和临时 Git 仓库中的 CLI 行为测试，不修改被跟踪文件。CI 在 Python 3.10 和 3.14 上运行 check，然后验证 `git diff --exit-code`。测试验证机械契约，不能替代真实的模型行为效果验证。

`doctor` 只读诊断源树、current release 和宿主部署，分别报告有效、漂移、无效或未安装。`build` 从同一源码快照运行检查、打包、更新 current；保留当前版本、上一个版本和安装状态引用的版本。`deploy` 复用完整且与源树一致的当前 release，否则构建后安装；维护命令须在相应授权范围内执行。

完整顶层命令清单如下，各命令参数以 `--help` 为准：

| 用途 | 命令 |
|---|---|
| 配置与迁移 | setup、migrate |
| Topic与实施 | topic、implement、resolve、work-overview、metrics |
| 检查与部署 | validate、check、doctor、build、install、deploy、prune-releases |
| 规则与Ticket | resolve-rules、inspect-rules、validate-ticket |
| 内容快照 | review-snapshot |
| 工件审查 | artifact-review-snapshot、artifact-review-open、artifact-review-submit、artifact-review-verify、artifact-review-finalize |

`artifact-review-*` 支持 general/design，用原参数和 `--expect-content-id` 绑定内容；串行执行所需方法，不累计审查轮数。独立工件审查与 Ticket/整分支审查各自使用其对应单元。

Codex 默认将 Skills 放在 `${CODEX_HOME:-~/.codex}/skills`，安装状态和版本化 runtime 放在 `${CODEX_HOME:-~/.codex}/my-matt-workflow`；Cursor、Claude 使用各自宿主目录。项目调用以安装状态中的 runtime_entry 为准。
