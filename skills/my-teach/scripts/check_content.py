#!/usr/bin/env python3
"""Validate the deterministic handoff contract of a my-teach content artifact."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path, PurePosixPath


ROOT_STUDENT = "学生课程"
ROOT_PRODUCTION = "制作记录（不得渲染）"
REQUIRED_FRONTMATTER = {
    "document_kind": "lesson",
    "status": "content-ready",
    "render_root": ROOT_STUDENT,
    "template_ref": "assets/TEMPLATE.html",
}
VISUAL_INTENTS = {"none", "relationship", "flow", "sequence", "state", "table"}
SECTION_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def parse_frontmatter(text: str) -> tuple[dict[str, str], str, list[str]]:
    errors: list[str] = []
    if not text.startswith("---\n"):
        return {}, text, ["缺少起始 frontmatter"]
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}, text, ["frontmatter 未闭合"]

    fields: dict[str, str] = {}
    for raw in text[4:end].splitlines():
        if raw.startswith((" ", "\t", "-")) or ":" not in raw:
            continue
        key, value = raw.split(":", 1)
        fields[key.strip()] = value.strip().strip("\"'")
    return fields, text[end + 5 :], errors


def markdown_headings(text: str) -> list[tuple[int, str, int]]:
    headings: list[tuple[int, str, int]] = []
    fence: str | None = None
    for index, line in enumerate(text.splitlines()):
        fence_match = re.match(r"^\s*(`{3,}|~{3,})", line)
        if fence_match:
            marker = fence_match.group(1)
            if fence is None:
                fence = marker[0]
            elif marker[0] == fence:
                fence = None
            continue
        if fence is not None:
            continue
        match = re.match(r"^(#{1,6})[ \t]+(.+?)\s*#*\s*$", line)
        if match:
            headings.append((len(match.group(1)), match.group(2).strip(), index))
    return headings


def render_map_blocks(text: str) -> list[str]:
    blocks: list[str] = []
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        start = re.match(r"^\s*(`{3,}|~{3,})\s*json\s+render-map\s*$", lines[index])
        if not start:
            index += 1
            continue
        marker = start.group(1)
        content: list[str] = []
        index += 1
        while index < len(lines) and not re.match(
            rf"^\s*{re.escape(marker[0])}{{{len(marker)},}}\s*$", lines[index]
        ):
            content.append(lines[index])
            index += 1
        if index == len(lines):
            blocks.append("\n".join(content))
            break
        blocks.append("\n".join(content))
        index += 1
    return blocks


def validate_render_map(block: str, student_headings: list[str]) -> list[str]:
    errors: list[str] = []
    try:
        entries = json.loads(block)
    except json.JSONDecodeError as exc:
        return [f"render-map 不是有效 JSON：{exc.msg}"]
    if not isinstance(entries, list) or not entries:
        return ["render-map 必须是非空 JSON 数组"]

    mapped_headings: list[str] = []
    section_ids: list[str] = []
    for index, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            errors.append(f"render-map 第 {index} 项必须是对象")
            continue
        missing = [
            key for key in ("section_id", "heading", "visual_intent", "visual_reason")
            if not isinstance(entry.get(key), str) or not entry[key].strip()
        ]
        if missing:
            errors.append(f"render-map 第 {index} 项缺少非空字段：{', '.join(missing)}")
            continue
        section_id = entry["section_id"].strip()
        heading = entry["heading"].strip()
        visual_intent = entry["visual_intent"].strip()
        if not SECTION_ID.fullmatch(section_id):
            errors.append(f"section_id 不是 dash-case：{section_id}")
        if visual_intent not in VISUAL_INTENTS:
            errors.append(
                f"{section_id} 的 visual_intent 无效：{visual_intent}；"
                f"应为 {', '.join(sorted(VISUAL_INTENTS))}"
            )
        section_ids.append(section_id)
        mapped_headings.append(heading)

    duplicate_ids = sorted({item for item in section_ids if section_ids.count(item) > 1})
    duplicate_headings = sorted(
        {item for item in mapped_headings if mapped_headings.count(item) > 1}
    )
    if duplicate_ids:
        errors.append("render-map 存在重复 section_id：" + ", ".join(duplicate_ids))
    if duplicate_headings:
        errors.append("render-map 存在重复 heading：" + ", ".join(duplicate_headings))
    if mapped_headings != student_headings:
        errors.append(
            "render-map 的 heading 必须与学生课程二级标题按顺序完全一致；"
            f"学生课程={student_headings!r}，render-map={mapped_headings!r}"
        )
    return errors


def validate(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    fields, body, errors = parse_frontmatter(text)
    for key, expected in REQUIRED_FRONTMATTER.items():
        if fields.get(key) != expected:
            errors.append(f"frontmatter {key} 必须为 {expected!r}")
    for key in ("reader", "purpose"):
        if not fields.get(key):
            errors.append(f"frontmatter {key} 必须是非空文本")
    if "source_refs" not in fields:
        errors.append("frontmatter 必须包含 source_refs")
    try:
        revision = int(fields.get("content_revision", ""))
        if revision < 1:
            raise ValueError
    except ValueError:
        errors.append("frontmatter content_revision 必须是正整数")

    output_path = fields.get("output_path", "")
    output = PurePosixPath(output_path)
    if (
        output.is_absolute()
        or ".." in output.parts
        or len(output.parts) < 2
        or output.parts[0] != "lessons"
        or output.suffix.lower() != ".html"
    ):
        errors.append("output_path 必须是 lessons/ 下的相对 HTML 路径")

    headings = markdown_headings(body)
    roots = [(title, line) for level, title, line in headings if level == 1]
    expected_roots = [ROOT_STUDENT, ROOT_PRODUCTION]
    if [title for title, _ in roots] != expected_roots:
        errors.append(
            "正文必须依次且仅包含两个一级标题："
            f"{ROOT_STUDENT!r}、{ROOT_PRODUCTION!r}"
        )
        return errors

    lines = body.splitlines()
    student_start = roots[0][1] + 1
    production_start = roots[1][1]
    student = "\n".join(lines[student_start:production_start])
    production = "\n".join(lines[production_start + 1 :])
    student_headings = [
        title for level, title, _ in markdown_headings(student) if level == 2
    ]
    if not student_headings:
        errors.append("学生课程至少需要一个二级教学章节")
    if len(student_headings) != len(set(student_headings)):
        errors.append("学生课程二级标题必须唯一，以便稳定映射 section_id")

    blocks = render_map_blocks(production)
    if len(blocks) != 1:
        errors.append("制作记录必须有且只有一个 ```json render-map 代码块")
    else:
        errors.extend(validate_render_map(blocks[0], student_headings))
    return errors


def render_map_entries(path: Path) -> list[dict[str, str]]:
    """Return the render map from an artifact that has passed validate()."""
    text = path.read_text(encoding="utf-8")
    _, body, _ = parse_frontmatter(text)
    roots = [(title, line) for level, title, line in markdown_headings(body) if level == 1]
    production_start = roots[1][1]
    production = "\n".join(body.splitlines()[production_start + 1 :])
    return json.loads(render_map_blocks(production)[0])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    args = parser.parse_args()
    errors = validate(args.artifact)
    for item in errors:
        print(f"ERROR {item}")
    print(f"CHECK errors={len(errors)} artifact={args.artifact}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
