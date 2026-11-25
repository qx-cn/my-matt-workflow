# my-matt-workflow 仓库准则

本仓库维护跨宿主（Cursor / Claude Code / Codex / WorkBuddy）共用的 4 个核心 Skill（`my-grill`、`my-tech-design`、`my-doc-publish`、`my-review`）和 1 份个人通用规则 `rules/global.md`。

---

## 1. 权威依据

讨论本仓库的设计取舍、增删规则或评估写法时，按主题查阅[编写与审核参考](docs/authoring-guidance.md)，用网页检索工具核对原始出处，给出原文关键句、链接和适用范围，区分官方结论与项目判断。该文档只用于维护本仓规则，日常业务写作和运行 Skill 时无需读取；只做细微措辞调整或修脚本时也不用重新抓取网页。

---

## 2. 维护自检清单

每次修改本仓规则、模板或 Skill 时，对照下面四条核查：

1. **保持精简、泛化与脱敏**：
   - 模型自己读代码就能知道的事和通用常识不写进规则；只在发现 Agent 重复犯错或存在明确团队约束时才加规则，不在同一阶段塞过多细碎要求分散注意力。
   - 从单次业务复盘提炼规则时，先抽象成跨项目通用的原则（可配 1 组简短正向改写例子），绝不把单一项目的表名、字段、命令参数或单次排障特例写进通用规则或模板。
   - 本仓库托管于公开 GitHub，所有纳入版本控制的文件不写入企业内部域名、真实业务表名或专有业务代号。
2. **明确四层单点事实源，改动时同步核对关联文件**：
   - `rules/global.md` 只放全会话跨任务通用的底线规范（表达、编码实施、安全与浏览器操作），把长文档专项细则留给按需加载的 Skill；本仓库维护约定放在本文件。
   - **单文档默认原则与边界**：单个需求在设计期默认只维护**唯一一份核心设计文档（本地 `design.md` 与对应的飞书云文档）**，同时用于团队评审与指导编码验收，不再额外维护重叠的代码级 `spec.md` 或独立 `decided.md` 流水账（关键选型取舍直接收入 `design.md` 的《方案取舍》表）。上线期按需另出《发布文档》与《测试报告》；涉及多个独立子系统或不同评审团队的大型项目，按评审边界拆分文档。
   - **4 个 Skill 按阶段分工**：`my-grill` 先查代码再逐轮提问对齐需求；`my-tech-design` 作为工程文档专项写作的唯一事实源，产出纯 Markdown 定稿（不混写 XML/HTML/DSL 排版代码）；`my-doc-publish` 将定稿渲染为飞书云文档（含画板）或本地交互式 HTML；`my-review` 定义独立只读审查流程与“必须修 / 建议”分级标尺，审查时按路径直接引用原始规范文件，不重复抄写上游条文。
   - **改动行为或标准后同步检查关联文件**：微调字句只改对应文件；一旦改动规则或 Skill 的行为、结构或判定标准，同步检查运行时会一起加载的关联文件，包括 `rules/global.md`、同目录模板与校验脚本（`TEMPLATES.md`、`TEMPLATE.html`、`check_html.py`、`check_feishu.py`）、下游 `my-review/SKILL.md`、引用的外部 Skill 以及 `docs/authoring-guidance.md`。若某阶段确有例外，回到上游规则写明适用前提，不在下层另写互相打架的指令。
   - **规则自身必须说人话**：本仓库所有 Markdown 文件本身就是模型最直接的模仿样本，必须遵守 `rules/global.md`，用平实自然的工程师语言编写，不造内部黑话、不连套多层定语和长括号。
3. **手动触发与两级脚本兜底**：
   - Skill 的 `description` 用第三人称写清“做什么”和“什么时候用（触发词放前面）”，兼作 `/` 菜单说明与按需开启自动匹配时的触发依据。
   - 4 个核心 Skill 统一保持手动触发（`disable-model-invocation: true` 且 `openai.yaml` 设 `allow_implicit_invocation: false`），防止重型工作流被模型误触发；宿主设为手动触发后模型上下文看不到 Skill 描述，跨阶段衔接（如改飞书方案调 `my-doc-publish`）需在 `rules/global.md` 或上游 Skill 中显式指明路径。
   - **能用脚本拦的就不靠加粗强调**：少堆满篇 `MUST / 必须 / 禁止`；反复强调仍漏掉的客观版式或结构要求写进确定性校验脚本（`./scripts/sync.sh --check`、`python3 skills/my-doc-publish/scripts/check_html.py <html路径>`、`python3 skills/my-doc-publish/scripts/check_feishu.py <xml路径> [board.json ...]`），在报错里直接写明怎么修。脚本门禁区分两级：客观必错或平台报错项报 `ERROR` 阻断发布，启发式可读性与构图提醒报 `WARN` 由作者逐条核查。审查本仓改动时，不用待审的新版 `my-review` 自己审批自己，改为对照本清单、修改前基线、权威依据和真实样本独立核查。
4. **不要重新引入的废弃设计**：
   - 不重新引入双轨文档（同时维护重型代码级 `spec.md` 与评审 `design.md`）或独立 `decided.md` 流水账。
   - 不搞 Python 状态机、Ticket 状态管理、审查轮数计数器、强制 JSON 中间笔记或构建打包流程。
   - 不拿自动 PR 评论机器人的窄标准（如“只报高确信崩溃 bug”）套用会话内审查。

---

## 3. 跨宿主同步与校验

安装软链正常不代表当前会话已经重新读取了最新规则，两件事要分开核实。

- 本仓库在 `main` 分支维护，v1 旧版基线可用 `git show 16c03b5:<path>` 查看。
- 运行 `./scripts/sync.sh` 建立本机 Claude Code、Codex（及按需开启的 WorkBuddy）软链并自动清理已退役 Skill 的残留软链；日常修改后运行 `./scripts/sync.sh --check` 检查软链与 `rules/global.md` 的 4,000 字符上限。WorkBuddy 仅在设置了环境变量 `WORKBUDDY_CONFIG_DIR` 时启用，将其 `skills/` 和 `MEMORY.md` 软链到本仓库。
- **宿主加载边界**：本同步方案面向本机 IDE 与 CLI 会话。Claude Desktop 的 Cowork 模式会跳过指向软链的 `CLAUDE.md` 且不加载本机 `~/.claude/skills/`；Cursor Cloud Agents 只同步 `~/.cursor/skills/` 而不同步 `~/.agents/skills/`。
- **Cursor 用户规则同步**：本机 Cursor 不读取软链规则文件。每次修改 `rules/global.md` 后，同步更新 Cursor 设置里名为“个人通用规则”的 User Rule：工具可用时直接调用 `cursor-app-control` 的 `cursor_dialog`（`item="rule", scope="user"`）更新，不可用时提醒用户手动粘贴同步。
