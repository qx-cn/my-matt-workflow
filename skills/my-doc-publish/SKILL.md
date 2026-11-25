---
name: my-doc-publish
description: 用户要求把文档发布到飞书、更新飞书云文档与画板，或渲染为本地交互式 HTML 时使用。将定稿 Markdown 排版为留白清晰、重点突出的飞书文档或本地 HTML，并运行脚本校验版式与画板。
disable-model-invocation: true
---

# 文档排版与发布

本 Skill 把已经写通顺的 Markdown 定稿（如 `design.md`、`release.md`、`test-report.md`）排成好读的**飞书云文档（含画板）**或**本地交互式 HTML**。如果用户没指明发布到飞书还是生成本地 HTML，先简短问一句。

- **没有干净定稿先写正文**：如果手头只有零散需求讨论而还没有写通顺的 Markdown 定稿，先读取同级目录的 `../my-tech-design/SKILL.md` 写出干净的 `design.md`（完成源码核实、口头复述自检和配图策划），再进入排版发布。
- **转 XML 时保住完整语义和全量映射表**：排版的目的是用卡片、清爽表格、代码块、画板和重点颜色帮读者更快看懂。把 `design.md` 转为飞书 XML 时，保留原本通顺的句子和完整的业务映射表，不砍掉动作对象或前提把句子压成电报残片，也不把全量映射表截断成几行示例；单段超过 4 行时直接拆成两段 `<p>`，窄列放不下的补充前提移到表下分点说明。
- **增量更新飞书并同步本地事实源**：`design.md` 是唯一长期维护的本地事实源，`.xml` 仅作首次建文档或局部更新前的临时校验产物。修改已有飞书文档时，先用 `lark-cli docs +fetch` 按节读取最新内容和 `block_id`，把改动片段用 `check_feishu.py --fragment` 校验后再做局部 `block_replace` 或 `str_replace`，避开原有 `<whiteboard>` 的 `block_id` 以保留画板与评论。若改动涉及业务规则、状态或契约，按全局规范同步更新同目录的 `design.md`。

---

## 1. 发布飞书云文档与画板

调用 `lark-doc`、`lark-whiteboard`、`lark-wiki` 技能操作：

### 用分割线和空行拉开间距

- **章节级留白**：Markdown 的 `##` 对应 `<h1 seq="auto">`，`###` 对应 `<h2 seq="auto">`（文档标题放顶层 `<title>`）。文首总览框和第 1 个 `<h1 seq="auto">` 之间，以及第 2 个起每个 `<h1 seq="auto">` 上方，统一加 `<p></p><hr/>`。
- **小节与块间留白**：同一个 `<h1>` 下第 2 个起每个 `<h2 seq="auto">` 上方，以及同一小节内“文字列表与下方表格/代码块”或“连续两张表格”之间，插入空行 `<p></p>` 拉开间距。
- **长条目拆子列表、对称内容用双栏**：单条列表超过两行半时拆成“1 句短主干加缩进短子列表”；对称的前后对比或正反分类（如改造前与改造后、核对项与排除项）优先排成 `<grid>` 左右双栏彩色 `<callout>` 卡片。

### 全篇保持一致的视觉层次

- **卡片内小标题单独成行，多段之间留空行**：无论是文首浅蓝总览 `<callout>`、`<grid>` 对比卡还是节内 `🚨` 警示 `<callout>`，卡片内小标题统一单独成行 `<p><b>小标题</b></p>`（末尾不加冒号），正文另起下一行写 `<p>...</p>` 或 `<ul><li>...</li></ul>`；包含多组小标题或连续多段正文时，在组间与段间插入 `<p></p>` 空行。
- **讲核心机制的小节加结论块**：讲核心机制的二级小节首句结论用 `<blockquote><p>...</p></blockquote>`；多条目汇总表小节可直接进表，不硬凑空泛总结句。
- **后半篇与前半篇保持同等视觉层次**：第 2 章中后段与第 3、4 章同样做好重点标记：
  - 在白底正文或 `<blockquote>` 里用 `<span background-color="light-*" text-color="*"><b>短语</b></span>` 点亮核心结论（不在同色 `<callout>` 内重复叠涂）。
  - 外部强依赖、安全隔离红线和回滚禁令用浅黄或浅红 `🚨` `<callout>` 标出；`emoji` 选用单码点图标（`📌`、`✅`、`🚫`、`💡`、`📊`、`🚀`、`🔧`、`⏳`、`🚨`），不用带变体选择符的图标。
  - 下线配置或废弃参数加 `<del>` 删除线；表格里用无底彩字 `<span text-color="green|red|purple|blue"><b>词</b></span>` 标出关键终态、允许或禁止结论。
- **克制行内 `<code>` 与修饰标签**：普通英文动作词与大类名称（如 Submit、Approve、Reject、Rollback）直接用正文字体，`<code>` 留给真实库表字段与底层字面值、路径文件名、配置键、命令参数与错误码；中文正文不用斜体 `<em>`/`<i>` 和非链接下划线 `<u>`。

### 表格写法

- **表头统一加浅灰底色**：每张表格上方配粗体表序号标题（如 `<p><b>表 2-1：...</b></p>`）。表头支持两种合法写法：`<thead><tr><th background-color="light-gray">...</th></tr></thead>`，或首行直接写 `<tr background-color="light-gray">`。逐行展示键值的表格给标签 `<th>` 加底色，对应的值保留普通 `<td>`。
- **控制列数与格内长度**：普通说明表控制在 3 至 4 列（`状态 × 操作权限矩阵表` 按实际操作列展开除外）。4 列及以上表格的单元格只放 1 至 2 行简明结论，不用多组 `A -> B` 符号串，单格不堆超过 5 个 `<code>`；复杂前提移到表下分点详述，同一列有多条动作时统一用 `<ul><li>` 对齐；超过 68 字符的长命令提取到表外全宽 `<pre lang="bash">` 代码块。

### 飞书 XML 基本语法

- 顶层以唯一 `<title>` 开头，正文标题从 `<h1>` 起步且不跳级（局部更新片段允许从 `<h2>` 起步）。使用 `seq="auto"` 时去掉源标题里的章节序号，例如把“1.1 背景与问题”写成 `<h2 seq="auto">背景与问题</h2>`。
- `<checkbox>` 直接写行内文本（如 `<checkbox done="false">核查内容</checkbox>`），内部不嵌套 `<p>` 等块级标签。
- `<ol>` 默认自动编号，不写冗余的 `seq="auto"`（需要延续编号时可写正整数，如 `<ol seq="3">`）。
- `<callout>` 内不嵌套 `<pre>`、`<table>`、`<grid>`、`<whiteboard>`、`<hr>`、`<img>` 或 `<details>`；`<grid>` 内不嵌套 `<pre>` 或 `<table>`；飞书 XML 不使用 `<details>`。

### 按图型选择画板路线

新建文档时在 XML 对应位置放 `<whiteboard type="blank"></whiteboard>` 获取画板 `token`，按图型选择最稳的生成路线：

| 场景与图型 | 推荐路线 | 原因与核查要点 |
| --- | --- | --- |
| 跨组件时序图（`sequenceDiagram`） | Mermaid | 生命线和调用箭头自动对齐，按下文的 Mermaid 命令写入目标画板 |
| 阶段对比矩阵、改造边界流程图、跨环境泳道图、分组状态图 | JSON DSL（默认） | Flex / Dagre 自动排版且文字与框体、连线自动绑定；动笔前先读 `lark-whiteboard` 的 `elements/schema.md`、`elements/style.md` 与对应 `scenes/*.md` |
| 定制示意图、时间轴、非对称信息图或用户明确指定 SVG | SVG（按 `lark-whiteboard/routes/svg.md`） | 视觉自由度高，但实测 `whiteboard-cli --check` 会漏检独立 `<text>` 溢出 `<rect>`，须先本地渲染 PNG 并用 `Read` 肉眼核对；若两轮调整后文字仍溢出或节点仍重叠，可改用 JSON DSL。用户指定 SVG 时先说明预览问题，由用户决定是否更换格式 |

### 用横向宽屏构图并标清分区颜色

- **横向宽屏外框**：JSON DSL 最外层包一层浅灰圆角画布框（`fillColor: "#F8FAFC"`、`borderColor: "#E5E6EB"`、`borderWidth: 1`、`borderRadius: 12`、`padding: 24`，顶部放独立加粗 `type: "text"` 图标题，直接给 `frame` 设置 `text` 或 `title` 无法显示预期标题），整体保持约 `1.8:1 ~ 3:1` 的宽屏比例。5 步以上流程优先用 `rankdir: "LR"` 横向排布、左右分区框或上下并行分支，避免拉成高瘦单列 `TB` 长条。
- **虚实分区与顶层样式**：用彩色虚线框（`borderDash: "dashed"`）或浅色分区框区分本次改造范围与既有复用模块，或旧方案痛点行与新方案收益行。样式属性直接写在节点顶层（`fillColor`、`borderColor`、`borderWidth: 2`、`borderRadius: 8`、`textColor`），不嵌套在 `"style": {...}` 子对象里。带文字的业务 `rect` 通常设 `height: "fit-content"`、`width: 170~230`（`cylinder` 用固定宽度 120~200 与 `height: "fit-content"`，不用 `fill-container`），框内写“动作/模块名 + 1 行简短职责或具体算例值”。
- **连线写法**：Flex 布局的 `connector` 放在根级 `nodes` 中，属性写在 `connector` 子对象里，标签用 `label`（不写 `text`），端点引用节点 ID 时，直线和曲线显式设置对应的 `fromAnchor` 或 `toAnchor`，折线按预览检查走向。坐标端点直接使用 `{x, y}`。`dagre` 连线写在根 `layoutOptions.edges` 中，带文字横向边的 `ranksep` 按 `max(80, 视觉字数 × 15 + 24)` 设置（中文按 1、ASCII 按 0.58 折算；无文字边设 `60~80`）。
- **画板写入命令**：
  - 先核对画板 token 与目标文档。以下命令用于新建的空白画板。若写入结果未知，先查询画板状态。需要重试同一次写入时，复用 `--idempotent-token`。已有画板优先局部编辑，只有用户明确授权整板替换时才加 `--overwrite`，该参数会先清空已有内容。
  - 将 SVG 编译为本地文件，运行 `npx -y @larksuite/whiteboard-cli@^0.2.13 -i diagram.svg -f svg --to openapi --format json > diagram.json`。若输入为 JSON DSL，把 `-i diagram.svg -f svg` 换成 `-i board.json`。编译成功并检查预览后，运行 `lark-cli whiteboard +update --whiteboard-token <token> --source @diagram.json --input_format raw --idempotent-token <10+字符唯一串> --as user`。
  - Mermaid 直接写入：`lark-cli whiteboard +update --whiteboard-token <token> --input_format mermaid --source @<diagram.mmd> --idempotent-token <10+字符唯一串> --as user`。

### 运行校验脚本并导出预览图检查

1. **上传前跑通双校验**：
   - 运行 `python3 <本 Skill 目录>/scripts/check_feishu.py <xml路径> [board1.json ...]`（局部块校验加 `--fragment`），把全部 `ERROR` 修到 `0`，并对每条 `WARN` 逐条核查确认后处理或说明。
   - 运行 `lark-cli docs +script --command parse --content "@<路径>" --format json`，确认返回 JSON 中 `data.assessment.status == "passed"`。
2. **新建或局部更新飞书文档**：更新已有文档时用 `block_replace` 或 `str_replace` 只改发生变化的文字块，跳过原 `<whiteboard>` 所在 `block_id`。
3. **导出画板预览图逐项检查**：画板写入后，用 `lark-cli whiteboard +export --whiteboard-token <token> --output-type preview --output <本地预览图.jpg> --as user` 导出预览图并用 `Read` 亲自查看下面四项；发现任何一项欠佳，当场修改重传并再次导出确认：
   - **宽高比是否匀称舒展**：若出现高瘦单列长条或大片空白，改为横向分区或双排排布。
   - **重点是否一眼分清**：改造边界与复用模块、旧痛点与新收益有无虚线框和语义色区分。
   - **框内文字能否直接看懂**：补足干瘪节点的关键参数或具体算例值。
   - **样式是否全部生效**：确认边框、底色与连线完整呈现，没有文字溢出、压字或穿框。

---

## 2. 发布本地交互式 HTML

- **基于模板填充页面**：使用 `<本 Skill 目录>/assets/TEMPLATE.html` 生成 `.agent/work/<主题>/design.html`（或 `release.html`、`test-report.html`；发布文档与测试报告按文体替换侧栏眉标与总览三卡片标题）。
- **替换占位槽位与删去空块**：填好标题、三张总览卡片（`{{WHY}}`、`{{HOW}}`、`{{TOP_RISK}}` 内填 `<p>` 或 `<ul>`）和各章内容；模板里的可选占位块（`{{OVERVIEW_DECISION_STRIP}}`、`{{DECISION_INDEX}}`、`{{OVERVIEW_VISUAL}}`、`{{OVERVIEW_EXTRA}}`）按需填入，用不到直接删掉。
- **保持清爽排版**：小节首句结论用 `<blockquote>`，重点短语用 `<mark>` 或 `.badge`，下线项用 `<del>`，长配置用 `<details>` 折叠，简图用内联 SVG；代码块与宽表放 `span-12` 全宽卡片。
- **脚本校验**：运行 `python3 <本 Skill 目录>/scripts/check_html.py <html路径>`，将所有报错修到 `errors=0`。
