# 教学前端阶段

把通过内容校验的课程语义工件渲染为可读、可练习、可打印的 HTML。读取[HTML 模板](assets/TEMPLATE.html)、配套样式与脚本、[图示表达](references/shared/visual-communication.md)和[内容/前端交接](references/shared/document-rendering.md)。

## 1. 准入

先运行本 Skill 随附的：

```bash
python3 scripts/check_content.py <artifact>
```

再只读 `# 学生课程`，确认它具备明确学习收获、顺序完整的解释、首次术语说明、可推演例子、必要边界、练习与原因反馈，以及改变表面情境的迁移任务。来源已经被综合成学生要理解的关系和判断方法。任一条件缺失时返回 `blocked-by-content`，并用 `render-map` 中对应的 `section_id` 定位；前端保持现有教学事实与答案。

完成条件：内容工件机械有效，并且学生课程达到[课程质量](references/course-quality.md)的准入标准。

## 2. 渲染

正文白名单只有 `# 学生课程`。制作记录仅提供 `output_path`、`render-map`、必要资源和页脚来源。每个二级教学章节生成带原 `section_id` 的 `lesson-section`；实现每个非 `none` 的 `visual_intent`，让图示紧邻它解释的文字结论，并让正文继续承载相同信息。

从模板开始，复用工作区的 `assets/course.css` 与 `assets/course.js`。缺少资产时从本 Skill 复制；已有资产先检查兼容性。课程专有内容放在 HTML，共享呈现与行为放在资产中。

页面保持一条连续文档流，并提供：

- 单一 `lesson-hero`，突出一个学习收获；
- 带锚点的简短章节导航；
- 适合关系的表格、流程或原生 SVG；
- 带 `data-quiz` 的练习、同区块原因反馈与 `print-answer`；
- 带 `data-transfer` 的迁移任务；
- 键盘可用的交互，以及打印时直接可见的答案解释与来源。

前端可以调整段落、列表、表格、短标题和导航标签来改善阅读，但保留行业主名称、理解依赖、事实、因果、限制、反例、来源归属、练习答案与评分标准。学生课程提供教学内容，前端负责把同一内容表达清楚。

完成条件：HTML 完整覆盖学生课程和 `render-map`，制作记录只贡献被白名单允许的数据。

## 3. 验收

运行本 Skill 随附的：

```bash
python3 scripts/check_html.py <html> --artifact <artifact>
```

然后完成三遍检查：

1. 单独阅读 HTML，应用学生价值门并实际完成练习；
2. 对照学生课程，逐节核对事实、关系、边界、术语、数字、答案、反馈和来源归属；
3. 对照 `render-map`，核对章节 ID、全部图示和制作信息隔离。

最后实际检查桌面宽度、390px 窄屏和打印预览，覆盖溢出、遮挡、对比度、锚点、键盘操作、全文搜索与打印答案。发现教学内容缺口时返回 `blocked-by-content`；呈现问题修正在 HTML 或共享资产中。

完成条件：机械校验、内容一致性和三个视图全部通过；未能实际验证的项目在最终回复中明确列出。
