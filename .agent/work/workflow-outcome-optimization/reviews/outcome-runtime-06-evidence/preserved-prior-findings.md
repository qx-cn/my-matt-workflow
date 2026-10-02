# Runtime 独立修复复审 05（冻结 final-06）

结论：**blocking 1，advisory 0**。用户指定的三个反例及相关对照在 default / `-v` 均得到预期结果，R1-tail-legacy 本轮未再复现。但围绕新增 per-loader proof 的额外窄探针实测发现：真实 Assertion 的简短 exception-only 诊断被证明为缺依赖，同 loader 身份进入 known；新鲜 fixture review 后普通 close 实际 exit 0。因此不能给出本范围全部通过结论。

## 范围、独立性与事实边界

- 唯一读取和执行的产品源码：`/tmp/outcome-review-final-06`，物理路径 `/private/tmp/outcome-review-final-06`。完整读完该根的 `prior-findings.md` 与 `repair.patch`。
- 本轮是普通工程独立复审；未使用 my-matt-workflow skill/runtime 对本次复审施工、登记或签验收。公共 CLI 是被测对象，所有 `setup / implement / batch` 均指向自建 `/tmp` Git fixture；未触碰真实 Topic 或 host。
- 未运行作者测试、未导入作者测试 helper，也未导入产品 helper 代替实际 CLI。读取少量作者 fixture 格式和相关实现以理解协议；探针的仓库、runner、输入、断言及 subprocess 调用独立构造。无子 agent。
- 所有 shell 调用 `login:false`；主探针、公共 CLI、Python runner 均使用 `python3 -B`，并传递 `PYTHONDONTWRITEBYTECODE=1`。写入仅发生在 `/tmp` 的探针、fixture、证据和报告。
- 8 个核心 fixture，126 次实际公共 CLI 调用，10 次独立直接 runner 确认；额外 proof 探针 2 个 fixture，20 次公共 CLI 调用，2 次直接 runner 确认。没有运行产品全量 suite。fixture 的 `batch test` 只运行本报告定义的微型 unittest runner 和一个 `python3 -B -c 'pass'`。

fixture review 的 pass、coverage、independent provenance 均为**合成门禁输入**，不代表真实 reviewer 对 toy 产品作出认证。核心失败场景为排除过期 HEAD / review 门禁，在当前 HEAD、当前 content_id 上用公共 CLI 创建并提交新鲜 fixture review：创建期间临时提供合成零失败 receipt，随即恢复真实 runner receipt，之后实际 close 必须因测试门禁拒绝。这一步不是测试通过证据。额外 blocking 的 review 无须临时替换测试 receipt：公共 CLI 直接接受了真实 runner 产生但错误比较为 known 的记录。

## 源身份与结束不变

开始、全部探针结束后，均对 manifest 的 **281 个唯一条目逐文件计算 SHA256，全部匹配**。冻结树共 284 个文件，清单外仅 manifest、prior-findings、repair.patch；开始与结束完整文件树的新增、删除、字节变化均为空，未产生源码缓存。

| 材料 | SHA256 |
|---|---|
| source-manifest.json | `663a55c183586d85c23f323473b8fc943e8b53558516e688ca11b947349ea187` |
| prior-findings.md | `4e9dfe3d52493ab61782d22a3ef0a377d68a95ccad9df25a8cf93778a950f270` |
| repair.patch | `d3dd9c13bb3d1f36dd0c01dd87f393636ce427572be0ebd25f24de24d1f79f6d` |

逐文件证据：[开始核验](/tmp/outcome-runtime-05-start.json)、[结束核验及完整树对照](/tmp/outcome-runtime-05-end.json)。实测环境为 Python 3.14.4，macOS 27.0.1 arm64。

## Blocking

### R1-loader-proof-concise：真实 Assertion 短诊断被当作 per-loader 缺依赖证明

严重性：**blocking / P1**。

定位：[evidence.py:76](/tmp/outcome-review-final-06/tools/workflow_lib/evidence.py:76)、[evidence.py:79](/tmp/outcome-review-final-06/tools/workflow_lib/evidence.py:79)、[evidence.py:119](/tmp/outcome-review-final-06/tools/workflow_lib/evidence.py:119)、[batches.py:268](/tmp/outcome-review-final-06/tools/workflow_lib/batches.py:268)、[batches.py:301](/tmp/outcome-review-final-06/tools/workflow_lib/batches.py:301)。

两套独立 fixture 分别运行 `python3 -B runner.py` 与 `python3 -B runner.py -v`。runner 使用真实 `unittest.TestSuite / TextTestRunner`，包含两个同名 `_FailedTest('collision', ...)` 和一个真正执行通过的 `Visible.test_ok`。

1. baseline 两个 loader block 都由真实 import 缺依赖产生，保留完整 traceback。baseline/current 的 loader identity 都是 `collision (unittest.loader._FailedTest.collision)`，runner exit 1；实际 passing 用例使 `execution_observed=true`、`unavailable=false`。未改变的缺依赖正常 known。
2. 当前第一个 block 改为**实际执行** `assert False, "No module named 'review05_behavior_condition'"`，捕获后通过标准库 `traceback.format_exception_only(exc)` 保留异常类别和消息，再放入 loader ImportError wrapper。第二个 block 仍是真实缺依赖，最后的 passing 用例保留。
3. `TextTestRunner` 实际输出两个相同 identity 的 ERROR block。第一个内容是 `ImportError: Failed to import test module: collision` 后接 `AssertionError: No module named 'review05_behavior_condition'`；第二个是完整 `ModuleNotFoundError` traceback。完整 runner exit 1，诊断未经文本后处理。
4. 实际 `batch test` 仍将该 identity 写入 `unavailable_loader_failures`。结果为 **new=0、known=1、unverified=0**。
5. 保留上述真实 receipt，以公共 CLI 在当前 HEAD 创建并提交新鲜合成 fixture review，普通 `batch close` **实际 exit 0**。这条放行没有依赖 legacy schema、截断 tail、伪造空 new 缓存或临时零失败测试 receipt。

| 模式 | 当前 runner exit | execution_observed / unavailable | loader gap proof | new / known / unverified | 新鲜 fixture review 后 close |
|---|---:|---|---|---|---:|
| default | 1 | true / false | 错误包含 collision | 0 / 1 / 0 | 0 |
| `-v` | 1 | true / false | 错误包含 collision | 0 / 1 / 0 | 0 |

原因是新的 per-loader proof 将 block 的 wrapper 后内容交给共享 `environment_only_failure`。其中 `[^\n]*: No module named [^\n]+` 的单行匹配没有限制异常类别，真实 `AssertionError: No module named ...` 也返回 true。重复 identity 的 `all(facts)` 防止了后写覆盖，但这次第一个真实失败的 fact 本身被错误证明为 true；故两个 block 全部被认作环境缺口，新增的 compare 分支让 Assertion 借用粗 loader identity 成为 known。

影响边界：这是**自定义 unittest runner 的简短 exception-only loader wrapper**，不是标准 `unittest discover` 直接生成的完整 Assertion traceback。用户指定的标准发现路径及完整 traceback 的重复 Assertion/RuntimeError 均在下节通过。该窄反例属于本补丁新 per-loader proof 的证明可靠性，未扩展成全 runner 审查；原有通用启动分类 helper 的其他调用点不在本轮结论内。

建议仅收紧 per-loader proof：其环境证明应明确要求可识别的 ModuleNotFoundError 诊断；不得借用任意异常标签或 interpreter 启动单行 shortcut 来证明某个 loader block。未知/真实异常应保留为不确定并进入 new。无需通用日志平台。

证据：[独立额外探针](/tmp/outcome-runtime-05-proof-extra.py)、[两组实际 receipt / review / close](/tmp/outcome-runtime-05-proof-extra-evidence/results.json)、[完整 CLI 和直接 runner 原始输出](/tmp/outcome-runtime-05-proof-extra-evidence/cli-events.json)、[探针日志](/tmp/outcome-runtime-05-proof-extra.log)。日志 `bypass=True` 表示实际放行反例复现，不表示产品通过。

## 指定反例与对照的通过事实

下表每一行均实际执行 default 和 `-v`，不是仅静态推演。

| 探针 | 实际 CLI 结果 |
|---|---|
| R1-tail-legacy，12 个纯 loader 缺依赖 | baseline failure identities 12，tail 恰 4000 字符，仅 4 个 ERROR 头；完整事实 unavailable=true、execution_observed=false、output_complete=false。一个模块改成真实顶层 Assertion 后身份数组不变。旧 baseline 删除全部五个新事实字段，历史 unavailable=false / true 分别验证；真实重跑均 unavailable=false、new=12、known=0、unverified=1；当前 HEAD 新鲜 fixture review 后 close exit 1，明确因测试新增失败 |
| 旧缓存空 new 不自证通过 | 两种旧 baseline 状态均将当前 receipt 删除新字段，写入空 new / 空 unverified / 全部 known；实际 status 推荐 batch test，普通 close exit 1。之后再次公共 batch test 得到上述真实新增失败；未将缓存比较当作 runner 事实 |
| 真实 passing + 一个 missing，同模块改为 Assertion | baseline/current 初始 execution_observed=true、unavailable=false、缺依赖 proof 1、new=0、known=1、unverified=0；保留 passing，仅 missing 模块变成顶层 Assertion 后，loader identity 不变，当前 unavailable=false、new=1、known=0、unverified=1；新鲜 fixture review 后 close exit 1 |
| 重复 loader identity：Assertion 在前、missing 在后 | 两个实际 unittest ERROR block 同一 identity。完整 Assertion traceback 不会被后面的 missing 覆盖；gap proof 空、unavailable=false、new=1、known=0、unverified=1；新鲜 fixture review 后 close exit 1 |
| 重复 loader identity：未知 RuntimeError 在前、missing 在后 | 同样由真实抛异常及 TextTestRunner 形成两个 block；完整未知 traceback 的 gap proof 空、unavailable=false、new=1、known=0、unverified=1；新鲜 fixture review 后 close exit 1 |
| 真实 test_known 保留 / test_new 新增 | 12 个 missing 模块加真实 test_known 失败与 test_new passing，形成截断 partial baseline。删除全部新字段并分别设历史 unavailable=false / true；未改变时 new=0、known=13、unverified=0，可创建提交 fixture review。仅 test_new 改为真实失败后 new=1 且唯一身份是 test_new，known=13 包括 test_known 和 12 个纯缺依赖，unverified=0、unavailable=false，close exit 1 |
| partial 中同一纯缺依赖保留合理路径 | 真实 passing + missing，以及上述 known 失败 + 多 missing 两类 fixture 都验证保留的缺依赖仍 known，没有将它们全部保守变成新行为失败 |
| 纯 startup default / `-v` 可披露后 review | 两套 12 模块纯缺依赖 fixture 的当前 unavailable=true、new=0、unverified 非空；status 披露基线缺口并推荐 review，公共 review 创建与合成结果提交均 exit 0 |

R1-tail-legacy 中 new=12 表示整个不可比较 runner 的失败身份被保守记为新增，并不声称 12 个模块都有实际行为回归；本 fixture 真实新增 Assertion 只有一个。全部五个被删除字段是 `comparison_eligible / execution_observed / output_complete / output_length / unavailable_loader_failures`。

证据：[独立核心探针](/tmp/outcome-runtime-05-probes.py)、[逐项 baseline / 重跑 / fresh review / close 事实](/tmp/outcome-runtime-05-evidence/results.json)、[完整公共 CLI 和直接 runner 原始输出](/tmp/outcome-runtime-05-evidence/cli-events.json)、[完成日志](/tmp/outcome-runtime-05-probes.log)。核心探针 exit 0 表示其独立断言通过；被测失败 runner 和拒绝 close 的 exit 1 均按原始事件保留。

## Advisory

无新增 advisory。额外短诊断问题具有真实新增失败被 known 隐藏及普通 close 放行的实测证据，归为 blocking。

## 未验证边界

未运行全库 suite；未重复 prior-findings 的旧 R2–R5、branch human/JSON、安装或部署审查；未修改冻结源码、主仓、真实历史、真实 Topic 或 host。未验证其他平台、Python 版本、并发、多进程、真实模型审查或上线状态。结束哈希核验不等于产品行为验收；本报告交付独立工程证据与一个尚存 blocking，没有进行修复施工或治理登记。
