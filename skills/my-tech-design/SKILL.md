---
name: my-tech-design
description: 将讨论与代码库事实整理为可评审的技术方案；支持内容语义工件与 HTML 前端分阶段执行，以便分别选择内容模型和前端模型。
disable-model-invocation: true
---

# 技术方案

为不了解当前代码细节、但需要判断方案是否成立和风险是否可接受的工程师生成技术方案。它不是实现清单。

先读取[面向读者写作](references/shared/reader-first-writing.md)、[最终态写作](references/shared/final-state-writing.md)与[内容/前端交接](references/shared/document-rendering.md)，再选择阶段：

- 未指定阶段且没有语义工件：执行 `content`，读取 [CONTENT.md](CONTENT.md)，写入 `.agent/work/<topic>/designs/design-content-<topic>-<time-or-sequence>.md`，报告绝对路径与 `/my-tech-design frontend <artifact>` 后停止。
- `frontend <artifact>`：只读取该语义工件、[FRONTEND.md](FRONTEND.md)、[HTML 模板](assets/TEMPLATE.html)及校验脚本；不得重读源材料来改写内容。
- `full`：按顺序完成两阶段，仍保留语义工件。明确说明这是同一运行，不构成内容模型与前端模型已隔离的证据。

内容阶段与前端阶段可由不同模型独立运行。前端阶段发现承重事实、结论、章节或来源缺失时，返回 `blocked-by-content` 和缺口，不自行补写。

## 完成条件

- `content`：语义工件状态为 `content-ready`，读者、用途、来源、结论、章节、承重决策、风险、未知与可视化意图完整；其中不含 HTML、CSS 或 JavaScript。
- `frontend`：输出 `.agent/work/<topic>/designs/designs-<topic>-<time-or-sequence>.html`，没有覆盖历史文件；所有可见主张可追溯到语义工件。
- HTML 通过 `python3 scripts/check_html.py <html>`，并实际检查 1440px 与 1280px 桌面宽度、离线导航、折叠和 Markdown 导出。
