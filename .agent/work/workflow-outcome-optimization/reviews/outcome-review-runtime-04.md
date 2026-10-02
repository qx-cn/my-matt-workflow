# Runtime 独立修复复审 04（绑定最终 05）

结论：**指定范围内 blocking 1，advisory 0。** 新 default/verbose 纯缺依赖 wrapper 分类及普通短输出路径通过；但实测复现 **R1-tail-legacy：多模块纯 loader 基线截断后，缺新字段且历史误分类的旧记录重新获得 coarse identity 可比较性，当前真实顶层 AssertionError 被列为 known，刷新 fixture review 后普通 close exit 0**。因此本轮不能给出指定范围内通过结论。该发现适用于字节相同的最终 `/tmp/outcome-review-final-05`，仅按下述五文件绑定范围转移结论。

## 范围与独立性

本轮为普通工程独立复审，没有参与修复施工，没有使用 my-matt-workflow skill/runtime 为本次复审登记、施工或签验收。完整阅读冻结根的 `prior-findings.md` 与 `repair.patch`；只审查新增 default/verbose all-loader 纯 ModuleNotFoundError wrapper 分类及对真实失败的影响。作者测试仅用于理解补丁意图与 CLI fixture 格式；未运行作者测试、未导入作者测试 helper 或生产 helper 代替独立探针。

公共 CLI 是被测对象：在自建 `/tmp` Git 仓库中调用 `setup/implement/batch`，独立构造 runner、Ticket、原始 receipt 和断言。fixture review 的 pass、coverage、provenance 是到达 close 门禁所需的**合成输入**，不表示真实 reviewer 认证 toy 产品；本报告的事实来自实际 CLI/runner 退出码、输出、持久化记录与源码调用路径。刷新这些合成输入是为了排除过期 HEAD/review 前置门禁，直接检验测试门禁。

所有 shell 调用 `login:false`；Python 主探针、CLI 与 Python runner 均使用 `python3 -B`，并设置 `PYTHONDONTWRITEBYTECODE=1`。所有写入仅在 `/tmp` 的自建 fixture、证据、探针和报告；未修改冻结源码或主仓源码。未派生其他 agent。

## 源身份与结束不变

- 唯一执行源码根：`/tmp/outcome-review-runtime-04`，物理路径 `/private/tmp/outcome-review-runtime-04`。
- `source-manifest.json` SHA256：`92442f8ba859bef3d11c4470cf7b932555aefc50f219ef6756abce4d63ee2203`。
- 开始及结束逐文件核验：281 个唯一 manifest 条目全部匹配。冻结树共 284 个文件，清单外仅 manifest、prior-findings、repair.patch；结束新增、删除、字节变化均为空，无源码缓存。
- `prior-findings.md` SHA256：`2aeb0338d0272a7b49ead87b38411eb2bbabfdb7079bcca23237180316e39805`。
- `repair.patch` SHA256：`72554e3e0e2f812f83ad077cd28d387486bc2eff312f9bd4e2fbaa79959694a2`。

逐文件凭证：[开始核验](/tmp/outcome-runtime-04-start.json)、[结束核验（含截断补探针之后）](/tmp/outcome-runtime-04-end.json)。

## Blocking

### R1-tail-legacy：截断旧 loader 基线放过同身份真实失败

严重性：**blocking / P1**。定位：[evidence.py:14](/tmp/outcome-review-runtime-04/tools/workflow_lib/evidence.py:14)、[evidence.py:23](/tmp/outcome-review-runtime-04/tools/workflow_lib/evidence.py:23)、[evidence.py:93](/tmp/outcome-review-runtime-04/tools/workflow_lib/evidence.py:93)、[batches.py:233](/tmp/outcome-review-runtime-04/tools/workflow_lib/batches.py:233)、[batches.py:257](/tmp/outcome-review-runtime-04/tools/workflow_lib/batches.py:257)。

复现为两套独立公共 CLI fixture，分别 default 与 `-v`：

1. 建立 `suite/test_00.py` 至 `suite/test_11.py` 共 12 个模块，每个仅 `import review04_intentionally_missing_dependency`。runner 为 `python3 -B -m unittest discover -s suite`，verbose 组追加 `-v`。
2. 公共 `implement start` 真实采集基线：runner exit 1，`unavailable=true`、`comparison_eligible=false`，完整 `failures` 数组含 12 个 loader 身份；`output_tail` 恰为最后 4000 字符，仅可见 4 个 ERROR 头，footer 仍为 `Ran 12 tests`。纯当前缺依赖运行无新增、有 unverified，并可进入 fixture review。
3. **仅将同一 `suite/test_00.py` 改为** `assert False, 'review04 real top-level assertion'`，提交后公共 `batch test` 真实运行。新 schema 下 `unavailable=false`、新增非空、普通 close exit 1，错误明确为全量测试新增失败；此时失败身份数组与基线完全相同。
4. 构造受测旧基线：只删除 baseline row 的 `comparison_eligible`，置历史错误 `unavailable=false`，保留原 `output_tail`、完整 12 项 `failures`、命令、环境及内容绑定。另构造缺新字段、缓存空新增/空 unverified/全部 known 的旧当前 receipt；随后**再次真实公共 `batch test`**，不依赖这份缓存的比较结果。
5. 重跑后：当前 runner exit 1、`unavailable=false`，但 **`new_failures=[]`、known 12、`unverified=[]`**。先直接 close exit 1 的唯一原因是 `HEAD 已变化；请对变化部分复审`；刷新本次 fixture 的合成 review 后，**普通 `batch close` 实际 exit 0**。

| 模式 | 旧基线 tail 可见头 / 完整身份数 | 当前 unavailable | 重跑 new / known / unverified | 刷新 review 后普通 close |
|---|---:|---|---:|---:|
| default | 4 / 12 | false | 0 / 12 / 0 | 0 |
| verbose | 4 / 12 | false | 0 / 12 / 0 | 0 |

另对两个 fixture 的同一实际当前 runner 直接捕获完整 stdout/stderr：exit 1、stdout 为空，stderr 分别 11310 / 11970 字符，均明确包含 `AssertionError: review04 real top-level assertion` 及 12 个 ERROR 头。故不是以再次缺依赖运行代替真实失败。完整 runner 原始输出见下述 CLI events 中 `role=direct-current-runner-confirmation`。

源码解释：`execution_observed` 对截断 tail 使用 `Ran N > 可见 loader_errors` 推断真实测试执行。12 > 4 使 `loader_only_failure(tail)` 返回 false；旧基线又没有显式 `comparison_eligible=false` 且历史 unavailable=false，因此 `baseline_gap` 不保留缺口，比较退回完整旧/新失败身份交集。同一模块从缺依赖转为顶层 AssertionError 的 loader 名称没有变化，当前真实失败全被列为 known。当前重跑新生成的 `comparison_eligible=false` 没有阻止此旧基线路径。

这是用户提示之后**实测确认**的条件性反例，不是基于假设直接报问题。影响边界仅为本轮纯 loader 旧 schema、历史错误 unavailable 分类、截断输出与相同 loader 身份组合；不声称任意真实 partial 基线均错误。建议窄修复这条旧记录可比较性恢复条件：不能仅凭可能截断的 tail/footer 恢复行为基线，应利用保留的原始身份/截断完整性证据保守保留 unverified，并使当前可观察失败进入 new。无须建设通用日志框架。

证据：[截断探针源码](/tmp/outcome-runtime-04-truncation-probes.py)、[原始 CLI/runner events](/tmp/outcome-runtime-04-truncation-evidence/cli-events.json)、[基线/旧记录/真实重跑/close 事实](/tmp/outcome-runtime-04-truncation-evidence/results.json)、[日志](/tmp/outcome-runtime-04-truncation-probes.log)。两组进程探针正常结束；`bypass=True` 表示反例复现。

## 已通过的相关事实

补丁的新 verbose progress 识别要求 announcement 与实际 ERROR header 顺序/身份逐项一致；default 和 verbose 均校验 Ran/errors/header 数量并要求每个 loader block 为窄缺依赖诊断。[evidence.py:28](/tmp/outcome-review-runtime-04/tools/workflow_lib/evidence.py:28)。以下是新增截断探针之前的 11 个自建 fixture 的独立实测事实：

| 探针 | 实际结果（default / verbose 均执行） |
|---|---|
| 单模块纯缺依赖 | baseline/current 均 unavailable=true、comparison_eligible=false；current new 为空、unverified 存在；batch status 披露基线环境缺口并推荐 review，review 创建与提交成功 |
| 同模块顶层 AssertionError | 与缺依赖基线相同 loader 身份；当前 unavailable=false、new 1、known 0、unverified 1；普通 close exit 1，确因测试新增失败 |
| 短输出旧记录 | 删除 baseline/current 新字段并设基线历史 unavailable=false，伪造空新增/全部 known；status 要求 batch test，close exit 1；真实重跑仍新增非空、known 空。此通过结果**不覆盖**上面的截断反例 |
| 修复真实断言后恢复 | 同模块替换为实际执行并通过的 unittest；runner exit 0、新增为空，保留基线 unverified；重新 fixture review 后 close exit 0，delivery 含对应未验证 runner |
| 真实 partial 测试 + loader | 基线同时存在缺依赖 loader、实际 `Behavior.test_known` 失败与 `Behavior.test_new` 通过；baseline/current unavailable=false、comparison_eligible=true。当前仅 test_new 改为失败，仅该身份新增；原 test_known 与 loader 两项 known，unverified 为空；close exit 1 |
| 两模块纯 loader / 混合真实失败 | 全纯缺依赖 baseline/current unavailable=true、无新增、有 unverified、可 review；其中一个模块改为顶层 AssertionError 后 unavailable=false、new 2、known 0，close exit 1。整个不可比较 runner 的身份保守进入 new，不声称精确归因到两个真实行为回归 |
| 额外真实 phase 失败 | 自建 driver 先真实运行子 Python 顶层 AssertionError，再运行缺依赖 unittest；完整诊断保留真实 phase 失败；当前 unavailable=false、new 非空，close exit 1 |
| 未知包装 | driver 在真实 unittest 输出前增加 CUSTOM WRAPPER DIAGNOSTIC；当前 unavailable=false、new 非空、close exit 1 |
| verbose announcement 不匹配 | 保留真实 unittest loader body，仅将 progress announcement 改成另一身份；当前 unavailable=false、new 非空、close exit 1 |

上述通过事实说明 prior advisory 的 verbose 纯环境缺口可用性已修复；不抵消截断旧记录的 blocking。

证据：[原独立探针源码](/tmp/outcome-runtime-04-probes.py)、[原 CLI events](/tmp/outcome-runtime-04-evidence/cli-events.json)、[逐项 receipt 与状态](/tmp/outcome-runtime-04-evidence/results.json)、[成功日志](/tmp/outcome-runtime-04-probes.log)。共 11 个 Git fixture、107 次公共 CLI 调用；截断补探针另 2 个 fixture、30 次公共 CLI 调用。探针进程成功不代表被测命令全部成功或产品通过验收。

首个执行尝试因自建 Ticket 的 `review_probes` 使用了不合法值被 admission 拒绝；修正为允许的 `recovery` 后重新建立 fixture，未改变被测源码。该尝试保留于 [首轮日志](/tmp/outcome-runtime-04-probes-attempt1.log) 与 [首轮 CLI events](/tmp/outcome-runtime-04-evidence/attempt1-cli-events.json)。

## Advisory

无新增 advisory。未知 wrapper、额外 phase 与部分执行均按上述实测保持保守；截断 legacy 放行属于 blocking，不降为普通边界说明。

## 最终 05 的限定字节绑定

按后续授权仅核验 `/tmp/outcome-review-final-05/source-manifest.json` 身份、281 唯一条目数量及以下五文件，不在最终 05 执行测试或复审其他源码：

- `tools/workflow_lib/evidence.py`
- `tests/test_batches.py`
- `tools/workflow_lib/batches.py`
- `tools/workflow_lib/status_text.py`
- `tools/workflow_lib/topic_service.py`

最终 05 manifest SHA256 与提供值完全一致：`4cc4bce59526ea168f0b7f75eebe6b07b595bfd080e6091619561826e956ad03`。五文件均与 runtime-04 **逐字节相同**且各自 SHA256 与最终 05 manifest 匹配；截断补探针结束后再次确认不变。因此本轮上述分类/门禁结论及 blocking 适用于最终 05 的相同相关实现。`test_batches.py` 的相同仅为材料绑定，不构成作者测试执行证据；status_text/topic_service 的相同不构成历史功能重审。

逐文件完整哈希：[最终 05 字节绑定](/tmp/outcome-runtime-04-final05-binding.json)。未检查其他最终源码差异，不声称独立验证“只有 installer 改变”；最终 suite 由 root 启动是用户提供的状态，本轮未观察或认证其结果，未重跑 suite。

## 未验证边界

未运行全量 suite，未复审 prior-findings 中其他历史 scope、branch human/JSON、真实 host、安装部署、真实 Topic、模型效果、跨进程并发或其他平台/Python 版本。实际 fixture 环境为 Python 3.14.4/macOS。所有 legacy schema 退化均为自建 fixture，未修改真实历史。没有源码修复；本报告交付 blocking 的可复现证据，后续修复需独立处置。
