---
name: my-tech-design
description: 将讨论与代码库事实整理为可评审的技术方案；支持内容语义工件、HTML 前端与可选飞书阶段执行，以便分别选择内容模型和前端模型。
disable-model-invocation: true
---

遵循[审查循环](references/shared/review-loop.md)，包括独立性、覆盖、建议归属、修复与停止；需用户处理时按[找用户的条件](references/shared/user-intervention.md)。

# 技术方案

为不了解当前代码细节、但需要判断方案是否成立和风险是否可接受的工程师生成技术方案。它不是实现清单。

先读取[面向读者写作](references/shared/reader-first-writing.md)、[最终态写作](references/shared/final-state-writing.md)与[内容/前端交接](references/shared/document-rendering.md)，再选择阶段：

- 未指定阶段且没有语义工件：执行 `content`，读取 [CONTENT.md](CONTENT.md)，写入 `.agent/work/<topic>/designs/design-content-<topic>-<time-or-sequence>.md`，报告绝对路径与 `{{skill-call:my-tech-design}} frontend <artifact>` 后停止。
- `frontend <artifact>`：只读取该语义工件、[FRONTEND.md](FRONTEND.md)、[HTML 模板](assets/TEMPLATE.html)及校验脚本；不得重读源材料来改写内容。
- `feishu <语义工件> [wiki 地址]`：仅从该语义工件取得方案内容，不重读源材料补写；按下节执行。
- `full`：按顺序完成两阶段，仍保留语义工件。明确说明这是同一运行，不构成内容模型与前端模型已隔离的证据。

内容定稿前，作者逐条核实承重现状断言并提供代码依据。涉及持久状态/存量数据、并发与锁、对外契约（接口、消息、表结构、配置键、错误码）、发布与回滚兼容、改变其他模块既有行为任一类时，自动调用 {{skill-call:my-review-design}}，派新上下文审查者；派不出时增强自审并如实记 self。均不涉及时写“未触发设计审查”及理由。只一次全面审查加最多一次差异复审，不因用户要求“直到通过”或切换阶段重置；挑战/语义假设在下一个现有对齐点交用户，裁决写入已决事项，不重开。

内容阶段与前端阶段可由不同模型独立运行。前端阶段发现承重事实、结论、章节或来源缺失时，返回 `blocked-by-content` 和缺口，不自行补写。

## 可选飞书阶段

先检查工件是否 `content-ready`，是否包含完整读者正文、来源、稳定 `section_id` 与四个固定章节。缺内容或更新时无法判定哪些章节改变，返回 `blocked-by-content`，列出缺口后停止，不猜测补写。

调用宿主已有的飞书文档工具写入；没有工具时停下并明确说明缺少飞书文档工具。给了 wiki 地址就在该目录下创建文档，不自行改用其他目录。已有目标文档含评论时，只更新有改动的章节，保留未改章节与评论；可读取目标文档来比较章节和保护评论，但内容权威仍是语义工件。工具无法完成章节级更新或保护评论时停止说明限制，不用全文替换。

不把作者审查材料和工件元数据发布为读者正文；保持内容指南的契约与唯一原文位置。交付说明标注“未实测”，报告实际工具执行结果，不把写入成功当作方案或工具完整实测证明。

## 完成条件

- `content`：语义工件状态为 `content-ready`，读者、用途、来源、结论、章节、承重决策、风险、未知与可视化意图完整；其中不含 HTML、CSS 或 JavaScript。
- `frontend`：输出 `.agent/work/<topic>/designs/designs-<topic>-<time-or-sequence>.html`，没有覆盖历史文件；所有可见主张可追溯到语义工件。
- HTML 通过 `python3 scripts/check_html.py <html>`，并实际检查 1440px 与 1280px 桌面宽度、离线导航、折叠和 Markdown 导出。
- 内容阶段保存前、HTML 或飞书交付前，按最终态写作审一遍，检查悬空的章节、来源、Spec 和附件引用；工件内审查材料与读者正文区分明确，四个固定章节和唯一接口原文位置完整。
- 文档审查遵循共享审查循环，记录产物、轮次、阻断数、建议数、修改范围与体积，汇报已用和剩余轮数，并执行其停止条件；不因切换阶段重置同一产物的预算。
- `feishu`：满足本阶段的内容与工具条件，并在交付说明中标注“未实测”；无法执行时报告具体缺口，不声称完成。
