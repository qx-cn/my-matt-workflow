Handoff-Status: ready
Reader-Reconstruction: pass

# workflow-simplification：05–07 批次后的新会话交接

生成阶段：2026-10-01，Asia/Shanghai；批次交付已闭合，下一批实施尚未授权选择。工作目录为本仓库根目录，本文路径均相对该根目录；安装 runtime 路径另行注明。

## 下一会话目标与第一步

承接已批准 Spec r1 的后续工作。05–07 和其补偿16已经完成，不再重开；首先读取本文的 Spec、批次交付和 Ticket08，只读确认依赖、验收及当前状态，然后向用户列出下一批候选并取得范围选择。当前 my-handoff 调用只要求交接，不能把它或“continue”解释为授权挑选08–14。确定范围后才创建新的固定 scope 并用 `$my-implement` 认领，保留逐 Ticket 自审、批末独立审核及有界修复方式。

来源：user-confirmed，本会话用户明确选择“05–07：先完成核心闭环”，并要求 auto、单Ticket自审、批末独立审核、修复至无有效问题；repository，`handoffs/batch-workflow-simplification-05-07.md` 和 `handoffs/scope-workflow-simplification-05-07.json`（均相对 `.agent/work/workflow-simplification/`）。Ticket08仅为首个可考虑候选，本次只读 `validate-ticket <08路径>` exit0/status ready，不代表已经认领。

## 已确认决定与边界

- 当前构建 profile 为 schema1、standard/local/shared，full-auto（automatic/approved-plan/autonomous、commit allow），外部写入 confirm、humanizer deny；以 `.agent/matt-workflow.md` 实际键为准。旧授权文档的 single-ticket 描述是早期历史，后来的05–07批次契约及当前profile是有效状态。
- 用户授权本会话内符合 Topic 目标的本地开发自动推进，原始凭据见 `handoffs/authorization-workflow-simplification-20260930.md`。新会话应遵守已确定的 scope；若扩大下一批范围，先取得用户选择。没有 push、MR、安装或其他项目迁移授权；不要升级模型、reasoning 或服务档位。
- 实施使用**已安装旧 runtime**：从 `/Users/sherly/.codex/my-matt-workflow/install-state.json` 解析 `runtime_entry`，当前为 `/Users/sherly/.codex/my-matt-workflow/runtime/20260929-234249/tools/workflow.py`。仓库 `tools/workflow.py` 是正在构建的新产品，不是当前 schema1项目的施工控制入口；不要对本仓库工作历史运行 migrate。
- 两个预算不得混淆：施工 runtime full-auto 最多5轮修复，连续同根因需正式停止；新产品 Spec M4 上限4轮审查。05–07批次已用2轮独立审查、1轮修复并收敛，不因补偿Ticket或派新会话重置同一审计预算。
- 已完成 Ticket 是历史事实；后续真实 finding 用新的补偿Ticket引用原owner，不能重开05–07/16、篡改原receipt或改原固定scope。08–14均未包含在已完成批次中；08迁移仅在fixtures/临时仓库验证，不转换本仓库历史或用户其他项目。

以上决策来源为本会话用户明确指令及当前profile/批次契约；范围外不通过模式推断授权。

## 当前状态与证据

| 状态面 | 已核验事实与限制 |
|---|---|
| 工作区 | branch `workflow-simplification`； tracked修改为空。存在未跟踪 `.agent/.matt-workflow.md.swp`、supplemental-snapshots、05/06/07/15/16的锁及snapshot所有权目录；保留，不手动清理。本交接为新未跟踪文件，尚未提交。 |
| Local commit | HEAD `203747f7a98ab8b8e4437ecc676df5b7ee148688`：补偿16及两轮独立审核证据。05=`6581fbc`，06=`c0b0c0a`，07=`ad6a89c`；批次基线=`9e24d381a00c51d0df286ccb7ac89f6083963b4f`（补偿15）。 |
| Remote | unknown：本批未推送，本次未fetch或查询远端，不推断同步/分支/PR状态。 |
| Release | unknown：本批未build/deploy；release与203747f的匹配性未核验。 |
| Codex安装宿主 | install-state记录release `20260929-234249`及上述runtime_entry；文件存在。本批未安装，当前源码/安装一致性unknown，未运行doctor。 |
| Claude安装宿主 | `/Users/sherly/.claude/my-matt-workflow/install-state.json`记录release `20260929-234249`；本批未安装，源码/安装一致性unknown，未运行doctor。 |

来源：repository/execution，本次读取git status/log、install-state和下列运行时证据。remote/release/currentness未知不阻碍只读下一范围讨论；如将来请求发布/安装，另查对应状态与doctor，不沿用本表推断。

Ticket01–07、补偿15/16当前均complete；05/06/07/16的runs均phase complete、submission outcome completed，runtime实施关闭成功。原批次scope及补偿scope均next-ticket返回approved-scope-complete。Topic本身仍有08–14待实施，**没有完成/归档整个Topic**。08依赖07，当前只读校验ready。来源：Ticket frontmatter、runs和交付记录。

05–07各完成时声明 `python3 -m unittest discover -s tests` 均有exit0的test receipt和冻结增强self receipt。补偿16同一argv完整测试exit0；code_content_id `67b82f9cccc69e8ab952edd7012b59740f82fcedf9d6026f9157ea1b28551cec`，test evidence `54d0ce8943d6bc08d123abc6e5c544f82792c33c86ec251e9cbf88b509b73770`，self review evidence `44af26e33169ea02e68ebc7b890a7002242246791da34e243b1afd698520abdb`。全量输出只存digest，不能宣称未保存的测试总数。

批次独立首轮 Code发现1个P1：4轮review开启未submit、预算耗尽进入needs-user后accept在metric读取不存在的reviewer崩溃，Ticket残留complete、branch不能归档。补偿16通过受管finding→repair-plan→设计自审→red/green→全量测试→增强自审修复共享metric seam：未知来源null，Ticket副作用前计算度量。新独立session round2 Code/Spec pass、findings=[]；27项相关tests及旧基线负对照提供修复实证。两轮冻结核验均status match/released true。独立相关27 tests与施工全量测试是不同证据，不能混用。原P1已经解决，无已知未解决finding；未验证其他Python版本或真实安装效果。

## 必读产物与定位

以下均从 `.agent/work/workflow-simplification/` 起算；只引用，不复制正文。

- Spec唯一要求权威：`specs/specs-workflow-simplification.md`，revision1。测试seam：仓库 `resources/testing-seams.md`。
- 当前批次总记录：`deliveries/deliveries-workflow-simplification-batch-05-07.md`；审计连续账：`reviews/review-log-batch-05-07.md`。
- 前序交接：`handoffs/handoffs-workflow-simplification-07.md`、`handoffs/handoff-workflow-simplification-16.md`；更早基础补偿见 `handoffs/handoffs-workflow-simplification-15-evidence-integrity.md`。不把逐Ticket自审当作独立审核。
- 原始独立报告及结果：`reviews/review-batch-05-07-independent-round-1.md`、`.json`；修复复审：`reviews/review-batch-05-07-independent-round-2.md`、`.json`。
- 冻结核验：`reviews/independent-evidence/batch-05-07/finalize.json`、`reviews/independent-evidence/batch-05-07-round2/finalize.json`。原owned临时snapshot已释放，不能读取报告中的已释放路径；round1原始字节保存在tar，按 `reviews/independent-evidence/batch-05-07/retained-README.md` 的wrapper重跑。旧复现driver exit0表示断言原失败，不表示当前accept通过。
- 16验收/作用域：`tickets/tickets-workflow-simplification-16.md`；journal：`runs/run-workflow-simplification-16-spec-r1.json`；receipt：同名 `.evidence/` 中上述test/self的 `<evidence_id>.json`。05–07同样按编号读取，不复制旧result到新session。
- 下一个候选：`tickets/tickets-workflow-simplification-08.md`，后续owner逐个读取09–14，先核对依赖及未完成验收。确认新批次后创建全新scope；现有 `handoffs/scope-workflow-simplification-05-07.json`、`handoffs/scope-workflow-simplification-16.json` 仅供历史证据，不追加08。

## 建议手动调用的 Skills

选择下一范围后用 `$my-implement`；恢复前读取对应SKILL及installation runtime help/适用profile。若用户要重审，调用 `$my-code-review` 并明确新冻结审查范围；有真实finding时遵守受管repair-plan。只有Spec语义失效且用户同意改需求时才用 `$my-to-spec`/`$my-to-tickets`，不因这份交接重新生成已批准Spec或历史Tickets。下一阶段交接用 `$my-handoff` 新增文件。

## 最终校验记录

四gate均pass；独立fresh-context审阅者 `handoff_fresh_reader_20261001` 未参与撰写，仅凭本文重建后执行只读验证。已确认目标/第一步为只读范围准备并取得下一批选择，08 ready不是认领授权；已核对引用路径、5个Commit、profile、各Ticket/journal、16当前三文件SHA与receipt、两轮independent result/finalize，以及两宿主install-state。完整原始证据仅引用，未把测试总数或宿主一致性推成已知。

- 来源账本：pass，承重决定/当前状态/验证均有来源，未知状态公开保留。
- 内部一致性：pass，范围、预算、历史与有效策略、施工/产品runtime和状态面一致。
- 读者重建：pass，独立上下文完整恢复目标、范围外、决定、当前状态、风险、证据和第一步。
- 事实正确性：pass，路径/Commit/真实receipt/current-code匹配，无承重断链。

此ready仅表示交接可供下一会话恢复上下文，不授权实施新批次。本文新增保存，未自动commit；历史交接不覆盖，工作区其他未跟踪metadata不清理。
