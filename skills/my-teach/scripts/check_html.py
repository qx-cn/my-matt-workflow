#!/usr/bin/env python3
"""Check structural invariants of a rendered my-teach lesson."""

from __future__ import annotations

import argparse
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote


class LessonParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.anchor_targets: list[str] = []
        self.stylesheets: list[str] = []
        self.scripts: list[str] = []
        self.lesson_sections = 0
        self.hidden_sections = 0
        self.learning_outcomes = 0
        self.main_count = 0
        self.h1_count = 0
        self.quiz_count = 0
        self.quiz_feedback_count = 0
        self.print_answer_count = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        classes = set((values.get("class") or "").split())
        element_id = values.get("id")
        if element_id:
            self.ids.append(element_id)
        href = values.get("href") or ""
        if tag == "a" and href.startswith("#") and len(href) > 1:
            self.anchor_targets.append(unquote(href[1:]))
        if tag == "link" and "stylesheet" in (values.get("rel") or "").split():
            if href:
                self.stylesheets.append(href)
        if tag == "script" and values.get("src"):
            self.scripts.append(values["src"] or "")
        if tag == "main":
            self.main_count += 1
        if tag == "h1":
            self.h1_count += 1
        if "lesson-section" in classes:
            self.lesson_sections += 1
            if "hidden" in values or "display:none" in (values.get("style") or "").replace(" ", "").lower():
                self.hidden_sections += 1
        if "data-learning-outcome" in values:
            self.learning_outcomes += 1
        if "data-quiz" in values:
            self.quiz_count += 1
        if "feedback" in classes:
            self.quiz_feedback_count += 1
        if "print-answer" in classes:
            self.print_answer_count += 1

def local_asset(document: Path, reference: str) -> Path | None:
    if re.match(r"^[a-z][a-z0-9+.-]*:", reference, re.I) or reference.startswith("//"):
        return None
    return (document.parent / reference.split("?", 1)[0].split("#", 1)[0]).resolve()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("html", type=Path)
    args = parser.parse_args()
    text = args.html.read_text(encoding="utf-8")
    document = LessonParser()
    document.feed(text)

    errors: list[str] = []
    warnings: list[str] = []
    if re.search(r"{{[^{}]+}}", text):
        errors.append("存在未替换的 {{...}} 占位符")
    if document.main_count != 1:
        errors.append(f"课程必须有且只有一个 main，当前为 {document.main_count}")
    if document.h1_count != 1:
        errors.append(f"课程必须有且只有一个 h1，当前为 {document.h1_count}")
    if document.learning_outcomes != 1:
        errors.append(f"课程必须有且只有一个 data-learning-outcome，当前为 {document.learning_outcomes}")
    if not document.lesson_sections:
        errors.append("课程缺少 lesson-section")
    if document.hidden_sections:
        errors.append(f"发现 {document.hidden_sections} 个被隐藏的 lesson-section")
    duplicates = sorted({item for item in document.ids if document.ids.count(item) > 1})
    if duplicates:
        errors.append(f"发现重复 id：{', '.join(duplicates)}")
    missing_targets = sorted(set(document.anchor_targets) - set(document.ids))
    if missing_targets:
        errors.append(f"锚点指向不存在的 id：{', '.join(missing_targets)}")
    if document.quiz_count and document.quiz_feedback_count < document.quiz_count:
        errors.append("至少一道练习缺少 feedback 区域")
    if document.quiz_count and document.print_answer_count < document.quiz_count:
        errors.append("至少一道练习缺少写入 HTML 的 print-answer 答案解释")

    asset_text: dict[str, str] = {}
    for reference in document.stylesheets + document.scripts:
        path = local_asset(args.html.resolve(), reference)
        if path is None:
            warnings.append(f"未检查远程资产：{reference}")
        elif not path.is_file():
            errors.append(f"本地资产不存在：{reference}")
        else:
            asset_text[reference] = path.read_text(encoding="utf-8")
    css = "\n".join(asset_text.get(item, "") for item in document.stylesheets)
    if "@media print" not in css:
        errors.append("样式缺少 @media print")
    if re.search(r"\.lesson-section[^{}]*\{[^{}]*display\s*:\s*none", css, re.I | re.S):
        errors.append("样式会隐藏 lesson-section，破坏全文搜索")
    if not re.search(r"\.lesson-section[^{}]*\{[^{}]*scroll-margin-top", css, re.I | re.S):
        warnings.append("lesson-section 未设置 sticky 导航所需的 scroll-margin-top")

    for item in errors:
        print(f"ERROR {item}")
    for item in warnings:
        print(f"WARN  {item}")
    print(
        f"CHECK errors={len(errors)} warnings={len(warnings)} "
        f"sections={document.lesson_sections} quizzes={document.quiz_count}"
    )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
