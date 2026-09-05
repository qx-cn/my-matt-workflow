# 文档内容与前端交接

带前端渲染的文档型 Skill 使用同一入口的三个阶段：

- `content`：内容模型读取事实来源并产出语义工件；不得写 HTML、CSS 或 JavaScript。没有显式阶段且不存在可用语义工件时，默认执行此阶段并在交接点停止。
- `frontend <artifact>`：前端模型只消费语义工件、模板和渲染资产；负责布局、样式、交互、响应式与视觉验收，不重新解释源材料，不增删或改写事实、结论和约束。
- `full`：显式要求同一运行连续完成两个阶段时，仍先落盘并校验语义工件，再渲染。此模式不提供模型隔离证据。

语义工件是 Markdown，frontmatter 至少包含：

```yaml
---
document_kind: <stable-kind>
content_revision: 1
status: content-ready
reader: <primary reader>
purpose: <decision or action>
output_path: <rendered file path>
template_ref: <template or asset reference>
source_refs: [<authoritative inputs>]
---
```

正文必须提供：结论、证据与未知、按顺序排列的章节（每节包含稳定 `section_id`）、事实/结论清单、必要关系，以及可选的 `visual_intent`。`visual_intent` 只描述要回答的问题和数据关系，不指定像素、配色或具体前端实现。没有可视化收益时写 `none`。

内容阶段完成时报告语义工件绝对路径和下一条同入口调用，例如 `/<skill> frontend <artifact>`，然后停止。这是允许用户或宿主切换模型的真实交接点，不假设输出一行命令会自动触发下一阶段。

前端阶段先检查必填字段、来源引用、章节顺序和未知项。承重内容缺失时返回 `blocked-by-content`，指出缺口并停止；不得自行补写。渲染完成后逐项核对可见主张与语义工件，报告输出路径与视觉验收范围。
