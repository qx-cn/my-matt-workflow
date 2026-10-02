# Runtime 独立修复复审 06（冻结 final-07）

结论：**blocking 0，advisory 0**。本轮限定范围未发现新反例。runtime05 的 R1-loader-proof-concise 在 default / `-v` 均不再复现：实际短 Assertion 被记为 new，缺依赖 loader proof 为空，普通 close exit 1。直接 exception-only AssertionError / RuntimeError 含 `No module named`、旧 unavailable=true 缓存、无 dependency_proof_version 的旧 loader proof list 均不能使真实失败沿用假 known 或绕过 close。

这只确认下述窄范围。真正缺依赖的 runner 仍 exit 1，并被披露为环境缺口；合成 fixture review 的 pass 不是模型审查认证，也不是测试实际通过。

## 范围与独立性

- 唯一产品源码根：`/tmp/outcome-review-final-07`，物理路径 `/private/tmp/outcome-review-final-07`。先核验 281 文件，随后完整读取 `prior-findings.md`、`repair.patch`；也完整读取 `/tmp/outcome-review-runtime-05.md`，确认其字节与 prior-findings 相同。
- 本轮普通工程独立窄复审，未用 my-matt-workflow 自身 Skill/runtime 管理本次施工或验收。公共 CLI 仅作为被测对象，所有 setup / implement / batch 都以自建 `/tmp` Git fixture 为 repo。未读写主仓产品内容、真实 Topic、host 或历史。
- 未运行作者测试或全量 suite，未导入产品 helper 或作者测试 helper。复用的是 runtime05 **独立审查员的探针 harness**，其中只用 subprocess 调公共 CLI；新异常 runner、旧缓存输入和断言另行构造。没有子 agent、没有模型升级。
- shell 全部 `login:false`；探针、公共 CLI、runner 使用 `python3 -B`，运行环境传递 `PYTHONDONTWRITEBYTECODE=1`。写入仅在 `/tmp`，冻结源没有缓存。
- 7 个 Git fixture；171 次公共 CLI 调用，16 次直接 runner 确认。公共 `batch test` 共 20 次，均 CLI exit 0，表示 receipt 生成成功；其主要 runner 实际 exit 1，不能将 CLI exit 0 解释为测试成功。fixture 的全量配置只含本报告的微型 runner / `python3 -B -m <不存在模块>`，以及 `python3 -B -c 'pass'`。

## 源身份与原证据保留

开始、所有探针结束后分别对 manifest 的 281 个条目逐文件计算 SHA256，全部匹配，源码无字节变化。manifest 摘要均为：

`0f7c4296a473ec1df31e3e61f87d8a861aa2ef6eaaa904a46c4c85ae4ecd3eb1`

开始与结束文件树均为 284 个文件，清单外仅 `prior-findings.md`、`repair.patch`、`source-manifest.json`；无新增文件或 `__pycache__` / `.pyc`。环境：Python 3.14.4，macOS 27.0.1 arm64。

证据：[开始核验](/tmp/outcome-runtime06-start-integrity.json)、[结束逐文件摘要与环境](/tmp/outcome-runtime06-end-integrity.json)。本轮材料 SHA256：prior-findings `026fd71d7167e5e49ad024788c117779286b8010bffc778bf70c63975e2dbc0b`，repair.patch `25d163adfe5d40fd9e7a602d24f0656ed6a0230b30d4578a26c1a024a90596cf`。

原 R1 报告、原 probe、原运行日志没有改写；保留副本与摘要见 [保留材料清单](/tmp/outcome-runtime-06-evidence/prior-preservation.json)，结束重新检查原路径与副本均匹配。原日志的 `bypass=True` 是 runtime05 历史反例结果，本轮另存日志为 `bypass=False`，没有用新结果覆盖旧记录。

## 实际 CLI 与 runner 结果

所有失败 runner 都由真实 Python 异常 / unittest TextTestRunner 产生；exception-only 使用标准库 `traceback.format_exception_only` 保留真实异常类别，不用伪造字符串替代本轮实际执行结果。表中的 N/K/U 是 new / known / unverified 条数。

| 探针 | 实际 runner / batch test | 当前事实与比较 | status / 普通 close |
|---|---|---|---|
| 原 R1 短 Assertion，default / `-v` | runner exit 1；batch test CLI exit 0 | execution_observed=true，unavailable=false，loader proof=[]，N/K/U=1/0/1 | 当前 HEAD 新鲜合成 review 后 close exit 1，stderr 含“新增失败” |
| 直接 exception-only AssertionError / RuntimeError，消息含 No module named | 两种 runner 均 exit 1；batch test exit 0 | 无 traceback 的真实异常诊断；unavailable=false，N/K/U=1/0/1 | fresh 合成 review 后 close exit 1；复跑仍 unavailable=false、new 非空 |
| partial passing + 同名 loader 中短 Assertion / RuntimeError，default / `-v` | 每次 runner exit 1；batch test exit 0 | 一条真实 passing + 两个同 identity ERROR block；任一真实异常使 proof=[]，unavailable=false，N/K/U=1/0/1 | fresh 合成 review 后 close exit 1 |
| 真正 ModuleNotFoundError，直接完整 traceback / exception-only | runner exit 1；batch test exit 0 | unavailable=true，N/K/U=0/0/1 | status exit 0，披露 baseline 缺口；公共 fixture review create / submit exit 0。缺依赖未被称为实际测试通过 |
| partial passing + 纯 ModuleNotFoundError，完整 / exception-only，default / `-v` | runner exit 1；batch test exit 0 | execution_observed=true，unavailable=false，typed loader proof 1，N/K/U=0/1/0 | fresh 合成 review 后 status 推荐 close；完整旧 proof 记录去掉版本后也能由 typed 原诊断重证，仍推荐 close |
| 实际 `python3 -B -m` 缺模块 / 缺模块.nested | runner exit 1；batch test exit 0 | unavailable=true，N/K/U=0/0/1 | status 明确披露缺口；去掉版本的完整 receipt 经 fresh 合成 review 后普通 close exit 0，属于允许披露缺口的路径，不是行为测试通过 |

原 R1 探针仅改源码路径、输出路径以及修复后必需的 fresh review 前置条件：修复后真实 receipt 已有 new，CLI 正确拒绝直接发起 review，因此短暂放入合成零失败 receipt 创建当前 HEAD/content_id 的 fixture review，提交合成 pass，再恢复真实失败 receipt 后测 close。这条前置路径与 runtime05 独立 harness 已有方法一致。原 runner、两个同名 ERROR block 和短 Assertion 保留。

直接异常与新 loader 反例同样在当前内容上创建 fresh review，确认 manifest 的 HEAD / content_id 等于当前实际 receipt，再恢复真实 receipt。这样 close 的拒绝明确来自测试门禁，而不是过期 review。reviewer 的 pass、coverage、independent provenance 都是**合成门禁输入**，没有真实模型 reviewer 作出该认证；临时零失败 receipt 不属于运行结果证据。

## 无版本旧缓存的窄探针

所有缓存探针以当前真实失败 receipt 为起点，仅在 fixture 的 `.agent` 记录内构造旧格式，保留 command / content_id / environment / failures，用空 new、伪 known 模拟先前错误比较；每组已具备相同当前内容的 fresh 合成 review。

1. 直接 AssertionError / RuntimeError：删除 dependency_proof_version，并把 unavailable 改为 true。
2. loader AssertionError / RuntimeError，default / `-v`：删除 dependency_proof_version，把 unavailable_loader_failures 错填成全部同名 failure identity。
3. 每种分别检查完整记录、完整但省略 output_complete/output_length 的旧记录、4000 字符截断记录，以及截断且省略这两个完整性字段的旧记录，共 **24 组**。实际 status 均 exit 0 且 next_command 指向 `batch test`；普通 close 均 exit 1，stderr 为“全量测试新增失败或记录过期；请 batch test”。不是凭空 new 数组判断。
4. 额外 **6 组**隔离完整性门禁：为 direct/default-loader/verbose-loader 的当前真实 RuntimeError 记录构造 4000 字符旧 tail，tail 去空白后刻意看似完整合法 ModuleNotFoundError / 纯 missing unittest report；分别保留 output_complete=false 或省略完整性字段，无 proof version。typed 片段取自真实缺依赖对照，旧 tail 本身是**合成缓存输入**，不冒充当前 runner 输出。全部 status 要求 batch test、close exit 1；不会因为最后可见的是合法 missing 诊断而沿用旧假证明。

这 30 组是缓存重判探针，并非新的真实 runner 行为失败；每次之后恢复实际 receipt。真正完整 ModuleNotFoundError 对照则允许从旧 typed 诊断恢复 proof，没有把全部旧依赖缺口一概新增为行为失败。

公共 CLI 汇总：20 次 batch test exit 0；44 次 batch status exit 0；40 次普通 close 中，38 次按预期 exit 1，2 次真实 Python -m 环境缺口在披露和合成 review 后 exit 0。完整命令、stdout、stderr、exit 与计数见 [执行摘要](/tmp/outcome-runtime-06-evidence/execution-summary.json)。

实现对应：[typed ModuleNotFoundError 诊断及旧记录重证](/tmp/outcome-review-final-07/tools/workflow_lib/evidence.py:111)、[当前比较与 tests_passed](/tmp/outcome-review-final-07/tools/workflow_lib/batches.py:240)。这些源码阅读用于解释 CLI 实测，不替代探针。

## 证据路径

- 原 R1 本轮适配探针：[脚本](/tmp/outcome-runtime-06-r1.py)、[复跑日志](/tmp/outcome-runtime-06-r1.log)、[两种模式实际结果](/tmp/outcome-runtime-06-r1-evidence/results.json)、[原始 CLI/runner 事件](/tmp/outcome-runtime-06-r1-evidence/cli-events.json)。复跑探针进程 exit 0，两个 bypass 均 false。
- 独立窄探针：[脚本](/tmp/outcome-runtime-06-narrow.py)、[日志](/tmp/outcome-runtime-06-narrow.log)、[receipt/cache/review/status/close 结果](/tmp/outcome-runtime-06-narrow-evidence/results.json)、[原始事件](/tmp/outcome-runtime-06-narrow-evidence/cli-events.json)。探针进程 exit 0。
- 看似合法 missing 的截断旧缓存：[脚本](/tmp/outcome-runtime-06-truncated-cache.py)、[日志](/tmp/outcome-runtime-06-truncated-cache.log)、[输入与结果](/tmp/outcome-runtime-06-truncated-evidence/results.json)、[原始 CLI 事件](/tmp/outcome-runtime-06-truncated-evidence/cli-events.json)。探针进程 exit 0。
- 已有独立 harness 的路径适配副本：[文件](/tmp/outcome-runtime-06-independent-harness.py)；未运行其原 tail/duplicate 全矩阵。

## Blocking / Advisory 与未验证边界

**Blocking：0。Advisory：0。** 没有新反例需要即时上报。本轮实测确认上述 R1 修复与指定相关缓存门禁；不构成全产品验收或真实模型审查通过。

未重复 runtime05 的旧 tail/duplicate 全矩阵及 R2–R5；未运行作者测试、产品全量 suite、安装部署、真实 Topic 生命周期、真实模型 review、多平台/其他 Python 版本或并发行为。未审查任意日志格式和通用日志框架，也未对版本标记本身遭恶意伪造等其他威胁扩展范围。真实缺依赖控制没有补装依赖，没有因此声称实际测试成功。主仓、冻结源码及原报告均未修改。
