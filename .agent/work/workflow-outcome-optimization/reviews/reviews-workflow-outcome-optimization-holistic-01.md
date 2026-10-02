# Topic 整体 review 与优化效果检查

审查结论：**Request changes。优化部分有效，但完成可靠性的关键目标尚未完全实现。** 本轮确认 **2 个 P1、1 个 P2**；另有 1 个 P3 文字歧义和 1 项非阻断成本建议。两条 P1 都能通过公共 CLI 复现错误收口，主审已独立复跑确认。它们是旧漏洞在本次优化范围内仍未补齐的路径；P2 是新增恢复机制的跨入口不一致。

审查对象为 `608b72b4783e9117b9c0f68636b158fc3958f1d9`，对照施工前 `7947cb28e37512ab52a0c87c2cfd736bc3205c25`，采用 revision 2 Spec。三个新上下文并行审查 runtime、安装升级、指令与能力机制；主审核对证据、交叉复现与汇总。没有用被审 workflow 的 Skill 组织或批准本次工作。

## 需要修复的发现

### R1 / P1：旧活动批次漏掉已完成 Ticket 的未解决自审发现

位置：`tools/workflow_lib/branch_review.py:108–110`；相关 `batches.py:312–315`、`:369–401`。

原文过滤条件：`if f.get('disposition')=='fix-in-batch'`。共享 `pending_self_findings()` 能识别 blocking、spec-challenge 和待批次处理的 advisory，但消费者只带走第三种。旧 runtime 曾允许含 blocking 或 spec-challenge 的 Ticket finish；如果升级时该 Ticket 已 complete、所在 batch 仍活动，新的 Ticket finish 门禁不会再次执行，批次路径又遗漏旧发现。

实际复现使用基线 CLI 创建旧记录，再切换候选 CLI 重跑批次测试和审查材料。两种旧记录均得到 `decisions_needed=[]`、`self_findings=[]`，普通 `batch close` 返回“已收口”；原始发现仍保存且未处置。测试用 review pass 是合成门禁输入，仅证明程序允许收口，不代表真实审查者认可业务正确。

影响：AC02/18/19 的活动记录恢复保证未闭合。这不要求重开合法已完成历史；需要在尚未完成的批次继续处理旧 runtime 漏过的发现。

建议：批次状态、审查材料与 close 共用完整的未解发现评估；blocking 要有真实修复证据，spec-challenge 要有对应裁决。保留原 Ticket 历史，可通过活动批次的明确处置或补偿记录承接，不能靠普通 pass 或字段过滤消除。

### R2 / P1：业务逻辑中的 ModuleNotFoundError 仍可能被当成纯环境缺口

位置：`tools/workflow_lib/evidence.py:132–137`，特别是 `module_missing_diagnostic(diagnostic)`；相关 `evidence.py:110–119,173–188`、`batches.py:248–255`。

当前分支把完整 `ModuleNotFoundError` traceback 当成环境不可用证明。然而异常类型不能证明错误发生在启动之前；`execution_observed()` 未看见特定测试框架标记，也不能证明普通脚本没有执行被测逻辑。

实际复现：基线缺测试依赖；当前验证脚本调用 `selected_plugin()`，因返回拼错的模块名而在真实 `importlib.import_module()` 中失败。执行标记证明已进入业务验证，traceback 来自 Python，没有伪造日志。候选同时记录 `exit_code=1`、`unavailable=true`、`execution_observed=false`、`new_failures=[]`，只披露 unverified，随后普通 close 成功。主审复跑结果一致。

影响：AC01/18/19 仍存在“基线不可运行、当前实际失败，却允许收口”的反例。新版缩小了旧关键词误判范围，但没有消除这个根因。

建议：只有能证明为纯启动阶段的事实才允许环境缺口短路；无法判断的非零退出保持失败，不能默认不可用。可采用明确的启动检查或受支持 runner 的结构化证据，不继续无限堆叠异常文本猜测；同时使受影响的旧分类缓存失效并重评。

### R3 / P2：旧 branch 恢复时 status 推荐了必然失败的动作

位置：`tools/workflow_lib/topic_service.py:333–344`；相关 `branch_review.py:49–51` 及 resolve 的状态检查。

旧非 batch 多 Ticket 流程中，当前审查已经 pass，但因体积超过旧阈值被标 needs-user。候选 `topic status` 仍建议 `resolve --branch --accept`；实际执行时 load 先解除几何停止、写成 reviewing，随后 accept 因状态已不是 needs-user 而退出 1。再次查询才返回 topic complete。

主审复跑得到同样的 `branch accept 只接受 needs-user`。虽然可继续恢复，它引入了无必要裁决提示和失败命令，违反 AC03/09/18/19 的共同状态/下一步要求。

建议：status 与 mutation 使用同一恢复后的有效状态视图，保留旧停止与恢复依据，直接输出当前可执行步骤。

## 优化效果：已经证明与尚未证明

| 范围 | 当前证据支持的判断 | 边界 |
|---|---|---|
| 安装升级 | 同一 fixture 完整验包 4→1 次，临时源码打包 1→0，验证用整树投影操作 15→0，copytree 35→0；suite gate 仍为 1。本轮复跑一致。 | 该计数 fixture 将 suite 替换为计数器；不能拿局部耗时冒充真实工程总提速。 |
| 安装实际阶段耗时 | 独立完整临时发布包、真实 hash/verify/install 小样本中，verify 约 0.705–0.734s→0.315–0.329s，同包安装约 2.691–2.732s→0.624–0.721s，候选真实返回 current。 | 两版包内容不同、顺序固定、样本小；不是线上宿主数据或统计效果试验。 |
| Runtime | 执行事实、冻结字节核验确有共享消费者；各 scope 的成功策略仍保留。新工作自审门禁、末票路由、几何误停等有定向正例。 | R1/R3 表明入口仍未完全共用判断；R2 表明共享的分类本身仍可错误。不能确认可靠完成目标已全部满足。 |
| 指令与方法 | triage 缺 Spec 路由、阶段止点、授权复用、多对多验收、独立存储验证、排障按需、静态与执行证据区分更明确。 | 这是文本追读与机械契约证据，不是模型实际遵循率。 |
| 上下文与维护成本 | 主链全部可选 Markdown 并集 33,919→38,356 字符，约增 13.1%；tools Python 8,822→9,540 行，增 718 行。两项均本轮重算。 | 并集不是一次任务常载；行数不等于复杂度。但不能称整体文本或 runtime 体量已缩小，新增保护有成本。 |

安装与指令子审查未确认新的 P1/P2。以下保留机制做得正确：同版安装仍核验真实目标，验证复用仍检查内容漂移；安装独立事务、回滚和路径保护未被性能短路省略；需求来源与承重假设、跨 Ticket 用户结果、独立 oracle 和原故障验证要求得到保留。

七项能力的结论分别是：完成率与准确率有防错机制改善但仍受 R1/R2 影响；需求理解、写作、代码实现、Bug 排查具有更合适的规则支撑，但实际能力变化未知；自动化的安装成本下降已获工程证据，端到端正确无人干预完成率未知。**本轮没有模型效果对照数据，不能声称七项能力或一次做对率已经提高。**

## 非阻断观察

- **O1 / P3**：`skills/my-ask-matt/SKILL.md:22–28` 要求“首个成立项”，却把“信息有用且空间够→继续”放在“完成止点→交付”之前。已完成且空间够时局部选择会错。共享阶段/授权规则可以阻止越权，因此不据此认定实际越阶段；将继续限定为当前阶段仍有必要工作，或前置止点判断即可。
- **O2 / advisory**：`resources/artifact-finalization.md:3,17,29` 保留承重文档的独立读者重建成本。它不是本次新增缺陷，也不足以证明违反 Spec。后续观察是否能复用同轮独立审查的读者证据、是否真的发现额外问题，再决定触发条件；不为减步骤先删除保护。

## 证据与审查边界

最终冻结清单为 281 文件，SHA256 `0f7c4296a473ec1df31e3e61f87d8a861aa2ef6eaaa904a46c4c85ae4ecd3eb1`；三名 reviewer 开始/结束均核验匹配，主审也核对当前源码一致。完整源码包的 1,569 个 manifest 文件及 mode 均匹配。旧全量测试 338 tests / exit 0 的日志摘要与当前源码清单对应，但本轮没有重跑全量 suite。

本轮新运行：主审文本/组合/资源/打包 48 tests 通过；安装 reviewer 25+7 个定向测试通过；runtime reviewer 4 个正例测试通过。不同组存在重叠，不相加成唯一测试覆盖数。两条 P1 的三个场景和 P2 场景由 reviewer 构造、主审独立复跑成功；正例绿色不能消解这些反例。

普通工程审查材料如下，不作为产品 runtime 自签回执：

- [runtime 独立报告](holistic-review-01/outcome-holistic-runtime.md)
- [安装独立报告](holistic-review-01/outcome-holistic-install.md)
- [指令与七项能力独立报告](holistic-review-01/outcome-holistic-instructions.md)
- [主审核验与优化计数](holistic-review-01/root-verification.json)
- [主审 P1 复现结果](holistic-review-01/outcome-holistic-root-repro.json) / [脚本](holistic-review-01/outcome-holistic-root-repro.py)
- [主审 P2 复现结果](holistic-review-01/outcome-holistic-root-geometry.json) / [脚本](holistic-review-01/outcome-holistic-root-geometry.py)
- [审查来源及文件摘要](holistic-review-01/evidence-manifest.json)

探针中的 BASE/FINAL 指向本轮两份 `/tmp` 冻结树；跨环境重放需用上述两个 commit 重建目录或修改路径。反例的仓库、业务逻辑及 review pass 均为临时合成夹具，只用于验证公开 CLI 合同；没有操作真实 Topic/宿主或实际业务项目。

之前 17 个已修问题与限定复审报告保留原时点结论。本次是新的整体发现，不能被旧报告的“0 blocking”覆盖，也不回写已完成 Ticket、Spec 或旧验收记录。

## 建议下一步

先通过明确的补偿修复处理 R1/R2/R3，并将这些公共 CLI 反例纳入回归；随后对修复差异做独立复审，核对当前有效源码的必要完整测试。不要再以只有 unittest loader 的变体覆盖来代表所有 runner，也不要只测新建 Ticket 而漏掉旧活动 batch。

再按已有 [能力验证计划](../evidence/outcome-evaluation-runbook.md) 做小规模匹配任务：局部 Bug、模糊需求、持久化与跨票接线、缺环境恢复、面向不同读者的文档、间歇故障及授权自动化。固定模型/预算/起始环境，分别报告首次正确、最终正确、错误完成声明、无效介入和成本；要判断整个包的净收益时加入无本包条件。当前证据不足以直接扩写通用规则或宣布全面能力提升。

本次只新增审查报告与证据，未修改生产实现、发布或安装。
