# my-matt-workflow 仓库准则

本仓库维护个人跨宿主（Cursor / Claude Code / Codex）的 4 个核心 Skill 与 1 份全局规则 `rules/global.md`。

## 1. 权威依据（按需查证）

讨论设计取舍、增删规则条款或评估写法是否合理时，按需用 `WebFetch` 查证以下一手来源（不凭记忆脑补，贴出原文关键句与链接，并核对适用场景是否一致；仅做文字微调或修脚本时不必抓取）：

- **Skill 与 Rule 编写规范**：
  - Anthropic Agent Skills Best Practices：`https://docs.claude.com/en/docs/agents-and-tools/agent-skills/best-practices`
  - Claude Code Best Practices：`https://code.claude.com/docs/en/best-practices`
  - Claude Code Memory (`CLAUDE.md` / `AGENTS.md`)：`https://code.claude.com/docs/en/memory`
  - Anthropic Effective Context Engineering：`https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents`
  - OpenAI Codex Skills：`https://developers.openai.com/codex/skills`
  - Cursor Rules：`https://cursor.com/docs/rules`
- **技术文档写作规范**（优化文档类规则或 Skill 时查证）：
  - Google Technical Writing：`https://developers.google.com/tech-writing/one/short-sentences` 、`.../lists-and-tables` 、`.../paragraphs` 、`.../active-voice` 、`.../words` 、`https://developers.google.com/tech-writing/two/large-docs` 、`.../illustrations`
  - Google Developer Documentation Style Guide：`https://developers.google.com/style/code-in-text` 、`.../lists` 、`.../tables` 、`.../headings`
  - Gemini CLI 官方 `docs-writer`：`https://raw.githubusercontent.com/google-gemini/gemini-cli/main/.gemini/skills/docs-writer/SKILL.md`
  - 阮一峰《中文技术文档的写作规范》：`https://raw.githubusercontent.com/ruanyf/document-style-guide/master/docs/text.md` 、`.../paragraph.md` 、`.../title.md`
- **实证研究基线**：
  - ETH Zurich `AGENTS.md` 实证（`https://arxiv.org/abs/2602.11988`）：只写代码与常识推不出来的非推断信息，冗余上下文会增加约 20% 成本并降低成功率。
  - SkillsBench（`https://arxiv.org/abs/2602.12670`）：聚焦、模块少（≤3 个）的 Skill 效果最好，复述模型默认能力的 Skill 会产生负优化。

## 2. 审核清单（每次改动自检）

1. **删减测试**：每加一行规则先问"删掉这行，前沿模型会犯错吗？"只有真实工作里出现过 2 次以上的失误、个人明确偏好、或环境/团队特有约束才写入。
2. **层级隔离与自洽（零重复）**：
   - `rules/global.md` 每次会话常驻加载，保持在 30 行以内，只放所有对话通用的底线。
   - 长文档排版、特定任务流程放在对应 `skills/<name>/SKILL.md` 按需加载；大段模板放同目录子文件（如 `TEMPLATES.md`）。`global.md` 已有内容，Skill 内不再重复。
   - 本仓库所有 Markdown 文件自身必须遵守 `global.md` 与排版规范（如不用破折号、不标题直接套标题、不设孤立子标题），因为模型模仿示例格式的权重高于字面指令。
3. **触发与自由度**：
   - `description` 用第三人称同时写清"做什么"与"何时使用（触发词前置）"。
   - 仅 `my-review` 允许模型自动调用；其余 Skill 保持手动调用（`disable-model-invocation: true` 及 `openai.yaml` 中 `allow_implicit_invocation: false`）。
   - 避免满篇 `MUST / 必须 / 禁止`；确定性检查交给脚本（如 `check_html.py`）。
4. **已否决的设计（不要重新引入）**：
   - 不引入 Python runtime 状态机、批次/Ticket 状态管理、审查轮数计数器、强制 JSON 笔记或构建打包复制流程。
   - 不把"自动 PR 评论机器人"的窄准入标准（如"只报高确信必修项"）套用到会话内交付前审查。

## 3. 跨宿主同步方式

- 本仓库在 `main` 上维护，v1 历史基线可查 `git show 16c03b5:<path>`。
- Skill 与 Claude/Codex 全局规则通过 `scripts/sync.sh` 软链生效；修改 `rules/global.md` 后，若当前在 Cursor 本地会话内，调用 `cursor-app-control` 的 `cursor_dialog`（`item="rule", scope="user"`）同步更新名为"个人通用规则"的用户规则；若在云端或其他宿主，提醒用户回本机 Cursor 同步。
