---
name: my-setup
description: 为当前项目初始化一次性的个人 Matt 工作流配置
disable-model-invocation: true
---

# My Setup

为当前项目建立 `.agent/matt-workflow.md`。`.agent/` 保存文档和进度，归属由 `agent_directory_mode` 明确：默认 `private` 时 Git 项目将它初始化为无 remote 的本地嵌套 Git 仓库（不是 Git submodule）；`shared` 时不建嵌套 Git，由主仓库跟踪、提交和推送。不得为 `.agent/` 修改主仓库的 `.gitignore`；无 Git 项目直接使用完整的 `.agent/` 工作目录，仅跳过 Git 默认分支发现。

1. 从当前 Agent 安装状态读取 `installed_agent`，作为 `default_execution_agent` 候选；用户可覆盖。读取该 Agent 的原生规则、`AGENTS.md`、README、贡献文档、Issue 模板和测试命令；存在 Git 时再读取 remote、默认分支和已跟踪目录。不要混读其他 Agent 的专属规则；后续仍按实际作用范围重新解析。
2. 检测结果只是证据。逐项向用户确认 Tracker、文档来源、测试命令、`.agent` 归属模式、Git 写操作策略和自治策略。默认建议五档预设之一：`strict-control`（严格控制，默认）、`light-control`（轻轻控制）、`review`（我做审核）、`semi-auto`（半自动化）、`full-auto`（全自动化）。旧名 `supervised` / `unattended` 仅作兼容别名。`agent_directory_mode` 与 `task_backend` 正交：`private` 是个人嵌套 Git，`shared` 是主仓库可跟踪目录；`local` 只表示本地任务产物。生成的 `.agent/matt-workflow.md` 会显式写出全部配置键（含默认值与 `humanizer_policy`），并内嵌五档说明；也可逐项覆盖细项。取值说明与校验同源：见 `tools/workflow_lib/profile.py` 的 `format_policy_catalog()`，以及 setup/refresh 写入配置文件顶部的预设注释。
3. 从安装状态读取绝对 `runtime_entry`；首次配置先运行 `python3 <runtime_entry> setup --repo <repo>` 展示预览，用户确认后再带 `--apply` 写入。不得依赖当前项目中存在本工作流仓库的 `tools/`。
4. 已有项目先运行 `workflow.py setup --repo <repo>` 展示工作产物布局 dry-run；报告必须列出移动、待删除旧路径、有效相对链接重写、候选失效链接修复、冲突和无法归类项，且此步零写入。
5. 用户审阅并明确确认后，运行 `workflow.py refresh-project --repo <repo> --migrate-work-artifacts` 执行有效产物迁移、链接重写和最终链接存在性验证。它保留未指定的既有配置，刷新后仍保持显式完整；需要更新策略时再附加 `--preset <strict-control|light-control|review|semi-auto|full-auto>` 或单独的策略覆盖参数。
6. 迁移前已失效的链接仍只作为候选。只有用户逐条确认后，才为每一条附加 `--confirm-candidate-link-repair <source> <link>`；未列出的候选不得写入。冲突项不得自动覆盖，无法归类项保持原位置并留在报告中。
7. Git 项目中，`private` 模式先检查主仓库是否已跟踪 `.agent/` 下的任意文件；若已跟踪，报告冲突，不初始化嵌套仓库，也不移动文件；否则仅在用户确认后的 apply 阶段：若 `.agent/.git` 不存在，执行 `git init --initial-branch=main .agent`。`shared` 模式允许主仓库跟踪 `.agent/`，且不创建嵌套仓库；它只使主仓库可以常规提交和推送，绝不自动推送。若切换时已有 `.agent/.git`，先展示待移除项；只有用户再次明确确认并附加 `--migrate-agent-directory-mode` 后才移除该嵌套 Git 元数据。不得修改主仓库 `.gitignore`、不得添加 remote、不得创建提交、不得移动或删除 `.agent/` 中其他已有文件。无 Git 项目仍直接维护 `.agent/`。
8. 已有配置时不重复询问；只有用户要求刷新或证据变化时才重新确认。

`--apply` 是硬门槛：即使用户要求赶时间或跳过询问，也必须先展示最终摘要并获得一次新的明确确认；最初的 setup 请求不算这次确认。

从当前 Agent 安装根目录中的 `my-matt-workflow/install-state.json` 读取来源；不得假设特定 Agent 品牌或用户目录。
