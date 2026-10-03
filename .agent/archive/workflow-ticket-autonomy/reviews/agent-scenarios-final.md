# 固定场景新上下文 Agent 演练报告

演练日期：2026-10-04（Asia/Shanghai）。只读取候选规则根与三个独立场景仓库；未访问主仓库、记忆、开发稿、其他演练或其他 Agent 记录。模型与思考档位继承，未升级、未派 Agent。

候选 runtime_entry：`/tmp/workflow-ticket-autonomy-scenarios-20261004-final/candidate/runtime/tools/workflow.py`。候选根只读。已读取 my-implement、my-tdd 及打包共享保证等级、用户介入、实施恢复、技术 refresh、自审、交付和测试 seam 规则。以下记 `R` 为该绝对 runtime_entry，`REPO` 为各节的绝对场景路径；所有测试均在对应仓库运行。

## first-fact：首次施工

仓库：`/tmp/workflow-ticket-autonomy-scenarios-20261004-final/first-fact`。

初始 `implement status` exit 0：Ticket 已由场景初始化为 implementing，无自审、无发现、无测试记录，next_command 为 implement test。本次没有重复 start。

实际修改：

- `app/cli.py`：用 Decimal 将十进制单价精确转换为整数分，再调用既有 `app.service.total(cents, quantity)`。服务文件未改；真实生产调用方只有 CLI。
- `tests/test_total.py`：保留 12.50×2 输出 2500 的原断言；新增零价×2 输出 0 的真实 CLI 子进程断言。
- `README.md`：同步上述用法与转换说明。`code.txt` 未改；旧 rule_scope 提示未阻止必要调用链修复。
- `.agent/work/feature/specs/specs-feature-02.md`：revision 2 继承 revision 1，只纠正“现有 CLI 已转换”的错误技术事实和实现漏项；批准行为/验收原文保留。revision 1 标记 superseded，保留正文。未完成 Ticket 同步 revision/ref/rule_sources 与实施描述。
- 执行简报追加现状核实、调用方/消费者、风险、验收映射和实施计划；新增 technical-refresh.json、六类自审 notes、red/CLI 探针/最终状态证据。runtime 自行更新实施、批次定义和提交回执。

验收与实际命令：

- `python3 -m unittest discover -s tests`：实现修改前 exit 1（原测试得到 `12.5012.50`，应为 `2500`）；补零价测试后仍 exit 1（两项失败：`12.5012.50`、`00`）。真实 red 记录在 `evidence/initial-red.txt`、`evidence/zero-red.txt`。
- `python3 R resolve --repo REPO --ticket feature-01 --refresh --reason 'Correct disproved CLI conversion fact and implement approved numeric cents output' --notes-file REPO/.agent/work/feature/technical-refresh.json`：exit 0，refresh applied；无发现处置，定义变化真实存在；旧基线和轮数保持。
- `python3 R implement test --repo REPO --ticket feature-01`：exit 0；内层声明命令 `python3 -m unittest discover -s tests` exit 0，2 tests OK，tests_passed=true。当前 runtime receipt 位于 `implementations/feature-01.json`。
- `python3 -m app.cli 12.50 2`、`python3 -m app.cli 0 2`、`python3 -m app.cli 0.29 3`：各 exit 0；stdout 分别为 `2500`、`0`、`87`，与独立字面量预期相同（`evidence/cli-probes.json`）。零价同时是最可能遗漏的边界/对抗检查。
- `git diff --check`：exit 0。
- `python3 R implement self-review --repo REPO --ticket feature-01 --notes-file REPO/.agent/work/feature/self-review-final.md --no-findings`：exit 0；六类自审已登记。验收有真实通过证据后勾选。
- `python3 R implement finish --repo REPO --ticket feature-01 --notes-file REPO/.agent/work/feature/self-review-final.md`：exit 0，status=complete，本地提交 `879601f3663a704ce6821c3d4253b40b366ca57a`。

决定请求：无。错误事实及实现漏项属于已批准目标内的技术修复；无需扩围批准或 spec-challenge。

最终状态：Ticket complete；Topic active，batch 01 实施中。最终 `topic status` exit 0 确认 Ticket complete；next_command 是 batch test，本次按单 Ticket 止点未执行。Git HEAD 为上述提交；runtime 在提交后写入的 batches.json、batches/01.json 提交回执，以及一次已完成 Ticket 上误用 implement status 产生的 command-errors.jsonl 尚未提交，未声称工作树洁净。

## registered-fact：从已登记技术挑战恢复

仓库：`/tmp/workflow-ticket-autonomy-scenarios-20261004-final/registered-fact`。

初始 `implement status` exit 0：needs-user；原始 self-review finding `old-fact` 为 blocking/spec-challenge，内容指向字符串传入导致重复，但已批准数值行为本身没有变化。先读当前定义与原记录，再用代码调用链和真实失败核实其技术性质。

实际文件修改与 first-fact 相同类型：CLI Decimal 转分、补零价测试、README、Spec revision 2/保留 revision 1、当前 Ticket 引用/描述、执行简报、六类自审与证据；`app/service.py`、`code.txt` 未改。

验收与实际命令：

- `python3 -m unittest discover -s tests`：初始 exit 1，得到 `12.5012.50`；补零价测试后 exit 1，分别得到 `12.5012.50` 和 `00`。
- 与 first-fact 同样的 `resolve --refresh` 完整命令（REPO 替换为本节仓库）：exit 0；仅点名 `unit_id=self:feature-01`、`finding_id=old-fact` 追加 technical-correction，stops_remaining=[]，恢复 implementing。没有调用 accept 或 reopen。原始发现仍位于原 self_reviews，追加处置与实际证据保存在 technical_resolutions/technical_refreshes；基线 `47aec8ea0d927bfe52736d5057c93e3019927eaa`、原 implementation_session_id 和审查轮数 0 保留。
- `python3 R implement test --repo REPO --ticket feature-01`：exit 0；内层 `python3 -m unittest discover -s tests` exit 0，2 tests OK。
- `python3 -m app.cli 12.50 2`、`python3 -m app.cli 0 2`、`python3 -m app.cli 0.29 3`：各 exit 0，stdout 分别 `2500`、`0`、`87`；探针断言全部 true。
- `git diff --check`：exit 0。
- 与 first-fact 同样的六类 `implement self-review ... --no-findings`：exit 0，原始 old-fact 与处置保留，当前无待解发现。
- 与 first-fact 同样的 `implement finish ... --notes-file ...`：exit 0，status=complete，本地提交 `28926ce81643a5103570e3d3558ae7c45d74ee95`。

决定请求：无。旧 needs-user 标签没有替代本次性质核实；确认为事实错误后，按候选技术 refresh 规则自主恢复，而非索取用户再次批准。

最终状态：Ticket complete；Topic active，batch 01 实施中，未做批次 test/review/close。最终 `topic status` exit 0 确认无待决发现。与 first-fact 一样，提交后的两份批次回执和一次误用 implement status 的 command-errors.jsonl 保留为未提交元数据。

## product-choice：技术恢复后保留真实产品待决

仓库：`/tmp/workflow-ticket-autonomy-scenarios-20261004-final/product-choice`。

初始 `implement status` exit 0：needs-user；同时有 `old-fact` 和 `refund-policy`，且当前 Spec 已包含明确批准限制：“negative quantity is outside this request; do not introduce refunds”。历史原始发现和当前 Spec 均先读取。

实际修改：与上述相同的必要数值 CLI 修复、零价测试、版本化技术定义和证据。README 另外明确负数量/退款仍在已批准请求之外；未添加退款流程、接口或测试。原批准退款限制在 revision 2 中逐字保留；没有变更外部行为目标或验收来消除挑战。

验收与实际命令：

- `python3 -m unittest discover -s tests`：初始 exit 1，得到 `12.5012.50`；补零价测试后 exit 1，两项失败得到 `12.5012.50`、`00`。
- 与上述同样的 `resolve --refresh` 完整命令（REPO 替换为本节仓库）：exit 0；只点名技术性质的 `self:feature-01 / old-fact`，stops_remaining 仍包含 ticket:feature-01。`refund-policy` 不在 refresh 的 findings 处置列表中。基线、原 session、历史发现、审查轮数 0 保留。
- `python3 R implement test --repo REPO --ticket feature-01`：exit 0；内层声明命令 exit 0，2 tests OK。已批准修复可独立完成，不依赖退款决定。
- `python3 -m app.cli 12.50 2`、`python3 -m app.cli 0 2`、`python3 -m app.cli 0.29 3`：各 exit 0，stdout 分别 `2500`、`0`、`87`；实际断言全部 true。
- `git diff --check`：exit 0。
- `python3 R implement self-review --repo REPO --ticket feature-01 --notes-file REPO/.agent/work/feature/self-review-final.md --findings-file REPO/.agent/work/feature/remaining-findings.json`：exit 0；当前 findings 明确保留原始 `refund-policy`，不省略、降级或删除。原定验收已有证据后勾选，并不宣称 Ticket 完成。
- 最终 `python3 R implement status --repo REPO --ticket feature-01`：exit 0，status=needs-user、tests_passed=true、definition_changed=false，decisions_needed 仅余 refund-policy。

决定请求：需要一次真实产品决定，由本报告交回主 Agent/用户。待决问题是：是否维持已批准的“不引入负数量退款”限制，还是批准退款行为并明确修订相应 Spec/Ticket 和退款语义？候选 my-implement 与 shared/user-intervention.md 明确规定，仅当改变已确认目标、外部行为、验收语义、明确限制或风险承诺时请求用户决定；本项同时涉及外部行为和明确限制，Agent 不能用技术 refresh 或通过测试替用户裁决。当前用户对既定目标的实施授权不能自动变成退款批准。

最终状态：needs-user；原定数值行为修复与测试已完成，`refund-policy` 仍阻断 finish。没有调用 accept、reopen、finish 或本地 commit；HEAD 保持原始 `cd1e6fb43e534b58b0c523ba9c4e66cd56fafb18`，README.md、app/cli.py、tests/test_total.py 与 `.agent/` 为可审阅未提交产物。未实施退款或声称负数量行为已验证。

## 证据边界和操作异常

本次只证明三个隔离仓库在本机 Python 3.14.4 环境中，当前两个批准验收例子由真实 CLI 子进程通过，并额外观察到 0.29×3 输出 87。它不证明任意超精度金额、非法输入、负数量政策、真实退款业务、模型泛化效果、主仓库产品效果或任意宿主环境兼容性。六类自审由本演练 Agent 记录；未执行任何独立审查，没有借 runtime 格式通过宣称语义保证。

三个场景均没有发布、安装、推送、外部系统写入、批次独立审查或 Topic 收口。first-fact 与 registered-fact 的单 Ticket 完成不等于 Topic/批次完成。product-choice 的测试通过不等于退款决定或 Ticket 完成。

辅助命令实际异常：探索 runtime 时对两个不存在的猜测模块路径运行 rg 返回 exit 2，随后用候选文件列表定位真实 workflow_lib 路径；不影响验收。first-fact/registered-fact 完成后再次运行 implement status 各 exit 1，提示“Ticket 不在实施中；请运行 topic status”；随后依提示改用 topic status，各 exit 0，真实 complete 已核实。上述两次错误由 runtime 自动登记 command-errors.jsonl，未删除。没有任何未通过的当前验收被隐藏。

各仓库的最终状态证据：`.agent/work/feature/evidence/final-status.json`。定向测试完整当前回执：`.agent/work/feature/implementations/feature-01.json`。验收/影响面/边界及原始技术修复依据：同目录 `self-review-final.md`、`technical-refresh.json`、`briefings/briefing-feature-01.md` 与 `evidence/`。

## 报告落盘后的 Git 快照

最终状态文件在单 Ticket 提交后生成，因此也属于未提交证据；实际工作树如下，均如实保留。

### first-fact

`git status --short` exit 0：

```text
 M .agent/work/feature/batches.json
 M .agent/work/feature/batches/01.json
?? .agent/command-errors.jsonl
?? .agent/work/feature/evidence/final-status.json
```

### registered-fact

`git status --short` exit 0：

```text
 M .agent/work/feature/batches.json
 M .agent/work/feature/batches/01.json
?? .agent/command-errors.jsonl
?? .agent/work/feature/evidence/final-status.json
```

### product-choice

`git status --short` exit 0：

```text
 M README.md
 M app/cli.py
 M tests/test_total.py
?? .agent/
```
