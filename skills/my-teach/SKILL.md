---
name: my-teach
description: 围绕学习者的现实任务设计课程；支持内容语义工件与 HTML 前端分阶段执行，以便分别选择教学推理模型和前端模型。
disable-model-invocation: true
argument-hint: "你想学习什么？可选：content、frontend <artifact> 或 full"
---

# 教学

把当前目录视为持久教学工作区，让每次教学都服务于学习者的现实任务和可验证掌握。

先读取[面向读者写作](references/shared/reader-first-writing.md)、[图示表达](references/shared/visual-communication.md)与[内容/前端交接](references/shared/document-rendering.md)，再选择阶段：

- 未指定阶段且没有语义工件：执行 `content`，读取 [CONTENT.md](CONTENT.md)，写入 `lesson-drafts/<sequence>-<slug>.content.md`，报告绝对路径与 `/my-teach frontend <artifact>` 后停止。
- `frontend <artifact>`：只读取该语义工件、[FRONTEND.md](FRONTEND.md)、[课程模板](assets/TEMPLATE.html)、配套样式与脚本、校验脚本和教学工作区现有 `assets/`；不得凭记忆补写教学事实或改变练习答案。
- `full`：先落盘内容工件再渲染；只在 Agent 对话的交付说明中注明同一运行不构成模型隔离证据，不把该声明写入 HTML。

内容阶段与前端阶段可由不同模型独立执行。前端发现解释、来源、练习反馈或正确答案缺失时返回 `blocked-by-content`。

## 选择教学工作区

- 默认当前目录是单主题工作区。
- 有 `topics/` 时使用 `topics/<topic-slug>/`；已在主题目录则直接使用。
- 用户指定已有主题时使用它；明确提出新主题时，先确认学习目的再创建目录；只说“继续学习”且有多个主题时请用户选择。
- 以下相对路径均属于选定主题。旧版根级 `MISSION.md` 只在用户确认迁移方案后移动。

## 持久状态

- `MISSION.md`：学习原因、学习者水平、现实任务、成功标准、约束与范围外内容；格式见 [MISSION-FORMAT.md](MISSION-FORMAT.md)。改变任务前需用户确认。
- `RESOURCES.md`：可信来源与实践社区；格式见 [RESOURCES-FORMAT.md](RESOURCES-FORMAT.md)。
- `learning-records/`：已证明掌握、误解与下一步依据；格式见 [LEARNING-RECORD-FORMAT.md](LEARNING-RECORD-FORMAT.md)。覆盖过不等于掌握。
- `GLOSSARY.md`：已掌握术语的复习资料；格式见 [GLOSSARY-FORMAT.md](GLOSSARY-FORMAT.md)，不能替代课程首次解释。
- `lessons/` 与 `reference/`：渲染后的 HTML；`assets/` 保存共享样式、测验和确有复用价值的组件；`NOTES.md` 保存用户教学偏好。

语义工件是模型间检查用的内部材料，不是课页目录。`content_revision`、status、来源账本、模型隔离声明、作者研究缺口，以及“事实/结论清单”“必要关系”等交接标题不得原样印进 HTML。影响学习者判断的限度必须改写成正文限制或“现场还要核什么”；有复习价值的关系可改写成“这一课记住”“对象怎么连”等读者标题，但不得为对齐工件设固定栏目。专题首页写“怎么学”，不展示学习状态、来源基线、待制作或初稿进度。

完成 HTML 后先运行教学 HTML 校验器检查机械结构，再由 Agent 对照语义工件完成最终内容一致性校验，并实际检查桌面、窄屏和打印效果；如环境允许则打开文件。邀请学习者继续提问只留在 Agent 对话中，不得在 HTML 中写“发给 Agent”“贴给 Agent”或“给 Agent 的出口题”。
