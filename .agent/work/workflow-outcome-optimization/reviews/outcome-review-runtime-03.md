# Runtime 第二轮独立修复复审 03

结论：**指定范围内 blocking 0；advisory 1。R1-startup 原有“纯 loader 缺依赖基线 → 同 loader 身份的真实顶层 AssertionError → 普通 close exit 0”反例已阻断。** default 与 `-v` 的真实当前 AssertionError 均为 `unavailable=false`，进入 `new_failures`，普通 close exit 1。旧记录缺少新字段时也重新判断并拒绝。已接受 branch 的 human 旧 stop 原因已标为历史，与 JSON 当前裁决状态一致。

本报告是普通工程独立复审。未参与施工；作者新增测试只用于理解修复意图与临时仓库 fixture 格式，未运行作者测试、未把作者测试/总结当作独立结果。判断依据为自己编写的公共 CLI 黑盒探针、实际 runner stdout/stderr/exit、持久化 receipt，以及冻结源码调用路径。

## 源身份与隔离

- 唯一源码：`/tmp/outcome-review-final-04`（物理路径 `/private/tmp/outcome-review-final-04`）。已阅读其 `prior-findings.md` 与完整 `repair.patch`。
- `source-manifest.json` SHA256：`feaed39c6e610ffd61566f381b404a7d36d49f69b0cbb4190dcc1abda55eb180`。
- 开始与结束：281 个唯一 manifest 条目，全部文件 SHA256 匹配；整个冻结树 284 个文件，清单外仅 manifest、prior-findings、repair.patch。结束新增/删除/字节变化均为空；未写源码、未生成源码缓存。
- shell 执行均 `login:false`，源码读取限定该绝对冻结目录；Python 及所有 Python 子 runner 使用 `-B`，并设置 `PYTHONDONTWRITEBYTECODE=1`。
- 所有写入仅 `/tmp` 的自建 Git fixture、探针、原始证据及报告。未访问主仓生产源码、未变更真实 Topic/host、未安装部署、未提交/push 主仓。
- 被测公共 CLI 只作为 fixture 被测对象执行 `setup/implement/batch/topic`；没有使用其 skill、CLI runtime 为本次施工登记、签验收或生成本报告。fixture 中结构合法的 review pass/accept 是合成输入，仅用来到达门禁与展示状态；其中 provenance 字段不代表真实 reviewer 对 toy 产品的独立认证，也不承担本报告的验收证据。

身份原始凭证：[开始核验](/tmp/outcome-runtime-03-start.json)、[结束核验](/tmp/outcome-runtime-03-end.json)。开始无 `python` 命令，首次哈希调用 exit 127 后改用 `python3 -B` 成功；没有因该命令产生源码写入。

## Blocking

**无。** 以下结果只支持指定反例和必要相关边界，不是全库正确性或发布验收。

### R1-startup：同 loader 身份的真实 AssertionError

公共 runner：`python3 -B -m unittest discover -s suite`，第二组加 `-v`。基线唯一模块 `suite/test_behavior.py` 为 `import runtime03_missing_dependency`，没有实际可执行测试；当前同模块改为 `assert 1 == 2, 'runtime03 actual top-level assertion'`，提交后公共 `batch test` 真实运行。

两轮解析出的失败身份完全相同：`test_behavior (unittest.loader._FailedTest.test_behavior)`。因此成功阻断不能归因于测试名变化。当前 stdout/stderr 明确含 `AssertionError: runtime03 actual top-level assertion`，runner exit 1；没有用缺依赖再次运行来替代这条真实失败。

| 路径 | 基线 exit / unavailable / comparison_eligible | 当前 exit / unavailable | 当前 new_failures comparison | 当前 known 数 | close exit | 缺新字段旧 receipt close exit |
|---|---|---|---|---|---|---|
| loader-default | 1 / `true` / `false` | 1 / `false` | `baseline-unavailable` | 0 | 1 | 1 |
| loader-v | 1 / `false` / `false` | 1 / `false` | `baseline-identity-unverifiable` | 0 | 1 | 1 |

当前两组 `new_failures` 各含上述 loader 身份，`unverified` 均含 runner；batch/topic status 均披露基线缺口。`batch test` 的外层 CLI exit 0 只是观察与比较结果已写出；报告中 runner exit 1、非空 new_failures 和 close exit 1 才是失败门禁事实。两组 close 的实际 stderr 同为：`全量测试新增失败或记录过期；请 batch test`，而不是未提交或缺 review 等其他前置条件。default 在注入 AssertionError 前已构造合法 fixture review pass；`-v` 纯缺依赖阶段保守拒绝 review，详见 advisory。

源码解释：[evidence.py:23](/tmp/outcome-review-final-04/tools/workflow_lib/evidence.py:23) 区分仅 loader 身份与真实测试执行；[evidence.py:28](/tmp/outcome-review-final-04/tools/workflow_lib/evidence.py:28) 只窄识别 default 全 loader 缺依赖包装；[evidence.py:79](/tmp/outcome-review-final-04/tools/workflow_lib/evidence.py:79) 不把当前 AssertionError 标为 unavailable。[batches.py:233](/tmp/outcome-review-final-04/tools/workflow_lib/batches.py:233) 对不可比较基线保留缺口；[batches.py:249](/tmp/outcome-review-final-04/tools/workflow_lib/batches.py:249) 把可观察当前失败列为新增，不按该 loader 名称交集放入 known。

### 旧记录无 newfield 与恢复

在自有 fixture 中保留原始输出、退出码、环境、内容身份和失败身份，删除基线与当前 row 的 `comparison_eligible`；基线同时置为历史错误分类 `unavailable=false`。当前旧 receipt 刻意缓存 `new_failures=[]`、该 loader known、`unverified=[]`，模拟 prior finding 的错误历史结果。

两组公共 `batch status` 均推荐重跑 batch test，直接 close 均 exit 1；随后实际 CLI 重跑仍返回非空 new_failures/unverified、空 known。该结果验证 [batches.py:292](/tmp/outcome-review-final-04/tools/workflow_lib/batches.py:292) 从旧原始事实重算，而非信任缓存的空比较列表。这是主动构造的 legacy schema fixture，不是迁移真实 Topic。

真实断言修复为一个执行并通过的 unittest 后，两组 runner exit 0、new/known 为空；仍保留基线 unverified，重新采集 fixture review 后 close 均 exit 0，delivery 包含对应 runner 缺口。因此没有以永久拒绝所有 loader 来源来冒充该修复成功。

### 必要相关回归：部分执行、known 身份及窄 startup

| 独立公共 CLI 探针 | 实际事实 |
|---|---|
| default / `-v` 部分执行 | 基线同时有缺依赖 loader、真实 `Behavior.test_known` 失败、真实 `Behavior.test_new` 通过；`unavailable=false`、comparison_eligible=true。当前只改变 test_new 为失败；仅 test_new 成为新增，test_known 与已有 loader 仍 known，unverified 为空；close exit 1 |
| 旧部分执行记录 | 删除新字段并设历史 unavailable=true，保留执行输出；两种 verbosity 仍只新增 test_new，不把部分执行整体降为环境缺口；close exit 1 |
| 已知真实失败收口 | 基线真实 test_a/test_b 均断言失败；仅修好 test_b 后，test_a 保留 known、无新增、无 unverified；fixture review 后普通 close exit 0。unittest `FAILED (failures=N)` 摘要未被混作测试身份 |
| 多阶段 runner | 缺依赖基线后，当前分别先运行真实子 Python AssertionError、SystemExit(text)、shell stderr+exit1，再 import 缺失可选依赖。三组真实 runner exit 1、unavailable=false、非空 new_failures，close 均 exit 1 |
| 窄 startup 正例 | 不存在的可执行文件、Python `-m` 缺模块、直接 import 缺模块、shell 缺命令，四组实际基线 unavailable=true |
| 成功负向诊断 | exit 0 的 runner 仅打印 ModuleNotFoundError 诊断文字，基线 unavailable=false；改为真实 AssertionError 后 unavailable=false、new_failures 非空、close exit 1 |

以上身份观察来自 Python unittest 与实际自建 runner；没有把 Go/pytest 的作者静态字符串测试当作本轮独立执行证据。

### 已接受 branch：human 与 JSON

两 Ticket fixture 完成后，构造整分支 spec-challenge finding，公共 `batch accept` 接受该 fixture 冲突。当前公共 `topic status`：decisions_needed 为空；known_issues 含原 finding；branch_review.status 为 accepted，stop_reason=null，historical_stop_reason 与接受前原 stop 原因逐字相同；next_command 与 accept 返回一致，均为 topic complete。

实际 human：

```text
已接受的历史原因：Spec 与现有系统冲突：用户已接受该冲突；作为已知问题保留
下一步：workflow.py topic complete --repo <临时 fixture> --topic feature
```

没有旧“请用户决定修订 Spec”请求，实际 topic complete exit 0。[topic_service.py:358](/tmp/outcome-review-final-04/tools/workflow_lib/topic_service.py:358) 与 [status_text.py:32](/tmp/outcome-review-final-04/tools/workflow_lib/status_text.py:32) 的接受状态和历史原因字段已一致。该复核不扩大到真实用户裁决或归档后任意 HEAD 变化。

## Advisory

**A-runtime-verbose-startup：`-v` 的纯缺依赖事实保守阻断，可用性/分类边界。** 本轮实际 `-v` 基线与未改模块的当前 batch test 都只产生缺依赖 loader；却 unavailable=false、comparison_eligible=false。当前模块仍是缺依赖 import 时即产生 new_failures，comparison 为 baseline-identity-unverifiable，`batch review` exit 1：`test: 审查需要当前全量测试相对基线无新增失败记录`。default 同情形 unavailable=true，并可构造 review。

这是 [evidence.py:29](/tmp/outcome-review-final-04/tools/workflow_lib/evidence.py:29) 明确只识别 default 包装的保守边界；本轮将其列 advisory，因为没有重现当前 AssertionError 被吞掉或 close 放行。若产品要求两种 verbosity 的纯环境缺口都允许披露后继续，应另窄扩展 `-v` startup wrapper，并继续保留当前真实失败 unavailable=false 的门禁。本轮不要求通用日志语义框架，也不把所有 loader 错误都解释为缺依赖。

证据：[纯 verbose startup 的当前事实](/tmp/outcome-runtime-03-evidence/verbose-startup-current.json)。不要将此 advisory 的纯缺依赖运行当作 R1 顶层 AssertionError 的替代证据；两者在 results/CLI events 中分别保留。

## 原始证据与执行状态

- [独立探针源码](/tmp/outcome-runtime-03-probes.py)：自建 fixture、公用 CLI argv、独立断言；未导入被测项目测试 helper 或生产 helper 来代替公共 CLI。
- [完整 CLI events](/tmp/outcome-runtime-03-evidence/cli-events.json)：132 次 fixture CLI 调用，均保留实际 argv、fixture repo、stdout/stderr、exit code。
- [逐项事实](/tmp/outcome-runtime-03-evidence/results.json)：baseline/current 原始 receipt，含 Python 环境、HEAD/content_id、failure 身份与完整 output_tail；原错误/修复后事实分开保留。
- [首轮日志](/tmp/outcome-runtime-03-probes.log)：首轮探针进程 exit 1，唯一脚本断言错误为预设 `-v` 纯缺依赖可先 review；当场公共 CLI 的保守拒绝是实际产品结果，未覆盖隐藏。
- [verbose 后续日志](/tmp/outcome-runtime-03-loader-v-followup.log)：改正上述探针前提，只把初始 review 预期改为拒绝，再注入真实 AssertionError，进程 exit 0。
- [修复后边界日志](/tmp/outcome-runtime-03-repaired-followup.log)：真实断言修复后 default/verbose close 成功且保留 unverified，进程 exit 0。

脚本 exit 0 表示探针断言符合预期，不等于所有被测命令 exit 0，更不等于产品全量验收。

## 未验证边界

没有运行全量 suite，也没有独立认证 root 统一跑的 suite。没有复审 prior-findings 的其他 R2–R4/A1 全部历史路径；本次只顺带验证已接受 branch human。未验证真实 Topic/host、发布安装、真实迁移、模型效果、跨进程并发、其他 Python 版本/平台、多于 output_tail 4000 字符的截断语义或任意 runner。真实执行的 same-case 不同失败原因一般比较策略没有在本轮扩大审查；本次明确覆盖的是无法充当行为基线的纯 loader 来源、实际执行的 known/new 身份，以及当前真实 AssertionError 的事实边界。
