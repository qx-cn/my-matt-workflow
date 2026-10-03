"""Behavioral backstops for learner-facing my-teach HTML."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/my-teach"


class TeachHtmlQualityGateTests(unittest.TestCase):
    def _check(
        self,
        body: str,
        *,
        include_quiz: bool = True,
        include_transfer: bool = True,
        section_id: str = "model",
    ) -> subprocess.CompletedProcess[str]:
        workspace = Path(self._temp.name)
        lessons = workspace / "lessons"
        assets = workspace / "assets"
        lessons.mkdir(exist_ok=True)
        assets.mkdir(exist_ok=True)
        shutil.copy(SKILL / "assets/course.css", assets / "course.css")
        shutil.copy(SKILL / "assets/course.js", assets / "course.js")
        artifact = workspace / "lesson.content.md"
        artifact.write_text(
            """---
document_kind: lesson
content_revision: 1
status: content-ready
reader: Web 开发者
purpose: 理解缓存行为
output_path: lessons/0001-quality.html
template_ref: assets/TEMPLATE.html
source_refs: [https://www.rfc-editor.org/rfc/rfc9111]
render_root: 学生课程
---

# 学生课程

## 工作原理

课程正文。

# 制作记录（不得渲染）

```json render-map
[
  {
    "section_id": "model",
    "heading": "工作原理",
    "visual_intent": "none",
    "visual_reason": "短解释适合文字"
  }
]
```
""",
            encoding="utf-8",
        )
        lesson = lessons / "0001-quality.html"
        quiz = (
            '<section data-quiz><button class="answer">作答</button>'
            '<div class="feedback">原因反馈</div>'
            '<div class="print-answer">答案与解释</div></section>'
            if include_quiz
            else ""
        )
        transfer = (
            '<section data-transfer><h2>迁移练习</h2><p>在新情境中应用方法。</p></section>'
            if include_transfer
            else ""
        )
        lesson.write_text(
            "<!doctype html><html><head>"
            '<link rel="stylesheet" href="../assets/course.css">'
            "</head><body><header><h1>缓存为什么会过期</h1>"
            '<div data-learning-outcome>能解释缓存过期并选择刷新策略</div>'
            f'</header><nav><a href="#{section_id}">工作原理</a></nav><main>'
            f'<section class="lesson-section" id="{section_id}">'
            f"{body}{quiz}{transfer}</section></main>"
            '<script src="../assets/course.js"></script></body></html>',
            encoding="utf-8",
        )
        return subprocess.run(
            [
                sys.executable,
                SKILL / "scripts/check_html.py",
                lesson,
                "--artifact",
                artifact,
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def setUp(self) -> None:
        self._temp = tempfile.TemporaryDirectory()

    def tearDown(self) -> None:
        self._temp.cleanup()

    def test_rejects_structural_production_markers(self) -> None:
        leaks = (
            "<p>content_revision: 2</p>",
            "<p>status: content-ready</p>",
            "<p>render_root: 学生课程</p>",
            "<p>section_id: model</p>",
            "<p>visual_intent: none</p>",
            "<h2>制作记录（不得渲染）</h2>",
            "<h2>来源账本</h2>",
            "<h2>作者研究缺口</h2>",
        )
        for leak in leaks:
            with self.subTest(leak=leak):
                checked = self._check(leak)
                self.assertNotEqual(0, checked.returncode)
                self.assertIn("制作信息泄漏", checked.stdout)

    def test_accepts_teaching_with_relevant_source_attribution(self) -> None:
        checked = self._check(
            "<h2>工作原理</h2>"
            "<p>缓存保存响应副本，过期时间决定何时必须重新验证；"
            "这避免每次读取都访问源站，又不会无限使用旧数据。</p>"
            "<p>HTTP Cache 规范定义了 freshness 的计算方式。"
            '<a href="https://www.rfc-editor.org/rfc/rfc9111">查看规范</a></p>'
        )
        self.assertEqual(0, checked.returncode, checked.stdout)

    def test_rejects_lesson_without_practice_or_transfer(self) -> None:
        no_practice = self._check(
            "<h2>工作原理</h2><p>缓存通过重新验证保持响应有效。</p>",
            include_quiz=False,
        )
        self.assertNotEqual(0, no_practice.returncode)
        self.assertIn("缺少 data-quiz 练习", no_practice.stdout)

        no_transfer = self._check(
            "<h2>工作原理</h2><p>缓存通过重新验证保持响应有效。</p>",
            include_transfer=False,
        )
        self.assertNotEqual(0, no_transfer.returncode)
        self.assertIn("缺少 data-transfer 迁移任务", no_transfer.stdout)

    def test_rejects_html_section_ids_that_drift_from_render_map(self) -> None:
        checked = self._check(
            "<h2>工作原理</h2><p>缓存通过重新验证保持响应有效。</p>",
            section_id="renamed-by-frontend",
        )
        self.assertNotEqual(0, checked.returncode)
        self.assertIn("必须与 render-map 按顺序完全一致", checked.stdout)

    def test_does_not_use_keyword_bans_for_semantic_quality(self) -> None:
        checked = self._check(
            "<h2>先判断</h2>"
            "<p>如果学习者已经掌握强缓存，可以直接比较重新验证的差异。"
            "这句话是本课要分析的反例，而不是制作状态。</p>"
            "<pre><code>status: content-ready\nvisual_intent: none</code></pre>"
        )
        self.assertEqual(0, checked.returncode, checked.stdout)


class TeachContentContractTests(unittest.TestCase):
    def _artifact(self, transform=None) -> subprocess.CompletedProcess[str]:
        text = """---
document_kind: lesson
content_revision: 1
status: content-ready
reader: Web 开发者
purpose: 判断缓存是否需要重新验证
output_path: lessons/0001-cache.html
template_ref: assets/TEMPLATE.html
source_refs: [https://www.rfc-editor.org/rfc/rfc9111]
render_root: 学生课程
---

# 学生课程

## 缓存怎样变旧

缓存会从新鲜变为陈旧，验证器让它能够向源站确认是否变化。

## 练习与迁移

先判断一个陈旧响应，再把方法用于另一组缓存配置。

# 制作记录（不得渲染）

## 渲染映射

```json render-map
[
  {
    "section_id": "cache-model",
    "heading": "缓存怎样变旧",
    "visual_intent": "flow",
    "visual_reason": "展示新鲜、陈旧与重新验证的条件流程"
  },
  {
    "section_id": "practice-transfer",
    "heading": "练习与迁移",
    "visual_intent": "none",
    "visual_reason": "两道短判断题用文字即可完整表达"
  }
]
```

## 核验记录

答案与来源已经核对。
"""
        if transform is not None:
            text = transform(text)
        with tempfile.TemporaryDirectory() as tmp:
            artifact = Path(tmp) / "lesson.content.md"
            artifact.write_text(text, encoding="utf-8")
            return subprocess.run(
                [sys.executable, SKILL / "scripts/check_content.py", artifact],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

    def test_accepts_lesson_with_exact_render_map(self) -> None:
        checked = self._artifact()
        self.assertEqual(0, checked.returncode, checked.stdout)

    def test_rejects_reference_as_a_second_product(self) -> None:
        checked = self._artifact(
            lambda text: text.replace("document_kind: lesson", "document_kind: reference")
            .replace("output_path: lessons/", "output_path: reference/")
        )
        self.assertNotEqual(0, checked.returncode)
        self.assertIn("document_kind 必须为 'lesson'", checked.stdout)
        self.assertIn("output_path 必须是 lessons/", checked.stdout)

    def test_rejects_ambiguous_root_boundary(self) -> None:
        checked = self._artifact(
            lambda text: text.replace(
                "# 制作记录（不得渲染）", "# 其他记录"
            )
        )
        self.assertNotEqual(0, checked.returncode)
        self.assertIn("依次且仅包含两个一级标题", checked.stdout)

    def test_rejects_render_map_that_cannot_identify_student_section(self) -> None:
        checked = self._artifact(
            lambda text: text.replace(
                '"heading": "练习与迁移"', '"heading": "另一标题"'
            )
        )
        self.assertNotEqual(0, checked.returncode)
        self.assertIn("按顺序完全一致", checked.stdout)

    def test_rejects_incomplete_frontmatter_contract(self) -> None:
        checked = self._artifact(
            lambda text: text.replace("purpose: 判断缓存是否需要重新验证\n", "")
        )
        self.assertNotEqual(0, checked.returncode)
        self.assertIn("purpose 必须是非空文本", checked.stdout)


if __name__ == "__main__":
    unittest.main()
