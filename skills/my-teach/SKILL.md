---
name: my-teach
description: 把可信材料转化为帮助学生理解、练习并迁移的完整课程；支持显式的内容与 HTML 阶段。
disable-model-invocation: true
argument-hint: "你想学习什么？可选：content <topic>、frontend <artifact> 或 full <topic>"
---

# 教学

唯一交付产品是学生课程：它让特定学生从已有认识走向可验证、可迁移的理解或能力。研究、学习记录和语义工件服务于制作，只有语义工件的 `# 学生课程` 拥有渲染权限。

## 运行方式

先选择教学工作区，再执行用户指定的阶段：

- 普通调用或 `full <topic>`：依次完成 [CONTENT.md](CONTENT.md) 和 [FRONTEND.md](FRONTEND.md)，交付 `lessons/` 中的课程 HTML。
- `content <topic>`：只完成内容阶段；交付通过校验的语义工件绝对路径和 `/my-teach frontend <artifact>`。
- `frontend <artifact>`：只完成前端阶段；教学事实、理解顺序、练习答案和反馈标准以该语义工件为准。

`content` 是唯一允许停在内部工件的显式模式。`full` 在同一运行内连续执行，不构成模型隔离证据；该状态只在对话中报告。

## 教学工作区

- 当前目录默认是单主题工作区。有 `topics/` 时使用 `topics/<topic-slug>/`；已经位于主题目录时直接使用。
- 用户指定已有主题时沿用它。创建新主题前确认学习目的；“继续学习”同时匹配多个主题时请用户选择。
- `MISSION.md` 保存学习原因、学生现状、现实任务、成功标准和范围，格式见 [MISSION-FORMAT.md](MISSION-FORMAT.md)。改变任务需用户确认。
- `RESOURCES.md` 保存可信来源与实践社区，格式见 [RESOURCES-FORMAT.md](RESOURCES-FORMAT.md)。
- `learning-records/` 保存掌握证据、误解和下一步依据，格式见 [LEARNING-RECORD-FORMAT.md](LEARNING-RECORD-FORMAT.md)。
- `GLOSSARY.md` 是已掌握术语的复习资料，格式见 [GLOSSARY-FORMAT.md](GLOSSARY-FORMAT.md)。
- `lesson-drafts/` 保存语义工件；`lessons/` 保存课程 HTML；`assets/` 保存共享呈现资产。

旧版根级 `MISSION.md` 只在用户确认迁移方案后移动。

## 完成

内容阶段以语义工件通过随附的 `scripts/check_content.py` 且学生课程通过[课程质量](references/course-quality.md)复核为完成。前端阶段以 HTML 通过 `scripts/check_html.py`、内容一致性复核，以及桌面、390px 窄屏和打印检查为完成。最终回复报告成品、检查范围和未验证项；制作状态留在对话中。
