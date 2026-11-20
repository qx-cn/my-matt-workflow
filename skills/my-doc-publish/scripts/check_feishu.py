#!/usr/bin/env python3
"""Deterministic layout, readability, and whiteboard collision checks for Feishu DocxXML & JSON DSL."""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

FORBIDDEN_IN_CALLOUT = {"pre", "table", "grid", "whiteboard", "hr", "details"}
FORBIDDEN_IN_GRID = {"pre", "table"}
HEADING_TAGS = {f"h{i}" for i in range(1, 10)}
MANUAL_NUM_RE = re.compile(
    r"^\s*(?:第?[一二三四五六七八九十百]+[章节条部分]|[一二三四五六七八九十]+[、.．]|（[一二三四五六七八九十0-9]+）|\d+(?:\.\d+)*[\s、.．)])"
)
PLACEHOLDER_RE = re.compile(r"\[待补充|TODO[:：]|{{\s*[^{}]+\s*}}")
FORBIDDEN_BUZZWORD_RE = re.compile(r"击穿|收口|抓手|盲区|赋能|伪造|锁死")
DASH_RE = re.compile(r"—+")

MAX_PARAGRAPH_UNITS = 180
MAX_LI_DIRECT_UNITS = 140
MAX_TD_DIRECT_UNITS = 85
MAX_TD_LI_UNITS = 70
MAX_TD_CODE_CHARS = 68
MAX_INLINE_CODES_IN_BLOCK = 6
MAX_TABLE_COLS_FOR_DENSE = 5
MAX_SEMICOLONS_IN_BLOCK = 3
MAX_BOARD_RECTS = 10
MAX_RECT_LINES = 2
MAX_RECT_LINE_CHARS = 22
MAX_EDGE_LABEL_CHARS = 10
MAX_LR_CHAIN_RANKS = 4


def longest_dag_nodes(edges: list[list[str]]) -> int:
    adj: dict[str, list[str]] = {}
    nodes: set[str] = set()
    for edge in edges:
        if isinstance(edge, list) and len(edge) >= 2:
            u, v = str(edge[0]), str(edge[1])
            if u != v:
                adj.setdefault(u, []).append(v)
                nodes.add(u)
                nodes.add(v)
    memo: dict[str, int] = {}

    def dfs(u: str, visiting: set[str]) -> int:
        if u in memo:
            return memo[u]
        best = 1
        visiting.add(u)
        for nxt in adj.get(u, []):
            if nxt not in visiting:
                best = max(best, 1 + dfs(nxt, visiting))
        visiting.remove(u)
        memo[u] = best
        return best

    return max((dfs(n, set()) for n in nodes), default=0)


def is_empty_paragraph(elem: ET.Element) -> bool:
    return elem.tag == "p" and len(elem) == 0 and not (elem.text or "").strip()


def direct_text_units(elem: ET.Element) -> float:
    parts = [elem.text or ""]
    for child in elem:
        if child.tag not in {"ul", "ol", "pre", "table"}:
            parts.append("".join(child.itertext()))
        parts.append(child.tail or "")
    text = re.sub(r"\s+", " ", "".join(parts)).strip()
    return visual_char_units(text)


def snippet(elem: ET.Element, limit: int = 36) -> str:
    raw = re.sub(r"\s+", " ", "".join(elem.itertext())).strip()
    return raw[:limit] + ("..." if len(raw) > limit else "")


def visual_char_units(text: str) -> float:
    units = 0.0
    for ch in text:
        units += 1.0 if ord(ch) > 127 else 0.58
    return units


def check_xml(xml_path: Path) -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []
    raw = xml_path.read_text(encoding="utf-8")

    for match in PLACEHOLDER_RE.finditer(raw):
        errors.append(f"XML 存在未清理的占位符：{match.group(0)!r}")

    if "<details" in raw:
        errors.append("飞书 XML 不支持 HTML <details> 标签")

    try:
        root = ET.fromstring(f"<root>{raw}</root>")
    except ET.ParseError as exc:
        return [f"XML 语法解析失败（请检查标签闭合或 &lt;/&gt;/&amp; 转义）：{exc}"], {}

    top_tags = [child.tag for child in root]
    if not top_tags or top_tags[0] != "title":
        errors.append("完整飞书 XML 顶层第一个元素应为 <title>")

    # Check two-tier visual separation:
    # 1) <hr/> before 1st <h1> (when preceded by overview blocks) and before 2nd+ <h1>
    # 2) <p></p> blank line before 2nd+ <h2> within the same <h1> chapter
    h1_seen = 0
    h2_in_chapter = 0
    saw_overview_before_h1 = False
    saw_hr_since_prev_h1 = False
    children = list(root)
    for idx, child in enumerate(children):
        if child.tag == "hr":
            saw_hr_since_prev_h1 = True
        elif child.tag in {"callout", "grid"} and h1_seen == 0:
            saw_overview_before_h1 = True
        elif child.tag == "h1":
            h1_seen += 1
            h2_in_chapter = 0
            if h1_seen == 1 and saw_overview_before_h1 and not saw_hr_since_prev_h1:
                errors.append(
                    f"文首总览块与第 1 个 <h1/>「{snippet(child)}」之间缺少 <hr/> 分割线，顶部摘要会紧贴标题"
                )
            elif h1_seen >= 2 and not saw_hr_since_prev_h1:
                errors.append(
                    f"一级章节 <h1/>「{snippet(child)}」上方缺少 <hr/> 分割线，章节容易黏连"
                )
            saw_hr_since_prev_h1 = False
        elif child.tag == "h2":
            h2_in_chapter += 1
            if h2_in_chapter >= 2:
                prev = children[idx - 1] if idx > 0 else None
                if prev is None or (not is_empty_paragraph(prev) and prev.tag != "hr"):
                    errors.append(
                        f"二级小节 <h2/>「{snippet(child)}」上方缺少 <p></p> 空行留白，会与上一小节末尾内容紧贴"
                    )

    warnings: list[str] = []
    body_accent_spans = 0

    def walk(node: ET.Element, ancestors: list[str]) -> None:
        nonlocal body_accent_spans
        tag = node.tag
        if tag == "span" and "callout" not in ancestors:
            tc = node.attrib.get("text-color", "")
            if "background-color" in node.attrib or (tc and tc != "gray"):
                body_accent_spans += 1
        if tag in {"p", "li", "h1", "h2", "h3"} and "pre" not in ancestors:
            non_code_text = "".join(
                [node.text or ""]
                + [
                    ("" if c.tag in {"code", "pre", "ul", "ol"} else "".join(c.itertext())) + (c.tail or "")
                    for c in node
                ]
            )
            bw = FORBIDDEN_BUZZWORD_RE.search(non_code_text)
            if bw:
                errors.append(
                    f"正文含禁用夸张词「{bw.group(0)}」（位于「{snippet(node)}」），请改为平实准确的工程表述"
                )
            if DASH_RE.search(non_code_text):
                errors.append(
                    f"正文含破折号（位于「{snippet(node)}」），请按全局规范改用逗号、冒号、句号或括号"
                )

        if tag in HEADING_TAGS:
            text = "".join(node.itertext()).strip()
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

        if tag == "ol" and "seq" in node.attrib:
            errors.append(
                "<ol> 标签不支持 seq 属性（飞书服务端会报 degrade_code=5002），请去掉 seq"
            )

        if tag == "pre":
            child_tags = [c.tag for c in node]
            if child_tags != ["code"]:
                errors.append("<pre> 内必须且只能直接包裹单个 <code> 子标签")

        if "callout" in ancestors and tag in FORBIDDEN_IN_CALLOUT:
            errors.append(f"<callout> 内禁止嵌套 <{tag}>")

        if "grid" in ancestors and tag in FORBIDDEN_IN_GRID:
            errors.append(f"<grid> 多栏内禁止塞入 <{tag}>，请改为全宽纵向排列")

        if tag == "p" and "td" not in ancestors and "th" not in ancestors:
            units = round(direct_text_units(node))
            raw_p = "".join(node.itertext())
            code_cnt = sum(1 for c in node if c.tag == "code")
            if units > MAX_PARAGRAPH_UNITS:
                errors.append(
                    f"段落过密过长（视觉字宽 {units} > {MAX_PARAGRAPH_UNITS} 上限），请拆短或转为双栏卡/小表格，避免视觉密麻：「{snippet(node)}」"
                )
            if code_cnt > MAX_INLINE_CODES_IN_BLOCK:
                errors.append(
                    f"单段内密集套用了 {code_cnt} 个 <code> 灰框（上限 {MAX_INLINE_CODES_IN_BLOCK} 个，满屏灰框晃眼），普通英文动作词与大类名称请直接用正文，<code> 仅留给真实字段、文件名与错误码：「{snippet(node)}」"
                )
            if raw_p.count("；") >= MAX_SEMICOLONS_IN_BLOCK:
                errors.append(
                    f"单段内连用了 {raw_p.count('；')} 个分号罗列多项规则（句内罗列文字墙），请拆为独立小表格或分点列表：「{snippet(node)}」"
                )

        if tag == "table":
            first_tr = node.find(".//tr")
            if first_tr is not None:
                col_cnt = len(list(first_tr))
                td_units_list = [
                    visual_char_units(re.sub(r"\s+", " ", "".join(td.itertext())).strip())
                    for td in node.findall(".//td")
                ]
                avg_td = (sum(td_units_list) / len(td_units_list)) if td_units_list else 0.0
                if col_cnt > MAX_TABLE_COLS_FOR_DENSE and avg_td > 18:
                    warnings.append(
                        f"表格列数较多（{col_cnt} 列）且单元格平均字宽 {avg_td:.0f}，在 820px 页面内易挤成窄豆腐块，建议合并列至 3~4 列"
                    )

        if tag == "td":
            has_list = any(c.tag in {"ul", "ol"} for c in node)
            for code_el in node.iter("code"):
                ctext = (code_el.text or "").strip()
                if len(ctext) > MAX_TD_CODE_CHARS:
                    errors.append(
                        f"表格单元格内塞入了 {len(ctext)} 字符的超长命令/代码（会在窄列内折成多行麻花），请把完整命令提取到表外全宽 <pre> 代码块，格内只写短子命令名：「{ctext[:36]}...」"
                    )
            if not has_list:
                td_text = re.sub(r"\s+", " ", "".join(node.itertext())).strip()
                td_units = round(visual_char_units(td_text))
                if td_units > MAX_TD_DIRECT_UNITS:
                    errors.append(
                        f"表格单元格文字过密（视觉字宽 {td_units} > {MAX_TD_DIRECT_UNITS} 上限，窄列会折成四五行豆腐块），请精炼为 1~2 行短词条、合并冗余列或在格内用 <ul><li> 分短点：「{snippet(node)}」"
                    )

        if tag == "li":
            units = round(direct_text_units(node))
            direct_codes = sum(1 for c in node if c.tag == "code")
            full_li_direct = "".join(
                [node.text or ""]
                + [
                    ("".join(c.itertext()) if c.tag not in {"ul", "ol"} else "") + (c.tail or "")
                    for c in node
                ]
            )
            if "td" in ancestors:
                if units > MAX_TD_LI_UNITS:
                    errors.append(
                        f"表格内单条分点仍过长（视觉字宽 {units} > {MAX_TD_LI_UNITS} 上限），请精炼为 1~1.5 行短检查点（去掉多余动作词 <code> 灰框）：「{snippet(node)}」"
                    )
            elif units > MAX_LI_DIRECT_UNITS:
                errors.append(
                    f"单条列表过密过长（视觉字宽 {units} > {MAX_LI_DIRECT_UNITS} 上限，超过 2.5 行挤成文字团），请拆成『1 句主干 + 缩进短子列表』或改用双栏卡/小表格：「{snippet(node)}」"
                )
            if direct_codes > MAX_INLINE_CODES_IN_BLOCK:
                errors.append(
                    f"单条列表内密集套用了 {direct_codes} 个 <code> 灰框（上限 {MAX_INLINE_CODES_IN_BLOCK} 个），普通英文动作词请直接用正文：「{snippet(node)}」"
                )
            if full_li_direct.count("；") >= MAX_SEMICOLONS_IN_BLOCK:
                errors.append(
                    f"单条列表内连用了 {full_li_direct.count('；')} 个分号罗列多项内容（句内罗列文字墙），请拆为独立小表格或子列表：「{snippet(node)}」"
                )

        next_ancestors = ancestors + [tag]
        for child in node:
            walk(child, next_ancestors)

    for top_child in root:
        walk(top_child, [])

    total_chars = len(re.sub(r"\s+", "", "".join(root.itertext())))
    callout_count = sum(1 for _ in root.iter("callout"))
    grid_count = sum(1 for _ in root.iter("grid"))
    bg_span_count = sum(
        1 for el in root.iter("span") if "background-color" in el.attrib
    )
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
            f"全文使用了 {bg_span_count} 处背景高亮 <span>，过多涂色会削弱重点信号（建议白底正文控制在 6~14 处核心短语）"
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
    for warn in warnings:
        print(f"WARN {warn}")
    return errors, stats


def extract_rect_text(node: dict) -> str:
    raw = node.get("text", "")
    if isinstance(raw, str):
        return raw
    if isinstance(raw, list):
        return "".join(str(item.get("content", "")) for item in raw if isinstance(item, dict))
    return ""


def check_board(board_path: Path) -> list[str]:
    errors: list[str] = []
    try:
        data = json.loads(board_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"{board_path.name}: JSON 解析失败：{exc}"]

    rects: list[dict] = []

    def walk_nodes(nodes: list[dict], in_children: bool) -> None:
        for node in nodes:
            if not isinstance(node, dict):
                continue
            ntype = node.get("type")
            if ntype == "connector" and in_children:
                errors.append(
                    f"{board_path.name}: connector 禁止嵌套在 frame.children 内，必须放在根级 nodes"
                )
            if ntype == "connector":
                conn = node.get("connector", {})
                if not (conn.get("fromAnchor") or node.get("fromAnchor")) or not (
                    conn.get("toAnchor") or node.get("toAnchor")
                ):
                    errors.append(
                        f"{board_path.name}: connector（{conn.get('from') or node.get('from')} -> {conn.get('to') or node.get('to')}）未显式设置 fromAnchor / toAnchor，默认锚点易斜线穿框"
                    )
                if "text" in conn or "text" in node:
                    errors.append(
                        f"{board_path.name}: connector（{conn.get('from') or node.get('from')} -> {conn.get('to') or node.get('to')}）误用了 'text' 字段（whiteboard-cli 会静默丢弃连线文字），请改用 'label' 并配 'labelFillColor': '#FFFFFF'"
                    )
                label = str(conn.get("label", "") or "").strip()
                if visual_char_units(label) > MAX_EDGE_LABEL_CHARS:
                    errors.append(
                        f"{board_path.name}: connector 连线标签过长（{label!r}），请控制在 {MAX_EDGE_LABEL_CHARS} 字以内以防压框"
                    )
            if ntype == "rect":
                rects.append(node)
                if node.get("height") != "fit-content":
                    errors.append(
                        f"{board_path.name}: rect（id={node.get('id')!r}）height 须设为 'fit-content' 防止文字截断"
                    )
                txt = extract_rect_text(node).strip()
                if txt:
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
            if ntype == "frame":
                if node.get("text") or node.get("title"):
                    errors.append(
                        f"{board_path.name}: frame（id={node.get('id')!r}）不支持直接写 text/title 属性（画板不渲染或极小），请在 children 顶部放独立 text 节点（外包 vertical frame），或 dagre 子图用 layoutOptions.clusterTitle"
                    )
                opts = node.get("layoutOptions") or {}
                rankdir = opts.get("rankdir", "TB")
                ranksep = int(opts.get("ranksep", 60) or 60)
                edges = opts.get("edges") or []
                if rankdir in {"LR", "RL"} and edges:
                    chain_len = longest_dag_nodes(edges)
                    if chain_len > MAX_LR_CHAIN_RANKS:
                        errors.append(
                            f"{board_path.name}: 横向 dagre 单链串联了 {chain_len} 级节点（上限 {MAX_LR_CHAIN_RANKS} 级），总宽过大在飞书 820px 正文中字号会极小；请用外层 vertical frame 分上下阶段排布或改用 TB"
                        )
                for edge in edges:
                    if isinstance(edge, list) and len(edge) >= 3:
                        label = str(edge[2] or "").strip()
                        units = visual_char_units(label)
                        if units > MAX_EDGE_LABEL_CHARS:
                            errors.append(
                                f"{board_path.name}: dagre 连线标签过长（{label!r}），请缩至 {MAX_EDGE_LABEL_CHARS} 字以内动作词，条件移入正文或表格"
                            )
                        elif rankdir in {"LR", "RL"} and label and ranksep < int(units * 15 + 50):
                            errors.append(
                                f"{board_path.name}: 横向 dagre ranksep={ranksep} 过窄，容纳标签 {label!r} 易压两侧框体（建议 ranksep >= 150）"
                            )
                walk_nodes(node.get("children") or [], True)

    walk_nodes(data.get("nodes") or [], False)

    if len(rects) > MAX_BOARD_RECTS:
        errors.append(
            f"{board_path.name}: 单图包含 {len(rects)} 个 rect 节点（上限 {MAX_BOARD_RECTS} 个；若是文字对比矩阵请直接改用飞书 <table>）"
        )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("xml", type=Path, help="Path to Feishu DocxXML file")
    parser.add_argument("boards", nargs="*", type=Path, help="Optional whiteboard JSON DSL files")
    args = parser.parse_args()

    errors, stats = check_xml(args.xml)
    for board in args.boards:
        errors.extend(check_board(board))

    for err in errors:
        print(f"ERROR {err}")
    print(
        f"CHECK errors={len(errors)} warnings={stats.get('warnings', 0)} "
        f"chars={stats.get('chars', 0)} h1={stats.get('h1', 0)} "
        f"callouts={stats.get('callouts', 0)} grids={stats.get('grids', 0)} "
        f"bg_spans={stats.get('bg_spans', 0)} whiteboards={stats.get('whiteboards', 0)} "
        f"boards_checked={len(args.boards)}"
    )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
