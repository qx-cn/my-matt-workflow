---
document_kind: lesson
content_revision: 1
status: content-ready
reader: 已理解 HTTP 请求响应的开发者
purpose: 判断缓存是否需要重新验证
output_path: lessons/0001-cache-revalidation.html
template_ref: assets/TEMPLATE.html
source_refs:
  - https://www.rfc-editor.org/rfc/rfc9111
render_root: 学生课程
---

# 学生课程

## 缓存重新验证

学习者已经能解释请求和响应。本课不重讲这些内容，只解决缓存何时重新验证。

RFC 9111 介绍 fresh、stale、validator、ETag、Last-Modified、Age 和 max-age。MDN 也介绍了浏览器缓存。两份材料都真实，用途不同。

## 练习

请判断一个 stale 响应能否直接使用。

# 制作记录（不得渲染）

## 渲染映射

```json render-map
[
  {
    "section_id": "cache-revalidation",
    "heading": "缓存重新验证",
    "visual_intent": "none",
    "visual_reason": "原稿认为文字足够"
  },
  {
    "section_id": "practice",
    "heading": "练习",
    "visual_intent": "none",
    "visual_reason": "原稿只有一道短判断题"
  }
]
```

## 核验记录

- 正确答案：材料不足，正文没有解释判断条件
- 作者研究缺口：尚未补充重新验证的因果关系与反馈
