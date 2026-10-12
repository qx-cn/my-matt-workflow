#!/usr/bin/env python3
"""Run deterministic structural checks for a generated tech-design HTML."""

from __future__ import annotations

import argparse
import re
import sys
from html.parser import HTMLParser
from pathlib import Path


class DesignParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.stack: list[tuple[str, set[str]]] = []
        self.page_ids: set[str] = set()
        self.page_links: set[str] = set()
        self.narrow_tables = 0
        self.active_comparison_cards: list[dict[str, int | bool]] = []
        self.comparison_cards: list[bool] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        classes = set((values.get("class") or "").split())
        if values.get("data-page") is not None and values.get("id"):
            self.page_ids.add(values["id"])
        if values.get("data-page-link"):
            self.page_links.add(values["data-page-link"])
        if tag == "table" and any("span-4" in item[1] for item in self.stack):
            self.narrow_tables += 1
        if tag in {"ul", "ol"}:
            for card in self.active_comparison_cards:
                card["has_list"] = True
        if "comparison-card" in classes:
            self.active_comparison_cards.append(
                {"depth": len(self.stack), "has_list": False}
            )
        self.stack.append((tag, classes))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.stack.pop()

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                for card in list(self.active_comparison_cards):
                    if card["depth"] == index:
                        self.comparison_cards.append(bool(card["has_list"]))
                        self.active_comparison_cards.remove(card)
                del self.stack[index:]
                return


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("html", type=Path)
    args = parser.parse_args()
    text = args.html.read_text(encoding="utf-8")
    document = DesignParser()
    document.feed(text)

    errors: list[str] = []
    if re.search(r"{{[^{}]+}}", text):
        errors.append("存在未替换的 {{...}} 占位符")
    missing_pages = sorted(document.page_links - document.page_ids)
    missing_links = sorted(document.page_ids - document.page_links)
    if missing_pages:
        errors.append(f"导航指向不存在的章节：{', '.join(missing_pages)}")
    if missing_links:
        errors.append(f"章节缺少导航入口：{', '.join(missing_links)}")
    if document.narrow_tables:
        errors.append(f"发现 {document.narrow_tables} 个表格位于 span-4 窄栏")
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
