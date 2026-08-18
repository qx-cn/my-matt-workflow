---
name: my-setup
description: 为当前项目初始化一次性的个人 Matt 工作流配置
disable-model-invocation: true
---

# My Setup

为当前项目建立 `.agent/matt-workflow.md`。无 Git 项目使用完整的 `.agent/` 工作目录作为文档和进度的持久位置；仅跳过 Git 默认分支发现与 `.gitignore` 维护。

1. 从当前 Agent 安装状态读取 `installed_agent`，作为 `default_execution_agent` 候选；用户可覆盖。读取该 Agent 的原生规则、`AGENTS.md`、README、贡献文档、Issue 模板和测试命令；存在 Git 时再读取 remote、默认分支和已跟踪目录。不要混读其他 Agent 的专属规则；后续仍按实际作用范围重新解析。
2. 检测结果只是证据。逐项向用户确认 Tracker、文档来源、测试命令、Git 写操作策略和自治策略。默认建议五档预设之一：`strict-control`（严格控制，默认）、`light-control`（轻轻控制）、`review`（我做审核）、`semi-auto`（半自动化）、`full-auto`（全自动化）。旧名 `supervised` / `unattended` 仅作兼容别名。生成的 `.agent/matt-workflow.md` 会显式写出全部配置键（含默认值与 `humanizer_policy`），并内嵌五档说明；也可逐项覆盖细项。取值说明与校验同源：见 `tools/workflow_lib/profile.py` 的 `format_policy_catalog()`，以及 setup/refresh 写入配置文件顶部的预设注释。
3. 从安装状态读取绝对 `runtime_entry`；首次配置先运行 `python3 <runtime_entry> setup --repo <repo>` 展示预览，用户确认后再带 `--apply` 写入。不得依赖当前项目中存在本工作流仓库的 `tools/`。
4. 已有项目先运行 `workflow.py setup --repo <repo>` 展示工作产物布局 dry-run；报告必须列出移动、待删除旧路径、有效相对链接重写、候选失效链接修复、冲突和无法归类项，且此步零写入。
5. 用户审阅并明确确认后，运行 `workflow.py refresh-project --repo <repo> --migrate-work-artifacts` 执行有效产物迁移、链接重写和最终链接存在性验证。它保留未指定的既有配置，刷新后仍保持显式完整；需要更新策略时再附加 `--preset <strict-control|light-control|review|semi-auto|full-auto>` 或单独的策略覆盖参数。
6. 迁移前已失效的链接仍只作为候选。只有用户逐条确认后，才为每一条附加 `--confirm-candidate-link-repair <source> <link>`；未列出的候选不得写入。冲突项不得自动覆盖，无法归类项保持原位置并留在报告中。
7. Git 项目中，若 `.agent/` 已含跟踪文件，报告冲突，不用整目录规则忽略它；无 Git 项目不创建 `.gitignore`，仍直接维护 `.agent/`。
8. 已有配置时不重复询问；只有用户要求刷新或证据变化时才重新确认。

`--apply` 是硬门槛：即使用户要求赶时间或跳过询问，也必须先展示最终摘要并获得一次新的明确确认；最初的 setup 请求不算这次确认。

从当前 Agent 安装根目录中的 `my-matt-workflow/install-state.json` 读取来源；不得假设特定 Agent 品牌或用户目录。
