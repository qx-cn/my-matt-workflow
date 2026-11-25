#!/usr/bin/env python3
"""Zero-dependency regression tests for check_feishu.py and check_html.py."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "skills" / "my-doc-publish" / "scripts"
TEMPLATE_HTML = REPO_ROOT / "skills" / "my-doc-publish" / "assets" / "TEMPLATE.html"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


check_feishu = load_module("check_feishu", SCRIPTS_DIR / "check_feishu.py")
check_html = load_module("check_html", SCRIPTS_DIR / "check_html.py")


class CheckFeishuXmlTests(unittest.TestCase):
    def _run_xml(self, content: str, *, fragment: bool = False):
        with tempfile.TemporaryDirectory() as tmpdir:
            xml_path = Path(tmpdir) / "doc.xml"
            xml_path.write_text(content, encoding="utf-8")
            return check_feishu.check_xml(xml_path, fragment=fragment)

    def test_valid_full_document_with_both_table_header_styles(self) -> None:
        xml = """
        <title>订单查询改造方案</title>
        <callout emoji="📌" background-color="light-blue">
          <p><b>背景与问题</b></p>
          <p>旧接口串联三次远程查询，高峰期超时明显。</p>
          <p></p>
          <p><b>核心方案</b></p>
          <p>新增聚合读取路径，并保持原有返回结构不变。</p>
        </callout>
        <p></p><hr/>
        <h1 seq="auto">业务背景</h1>
        <p>采用 <span background-color="light-blue" text-color="blue"><b>聚合查询</b></span> 降低延迟。</p>
        <ol><li><p>先读取路由配置。</p></li></ol>
        <ol seq="2"><li><p>再按分片发起并发查询。</p></li></ol>
        <p></p>
        <table>
          <thead><tr><th background-color="light-gray">字段</th><th background-color="light-gray">说明</th></tr></thead>
          <tbody><tr><td><code>order_id</code></td><td>订单主键</td></tr></tbody>
        </table>
        <p></p>
        <table>
          <tr background-color="light-gray"><td>项</td><td>值</td></tr>
          <tr><td>超时</td><td>200ms</td></tr>
        </table>
        <p></p><hr/>
        <h1 seq="auto">核心设计</h1>
        <h2 seq="auto">查询流程</h2>
        <p>缓存击穿防护使用单飞合并。</p>
        <p></p>
        <h2 seq="auto">方案取舍</h2>
        <p>保留兼容协议，降低调用方改造成本。</p>
        """
        errors, warnings, stats = self._run_xml(xml)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])
        self.assertEqual(stats["h1"], 2)

    def test_table_missing_light_gray_header_is_error(self) -> None:
        xml = """
        <title>测试</title>
        <h1 seq="auto">章节</h1>
        <table>
          <thead><tr><th>列一</th><th>列二</th></tr></thead>
          <tbody><tr><td>值一</td><td>值二</td></tr></tbody>
        </table>
        """
        errors, _, _ = self._run_xml(xml)
        self.assertTrue(any("浅灰底色表头" in e for e in errors))

    def test_ol_seq_rules(self) -> None:
        xml_bad_auto = """
        <title>测试</title>
        <h1 seq="auto">章节</h1>
        <ol seq="auto"><li><p>步骤一</p></li></ol>
        """
        errors, _, _ = self._run_xml(xml_bad_auto)
        self.assertTrue(any('seq="auto"' in e for e in errors))

        xml_bad_zero = """
        <title>测试</title>
        <h1 seq="auto">章节</h1>
        <ol seq="0"><li><p>步骤一</p></li></ol>
        """
        errors_zero, _, _ = self._run_xml(xml_bad_zero)
        self.assertTrue(any("正整数" in e for e in errors_zero))

        xml_ok_int = """
        <title>测试</title>
        <h1 seq="auto">章节</h1>
        <ol seq="3"><li><p>步骤三</p></li></ol>
        """
        errors_ok, _, _ = self._run_xml(xml_ok_int)
        self.assertEqual(errors_ok, [])

    def test_callout_forbids_img_and_fe0f_emoji(self) -> None:
        xml = """
        <title>测试</title>
        <callout emoji="⚠️" background-color="light-yellow">
          <p><b>注意事项</b></p>
          <img src="token"/>
        </callout>
        <p></p><hr/>
        <h1 seq="auto">章节</h1>
        """
        errors, _, _ = self._run_xml(xml)
        self.assertTrue(any("\\ufe0f" in e for e in errors))
        self.assertTrue(any("禁止嵌套 <img>" in e for e in errors))

    def test_heading_skip_full_and_fragment(self) -> None:
        full_start_h2 = "<title>测试</title><h2 seq=\"auto\">二级起步</h2>"
        errors, _, _ = self._run_xml(full_start_h2)
        self.assertTrue(any("首个标题应为 <h1>" in e for e in errors))

        full_skip = "<title>测试</title><h1 seq=\"auto\">一级</h1><h3 seq=\"auto\">跳到三级</h3>"
        errors_skip, _, _ = self._run_xml(full_skip)
        self.assertTrue(any("跳级" in e for e in errors_skip))

        frag_ok = "<h2 seq=\"auto\">局部小节</h2><p>正文</p><h3 seq=\"auto\">子节</h3>"
        errors_frag, _, _ = self._run_xml(frag_ok, fragment=True)
        self.assertEqual(errors_frag, [])

        frag_skip = "<h2 seq=\"auto\">局部小节</h2><h4 seq=\"auto\">跳过三级</h4>"
        errors_fskip, _, _ = self._run_xml(frag_skip, fragment=True)
        self.assertTrue(any("跳级" in e for e in errors_fskip))

    def test_adjacent_list_table_pre_blank_line_errors(self) -> None:
        xml = """
        <title>测试</title>
        <h1 seq="auto">章节</h1>
        <ul><li><p>要点</p></li></ul>
        <table>
          <tr background-color="light-gray"><td>甲</td><td>乙</td></tr>
          <tr><td>一</td><td>二</td></tr>
        </table>
        <table>
          <tr background-color="light-gray"><td>丙</td><td>丁</td></tr>
          <tr><td>三</td><td>四</td></tr>
        </table>
        <ol><li><p>命令如下</p></li></ol>
        <pre lang="bash"><code>echo ok</code></pre>
        """
        errors, _, _ = self._run_xml(xml)
        self.assertTrue(any("列表与下方 <table>" in e for e in errors))
        self.assertTrue(any("连续两张 <table>" in e for e in errors))
        self.assertTrue(any("列表与下方 <pre>" in e for e in errors))

    def test_two_tier_thresholds_warn_vs_error(self) -> None:
        para_warn = "中" * 235
        para_err = "中" * 270
        td_warn = "字" * 58
        td_err = "字" * 125
        xml_warn_only = f"""
        <title>测试</title>
        <callout emoji="📌" background-color="light-blue">
          <p>第一段正文</p>
          <p>第二段正文未留空行</p>
        </callout>
        <p></p><hr/>
        <h1 seq="auto">甲、乙并列标题</h1>
        <p>{para_warn}</p>
        <p>这里有一个抓手词，并且有 <code>a</code> <code>b</code> <code>c</code> <code>d</code> <code>e</code> <code>f</code> <code>g</code>。</p>
        <ul><li><p>{"列" * 145}</p></li></ul>
        <p></p>
        <table>
          <tr background-color="light-gray"><td>一</td><td>二</td><td>三</td><td>四</td></tr>
          <tr><td>{td_warn}</td><td>一；二；三；四</td><td>涉及 <code>a</code>、<code>b</code>、<code>c</code>、<code>d</code>、<code>e</code>、<code>f</code></td><td>正常</td></tr>
        </table>
        """
        errors, warnings, _ = self._run_xml(xml_warn_only)
        self.assertEqual(errors, [])
        self.assertTrue(any("连续多段正文" in w for w in warnings))
        self.assertTrue(any("顿号" in w for w in warnings))
        self.assertTrue(any("段落偏长" in w for w in warnings))
        self.assertTrue(any("疑似夸张词" in w for w in warnings))
        self.assertTrue(any("<code> 灰框" in w for w in warnings))
        self.assertTrue(any("单条列表偏长" in w for w in warnings))
        self.assertTrue(any("表格单元格偏长" in w for w in warnings))
        self.assertTrue(any("表格单元格内连用了" in w for w in warnings))

        xml_extreme = f"""
        <title>测试</title>
        <h1 seq="auto">极端超长</h1>
        <p>{para_err}</p>
        <p>规则一；规则二；规则三；规则四</p>
        <p>配置配置中心参数。</p>
        <ul><li><p>条目一；条目二；条目三；条目四</p></li></ul>
        <p></p>
        <table>
          <tr background-color="light-gray"><td>一</td><td>二</td></tr>
          <tr><td>{td_err}</td><td><code>init</code>/<code>run</code>/<code>done</code></td></tr>
        </table>
        """
        errors_ext, warnings_ext, _ = self._run_xml(xml_extreme)
        self.assertTrue(any("严重文字墙" in e for e in errors_ext))
        self.assertTrue(any("严重文字砖" in e for e in errors_ext))
        self.assertTrue(any("单段内连用了 3 个分号" in w for w in warnings_ext))
        self.assertTrue(any("疑似重复词" in w for w in warnings_ext))
        self.assertTrue(any("斜杠挤在同一格" in w for w in warnings_ext))
        # <li><p> must not emit duplicate semicolon warnings from both <li> and <p>
        li_semicolon_warns = [w for w in warnings_ext if "条目一" in w]
        self.assertEqual(len(li_semicolon_warns), 1)

    def test_callout_code_paragraph_kpi_card_and_kv_colspan_tables(self) -> None:
        wide_colspan_text = "实" * 135
        xml = f"""
        <title>测试报告</title>
        <callout emoji="💡" background-color="light-blue">
          <p><b>验证命令</b></p>
          <p><code>curl -s https://example.com/health:8080</code></p>
        </callout>
        <grid>
          <column width-ratio="0.5">
            <callout emoji="✅" background-color="light-green">
              <p><b>拼图进度</b></p>
              <p><span text-color="green"><b>拼好 3 块</b></span></p>
              <p>还差一块蓝色拼图。</p>
            </callout>
          </column>
          <column width-ratio="0.5">
            <callout emoji="📊" background-color="light-blue">
              <p><b>第一组</b></p>
              <p>第一组正文说明</p>
              <p></p>
              <p><b>第二组</b></p>
              <p>第二组正文说明</p>
            </callout>
          </column>
        </grid>
        <p></p><hr/>
        <h1 seq="auto">重点场景核对</h1>
        <table>
          <tbody>
            <tr>
              <th background-color="light-gray"><p><b>拼图名称</b></p></th>
              <td><p><code>kite</code></p></td>
              <th background-color="light-gray"><p><b>颜色</b></p></th>
              <td><p><code>blue</code></p></td>
            </tr>
            <tr>
              <th background-color="light-gray"><p><b>核对结论</b></p></th>
              <td colspan="3"><p>{wide_colspan_text}</p></td>
            </tr>
          </tbody>
        </table>
        """
        errors, warnings, _ = self._run_xml(xml)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_callout_title_punctuation_and_code_spaces(self) -> None:
        for title in ("<b>颜色：</b>", "<b>颜色</b> ：", "<span><b>颜色</b></span><span>:</span>"):
            for body, diagnostic in (("", "末尾不要带冒号"), (" <code>mix red blue</code>", "紧贴在同一行")):
                with self.subTest(title=title, body=body):
                    xml = f"<callout><p>{title}{body}</p></callout>"
                    errors, warnings, _ = self._run_xml(xml, fragment=True)
                    self.assertEqual(len(errors), 1, errors)
                    self.assertIn(diagnostic, errors[0])
                    self.assertEqual(warnings, [])

        xml = '<callout><p><b>画笔</b></p><p>输入 <code>paint  --label "颜色：蓝"</code>。</p></callout>'
        errors, warnings, _ = self._run_xml(xml, fragment=True)
        self.assertEqual((errors, warnings), ([], []))

    def test_new_callout_section_after_body_requires_blank_paragraph(self) -> None:
        xml = '<callout><p><b>纸张</b></p><p>选白纸。</p><p><b>画笔</b></p><p>用铅笔。</p></callout>'
        errors, warnings, _ = self._run_xml(xml, fragment=True)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("上方缺少 <p></p>", errors[0])
        self.assertEqual(warnings, [])

    def test_long_doc_second_half_and_tradeoff_are_warnings(self) -> None:
        body = "这是用来填充章节长度的正常说明文字。" * 50
        xml = f"""
        <title>支付路由改造技术方案</title>
        <h1 seq="auto">背景</h1>
        <p><span background-color="light-blue" text-color="blue"><b>核心目标</b></span></p>
        <p>{body[:200]}</p>
        <p>{body[:200]}</p>
        <p>{body[:200]}</p>
        <p>{body[:200]}</p>
        <p></p><hr/>
        <h1 seq="auto">方案</h1>
        <p>{body[:200]}</p>
        <p>{body[:200]}</p>
        <p>{body[:200]}</p>
        <p>{body[:200]}</p>
        <p></p><hr/>
        <h1 seq="auto">上线</h1>
        <p>{body[:200]}</p>
        <p>{body[:200]}</p>
        <p>{body[:200]}</p>
        <p>{body[:200]}</p>
        """
        errors, warnings, _ = self._run_xml(xml)
        self.assertEqual(errors, [])
        self.assertTrue(any("文档后半程章节无任何高亮" in w for w in warnings))
        self.assertTrue(any("方案取舍" in w for w in warnings))


class CheckFeishuBoardTests(unittest.TestCase):
    def _run_board(self, payload: dict):
        with tempfile.TemporaryDirectory() as tmpdir:
            board_path = Path(tmpdir) / "board.json"
            board_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            return check_feishu.check_board(board_path)

    def test_valid_board_with_cylinder_text_stickynote_and_connector(self) -> None:
        board = {
            "version": 2,
            "nodes": [
                {
                    "type": "frame",
                    "id": "root",
                    "width": 960,
                    "height": "fit-content",
                    "layout": "vertical",
                    "gap": 16,
                    "padding": 24,
                    "children": [
                        {"type": "text", "id": "t1", "text": "核心架构图", "width": "fit-content", "height": "fit-content"},
                        {"type": "rect", "id": "svc", "width": 200, "height": "fit-content", "text": "订单服务\n写入主库"},
                        {"type": "cylinder", "id": "db", "width": 160, "height": "fit-content", "text": "MySQL\n订单主表"},
                        {"type": "stickyNote", "id": "note", "width": 180, "height": "fit-content", "text": "仅新增索引"},
                    ],
                },
                {
                    "type": "connector",
                    "id": "c1",
                    "connector": {
                        "from": "svc",
                        "to": "db",
                        "fromAnchor": "right",
                        "toAnchor": "left",
                        "label": "写入订单",
                    },
                },
            ],
        }
        errors, warnings = self._run_board(board)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_board_schema_errors_cylinder_and_top_level_connector(self) -> None:
        board = {
            "version": 2,
            "nodes": [
                {"type": "cylinder", "id": "db", "width": "fill-container", "height": 80, "text": "DB"},
                {"type": "connector", "id": "c1", "from": "a", "to": "b", "text": "误用text"},
                {"type": "text", "id": "t1", "text": "标题——含破折号", "width": "fit-content", "height": "fit-content"},
            ],
        }
        errors, _ = self._run_board(board)
        self.assertTrue(any("cylinder" in e and "height" in e for e in errors))
        self.assertTrue(any("cylinder" in e and "width" in e for e in errors))
        self.assertTrue(any("直接写在节点顶层" in e for e in errors))
        self.assertTrue(any("误用了 'text'" in e for e in errors))
        self.assertTrue(any("破折号" in e for e in errors))

    def test_board_two_tier_warnings_polyline_tb_and_buzzword(self) -> None:
        board = {
            "version": 2,
            "nodes": [
                {
                    "type": "frame",
                    "id": "dag",
                    "width": 800,
                    "height": "fit-content",
                    "layout": "dagre",
                    "gap": 16,
                    "padding": 16,
                    "layoutOptions": {
                        "rankdir": "TB",
                        "edges": [["n1", "n2"], ["n2", "n3"], ["n3", "n4"], ["n4", "n5"]],
                    },
                    "children": [
                        {"type": "rect", "id": f"n{i}", "width": 180, "height": "fit-content", "text": f"步骤 {i}"}
                        for i in range(1, 6)
                    ],
                },
                {"type": "stickyNote", "id": "s1", "width": 160, "height": "fit-content", "text": "核心抓手"},
                {
                    "type": "connector",
                    "id": "c1",
                    "connector": {"from": "n1", "to": "n5", "lineShape": "polyline", "label": "回流"},
                },
            ],
        }
        errors, warnings = self._run_board(board)
        self.assertEqual(errors, [])
        self.assertTrue(any("竖向 dagre 串联了 5 层" in w for w in warnings))
        self.assertTrue(any("疑似夸张词" in w for w in warnings))
        self.assertTrue(any("折线 connector" in w for w in warnings))

    def test_board_coordinate_connector_and_decorative_rect(self) -> None:
        board = {
            "version": 2,
            "nodes": [
                {"type": "rect", "id": "legend_dot", "width": 16, "height": 16, "fillColor": "#3B82F6"},
                {"type": "rect", "id": "b", "width": 180, "height": "fit-content", "text": "目标节点"},
                {"type": "rect", "id": "card_eq", "width": 180, "height": "fill-container", "text": "等高卡片"},
                {
                    "type": "connector",
                    "id": "c_coord",
                    "connector": {
                        "from": {"x": 150, "y": 200},
                        "to": "b",
                        "toAnchor": "left",
                        "lineShape": "curve",
                        "label": "注解",
                    },
                },
            ],
        }
        errors, warnings = self._run_board(board)
        self.assertEqual(errors, [])
        self.assertTrue(any("card_eq" in w and "fit-content" in w for w in warnings))
        self.assertFalse(any("legend_dot" in w for w in warnings))

    def test_each_connector_endpoint_requires_an_anchor_only_for_a_node(self) -> None:
        point = {"x": 0, "y": -4}
        shapes = [{"type": "rect", "id": name, "width": 80, "height": 40} for name in ("a", "b")]
        for source, target, anchors, missing in (
            (point, {"x": 8, "y": 0}, {}, False),
            ("a", point, {"fromAnchor": "right"}, False),
            (point, "b", {"fromAnchor": "right"}, True),
            ("a", point, {"toAnchor": "left"}, True),
            ("a", "b", {"fromAnchor": "right"}, True),
            ("a", "b", {"toAnchor": "left"}, True),
        ):
            for line_shape in ("straight", "curve", "polyline", "rightAngle"):
                with self.subTest(source=source, target=target, anchors=anchors, line_shape=line_shape):
                    conn = {"from": source, "to": target, "lineShape": line_shape, **anchors}
                    nodes = [*shapes, {"type": "connector", "id": "edge", "connector": conn}]
                    errors, warnings = self._run_board({"version": 2, "nodes": nodes})
                    soft = line_shape in {"polyline", "rightAngle"}
                    self.assertEqual(len(errors), int(missing and not soft), errors)
                    self.assertEqual(len(warnings), int(missing and soft), warnings)
                    if missing:
                        self.assertIn("Anchor", (warnings if soft else errors)[0])

    def test_non_rect_shapes_accept_fixed_heights_and_validate_text(self) -> None:
        for shape in ("ellipse", "diamond", "triangle", "trapezoid"):
            with self.subTest(shape=shape):
                node = {"type": shape, "id": "tile", "width": 80, "height": 40, "text": "拼图"}
                errors, warnings = self._run_board({"version": 2, "nodes": [node]})
                self.assertEqual((errors, warnings), ([], []))
                node["text"] = "蓝\n红\n绿\n黄"
                errors, _ = self._run_board({"version": 2, "nodes": [node]})
                self.assertTrue(any("4 行文字" in e for e in errors), errors)

    def test_cli_exit_code_zero_when_only_warnings(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            xml_path = Path(tmpdir) / "doc.xml"
            xml_path.write_text(
                "<title>测试</title><h1 seq=\"auto\">甲、乙</h1><p>核心抓手。</p>",
                encoding="utf-8",
            )
            proc = subprocess.run(
                [sys.executable, str(SCRIPTS_DIR / "check_feishu.py"), str(xml_path)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("WARN", proc.stdout)
            self.assertIn("CHECK errors=0 warnings=2", proc.stdout)


class CheckHtmlTests(unittest.TestCase):
    def _run_html(self, html: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as tmpdir:
            html_path = Path(tmpdir) / "doc.html"
            html_path.write_text(html, encoding="utf-8")
            return subprocess.run(
                [sys.executable, str(SCRIPTS_DIR / "check_html.py"), str(html_path)],
                capture_output=True,
                text=True,
                check=False,
            )

    def test_start_tag_placeholder_in_code_or_script_is_skipped(self) -> None:
        html = """<!doctype html>
        <html><body>
        <nav><a href="#overview" data-page-link="overview">总览</a></nav>
        <section id="overview" data-page="overview">
          <code data-template="{{OK_IN_CODE}}">{{OK_BODY}}</code>
          <script data-tpl="{{OK_IN_SCRIPT}}">const x = "{{OK_JS}}";</script>
          <p>正文无占位符</p>
        </section>
        </body></html>
        """
        proc = self._run_html(html)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_normal_tag_attribute_placeholder_is_caught(self) -> None:
        html = """<!doctype html>
        <html><body>
        <nav><a href="#overview" data-page-link="overview">总览</a></nav>
        <section id="overview" data-page="overview">
          <div title="{{UNFILLED_ATTR}}">正文</div>
        </section>
        </body></html>
        """
        proc = self._run_html(html)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("{{UNFILLED_ATTR}}", proc.stdout)

    def test_template_html_th_style_and_optional_slot_comments(self) -> None:
        text = TEMPLATE_HTML.read_text(encoding="utf-8")
        self.assertIn("th { background: #f4f6f9;", text)
        self.assertNotIn("text-transform: uppercase; }", text)
        self.assertIn("Optional: 3-column decision strip", text)
        self.assertIn("Optional: anchor index card", text)
        self.assertIn("Optional: full-width overview diagram", text)
        self.assertIn("Optional: extra overview cards", text)
        self.assertIn("try { localStorage.setItem(storageKey, JSON.stringify(notes)); }", text)


class SyncScriptTests(unittest.TestCase):
    def test_independent_legacy_directory_symlink_only_cleans_managed_skill_links(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            store = home / "archive"
            store.mkdir()
            legacy = home / ".codex" / "skills"
            legacy.parent.mkdir()
            legacy.symlink_to(store, target_is_directory=True)
            skill = REPO_ROOT / "skills" / "my-review"
            managed = store / skill.name
            retired = store / "my-retired-example"
            managed.symlink_to(skill)
            retired.symlink_to(skill.parent / retired.name)
            (store / "bookmark").symlink_to(skill)
            (store / "my-notes").symlink_to(REPO_ROOT / "rules" / "global.md")
            (store / "my-drawing").mkdir()
            note = store / "my-drawing" / "paper.txt"
            note.write_text("blue", encoding="utf-8")
            (store / "outside").symlink_to(note)
            env = {"HOME": str(home), "PATH": "/usr/bin:/bin:/usr/local/bin"}
            script = str(REPO_ROOT / "scripts" / "sync.sh")

            def run(*args: str):
                return subprocess.run([script, *args], env=env, capture_output=True, text=True)

            for args, status, message in ((["--check"], 1, "stale link"), (["--dry-run"], 0, "REMOVE stale")):
                result = run(*args)
                self.assertEqual(result.returncode, status, result.stdout + result.stderr)
                for path in (managed, retired):
                    self.assertIn(f"{message} {legacy / path.name}\n", result.stdout)
                    self.assertTrue(path.is_symlink())
            for args in ([], ["--check"]):
                result = run(*args)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse(managed.is_symlink())
            self.assertFalse(retired.is_symlink())
            self.assertEqual(legacy.readlink(), store)
            self.assertEqual((store / "bookmark").readlink(), skill)
            self.assertEqual((store / "my-notes").readlink(), REPO_ROOT / "rules" / "global.md")
            self.assertEqual((store / "outside").readlink(), note)
            self.assertEqual(note.read_text(encoding="utf-8"), "blue")

    def test_legacy_skill_dir_symlink_to_active_dir_does_not_delete_or_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_home = Path(tmpdir)
            active = fake_home / ".agents" / "skills"
            active.mkdir(parents=True)
            cursor_dir = fake_home / ".cursor"
            cursor_dir.mkdir(parents=True)
            (cursor_dir / "skills").symlink_to(active)
            env = {
                "HOME": str(fake_home),
                "PATH": "/usr/bin:/bin:/usr/local/bin",
            }
            sync_sh = str(REPO_ROOT / "scripts" / "sync.sh")
            r_sync = subprocess.run([sync_sh], env=env, capture_output=True, text=True, check=False)
            self.assertEqual(r_sync.returncode, 0, r_sync.stdout + r_sync.stderr)
            r_chk = subprocess.run([sync_sh, "--check"], env=env, capture_output=True, text=True, check=False)
            self.assertEqual(r_chk.returncode, 0, r_chk.stdout + r_chk.stderr)
            self.assertNotIn("stale link", r_chk.stdout)
            self.assertTrue((active / "my-review").is_symlink())


if __name__ == "__main__":
    unittest.main()
