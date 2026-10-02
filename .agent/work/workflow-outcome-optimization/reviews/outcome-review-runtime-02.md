# Runtime 修复复审：02b（最终 03 相关源码字节确认）

## 结论

**不通过：1 个 P1 阻塞。** R1 原有非标准 runner 反例和 SystemExit(text)/shell failure 扩展已阻断，但修复引入了纯 unittest loader 启动缺依赖的分类退化：不可比较的基线被当作已知失败来源，随后真实断言失败仍可普通 batch close。R2、R3、R4 的指定反例已修复；R5 的 JSON 裁决与下一步一致，human 的旧裁决原因残留列建议。A1 的 Ticket definition drift accept 已拒绝。

本结论来自源码与实际隔离 CLI 事实，不由新增测试通过推导。没有读取作者实现总结作为依据，没有修改生产源码、主仓或真实 Topic/host；本轮有一次生成字节码缓存的操作偏差，详见隔离边界。未使用 workflow Skill 或 runtime 治理本次施工/复审。

## 源身份与范围

初始及结束均核验 `/tmp/outcome-review-runtime-repair-02b/source-manifest.json`：

- SHA256：`1775f5169a33cf5be57545414e27adf1b7e1b344e8babd11f5dc6b94866c6b97`。
- 280 个唯一条目，280 个文件 SHA256 全部匹配。
- 清单外仅 `source-manifest.json`、`repair.patch`、`prior-findings.md`；结束无其他文件。
- 所有源码读取使用该冻结源的绝对路径，所有 shell exec 使用 `login:false`。

依据为 02b 的 `repair.patch`、允许读取的 `prior-findings.md`、current Spec revision 2 的 AC01–03/13/18/19，以及其相关生产调用路径。复审只覆盖 R1–R5、修复影响的 A1、legacy 自审历史、快照及完成保护；没有扩大全库问题搜索。

用户后续指定最终 `/tmp/outcome-review-final-03`。本轮实际核验其 manifest SHA256 为 `c8af43e2c97ed827f697d336f8a3c87365a6b49318be6281b9034990cc10cfa2`，280 个唯一条目及文件全部匹配，清单外仅 manifest。两源的 **全部 35 个 tools 文件逐字节一致**，包含本轮修复涉及的 7 个生产模块。因此本轮 runtime 结论同样适用于最终 03。确认材料：[identity-02-03.json](/tmp/outcome-review-identity-02-03.json)。

两源整体并不完全相同：差异位于 composition/resources manifest、review-loop/user-intervention、若干 Skill、composition/设计 fixture 测试和 `tests/test_workflow.py`，均未据此重做其他范围审查。实际读取的 test_workflow diff 确认最后一项断言由遍历全部 routable_entries 改为检查 `my-ask-matt` 的技术设计入口。

## 阻塞：R1-startup — P1，纯 loader 环境缺口被转成可比较失败，真实断言被当作 known

**原 R1 修复有效部分：** 基线为真实 `import outcome_missing_startup_dependency`；当前 wrapper 分别先执行子 Python assertion、`SystemExit('actual regression')` 或 shell stderr + exit 1，再 import 缺失可选依赖。三个实际 runner 均退出 1，`unavailable=false`，`new_failures` 非空；三个 `batch close` 均退出 1。直接缺可执行文件、Python `-m` 缺模块、直接 import 缺模块及 shell 缺命令，也仍记录 `unavailable=true`。

**仍失败的合理兼容边界：** `python3 -B -m unittest discover -s suite`，suite 仅有一个模块 `test_behavior.py`，基线内容为缺依赖 import，没有可执行测试。正式 CLI 当场创建基线，未伪造或修改测试 receipt。随后同一模块改成一个明确失败的断言，再运行当前测试。

实际原始事实：

| 阶段 | 观察与实际结果 |
|---|---|
| 基线启动 | exit 1；输出 `ModuleNotFoundError: No module named 'outcome_missing_startup_dependency'`；仅 loader `_FailedTest`；本候选 `execution_observed(output)=false`；却记录 `unavailable=false` |
| 当前断言 | exit 1；输出 `AssertionError: actual behavior regression at import`；记录 `unavailable=false` |
| batch test | CLI exit 0；`new_failures=[]`、`unverified=[]`；`known_failures` 为 `test_behavior (unittest.loader._FailedTest.test_behavior)` |
| 隔离审查状态 | fixture 构造完整合法 pass，仅用于验证门禁，不是对 toy 产品的独立正确性保证 |
| 普通 batch close | **CLI exit 0，state=已收口**；真实断言未修复 |

**根因与源码位置：** [evidence.py:35](/tmp/outcome-review-runtime-repair-02b/tools/workflow_lib/evidence.py:35) 仅接受以 Traceback 开头、以 ModuleNotFoundError 结尾的单一诊断。unittest 的正常 loader 包装有 `E/ERROR/ImportError` 前缀及 `Ran/FAILED` 后缀，故纯缺依赖也被拒绝为 environment-only；[evidence.py:58](/tmp/outcome-review-runtime-repair-02b/tools/workflow_lib/evidence.py:58) 持久化错误分类。[batches.py:241](/tmp/outcome-review-runtime-repair-02b/tools/workflow_lib/batches.py:241) 因此不走不可比基线分支，而在 [batches.py:248](/tmp/outcome-review-runtime-repair-02b/tools/workflow_lib/batches.py:248) 按 loader 名称相交为 known；[batches.py:283](/tmp/outcome-review-runtime-repair-02b/tools/workflow_lib/batches.py:283) 认可零新增失败并放行 close。

这是 R1 新分类器的兼容退化，不把既有“同名测试不同原因”的一般比较限制单独升级为新阻塞。基线的纯缺依赖和无测试执行已有明确原始事实；正确保留其不可比较状态，现有 compare 分支即可把当前断言列为 `baseline-unavailable`。应窄化识别启动缺口的 wrapper，或保留未知/不可比较并阻断该完成判断，同时继续拒绝真实部分失败被环境缺口吞掉。不要求通用日志语义框架。

涉及 **AC01、AC19**。独立探针与原始输出：[extension-probes-02.py](/tmp/outcome-review-extension-probes-02.py)、[extension-probes-02.log](/tmp/outcome-review-extension-probes-02.log) 的 `LOADER_STARTUP_BASELINE/LOADER_CURRENT/LOADER_CLOSE`；精简事实：[r1-startup-proof-02.json](/tmp/outcome-review-r1-startup-proof-02.json)。

## 其余指定修复与边界

| 项目 | 实际核验 |
|---|---|
| R2 无关 reopen | `wrong` 内容及 blocking 不变；reopen exit 0 后 `--no-findings` exit 1，finish exit 1；pending 仍有 `unfixed`，没有 epoch 豁免 |
| R2 singleton/旧 epoch | 仅 singleton 的 blocking 被保存至 self_reviews，仍 pending；人为构造旧 epoch 字段不再隐藏历史。batch 与 legacy 非 batch 路径均验证 |
| R2 逐项处置 | 两个 spec-challenge、一个 correctness blocking、一个 fix-in-batch advisory 同时存在；reopen 理由明确引用 challenge-one，仅处置此项并保留新旧 definition/理由/时间；其余三项仍 pending，零发现登记拒绝 |
| R2 合法继续 | 明确裁决对应挑战后重采测试/自审，finish、batch close、Topic complete 均 exit 0；旧 finding 与逐项 resolution 可追溯。legacy singleton 的普通内容修复、测试、自审与正式 review 后 finish exit 0 |
| R3 quick | 无自动测试配置、仅“验收证据/影响与风险/未验证项”的原摘要，complete exit 0，归档状态 `tests_configured=false/test_runs=0`。安全披露位置替代原强制“测试结果”查找 |
| R4 dirty 无 finding | batch JSON `next_command=null` 且有恢复内容输入；batch/topic 的 human 均显示所需恢复条件；close exit 1 且不再指向不存在 finding 的 repair。恢复 code.txt 后 status 返回 batch close，实际 close exit 0 |
| R5 accept branch | batch accept exit 0；随后 Topic JSON `decisions_needed=[]`，保留 known_issues，next_command 与 mutation 同为 Topic complete；实际 complete exit 0 |
| A1 definition drift | Spec 改变后重跑测试及当前自审，status 明确 definition_changed/reopen；直接 accept exit 1，错误为定义变化需 reopen。合法定义裁决后可完成，未形成永久阻断 |
| 快照/完成 | 隔离生成的冻结材料完整时接受；篡改自有 fixture 材料被 `snapshot` 拒绝。branch 同字节空提交改变 HEAD 后 close exit 1；artifact 同字节换源路径返回 stale。完成归档后 reopen/complete 均 exit 1，归档所有文件字节不变 |

对应源码检查保留 Ticket 当前内容、definition/config/rules/decided/downstream 校验、branch HEAD 校验和 artifact scope 语义。未把共享 helper 的相同实现当作不同入口成功策略相同的证明。

证据：

- [probes-02.log](/tmp/outcome-review-probes-02.log)：原 quick/reopen/partial/A1。
- [boundary-probes-02.log](/tmp/outcome-review-boundary-probes-02.log)：dirty/singleton/HEAD/artifact/frozen。
- [routing-probes-02.log](/tmp/outcome-review-routing-probes-02.log)：accept branch 与实际 complete。
- [lifecycle-probes-02.py](/tmp/outcome-review-lifecycle-probes-02.py)、[lifecycle-probes-02.log](/tmp/outcome-review-lifecycle-probes-02.log)：逐项历史、legacy、合法完成、归档只读、human 与恢复。

## 建议（不计阻塞）

**R5-human：已接受裁决仍显示旧待裁决原因。** 隔离 accept 后 human status 的下一步正确为 complete，但仍打印“原因：Spec 与现有系统冲突：请用户决定修订 Spec、接受风险或按原 Spec 继续”。[topic_service.py:358](/tmp/outcome-review-runtime-repair-02b/tools/workflow_lib/topic_service.py:358) 仍传递历史 branch stop_reason；[status_text.py:27](/tmp/outcome-review-runtime-repair-02b/tools/workflow_lib/status_text.py:27) 无接受状态区分地展示。JSON 没有重复 decisions，且 complete 成功；本轮将此列为展示建议，建议标明“已接受的历史原因/已知问题”，避免 human 将它理解成新裁决请求。证据为 lifecycle 日志 `ACCEPTED_HUMAN`。

没有追加与修复无关的全库问题。

## 测试事实、exit 码及限制

根实际执行原 02b 完整普通 unittest：

```text
cwd=/tmp
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/tmp/outcome-review-runtime-repair-02b python3 -B -m unittest discover -s /tmp/outcome-review-runtime-repair-02b/tests
Ran 324 tests in 405.024s
FAILED (errors=2)
process exit_code=1
```

原始日志：[full-suite-02.log](/tmp/outcome-review-full-suite-02.log)。两项 ERROR：

1. `test_repository_configuration_matches_declared_full_tests`：提供的冻结源没有 `.agent/matt-workflow.md`，read_config 报缺少配置。
2. `test_build_gate_retains_configuration_without_topic_state`：复制同一缺失文件时报 FileNotFoundError。

没有 assertion failure；其余测试完成。上述两项是本冻结材料缺配置的验证限制，未据此宣称生产回归，也没有在快照补配置、运行 setup 或重跑完整 suite。日志里的 INSTALLED/deploy 输出来自完整 suite 自建临时 host fixture，未操作真实 host。

用户后续提供的集成事实为：第二轮 325 项完整 suite 只有一项旧技术设计 routable_entries 断言失败，root 将该断言收窄到 my-ask-matt 并定向通过。本轮已核验最终 03 的相应 diff 和所有相关 tools 字节一致，**没有独立重跑/认证这组 325 项或最终 03 完整 suite 的成功结果**；按用户指示不重复全范围及完整 suite。

三个由原脚本适配的 probe 及新增两组隔离 probe 均进程 exit 0。脚本输出逐项保留 CLI/runner 实际 exit；脚本本身 exit 0 不等于所有产品路径通过。原 partial 探针的 `PROBE_ERROR AssertionError` 是其旧脚本尝试 review 被新失败门禁拒绝，扩展探针另直接验证 close exit 1；旧 R5 脚本仍刻意调用原无效 resolve，exit 1 不再是 status 推荐动作。

原脚本适配只把源路径指向 02b；另将 R1 基线从手动抛无标准文本的 ModuleNotFoundError 改为真实缺依赖 import，并把旧 reopen 的预期成功断言改为打印拒绝事实。原 01 脚本未修改，快照 tests 未新增或修改；所有新 probe 位于 /tmp，使用现有 temporary Git/CLI seam。

## AC 与隔离边界

| AC | 本轮判断 |
|---|---|
| AC01 | R1 原部分失败保护有效，但纯 loader 启动兼容退化仍 P1 阻塞 |
| AC02 | 指定 reopen、blocking、逐项挑战、修复后继续及历史边界未发现阻塞 |
| AC03 | R3/R4/R5 指定机械路由有效；R5 human 残留列建议 |
| AC13 | 指定 quick 简短无测试摘要完成路径有效 |
| AC18 | batch/legacy singleton、旧 epoch 重评及归档只读边界有效；真实升级、writer 切换与宿主盘点未验证 |
| AC19 | R1 纯启动比较路径阻塞；指定内容漂移、快照、HEAD、scope、definition 与完成拒绝边界保留 |

未进行真实部署/安装/迁移/模型效果验证、跨进程通用并发实验；fixture pass 仅构造可验证门禁的合法状态。没有提交、push 或主仓变更。

操作偏差：整理证据的一条 Python 命令遗漏 `-B`，在 02b 生成 `tools/__pycache__/__init__.cpython-314.pyc`、`tools/workflow_lib/__pycache__/__init__.cpython-314.pyc`、`tools/workflow_lib/__pycache__/evidence.cpython-314.pyc`。发现后仅删除这 3 个本轮缓存及空目录，已即时通知用户；没有更改清单源码字节。结束再次核验两份 manifest 与全部文件均匹配，02b 无新增文件、03 无新增文件。本偏差明确披露，不宣称整个过程中冻结目录从未发生缓存写入。
