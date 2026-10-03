---
name: my-setup
description: 为当前项目初始化一次性的个人 Matt 工作流配置
disable-model-invocation: true
---

# My Setup

保证等级的准入与升级条件以[开发保证等级](references/shared/adapters/assurance-levels.md)为唯一事实来源。

为当前项目建立 `.agent/matt-workflow.md`。`.agent/` 保存文档和进度，归属由 `agent_directory_mode` 明确：默认 `private` 时 Git 项目将它初始化为无 remote 的本地嵌套 Git 仓库（不是 Git submodule）；`shared` 时不建嵌套 Git，由主仓库跟踪、提交和推送。不得为 `.agent/` 修改主仓库的 `.gitignore`；无 Git 项目直接使用完整的 `.agent/` 工作目录，仅跳过 Git 默认分支发现。

1. 从当前 Agent 安装状态读取 `installed_agent`，作为 `default_execution_agent` 候选；用户可覆盖。读取该 Agent 的原生规则、`AGENTS.md`、README、贡献文档、Issue 模板和测试命令；存在 Git 时再读取 remote、默认分支和已跟踪目录。不要混读其他 Agent 的专属规则；后续仍按实际作用范围重新解析。
2. 检测结果只是证据。展示测试命令、规则与文档来源、默认分支、执行 Agent、保证等级（quick 或 standard，默认 standard）、`.agent` 归属模式和 local 后端。执行 `python3 <runtime_entry> setup --repo <repo>` 及已选配置参数，先探测并展示，零写入。
3. 用户确认一次后，以相同参数加 `--apply` 写入 schema_version 2 配置。private 模式沿用本地无 remote 的嵌套 Git 初始化；shared 模式由主仓库跟踪。既有归属冲突不自动删除元数据。
4. 发现旧配置或旧产物时执行 `migrate --repo <repo>` 预览，说明备份、移动、冲突和无法推断项；获用户确认后以 `--apply` 执行，保留已完成历史，不猜测缺失事实。不得静默兼容旧格式。
5. 已有有效配置不重复询问；只有用户要求变更或探测证据变化时再展示差异。需用户处理时遵循[找用户的条件](references/shared/user-intervention.md)。

从当前 Agent 安装根目录中的 `my-matt-workflow/install-state.json` 读取来源；不得假设特定 Agent 品牌或用户目录。
