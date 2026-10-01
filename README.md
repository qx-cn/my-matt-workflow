# My Matt Workflow

个人使用的 Matt Pocock 工作流适配包，支持 Python 3.10+，可安装到 Codex、Cursor 和 Claude。

## 使用流程

对齐点 1 是确认需求摘要与 quick/standard 等级：目标、范围、约束和可观察验收注明来源。standard 还有对齐点 2：一起审阅 Spec 与 Ticket 拆分，包括逐张行为、依赖、测试命令和测试边界；quick 在第一个对齐点后直接实施。已确认范围内的测试、审查和本地提交由 Agent 继续完成；目标、范围、接口或风险承担变化时，再找用户确认。工作流不推送、不建 MR、不写外部系统。

首次使用项目时调用 `my-setup`，探测并展示配置，确认一次后写入。日常由 `my-ask-matt` 帮助选择入口；组合清单中的被调用 Skill 可以由模型调用，其余入口由用户手动调用。Matt 原生 Skills 仅用于升级比较，运行时使用本包的 `my-*`。

- **quick**：单会话能完成、局部可撤回、不改持久化结构、权限或对外 API 契约，且预计一张 Ticket 就能做完；不写 Spec 或 Ticket，Agent 完成测试和同会话自审。
- **standard**：以版本化 Spec 和 Ticket 切片实施；每张 Ticket 定向测试、六节增强自审、本地提交；批次末全量测试与基线比较、独立批次审查后收口。

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

# standard：确认Spec/Ticket与批次划分后开始
python3 tools/workflow.py topic start --repo <project> --topic <topic> --level standard
python3 tools/workflow.py batch plan --repo <project> --topic <topic>
# 分批时加 --groups-file <已确认的Ticket分组JSON> --reason <理由>

# 对批次内每张Ticket按依赖重复；干净自审用--no-findings
python3 tools/workflow.py implement start --repo <project> --ticket <topic>-01
python3 tools/workflow.py implement test --repo <project> --ticket <topic>-01
python3 tools/workflow.py implement self-review --repo <project> --ticket <topic>-01 --notes-file <六节记录.md> --no-findings
python3 tools/workflow.py implement finish --repo <project> --ticket <topic>-01

# 全部Ticket提交后：全量测试、一次新上下文批次审查、收口
python3 tools/workflow.py batch test --repo <project> --topic <topic>
python3 tools/workflow.py batch review --repo <project> --topic <topic> --reviewer-model <实际模型> --reviewer-session-id <宿主的新上下文标识>
python3 tools/workflow.py batch review --repo <project> --topic <topic> --submit <runtime返回的result_file>
python3 tools/workflow.py batch close --repo <project> --topic <topic>
# 所有批次收口，完成交付摘要后
python3 tools/workflow.py topic complete --repo <project> --topic <topic>

# 恢复状态与观察结果
python3 tools/workflow.py topic status --repo <project> --topic <topic> --human
python3 tools/workflow.py implement status --repo <project> --ticket <topic>-01 --human
python3 tools/workflow.py work-overview --repo <project> --json
python3 tools/workflow.py metrics --repo <project> --topic <topic>
```

`topic start` 必须指定 Topic；其他 Topic 操作在只有一个活动 Topic 时可以省略。Ticket id 包含 Topic，指定 `--ticket` 后无需另带 `--topic`；省略 Ticket 时选择该 Topic 唯一的活动 Ticket。多 Topic 时显式选择。

`batch review` 冻结提交范围、完整仓库、批次 Ticket/验收、有效 Spec、已决事项、项目规则与影响声明。新上下文审查者独立核实调用方与消费者。runtime 提供材料包和预填身份的结果骨架，Agent 填判断字段，提交时无需手抄哈希。发现用位置、五种视角（correctness/impact/spec/spec-challenge/maintainability）、依据和严重度登记，验收锚点可选；advisory 附 fix-in-batch/defer（建议归属）/decline（理由）。覆盖验收仍必填；Spec 导致可达故障时交用户裁决，不因符合 Spec 放行。

有阻断或本批次修复建议时，修改后用 `batch repair --notes-file <引用发现id的修复说明>` 提交，再 `batch test/review` 复审差异；不创建逐发现补偿 Ticket。内容变化使通过记录失效。批次收口之后才是不可改写历史，后续改变通过补偿或迁移 Ticket。

默认整个 Topic 一个批次。只有天然集成边界，或预计超过 8 张 Ticket / 20 个文件时考虑拆分；这是无实测依据的保守启发式，不是用户配置。划分与理由在对齐点2一起确认。未触发例外的干净批次只派一次审查子 Agent。

高风险 Ticket（迁移/持久状态、并发/锁、对外契约、发布回滚兼容、权限安全边界）可在提交前额外运行 `implement review --reason <触发理由> --reviewer-model <实际模型> --reviewer-session-id <新上下文标识>`，结果仍用 `implement review --submit <结果文件>` 提交；多数 Ticket 不需要。阻断及本批次修复项处理后再提交，批次审查仍执行且范围不缩小。宿主派不出时如实记同会话自审，摘要披露独立性缺口。

多批次最后一次批次审查包含整个 Topic 的改动清单。整分支审查可选，在最后批次收口前执行 `topic review --initiated-by user|agent --reason <理由>`，同样带实际模型和新上下文标识；不能替代批次审查。其修复由最后批次承接，允许涉及已收口批次代码；选择执行后也需通过才能最后收口。

Topic 首个批次开工前在干净基线跑一次全量集合；每张 Ticket 只跑声明的定向命令。批次末新增失败阻断，基线已失败且仍失败的用例列“已知问题”；基线环境缺失无法运行的命令列“未验证项”，不能为变绿改无关文件/配置/环境。旧版已开始的实施历史沿原协议恢复；未开始的旧格式 Ticket 可直接进入新批次路径，rule_* 不再必填，触点提示非边界。

Spec 定稿前遇到持久数据、锁/并发、外部契约、发布回滚兼容或改变其他模块行为，自动一次新上下文设计审查加最多一次差异复审；未触发要写理由。设计审查必须读代码核实事实，报告断言核验、发现、排除风险和待决语义假设四部分。挑战与假设在下一个已有对齐点交用户，已决事项不重开。保存设计报告到 Topic reviews，结构化 design_report 或完整四部分 Markdown 可供逃逸登记识别；无可识别记录标“未知”。

审查停止时由用户决定接受、修订后重开或放弃：批次用 `batch accept|reopen --reason <裁决>`；高风险 Ticket 用 `resolve --ticket <id> --accept|--reopen --reason <裁决>`；整分支用 `resolve --branch --accept|--reopen --reason <裁决>`。接受不能绕过测试；停止整个 Topic 用 `topic abandon --reason <原因>`，历史归档且不覆盖。

Agent 默认消费状态 JSON；给用户展示时用 topic/implement/batch status 的 `--human`，输出中文进度、需要决定的事项、未验证命令与下一步。quick 不建 Spec/Ticket，仍同会话自审六节。交付摘要包含改动概述、测试结果、审查发现与修复、建议、已知问题、长期知识沉淀、用户介入记录、未验证项；发现/修复按视角及自审/批次审查/用户来源分别统计，无可靠记录保持未知。

旧格式项目用 `migrate --repo <project>` 预览备份、冲突和无法推断项，经确认后加 `--apply`。先解决无法自动迁移的事项；已完成历史保留。本仓库自身仅更新配置，不运行该迁移。

## 维护与验证

工作流源码是唯一可编辑源，安装件来自稳定 release。修改工作流的提交必须有一行 `Trigger:`，说明哪个项目的什么问题触发，例如：

```text
Trigger: trader 的重复审查停止无法恢复，补充状态恢复契约。
```

在度量证明有必要之前，不新增门禁。`.agent/metrics.jsonl` 记录 Ticket、Topic、quick 的测试、审查、修复、用户介入和命令错误；无法观察的字段为 null，命令错误不含测试失败，审查来源区分 self、independent 和 mixed。`metrics` 按 Topic 汇总，包括视角/来源/严重度的发现数、每批次独立审查子 Agent 数、高风险审查次数与其中有阻断的次数、可选整分支的发起方/理由/发现数。相同审查单元内同 id 的发现跨轮次只计一次；独立子 Agent 按宿主声明的新上下文标识去重，未取得上下文的旧记录保持未知。来源另列高风险、整分支和旧版逐 Ticket 审查，避免误算为自审或普通批次发现。

自审发现用 `implement self-review --findings-file <M2发现数组.json>` 登记，确实无发现用 `--no-findings`；只有旧六节记录的数目保持未知。逃逸缺陷可登记活动或已归档 Topic：

```bash
python3 tools/workflow.py escape --repo <project> --topic <topic> --batch 01 --ticket <topic>-01 --source 人工评审 --view impact --expected-layer 批次审查 --description <具体缺陷>
python3 tools/workflow.py metrics --repo <project> --topic <topic>
```

来源还可为外部审查工具、测试环境、生产、后续开发；本应捕获层还可为访谈、Spec 编写、设计审查、实施自审。批次/Ticket 可省略，登记自动附设计审查状态，不需用户补字段。metrics 列每 Topic 逃逸数及按本应捕获层分组。机械测试与一次模型演练不能证明真实项目审查更好，应通过后续逃逸数据观察。

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
| Topic与实施 | topic、batch、implement、resolve、work-overview、metrics、escape |
| 检查与部署 | validate、check、doctor、build、install、deploy、prune-releases |
| 规则与Ticket | resolve-rules、inspect-rules、validate-ticket |
| 内容快照 | review-snapshot |
| 工件审查 | artifact-review-snapshot、artifact-review-open、artifact-review-submit、artifact-review-verify、artifact-review-finalize |

`artifact-review-*` 支持 general/design；design 的结果额外含 design_report 四部分，无内容附理由。用原参数和 `--expect-content-id` 绑定内容；串行执行所需方法，不累计审查轮数。独立工件审查与 Ticket/整分支审查各自使用其对应单元。

Codex 默认将 Skills 放在 `${CODEX_HOME:-~/.codex}/skills`，安装状态和版本化 runtime 放在 `${CODEX_HOME:-~/.codex}/my-matt-workflow`；Cursor、Claude 使用各自宿主目录。项目调用以安装状态中的 runtime_entry 为准。
