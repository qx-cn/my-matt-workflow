#!/usr/bin/env python3
"""Deterministic layout, readability, and whiteboard collision checks for Feishu DocxXML & JSON DSL."""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

FORBIDDEN_IN_CALLOUT = {"pre", "table", "grid", "whiteboard", "hr", "details", "img"}
FORBIDDEN_IN_GRID = {"pre", "table"}
HEADING_TAGS = {f"h{i}" for i in range(1, 10)}
BLOCK_CONTAINERS = {"ul", "ol", "pre", "table"}
MANUAL_NUM_RE = re.compile(
    r"^\s*(?:第?[一二三四五六七八九十百]+[章节条部分]|[一二三四五六七八九十]+[、.．]|[（(][一二三四五六七八九十0-9]+[）)]|\d+(?:\.\d+)+[\s、.．)]|\d+[、.．)])"
)
PLACEHOLDER_RE = re.compile(r"\[待补充|TODO[:：]|{{\s*[^{}]+\s*}}")
HARD_TODO_RE = re.compile(r"\[待补充|TODO[:：]")
ALLOWED_COMPOUND_TERM_RE = re.compile(
    r"缓存击穿|跨站请求伪造|请求伪造|伪造请求|伪造签名|签名伪造|伪造令牌|令牌伪造"
)
SUSPECT_BUZZWORD_RE = re.compile(r"击穿|收口|抓手|盲区|赋能|伪造|锁死|封死")
STUTTER_WORD_RE = re.compile(r"(报表|任务|状态|配置|字段|模板|校验|接口)\s*\1")
ARROW_TOKEN_RE = re.compile(r"->|→")
DASH_RE = re.compile(r"—+")
XML_DECL_RE = re.compile(r"^\s*<\?xml[^?]*\?>\s*", re.IGNORECASE)

MAX_PARAGRAPH_UNITS = 225
EXTREME_PARAGRAPH_UNITS = 260
MAX_LI_DIRECT_UNITS = 140
MAX_TD_DIRECT_UNITS = 85
MAX_FOUR_COL_TD_UNITS = 50
MAX_FIVE_PLUS_TD_UNITS = 42
EXTREME_TD_UNITS = 120
MAX_TD_LI_UNITS = 70
MAX_TD_CODE_CHARS = 68
MAX_TD_INLINE_CODES = 5
MAX_INLINE_CODES_IN_BLOCK = 6
MAX_TABLE_COLS_FOR_DENSE = 5
MAX_SEMICOLONS_IN_BLOCK = 3
MAX_BOARD_RECTS = 16
MAX_RECT_LINES = 3
MAX_RECT_LINE_CHARS = 24
MAX_EDGE_LABEL_CHARS = 10
MAX_LR_CHAIN_RANKS = 6
MAX_TB_SINGLE_COL_RANKS = 4

BOARD_SHAPE_TYPES = {"rect", "ellipse", "cylinder", "diamond", "triangle", "trapezoid"}
ILLEGAL_STYLE_KEYS = {
    "fillColor",
    "borderColor",
    "strokeColor",
    "textColor",
    "borderWidth",
    "strokeWidth",
    "borderDash",
    "fill",
    "stroke",
    "color",
}
TOP_LEVEL_CONNECTOR_KEYS = {
    "from",
    "to",
    "fromAnchor",
    "toAnchor",
    "lineShape",
    "lineColor",
    "lineWidth",
    "lineStyle",
    "startArrow",
    "endArrow",
    "waypoints",
    "label",
    "labelPosition",
    "text",
}


def longest_dag_nodes(edges: list[list[str]], cap: int = MAX_LR_CHAIN_RANKS + 2) -> int:
    """Return longest simple-path node count capped at `cap` (fast & exact up to cap on cyclic graphs)."""
    adj: dict[str, list[str]] = {}
    nodes: list[str] = []
    seen_nodes: set[str] = set()
    for edge in edges:
        if isinstance(edge, list) and len(edge) >= 2:
            u, v = str(edge[0]), str(edge[1])
            if u not in seen_nodes:
                seen_nodes.add(u)
                nodes.append(u)
            if v not in seen_nodes:
                seen_nodes.add(v)
                nodes.append(v)
            if u != v and v not in adj.setdefault(u, []):
                adj[u].append(v)

    def dfs(u: str, visiting: set[str], depth: int) -> int:
        if depth >= cap:
            return depth
        best = depth
        visiting.add(u)
        for nxt in adj.get(u, []):
            if nxt not in visiting:
                cand = dfs(nxt, visiting, depth + 1)
                if cand > best:
                    best = cand
                if best >= cap:
                    break
        visiting.remove(u)
        return best

    best_overall = 0
    for n in nodes:
        cand = dfs(n, set(), 1)
        if cand > best_overall:
            best_overall = cand
        if best_overall >= cap:
            break
    return best_overall


def is_empty_paragraph(elem: ET.Element) -> bool:
    return elem.tag == "p" and len(elem) == 0 and not (elem.text or "").strip()


def standalone_bold_heading_text(elem: ET.Element) -> str | None:
    """Return heading text when <p> contains only bold/colored inline title (e.g. <p><b>核心方案</b></p>)."""
    if elem.tag != "p" or (elem.text or "").strip() or len(elem) == 0:
        return None

    has_bold = False

    def valid_title_children(parent: ET.Element) -> bool:
        nonlocal has_bold
        for ch in parent:
            if ch.tag in {"b", "strong"}:
                has_bold = True
            elif ch.tag == "code":
                pass
            elif ch.tag == "span":
                if (ch.text or "").strip() not in {"", ":", "："} or not valid_title_children(ch):
                    return False
            else:
                return False
            if (ch.tail or "").strip() not in {"", "）", ")", ":", "："}:
                return False
        return True

    if not valid_title_children(elem) or not has_bold:
        return None
    txt = "".join(elem.itertext()).strip()
    return txt or None


def callout_prose(elem: ET.Element) -> str:
    """Keep inline code as an object so its punctuation cannot act as a title separator."""
    if elem.tag == "code":
        return "<code>"
    return (elem.text or "") + "".join(callout_prose(ch) + (ch.tail or "") for ch in elem)


def has_inline_callout_title_glued(elem: ET.Element) -> str | None:
    """Return glued title text if <p> inside <callout> starts with <b>小标题</b>：正文 on the same line."""
    if elem.tag != "p" or (elem.text or "").strip() or len(elem) == 0:
        return None
    lead_bold = elem[0]
    while lead_bold.tag == "span" and not (lead_bold.text or "").strip() and len(lead_bold):
        lead_bold = lead_bold[0]
    if lead_bold.tag not in {"b", "strong"}:
        return None
    title = "".join(lead_bold.itertext()).strip()
    if not title or len(title) > 24:
        return None
    prefix = callout_prose(lead_bold).strip()
    rest = callout_prose(elem).strip()[len(prefix):].strip()
    if (prefix.endswith(("：", ":")) and rest) or (rest.startswith(("：", ":")) and rest[1:].strip()):
        return title.rstrip("：:")
    return None


def direct_text_units(elem: ET.Element) -> float:
    parts = [elem.text or ""]
    for child in elem:
        if child.tag not in BLOCK_CONTAINERS:
            parts.append("".join(child.itertext()))
        parts.append(child.tail or "")
    text = re.sub(r"\s+", " ", "".join(parts)).strip()
    return visual_char_units(text)


def direct_non_code_text(elem: ET.Element, *, skip_p: bool = False) -> str:
    """Collect text inside elem while skipping nested code/pre and nested block containers."""
    parts: list[str] = []
    skip_tags = BLOCK_CONTAINERS | {"code"} | ({"p"} if skip_p else set())

    def collect(cur: ET.Element, is_root: bool) -> None:
        if not is_root and cur.tag in skip_tags:
            return
        if cur.text:
            parts.append(cur.text)
        for ch in cur:
            collect(ch, False)
            if ch.tail:
                parts.append(ch.tail)

    collect(elem, True)
    return "".join(parts)


def direct_inline_code_count(elem: ET.Element) -> int:
    """Count all inline <code> descendants excluding nested block lists/tables/pre."""
    count = 0

    def visit(cur: ET.Element, is_root: bool) -> None:
        nonlocal count
        if not is_root and cur.tag in BLOCK_CONTAINERS:
            return
        if not is_root and cur.tag == "code":
            count += 1
            return
        for ch in cur:
            visit(ch, False)

    visit(elem, True)
    return count


def direct_plain_text(elem: ET.Element) -> str:
    parts = [elem.text or ""]
    for ch in elem:
        if ch.tag not in BLOCK_CONTAINERS:
            parts.append("".join(ch.itertext()))
        parts.append(ch.tail or "")
    return "".join(parts)


def count_subtree_accent_spans(elem: ET.Element) -> int:
    cnt = 0

    def visit(node: ET.Element, in_callout: bool) -> None:
        nonlocal cnt
        now_in_callout = in_callout or (node.tag == "callout")
        if node.tag == "span" and not now_in_callout:
            tc = node.attrib.get("text-color", "")
            if "background-color" in node.attrib or (tc and tc != "gray"):
                cnt += 1
        for ch in node:
            visit(ch, now_in_callout)

    visit(elem, False)
    return cnt


def snippet(elem: ET.Element, limit: int = 36) -> str:
    raw = re.sub(r"\s+", " ", "".join(elem.itertext())).strip()
    return raw[:limit] + ("..." if len(raw) > limit else "")


def visual_char_units(text: str) -> float:
    units = 0.0
    for ch in text:
        units += 1.0 if ord(ch) > 127 else 0.58
    return units


def parse_colspan(cell: ET.Element) -> int:
    raw = (cell.attrib.get("colspan") or "").strip()
    if raw.isdigit() and int(raw) >= 1:
        return int(raw)
    return 1


def has_light_gray_header(first_tr: ET.Element) -> bool:
    if first_tr.attrib.get("background-color") == "light-gray":
        return True
    cells = [c for c in first_tr if c.tag in {"th", "td"}]
    if not cells:
        return False
    if all(c.attrib.get("background-color") == "light-gray" for c in cells):
        return True
    # Accept Key-Value metadata tables where label cells are <th background-color="light-gray"> paired with <td> values.
    th_cells = [c for c in cells if c.tag == "th"]
    td_cells = [c for c in cells if c.tag == "td"]
    return bool(th_cells) and bool(td_cells) and all(
        c.attrib.get("background-color") == "light-gray" for c in th_cells
    )


def check_xml(
    xml_path: Path, *, fragment: bool = False
) -> tuple[list[str], list[str], dict[str, int]]:
    errors: list[str] = []
    warnings: list[str] = []
    raw = xml_path.read_text(encoding="utf-8")

    if "<details" in raw:
        errors.append("飞书 XML 不支持 HTML <details> 标签")

    xml_body = XML_DECL_RE.sub("", raw)
    try:
        root = ET.fromstring(f"<root>{xml_body}</root>")
    except ET.ParseError as exc:
        return [f"XML 语法解析失败（请检查标签闭合或 &lt;/&gt;/&amp; 转义）：{exc}"], [], {}

    top_tags = [child.tag for child in root]
    title_text = ""
    if not fragment:
        if not top_tags or top_tags[0] != "title":
            errors.append("完整飞书 XML 顶层第一个元素应为 <title>（局部块更新校验可加 --fragment）")
        elif top_tags.count("title") > 1:
            errors.append("飞书 XML 顶层只能包含唯一一个 <title>")
        else:
            title_text = "".join(root[0].itertext()).strip()

    # Check visual separation and heading hierarchy:
    # 1) <hr/> immediately before 1st <h1> (when preceded by overview blocks) and before 2nd+ <h1>
    # 2) <p></p> blank line before 2nd+ <h2> within the same <h1> chapter
    # 3) <p></p> blank line between top-level ul/ol and table/pre, or between consecutive tables
    # 4) No heading level skips (full doc must start at <h1>; fragment may start at <h2>)
    h1_seen = 0
    h2_in_chapter = 0
    saw_overview_before_h1 = False
    saw_hr_before_next_h1 = False
    prev_heading_level: int | None = None
    children = list(root)
    for idx, child in enumerate(children):
        prev = children[idx - 1] if idx > 0 else None
        if child.tag in HEADING_TAGS:
            level = int(child.tag[1:])
            if not fragment and prev_heading_level is None and level != 1:
                errors.append(
                    f"完整文档正文首个标题应为 <h1>，当前从 <{child.tag}> 起步：「{snippet(child)}」"
                )
            elif prev_heading_level is not None and level > prev_heading_level + 1:
                errors.append(
                    f"标题层级跳级（从 <h{prev_heading_level}> 直接跳到 <{child.tag}>）：「{snippet(child)}」"
                )
            prev_heading_level = level

        if child.tag == "hr":
            saw_hr_before_next_h1 = True
        elif is_empty_paragraph(child):
            pass
        elif child.tag == "h1":
            h1_seen += 1
            h2_in_chapter = 0
            if not fragment and h1_seen == 1 and saw_overview_before_h1 and not saw_hr_before_next_h1:
                errors.append(
                    f"文首总览块与第 1 个 <h1/>「{snippet(child)}」之间缺少 <hr/> 分割线，顶部摘要会紧贴标题"
                )
            elif h1_seen >= 2 and not saw_hr_before_next_h1:
                errors.append(
                    f"一级章节 <h1/>「{snippet(child)}」上方缺少紧邻的 <hr/> 分割线，章节容易黏连"
                )
            saw_hr_before_next_h1 = False
        elif child.tag == "h2":
            h2_in_chapter += 1
            saw_hr_before_next_h1 = False
            if h2_in_chapter >= 2:
                if prev is None or (not is_empty_paragraph(prev) and prev.tag != "hr"):
                    errors.append(
                        f"二级小节 <h2/>「{snippet(child)}」上方缺少 <p></p> 空行留白，会与上一小节末尾内容紧贴"
                    )
        else:
            if child.tag in {"table", "pre"} and prev is not None and prev.tag in {"ul", "ol"}:
                errors.append(
                    f"列表与下方 <{child.tag}> 之间缺少 <p></p> 空行留白（位于「{snippet(child)}」）"
                )
            elif child.tag == "table" and prev is not None and prev.tag == "table":
                errors.append(
                    f"连续两张 <table> 之间缺少 <p></p> 空行留白（位于「{snippet(child)}」）"
                )
            if child.tag in {"callout", "grid", "blockquote"} and h1_seen == 0:
                saw_overview_before_h1 = True
            saw_hr_before_next_h1 = False

    body_accent_spans = 0
    reported_placeholders: set[str] = set()
    heading_texts: list[str] = []

    def record_placeholder(text: str, *, in_code: bool) -> None:
        regex = HARD_TODO_RE if in_code else PLACEHOLDER_RE
        for m in regex.finditer(text):
            tok = m.group(0)
            if tok not in reported_placeholders:
                reported_placeholders.add(tok)
                errors.append(f"XML 存在未清理的占位符：{tok!r}")

    def walk(
        node: ET.Element, ancestors: list[str], table_cols: int = 0, is_header_row: bool = False
    ) -> None:
        nonlocal body_accent_spans
        tag = node.tag
        in_code = tag in {"pre", "code"} or "pre" in ancestors or "code" in ancestors
        if node.text:
            record_placeholder(node.text, in_code=in_code)
        if node.tail:
            parent_in_code = "pre" in ancestors or "code" in ancestors
            record_placeholder(node.tail, in_code=parent_in_code)

        if tag == "span" and "callout" not in ancestors:
            tc = node.attrib.get("text-color", "")
            if "background-color" in node.attrib or (tc and tc != "gray"):
                body_accent_spans += 1

        if tag in {"em", "i"} and "pre" not in ancestors and "code" not in ancestors:
            errors.append(
                f"中文正文请勿使用斜体 <{tag}>（位于「{snippet(node)}」），请改用 <b> 加粗或常规正文"
            )
        if tag == "u" and "pre" not in ancestors and "code" not in ancestors and "a" not in ancestors:
            errors.append(
                f"非链接正文请勿使用下划线 <u>（位于「{snippet(node)}」），请改用 <b> 加粗或常规正文"
            )

        if tag in ({"title", "p", "li", "checkbox", "td", "th"} | HEADING_TAGS) and "pre" not in ancestors:
            non_code_text = direct_non_code_text(node, skip_p=(tag in {"li", "td", "th", "checkbox"}))
            scrubbed = ALLOWED_COMPOUND_TERM_RE.sub("", non_code_text)
            bw = SUSPECT_BUZZWORD_RE.search(scrubbed)
            if bw:
                warnings.append(
                    f"正文出现疑似夸张词「{bw.group(0)}」（位于「{snippet(node)}」），请核对并改为平实准确的工程表述"
                )
            st = STUTTER_WORD_RE.search(non_code_text)
            if st:
                warnings.append(
                    f"正文出现疑似重复词「{st.group(0)}」（位于「{snippet(node)}」），请核对是否为机械替换残留（若为『配置配置中心』等正常动宾短语可忽略）"
                )
            if DASH_RE.search(non_code_text):
                errors.append(
                    f"正文含破折号（位于「{snippet(node)}」），请按全局规范改用逗号、冒号、句号或括号（表格空项用 - 或 无）"
                )

        if tag in HEADING_TAGS:
            text = "".join(node.itertext()).strip()
            heading_texts.append(text)
            if node.attrib.get("seq") == "auto" and MANUAL_NUM_RE.match(text):
                errors.append(
                    f"<{tag} seq=\"auto\"> 标题内手写了重复前置序号：「{snippet(node)}」"
                )
            if "、" in text:
                warnings.append(
                    f"标题「{snippet(node)}」含顿号并列多个子点，建议提炼为本节解决的单一核心主题，不要把节内要点堆进标题"
                )

        if tag == "checkbox":
            bad_children = [
                c.tag for c in node if c.tag in {"p", "ul", "ol", "pre", "table", "blockquote", "callout"}
            ]
            if bad_children:
                errors.append(
                    f"<checkbox> 内禁止嵌套 <{bad_children[0]}> 块级标签（飞书会把复选框与文字拆成上下两行错位），请直接写行内文本如 <checkbox done=\"false\">核查内容</checkbox>：「{snippet(node)}」"
                )
            cb_units = round(direct_text_units(node))
            cb_codes = direct_inline_code_count(node)
            cb_non_code = direct_non_code_text(node)
            if cb_units > MAX_LI_DIRECT_UNITS:
                warnings.append(
                    f"<checkbox> 单条核查项偏长（视觉字宽 {cb_units} > {MAX_LI_DIRECT_UNITS}），建议精炼核查条件并将长 SQL 或命令放入独立 <pre> 代码块：「{snippet(node)}」"
                )
            if cb_codes > MAX_INLINE_CODES_IN_BLOCK:
                warnings.append(
                    f"<checkbox> 内密集使用了 {cb_codes} 个 <code> 灰框（建议不超过 {MAX_INLINE_CODES_IN_BLOCK} 个），普通英文动作词请直接用正文：「{snippet(node)}」"
                )
            if cb_non_code.count("；") >= MAX_SEMICOLONS_IN_BLOCK:
                warnings.append(
                    f"<checkbox> 内连用了 {cb_non_code.count('；')} 个分号罗列多项内容，建议拆分为多条独立 <checkbox>：「{snippet(node)}」"
                )

        if tag == "ol" and "seq" in node.attrib:
            seq_val = (node.attrib.get("seq") or "").strip()
            if seq_val == "auto":
                errors.append(
                    "<ol> 默认自动编号，不支持冗余的 seq=\"auto\"（飞书服务端会报 degrade_code=5002），请去掉 seq 或改用正整数起始值"
                )
            elif not (seq_val.isdigit() and int(seq_val) >= 1):
                errors.append(
                    f"<ol seq={seq_val!r}> 的 seq 必须为正整数（如 seq=\"3\"），或直接省略 seq"
                )

        if tag == "pre":
            child_tags = [c.tag for c in node]
            if child_tags != ["code"]:
                errors.append("<pre> 内必须且只能直接包裹单个 <code> 子标签")

        if "callout" in ancestors and tag in FORBIDDEN_IN_CALLOUT:
            errors.append(f"<callout> 内禁止嵌套 <{tag}>")

        if tag == "callout":
            emoji = node.attrib.get("emoji", "")
            if "️" in emoji:
                errors.append(
                    f"<callout emoji={emoji!r}> 含双码点变体选择符（\\ufe0f），飞书易降级或渲染异常，请改用单码点图标（如 📌、✅、🚫、💡、🚨、🔧）"
                )
            c_children = list(node)
            bold_heading_seen = 0
            saw_body_since_heading = False
            saw_blank_since_content = False
            consecutive_body_ps = 0
            for c_el in c_children:
                glued = has_inline_callout_title_glued(c_el)
                if glued:
                    errors.append(
                        f"<callout> 卡片内小标题「{glued}」与正文紧贴在同一行，请将小标题单独成行（<p><b>{glued}</b></p>），正文另起下一行写"
                    )
                heading_txt = standalone_bold_heading_text(c_el)
                if is_empty_paragraph(c_el):
                    saw_blank_since_content = True
                    consecutive_body_ps = 0
                elif heading_txt is not None:
                    if heading_txt.endswith(("：", ":")):
                        clean_h = heading_txt.rstrip("：:")
                        errors.append(
                            f"<callout> 卡片内小标题「{heading_txt}」末尾不要带冒号，请写为 <p><b>{clean_h}</b></p>"
                        )
                    bold_heading_seen += 1
                    # Consecutive bold lines at card top (e.g. KPI card title + metric) have no body between them;
                    # only require <p></p> when starting a new titled section after body content.
                    if bold_heading_seen >= 2 and saw_body_since_heading and not saw_blank_since_content:
                        errors.append(
                            f"<callout> 卡片内小标题「{snippet(c_el)}」上方缺少 <p></p> 空行分隔，多组内容会上下紧贴"
                        )
                    saw_body_since_heading = False
                    saw_blank_since_content = False
                    consecutive_body_ps = 0
                elif c_el.tag == "p":
                    consecutive_body_ps += 1
                    saw_body_since_heading = True
                    saw_blank_since_content = False
                    if consecutive_body_ps >= 2:
                        warnings.append(
                            f"<callout> 卡片内连续多段正文未加空行分隔（位于「{snippet(c_el)}」），建议在段间插入 <p></p> 空行"
                        )
                else:
                    saw_body_since_heading = True
                    saw_blank_since_content = False
                    consecutive_body_ps = 0

        if "grid" in ancestors and tag in FORBIDDEN_IN_GRID:
            errors.append(f"<grid> 多栏内禁止塞入 <{tag}>，请改为全宽纵向排列")

        if tag == "p" and "td" not in ancestors and "th" not in ancestors and "li" not in ancestors:
            units = round(direct_text_units(node))
            non_code_p = direct_non_code_text(node)
            code_cnt = direct_inline_code_count(node)
            if units > EXTREME_PARAGRAPH_UNITS:
                errors.append(
                    f"段落形成严重文字墙（视觉字宽 {units} > {EXTREME_PARAGRAPH_UNITS} 上限），请按逻辑层次拆成两段或列表/小表格：「{snippet(node)}」"
                )
            elif units > MAX_PARAGRAPH_UNITS:
                warnings.append(
                    f"段落偏长（视觉字宽 {units} > {MAX_PARAGRAPH_UNITS}），若含多个前提或步骤建议按层次拆分：「{snippet(node)}」"
                )
            if code_cnt > MAX_INLINE_CODES_IN_BLOCK:
                warnings.append(
                    f"单段内密集使用了 {code_cnt} 个 <code> 灰框（建议不超过 {MAX_INLINE_CODES_IN_BLOCK} 个），普通英文动作词与大类名称请直接用正文：「{snippet(node)}」"
                )
            if non_code_p.count("；") >= MAX_SEMICOLONS_IN_BLOCK:
                warnings.append(
                    f"单段内连用了 {non_code_p.count('；')} 个分号罗列多项内容，建议拆为独立小表格或分点列表：「{snippet(node)}」"
                )

        cur_table_cols = table_cols
        if tag == "table":
            all_trs = node.findall(".//tr")
            first_tr = all_trs[0] if all_trs else None
            if first_tr is not None and not has_light_gray_header(first_tr):
                hdr_snip = snippet(first_tr)
                errors.append(
                    f"表格「{hdr_snip}」首行缺少浅灰底色表头，请将首行写为 <tr background-color=\"light-gray\"> 或在 <thead> 内的每个 <th> 上设置 background-color=\"light-gray\""
                )
            if first_tr is not None:
                cur_table_cols = sum(parse_colspan(c) for c in first_tr if c.tag in {"th", "td"})
                td_units_list = [
                    visual_char_units(re.sub(r"\s+", " ", "".join(td.itertext())).strip())
                    for td in node.findall(".//td")
                ]
                avg_td = (sum(td_units_list) / len(td_units_list)) if td_units_list else 0.0
                if cur_table_cols > MAX_TABLE_COLS_FOR_DENSE and avg_td > 18:
                    warnings.append(
                        f"表格列数较多（{cur_table_cols} 列）且单元格平均字宽 {avg_td:.0f}，在 820px 页面内易挤成窄块，建议合并列至 3 至 4 列"
                    )
                if len(all_trs) >= 4 and cur_table_cols >= 2:
                    for col_idx in range(cur_table_cols):
                        list_rows = 0
                        para_rows = 0
                        for data_tr in all_trs[1:]:
                            cells = [c for c in data_tr if c.tag in {"th", "td"}]
                            if col_idx < len(cells):
                                c_el = cells[col_idx]
                                if any(sub.tag in {"ul", "ol"} for sub in c_el):
                                    list_rows += 1
                                elif "".join(c_el.itertext()).strip():
                                    para_rows += 1
                        if list_rows >= 1 and para_rows >= 1:
                            warnings.append(
                                f"表格「{snippet(first_tr)}」第 {col_idx + 1} 列混用了纯段落 <p> 与分点列表 <ul>，建议同列统一格式保持视觉整齐"
                            )

        if tag == "td" and not is_header_row:
            has_list = any(c.tag in {"ul", "ol"} for c in node)
            td_codes = direct_inline_code_count(node)
            td_non_code = direct_non_code_text(node)
            if td_codes >= 3 and "/" in (td_non_code or "") and re.fullmatch(r"[\s/]+", td_non_code or ""):
                warnings.append(
                    f"表格单元格内将 {td_codes} 个枚举或标识用斜杠挤在同一格，若属状态定义或字段说明表请拆为一行一个枚举值：「{snippet(node)}」"
                )
            if td_codes > MAX_TD_INLINE_CODES:
                warnings.append(
                    f"表格单个单元格内密集使用了 {td_codes} 个 <code> 灰框（建议不超过 {MAX_TD_INLINE_CODES} 个），请检查是否应拆为多行：「{snippet(node)}」"
                )
            for code_el in node.iter("code"):
                ctext = (code_el.text or "").strip()
                if len(ctext) > MAX_TD_CODE_CHARS:
                    errors.append(
                        f"表格单元格内塞入了 {len(ctext)} 字符的超长命令/代码（会在窄列内折成多行），请把完整命令提取到表外全宽 <pre> 代码块，格内只写短子命令名：「{ctext[:36]}...」"
                    )
            span = parse_colspan(node)
            effective_cols = max(1, (cur_table_cols + span - 1) // span) if cur_table_cols > 0 else 1
            if effective_cols >= 5:
                cell_limit = MAX_FIVE_PLUS_TD_UNITS
            elif effective_cols == 4:
                cell_limit = MAX_FOUR_COL_TD_UNITS
            else:
                cell_limit = MAX_TD_DIRECT_UNITS
            if span > 1 and cur_table_cols > 0:
                extreme_td_limit = min(EXTREME_PARAGRAPH_UNITS, round(EXTREME_TD_UNITS * min(span, cur_table_cols) * 0.75))
                extreme_td_limit = max(EXTREME_TD_UNITS, extreme_td_limit)
                cell_limit = max(cell_limit, min(MAX_PARAGRAPH_UNITS, round(cell_limit * min(span, cur_table_cols) * 0.75)))
            else:
                extreme_td_limit = EXTREME_TD_UNITS
            if not has_list:
                td_text = re.sub(r"\s+", " ", "".join(node.itertext())).strip()
                td_units = round(visual_char_units(td_text))
                if len(ARROW_TOKEN_RE.findall(td_text)) >= 2 and ("；" in td_text or ";" in td_text):
                    errors.append(
                        f"表格单元格内堆砌了多组状态箭头符号串（易读性差），请改用自然短语（如『status 进 locked，retry_count 置 0』）：「{snippet(node)}」"
                    )
                if td_non_code.count("；") >= MAX_SEMICOLONS_IN_BLOCK:
                    warnings.append(
                        f"表格单元格内连用了 {td_non_code.count('；')} 个分号罗列多项内容，建议改用 <ul><li> 或移至表下分点详述：「{snippet(node)}」"
                    )
                if td_units > extreme_td_limit:
                    errors.append(
                        f"表格单元格形成严重文字砖（视觉字宽 {td_units} > {extreme_td_limit} 上限），表内请只放简明结论，复杂前提与补充原因请提取到表格下方分点详述：「{snippet(node)}」"
                    )
                elif td_units > cell_limit:
                    warnings.append(
                        f"表格单元格偏长（{cur_table_cols} 列表单格视觉字宽 {td_units} > {cell_limit}），建议表内只留 1 至 2 行简明结论，补充前提移至表下分点：「{snippet(node)}」"
                    )
            else:
                for sub in node:
                    if sub.tag == "p":
                        p_non_code = direct_non_code_text(sub)
                        p_units = round(direct_text_units(sub))
                        if p_non_code.count("；") >= MAX_SEMICOLONS_IN_BLOCK:
                            warnings.append(
                                f"表格单元格内段落连用了 {p_non_code.count('；')} 个分号，建议并入 <ul><li> 或移至表下分点：「{snippet(sub)}」"
                            )
                        if p_units > extreme_td_limit:
                            errors.append(
                                f"表格单元格内段落形成严重文字砖（视觉字宽 {p_units} > {extreme_td_limit} 上限），表内请简述结论，复杂说明移至表下：「{snippet(sub)}」"
                            )
                        elif p_units > cell_limit:
                            warnings.append(
                                f"表格单元格内段落偏长（视觉字宽 {p_units} > {cell_limit}），建议精炼或移至表下说明：「{snippet(sub)}」"
                            )

        if tag == "li":
            units = round(direct_text_units(node))
            direct_codes = direct_inline_code_count(node)
            li_non_code = direct_non_code_text(node)
            if "td" in ancestors:
                if units > MAX_TD_LI_UNITS:
                    warnings.append(
                        f"表格内单条分点偏长（视觉字宽 {units} > {MAX_TD_LI_UNITS}），建议精炼为 1 至 1.5 行短句，复杂背景移至表下说明：「{snippet(node)}」"
                    )
                if li_non_code.count("；") >= MAX_SEMICOLONS_IN_BLOCK:
                    warnings.append(
                        f"表格内单条分点连用了 {li_non_code.count('；')} 个分号，建议拆分为多条 <li>：「{snippet(node)}」"
                    )
            else:
                if units > MAX_LI_DIRECT_UNITS:
                    warnings.append(
                        f"单条列表偏长（视觉字宽 {units} > {MAX_LI_DIRECT_UNITS}），若含多层信息建议拆成『1 句短主干加缩进短子列表』或小表格：「{snippet(node)}」"
                    )
                if li_non_code.count("；") >= MAX_SEMICOLONS_IN_BLOCK:
                    warnings.append(
                        f"单条列表内连用了 {li_non_code.count('；')} 个分号罗列多项内容，建议拆分为嵌套子列表或小表格：「{snippet(node)}」"
                    )
            if direct_codes > MAX_INLINE_CODES_IN_BLOCK:
                warnings.append(
                    f"单条列表内密集使用了 {direct_codes} 个 <code> 灰框（建议不超过 {MAX_INLINE_CODES_IN_BLOCK} 个），普通英文动作词请直接用正文：「{snippet(node)}」"
                )

        next_ancestors = ancestors + [tag]
        if tag == "table":
            all_trs = node.findall(".//tr")
            first_tr = all_trs[0] if all_trs else None
            for child in node:
                if child.tag == "tr":
                    walk(child, next_ancestors, cur_table_cols, child is first_tr)
                else:
                    for sub in child:
                        if sub.tag == "tr":
                            walk(sub, next_ancestors + [child.tag], cur_table_cols, sub is first_tr)
                        else:
                            walk(sub, next_ancestors + [child.tag], cur_table_cols, False)
        else:
            for child in node:
                walk(child, next_ancestors, cur_table_cols, is_header_row)

    if root.text:
        record_placeholder(root.text, in_code=False)
    for top_child in root:
        walk(top_child, [])

    total_chars = len(re.sub(r"\s+", "", "".join(root.itertext())))
    callout_count = sum(1 for _ in root.iter("callout"))
    grid_count = sum(1 for _ in root.iter("grid"))
    bg_span_count = sum(
        1 for el in root.iter("span") if "background-color" in el.attrib
    )
    if not fragment:
        if total_chars >= 1400 and callout_count <= 1 and grid_count == 0:
            warnings.append(
                "正文超过 1400 字但除文首总览外未使用 <grid> 对比卡或警示 <callout>，请核对是否有二元边界或高危红线可做视觉分层"
            )
        if total_chars >= 1800 and body_accent_spans < 3:
            warnings.append(
                f"白底正文与列表中仅使用了 {body_accent_spans} 处重点高亮或彩色 <span>（勿将高亮全塞在 <callout> 内），建议在各节白底关键结论处点亮核心短语"
            )
        if bg_span_count > 22:
            warnings.append(
                f"全文使用了 {bg_span_count} 处背景高亮 <span>，过多涂色会削弱重点信号（建议白底正文控制在 6 至 14 处核心短语）"
            )
        # Check second-half formatting drop-off on multi-chapter docs (split by chapters, not raw child count)
        h1_indices = [i for i, ch in enumerate(children) if ch.tag == "h1"]
        if total_chars >= 2200 and len(h1_indices) >= 3:
            mid_idx = h1_indices[len(h1_indices) // 2]
            second_half = children[mid_idx:]
            sh_spans = sum(count_subtree_accent_spans(ch) for ch in second_half)
            sh_callouts = sum(1 for ch in second_half for _ in ch.iter("callout"))
            sh_grids = sum(1 for ch in second_half for _ in ch.iter("grid"))
            sh_dels = sum(1 for ch in second_half for _ in ch.iter("del"))
            sh_cues = sh_spans + sh_callouts + sh_grids + sh_dels
            if sh_cues == 0:
                warnings.append(
                    "文档后半程章节无任何高亮/彩字 <span>、提示框 <callout>、<grid> 卡片或 <del> 标记，请核对后半部分章节是否需要补齐核心结论高亮、前置依赖/红线提示框或表内状态标色"
                )
            elif sh_spans == 0 or sh_cues < 3:
                warnings.append(
                    f"文档后半程视觉层次偏淡（后半部分彩色/高亮 <span> {sh_spans} 处，卡片与删除线合计 {sh_callouts + sh_grids + sh_dels} 处），建议核对是否需补充关键结论高亮或提示框"
                )
        # Check section-skipping of trade-offs table in technical design docs
        is_tech_design = ("方案" in title_text or "设计" in title_text) and not any(
            kw in title_text
            for kw in ("发布", "上线", "变更", "割接", "回滚", "测试", "调研", "纪要", "评估")
        )
        if is_tech_design and total_chars >= 2200:
            if not any(
                any(kw in h for kw in ("取舍", "备选", "选型", "决策"))
                for h in heading_texts
            ):
                warnings.append(
                    "标题含“方案/设计”但正文未见《方案取舍》小节（标题可含取舍、备选、选型或决策），如属需评审的技术方案请核对是否漏写选型对照表"
                )

    stats = {
        "chars": total_chars,
        "h1": h1_seen,
        "callouts": callout_count,
        "grids": grid_count,
        "bg_spans": bg_span_count,
        "body_spans": body_accent_spans,
        "whiteboards": sum(1 for _ in root.iter("whiteboard")),
        "warnings": len(warnings),
    }
    return errors, warnings, stats


def extract_rect_text(node: dict) -> str:
    raw = node.get("text", "")
    if isinstance(raw, str):
        return raw
    if isinstance(raw, list):
        return "".join(str(item.get("content", "")) for item in raw if isinstance(item, dict))
    return ""


def is_fit_content(val: object) -> bool:
    return isinstance(val, str) and (val == "fit-content" or val.startswith("fit-content("))


def check_board(board_path: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        data = json.loads(board_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"{board_path.name}: JSON 解析失败：{exc}"], []
    if not isinstance(data, dict):
        return [f"{board_path.name}: 顶层 JSON 必须为对象"], []

    shapes: list[dict] = []

    def check_node_text_common(txt: str) -> None:
        scrub_b = ALLOWED_COMPOUND_TERM_RE.sub("", txt)
        bw_b = SUSPECT_BUZZWORD_RE.search(scrub_b)
        if bw_b:
            warnings.append(
                f"{board_path.name}: 画板节点出现疑似夸张词「{bw_b.group(0)}」（位于 {txt[:24]!r}），请核对并改为平实工程表述"
            )
        if DASH_RE.search(txt):
            errors.append(
                f"{board_path.name}: 画板节点含破折号（位于 {txt[:24]!r}），请改用逗号、冒号、括号或换行"
            )

    def walk_nodes(nodes: object, in_children: bool) -> None:
        if not isinstance(nodes, list):
            return
        for node in nodes:
            if not isinstance(node, dict):
                continue
            ntype = node.get("type")
            raw_style = node.get("style")
            if isinstance(raw_style, dict):
                bad_skeys = sorted(set(raw_style.keys()) & ILLEGAL_STYLE_KEYS)
                if bad_skeys:
                    errors.append(
                        f"{board_path.name}: 节点（id={node.get('id')!r}）误将样式属性 {bad_skeys} 嵌在 'style' 子对象内（whiteboard-cli 会静默丢弃导致边框和底色全丢），请把 fillColor、borderColor、borderWidth、borderDash、textColor 直接写在节点顶层"
                    )
            if ntype == "connector":
                if in_children:
                    errors.append(
                        f"{board_path.name}: connector 禁止嵌套在 frame.children 内，必须放在根级 nodes"
                    )
                bad_top_keys = sorted(set(node.keys()) & TOP_LEVEL_CONNECTOR_KEYS)
                if bad_top_keys:
                    errors.append(
                        f"{board_path.name}: connector（id={node.get('id')!r}）误将连线属性 {bad_top_keys} 直接写在节点顶层，请移入 'connector' 子对象内"
                    )
                conn = node.get("connector") if isinstance(node.get("connector"), dict) else {}
                if not conn and not bad_top_keys:
                    errors.append(
                        f"{board_path.name}: connector（id={node.get('id')!r}）缺少 'connector' 子对象"
                    )
                src_ref = conn.get("from") if "from" in conn else node.get("from")
                dst_ref = conn.get("to") if "to" in conn else node.get("to")
                if not src_ref or not dst_ref:
                    errors.append(
                        f"{board_path.name}: connector（id={node.get('id')!r}）缺少有效的 from / to 端点"
                    )
                need_from_anchor = isinstance(src_ref, str)
                need_to_anchor = isinstance(dst_ref, str)
                has_from_anchor = bool(conn.get("fromAnchor") or node.get("fromAnchor"))
                has_to_anchor = bool(conn.get("toAnchor") or node.get("toAnchor"))
                missing_anchor = (need_from_anchor and not has_from_anchor) or (
                    need_to_anchor and not has_to_anchor
                )
                if missing_anchor:
                    line_shape = str(conn.get("lineShape") or node.get("lineShape") or "straight")
                    if line_shape in {"polyline", "rightAngle"}:
                        warnings.append(
                            f"{board_path.name}: 折线 connector（{src_ref} -> {dst_ref}，lineShape={line_shape}）未显式设置 fromAnchor / toAnchor，建议补齐锚点防止绕线或穿框"
                        )
                    else:
                        errors.append(
                            f"{board_path.name}: connector（{src_ref} -> {dst_ref}）未显式设置 fromAnchor / toAnchor，默认锚点易斜线穿框"
                        )
                if "text" in conn or "text" in node:
                    errors.append(
                        f"{board_path.name}: connector（{src_ref} -> {dst_ref}）误用了 'text' 字段（whiteboard-cli 会静默丢弃连线文字），请改用 'label'"
                    )
                label = str(conn.get("label") or node.get("label") or "").strip()
                if label:
                    check_node_text_common(label)
                    if visual_char_units(label) > MAX_EDGE_LABEL_CHARS:
                        errors.append(
                            f"{board_path.name}: connector 连线标签过长（{label!r}），请控制在 {MAX_EDGE_LABEL_CHARS} 字以内以防压框"
                        )
            elif ntype in BOARD_SHAPE_TYPES:
                shapes.append(node)
                txt = extract_rect_text(node).strip()
                if ntype == "cylinder":
                    if not is_fit_content(node.get("height")):
                        errors.append(
                            f"{board_path.name}: cylinder（id={node.get('id')!r}）height 须设为 'fit-content' 防止文字截断"
                        )
                    w = node.get("width")
                    if not isinstance(w, (int, float)) or isinstance(w, bool):
                        errors.append(
                            f"{board_path.name}: cylinder（id={node.get('id')!r}）width 须设为固定像素数值（通常 120 至 200），不能使用 fill-container 或自适应字符串：{w!r}"
                        )
                elif ntype == "rect" and txt and not is_fit_content(node.get("height")):
                    warnings.append(
                        f"{board_path.name}: 含文字的 rect（id={node.get('id')!r}）height 为 {node.get('height')!r}，如非同排等高卡片建议设为 'fit-content' 防止文字截断"
                    )
                if txt:
                    check_node_text_common(txt)
                    lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
                    if len(lines) > MAX_RECT_LINES:
                        errors.append(
                            f"{board_path.name}: 节点「{lines[0][:16]}」塞入了 {len(lines)} 行文字（上限 {MAX_RECT_LINES} 行），请只留标题与 1 行短说明"
                        )
                    for ln in lines:
                        if visual_char_units(ln) > MAX_RECT_LINE_CHARS:
                            errors.append(
                                f"{board_path.name}: 节点单行文字过长（{ln!r}，超 {MAX_RECT_LINE_CHARS} 字宽），易折行超框"
                            )
            elif ntype in {"text", "stickyNote"}:
                if ntype == "stickyNote":
                    shapes.append(node)
                txt = extract_rect_text(node).strip()
                if txt:
                    check_node_text_common(txt)
            elif ntype == "frame":
                if node.get("text") or node.get("title"):
                    errors.append(
                        f"{board_path.name}: frame（id={node.get('id')!r}）不支持直接写 text/title 属性（画板不渲染或极小），请在 children 顶部放独立 text 节点（外包 vertical frame），或 dagre 子图用 layoutOptions.clusterTitle"
                    )
                opts = node.get("layoutOptions") if isinstance(node.get("layoutOptions"), dict) else {}
                rankdir = str(opts.get("rankdir", "TB") or "TB")
                raw_ranksep = opts.get("ranksep", 60)
                try:
                    ranksep = int(raw_ranksep) if raw_ranksep is not None else 60
                except (TypeError, ValueError):
                    errors.append(f"{board_path.name}: layoutOptions.ranksep 必须为整数：{raw_ranksep!r}")
                    ranksep = 60
                edges = opts.get("edges") if isinstance(opts.get("edges"), list) else []
                if rankdir in {"LR", "RL"} and edges:
                    chain_len = longest_dag_nodes(edges)
                    if chain_len > MAX_LR_CHAIN_RANKS:
                        warnings.append(
                            f"{board_path.name}: 横向 dagre 单链串联了 {chain_len} 级节点（建议不超过 {MAX_LR_CHAIN_RANKS} 级），建议用外层 vertical frame 分上下两排阶段展示"
                        )
                if rankdir in {"TB", "BT"} and edges:
                    tb_len = longest_dag_nodes(edges, cap=MAX_TB_SINGLE_COL_RANKS + 2)
                    if tb_len > MAX_TB_SINGLE_COL_RANKS:
                        warnings.append(
                            f"{board_path.name}: 竖向 dagre 串联了 {tb_len} 层节点（建议不超过 {MAX_TB_SINGLE_COL_RANKS} 层），在飞书正文中易拉成高瘦长条，建议改用 rankdir='LR' 横向宽屏构图或左右分区排布"
                        )
                for edge in edges:
                    if isinstance(edge, list) and len(edge) >= 3:
                        label = str(edge[2] or "").strip()
                        if label:
                            check_node_text_common(label)
                        units = visual_char_units(label)
                        min_needed = max(80, int(units * 15 + 24))
                        if units > MAX_EDGE_LABEL_CHARS:
                            errors.append(
                                f"{board_path.name}: dagre 连线标签过长（{label!r}），请缩至 {MAX_EDGE_LABEL_CHARS} 字以内动作词，条件移入正文或表格"
                            )
                        elif rankdir in {"LR", "RL"} and label and ranksep < min_needed:
                            errors.append(
                                f"{board_path.name}: 横向 dagre ranksep={ranksep} 过窄，容纳标签 {label!r} 易压两侧框体（建议 ranksep >= {min_needed}）"
                            )
                walk_nodes(node.get("children"), True)

    walk_nodes(data.get("nodes"), False)

    if len(shapes) > MAX_BOARD_RECTS:
        warnings.append(
            f"{board_path.name}: 单图包含 {len(shapes)} 个业务节点（建议不超过 {MAX_BOARD_RECTS} 个；若是文字对比矩阵建议直接改用飞书 <table>）"
        )
    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fragment", action="store_true", help="Validate a partial XML snippet for block_replace")
    parser.add_argument("xml", type=Path, help="Path to Feishu DocxXML file")
    parser.add_argument("boards", nargs="*", type=Path, help="Optional whiteboard JSON DSL files")
    args = parser.parse_args()

    errors, warnings, stats = check_xml(args.xml, fragment=args.fragment)
    for board in args.boards:
        b_errors, b_warnings = check_board(board)
        errors.extend(b_errors)
        warnings.extend(b_warnings)

    for warn in warnings:
        print(f"WARN {warn}")
    for err in errors:
        print(f"ERROR {err}")
    print(
        f"CHECK errors={len(errors)} warnings={len(warnings)} "
        f"chars={stats.get('chars', 0)} h1={stats.get('h1', 0)} "
        f"callouts={stats.get('callouts', 0)} grids={stats.get('grids', 0)} "
        f"bg_spans={stats.get('bg_spans', 0)} whiteboards={stats.get('whiteboards', 0)} "
        f"boards_checked={len(args.boards)}"
    )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
