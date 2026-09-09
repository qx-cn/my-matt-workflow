# 教学内容阶段

产出一份准确、可独立阅读并可交给前端渲染的课程语义工件。读取[课程质量](references/course-quality.md)、[面向读者写作](references/shared/reader-first-writing.md)、[图示表达](references/shared/visual-communication.md)和[内容/前端交接](references/shared/document-rendering.md)。

## 1. 确定教学起点

读取 `MISSION.md`、`learning-records/` 和 `RESOURCES.md`。只有学习者类型、现实任务、当前能力证据或成功标准中的缺口会改变教学路径时，才一次询问一个关键问题。用掌握证据选择最近发展区；把必要先备知识转成简短提醒、回忆题或前置课程链接。

补齐本次学习收获需要的一手资料、当前版本文档或公认专家来源。事实、代码、例子和答案都应能由来源或可运行示例复核；暂时无法确认的内容以学生可用的适用限制呈现，并在制作记录保存研究状态。

完成条件：已经确定一个与现实任务直接相关、可验证的学习收获，并有足够证据支持课程结论和答案。

## 2. 设计课程

按[课程质量](references/course-quality.md)组织心智模型、机制关系、推演例子、边界辨析、练习反馈和迁移任务。结构服从理解依赖与练习时机。检索、间隔和合适的交错练习用于制造有益困难；练习取自可信场景并有正确答案或评分标准。

关键概念首次出现时使用行业通行术语作为主名称，并完成“中文名（英文全称，缩写）→ 白话含义 → 当前案例中的作用”。从具体案例搭桥到发生的现象、原因、标准术语以及相关字段、状态或代码含义。高风险概念同时给出容易混淆的边界。

逐节选择 `visual_intent`：

- `relationship`：系统边界、组成与依赖；
- `flow`：步骤、条件与异常；
- `sequence`：跨角色或跨系统协作；
- `state`：状态迁移；
- `table`：多项精确对照；
- `none`：纯结论、短步骤、少量字段或短列表已经适合用文字表达。

每项意图用 `visual_reason` 写清图要回答的问题；`none` 写清文字足够的理由。图示和正文共同承载关键规则与答案。

完成条件：学生只沿课程顺序阅读，就能解释机制、推演例子、辨认边界、完成练习并把方法用于新情境。

## 3. 写语义工件

写入 `lesson-drafts/<sequence>-<slug>.content.md`。文档类型固定为 `lesson`，输出固定在 `lessons/`。采用下面的交接结构：

````markdown
---
document_kind: lesson
content_revision: 1
status: content-ready
reader: ...
purpose: ...
output_path: lessons/0001-<slug>.html
template_ref: assets/TEMPLATE.html
source_refs: [...]
render_root: 学生课程
---

# 学生课程

这里放可连续阅读的课程。每个教学章节使用自然、唯一的二级标题。

## 一个自然的学生标题

解释、例子或练习等学生内容。

# 制作记录（不得渲染）

## 渲染映射

```json render-map
[
  {
    "section_id": "stable-dash-case-id",
    "heading": "一个自然的学生标题",
    "visual_intent": "none",
    "visual_reason": "这一节是短结论，文字已经足够"
  }
]
```

## 核验记录

保存学习者与用途依据、结论与来源账本、答案来源、掌握证据、研究状态和后续更新建议。
````

`render-map` 的项目顺序与学生课程二级标题完全一致；`heading` 精确复用标题，`section_id` 唯一且使用 dash-case。制作记录向前端提供渲染映射、来源和核验信息，学生真正需要的限制与判断方法已经写在学生课程中。

自然语言需要润色时，可用已安装的 `humanizer` embedded mode 处理 `# 学生课程`；保持事实、数字、链接、术语和答案不变。

完成条件：学生课程脱离制作记录仍可完整理解，制作记录足以复核每项结论、答案与渲染决策。

## 4. 验收

先连续阅读 `# 学生课程` 并应用课程质量中的学生价值门，再运行本 Skill 随附的：

```bash
python3 scripts/check_content.py <artifact>
```

只有两项检查均通过时才保留 `status: content-ready`。`content` 模式在此交付工件路径；普通调用和 `full` 继续进入前端阶段。
