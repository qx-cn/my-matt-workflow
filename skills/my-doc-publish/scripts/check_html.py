#!/usr/bin/env python3
"""Run deterministic structural checks for a generated local HTML doc."""

from __future__ import annotations

import argparse
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

NARROW_TABLE_CONTAINERS = {"span-4", "comparison-card", "decision-card"}
NARROW_PRE_CONTAINERS = {"span-4", "span-6", "comparison-card", "decision-card"}
VOID_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}
SKIP_PLACEHOLDER_TAGS = {"pre", "code", "script", "style"}
PLACEHOLDER_RE = re.compile(r"{{[^{}]+}}")


class DesignParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.stack: list[tuple[str, set[str]]] = []
        self.page_ids: set[str] = set()
        self.page_links: set[str] = set()
        self.narrow_tables = 0
        self.narrow_pres = 0
        self.active_comparison_cards: list[dict[str, int | bool]] = []
        self.comparison_cards: list[bool] = []
        self.placeholders: set[str] = set()

    def _in_skip_placeholder(self) -> bool:
        return any(tag in SKIP_PLACEHOLDER_TAGS for tag, _ in self.stack)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        values = dict(attrs)
        if tag not in SKIP_PLACEHOLDER_TAGS and not self._in_skip_placeholder():
            for _, val in attrs:
                if val:
                    for match in PLACEHOLDER_RE.finditer(val):
                        self.placeholders.add(match.group(0))
        classes = set((values.get("class") or "").split())
        if values.get("data-page") is not None and values.get("id"):
            self.page_ids.add(values["id"])
        if values.get("data-page-link"):
            self.page_links.add(values["data-page-link"])
        if tag == "table" and any(
            item[1] & NARROW_TABLE_CONTAINERS for item in self.stack
        ):
            self.narrow_tables += 1
        if tag == "pre" and any(
            item[1] & NARROW_PRE_CONTAINERS for item in self.stack
        ):
            self.narrow_pres += 1
        if tag in {"ul", "ol"}:
            for card in self.active_comparison_cards:
                card["has_list"] = True
        if tag in VOID_TAGS:
            if "comparison-card" in classes:
                self.comparison_cards.append(False)
            return
        if "comparison-card" in classes:
            self.active_comparison_cards.append(
                {"depth": len(self.stack), "has_list": False}
            )
        self.stack.append((tag, classes))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_lower = tag.lower()
        self.handle_starttag(tag_lower, attrs)
        if tag_lower not in VOID_TAGS:
            self.handle_endtag(tag_lower)

    def handle_data(self, data: str) -> None:
        if not self._in_skip_placeholder():
            for match in PLACEHOLDER_RE.finditer(data):
                self.placeholders.add(match.group(0))

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in VOID_TAGS:
            return
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                for card in list(self.active_comparison_cards):
                    if int(card["depth"]) >= index:
                        self.comparison_cards.append(bool(card["has_list"]))
                        self.active_comparison_cards.remove(card)
                del self.stack[index:]
                return

    def close(self) -> None:
        super().close()
        for card in list(self.active_comparison_cards):
            self.comparison_cards.append(bool(card["has_list"]))
        self.active_comparison_cards.clear()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("html", type=Path)
    args = parser.parse_args()
    text = args.html.read_text(encoding="utf-8")
    document = DesignParser()
    document.feed(text)
    document.close()

    errors: list[str] = []
    if document.placeholders:
        sample = ", ".join(sorted(document.placeholders)[:5])
        errors.append(f"存在未替换的占位符：{sample}")
    missing_pages = sorted(document.page_links - document.page_ids)
    missing_links = sorted(document.page_ids - document.page_links)
    if missing_pages:
        errors.append(f"导航指向不存在的章节：{', '.join(missing_pages)}")
    if missing_links:
        errors.append(f"章节缺少导航入口：{', '.join(missing_links)}")
    if document.narrow_tables:
        errors.append(f"发现 {document.narrow_tables} 个表格位于窄栏或对比卡片内")
    if document.narrow_pres:
        errors.append(f"发现 {document.narrow_pres} 个 pre 代码块位于窄栏或双栏对比卡片内")
    missing_comparison_lists = document.comparison_cards.count(False)
    if missing_comparison_lists:
        errors.append(
            f"发现 {missing_comparison_lists} 个 comparison-card 未使用列表"
        )

    for item in errors:
        print(f"ERROR {item}")
    print(f"CHECK errors={len(errors)} pages={len(document.page_ids)}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
