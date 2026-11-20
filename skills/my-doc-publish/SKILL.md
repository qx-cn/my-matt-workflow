---
name: my-doc-publish
description: 用户要求把文档发布到飞书、更新飞书云文档与画板，或渲染为本地交互式 HTML 时使用。将定稿 Markdown 排版为留白清晰、重点突出的飞书文档或本地 HTML，并运行脚本校验版式与画板。
disable-model-invocation: true
---

# 文档排版与发布（飞书 / 本地 HTML）

本 Skill 把已经写通顺的 Markdown 定稿（如 `design.md`、`release.md`、`test-report.md`）排成好读的**飞书云文档（含画板）**或**本地交互式 HTML**。

- **没有干净定稿先别硬排**：如果手头只有零散需求讨论而还没有写通顺的 Markdown 定稿，先读取同级目录的 `my-tech-design/SKILL.md` 写出干净的 `design.md`，再做排版发布。
- **保留人话与样例，本地与远端对齐**：排版的目的是用卡片、表格、代码块、画板和重点颜色帮读者更快看懂，不要为了省行数把主语、宾语或文件样例砍掉。如果用户对着飞书文档改了业务规则、状态或契约，按全局规范同步更新同目录的本地 `design.md` / `design.xml`。没指定发飞书还是出 HTML 时先问一句。

---

## 1. 发布飞书云文档与画板

调用 `lark-doc`、`lark-whiteboard`、`lark-wiki` 技能操作，做到留白清楚、重点突出、不过度涂色：

- **章节与节内双重留白（防页面密密麻麻）**：
  - 文首总览框和第 1 个 `<h1 seq="auto">` 之间，以及第 2 个起每个 `<h1 seq="auto">` 上方，统一加 `<p></p><hr/>`（空行加分割线）。
  - 同一个 `<h1/>` 下面第 2 个起每个 `<h2 seq="auto">` 上方，以及**同一小节内“文字列表与下方表格/代码块”或“连续两张大表”之间**，插入空行 `<p></p>` 拉开垂直呼吸间距。
  - **拒绝大胖列表与连堆文字块**：单条列表超过两行半时，拆成“1 句短主干 + 缩进短子列表”；遇到正反两难或二元分类（如“现网两种走不通的做法”“允许跳过的任务 vs 报错阻断的任务”），优先排成 `<grid>` 左右双栏浅色卡片；遇到 3 种以上操作分支的结果说明，排成 3 列场景小表。
- **块级与行内重点格式（按需选用，克制灰框噪点）**：
  - **总览与小节结论**：文首总览用浅蓝 `<callout emoji="📌" background-color="light-blue" border-color="blue">`（量化报告下面可跟一行 3 栏指标卡）；每个二级小节开头的 1 句核心结论用竖线引用块 `<blockquote><p>...</p></blockquote>`，别整段加粗糊成黑块。
  - **双栏对比与红线警示**：两边各 2 到 4 条短句的对称关系可用 `<grid>` 双栏 `<callout>` 卡片（`emoji` 用单码点图标 `📌`、`✅`、`🚫`、`💡`、`📊`、`🚀`、`🔧`、`⏳`，别用 `⚠️`/`🛠️`）；会导致资损或回滚失败的硬禁令用浅黄或浅红 `🚨` `<callout>` 单独标出。
  - **白底正文重点与行内 `<code>` 降噪**：在**白底正文、结论块和列表**里，挑最核心的结论短语加 `<span background-color="light-*" text-color="*"><b>短语</b></span>` 胶囊高亮（别在同色 `<callout>` 里重复叠涂）；表格或列表里可用无底彩字 `<span text-color="green|red|purple|blue"><b>词</b></span>` 标允许项、报错码或终态。**克制使用 `<code>`**：飞书中每个 `<code>` 都是灰底方框，普通英文动作词与大类名称（如 Submit、Approve、Reject、DRAFT、FINAL）直接用正文字体，`<code>` 只留给真实物理表字段名、文件名、配置键与错误码，防止满页灰框晃眼；中文正文不用斜体 `<em>/<i>` 和非链接下划线 `<u>`。
  - **清爽表格、外提长命令与 `<checkbox>` 硬语法**：
    - 飞书正文宽约 `820px`，普通说明表控制在 **3 至 4 列**（最多 5 列，相同规则合并同行，单格文字精炼在 1 至 2 行内，避免列太窄竖折成五六行豆腐块）；**完整长 CLI 命令（超 68 字符）提取到表外全宽 `<pre lang="bash">` 代码块**，表格单元格内只写短子命令名（如 `执行 -command freeze`）。
    - **`<checkbox>` 内严禁套 `<p>`**：必须直接写成 `<checkbox done="false">核查内容（行内可带 &lt;code&gt;）</checkbox>`；若写成 `<checkbox><p>...</p></checkbox>`，飞书会把勾选框与文字拆成上下两行错位。
    - 顶层以唯一 `<title>` 开头，`<ol>` 不写 `seq` 属性，`<callout>` 和 `<grid>` 里不塞 `<pre>` 或 `<table>`，不用 `<details>`，超 18 行的辅助长配置加 `folded="true"`。
- **画板选型与防撞框**：
  - **跨服务先后调用画时序图**：写 `.mmd`（`sequenceDiagram`），用 `npx -y @larksuite/whiteboard-cli@^0.2.13 -i diagram.mmd --to openapi --format json | lark-cli whiteboard +update ... --input_format raw` 编译写入飞书画板。
  - **双维正交图（如横向人工推进 × 纵向系统冻结、多阶段泳道）**：用 Flex 布局，外层 `vertical` 框里用首个独立 `type: "text"` 子节点写分区标题（别写在 `frame.text` 上），内层 `horizontal` 行放节点（连线方向 `gap >= 40`），根级 `connector` 显式写明 `fromAnchor` 和 `toAnchor`（横向 `"right" -> "left"`，纵向 `"bottom" -> "top"`），连线标签用 `label`（配 `labelFillColor: "#FFFFFF"`，勿写 `text`）。
  - **一般拓扑与分支判定图**：用 `layout: "dagre"`（`ranksep >= 160`、`nodesep >= 60`，连线写在 `layoutOptions.edges` 里），子分区用 `isCluster: true` 虚线框圈出；横向单链不超过 4 级（步数多时分上下两行阶段框叠放），判定分支把判断节点放最前、报错节点独立终止。
  - **节点尺寸与配色**：业务 `rect` 设 `height: "fit-content"`、`width >= 210`，框内最多 2 行短字、零内部黑话；同性质节点同色（蓝常规、黄检查/锁定、紫核心保护、绿终态/放行、红阻断/报错），图下紧跟居中灰色图注。
- **脚本校验与导出复核（必跑）**：
  1. 上传前运行：
     `python3 <本 Skill 目录>/scripts/check_feishu.py <xml路径> [board1.json ...]`
     以及 `lark-cli docs +script --command parse --content "@<路径>" --format json`，把所有 `ERROR` 修到 `0` 再上传。
  2. 新建或局部更新飞书文档（目录已有团队近期方案时可先读 1 篇对齐深浅；更新已有文档用 `block_replace` / `str_replace` 只改变动块并保留原 `<whiteboard token="..."/>`，别用 `overwrite` 清空画板和评论）。
  3. 画板写入后，用 `lark-cli whiteboard +export --output-type preview` 导出预览图并亲自 `Read` 检查：确认文字没压框、状态箭头没漏画，有问题调完重传再看一遍。

---

## 2. 发布本地交互式 HTML

- 用 `<本 Skill 目录>/assets/TEMPLATE.html` 生成 `.agent/work/<主题>/design.html`（或 `release.html`、`test-report.html`）：填好标题、三张总览卡片（`{{WHY}}`、`{{HOW}}`、`{{TOP_RISK}}` 填 `<p>` 或 `<ul>`）与各章内容，删掉没用到的占位块。小节首句结论用 `<blockquote>`，重点短语用 `<mark>` 或 `.badge`，下线项用 `<del>`，长配置用 `<details>` 折叠，简图用内联 SVG；代码块与宽表放 `span-12` 全宽卡片。
- 运行 `python3 <本 Skill 目录>/scripts/check_html.py <html路径>`，修完所有报错至 `errors=0`。
