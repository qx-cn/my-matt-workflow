# R1/R2/R3 补偿修复独立复审

结论：**本次限定范围内未发现阻断问题。R1/P1、R2/P1、R3/P2 的既有公共 CLI 反例已不能错误收口；必要恢复正例和交叉路径通过。** 这是 final-01 冻结字节的工程复审结论，不是全仓无缺陷或真实模型业务效果结论。

## 对象、独立性和字节核验

- 候选：`/tmp/outcome-compensation-final-01`。
- 原问题版本：`/tmp/outcome-holistic-608b72b`；旧协议建仓 baseline：`/tmp/outcome-holistic-base-7947cb2`。v2 缓存反例另外使用只读预览 `/tmp/outcome-compensation-preview-01`。
- 开始：`2026-10-02T15:36:58.745582+00:00`；结束：`2026-10-02T15:42:25.308711+00:00`。
- 开始和结束 `source-manifest.json` SHA256 均为 `48126f1f9718524f7a907c75437c777b9f01bb179db77a48fb217de21edd8fa2`，均逐项核验 **283 文件、0 不匹配**。
- 只读取指定主仓 holistic 报告/holistic-review-01 证据以及冻结树；未读取主仓正在修改的生产源码，未参与生产修改，未调用被测 workflow Skills 治理。指定旧 evidence-manifest 的 19 项摘要也已核验匹配。
- 使用冻结旧测试文件中的临时 Git/CLI 建仓 seam；判定、变体和 controls 独立编写/修订。所有动作都在临时合成仓库执行，不操作真实 Topic 或宿主。

## 独立验证结果

修订主探针 **13/13** 通过，controls 的最终有效场景 **7/7** 通过，合计 **20 个场景、341 次记录的真实公共 CLI 调用**。这是场景和调用数，不是全量 suite 测试数。所有 CLI 命令、退出码、stdout/stderr 保存在 JSON 的 `cli_calls`。

| 范围 | 直接验证 | 结果 |
| --- | --- | --- |
| R1 旧未解发现 | 旧 CLI 实际完成含 correctness blocking/spec-challenge 的 Ticket；候选重测、合成 pass、close | status/materials 保留发现，普通 close 非零；历史 bytes 不变 |
| R1 correctness 修复 | 无代码变化 repair；真实内容修改后 repair；未刷新证据 close；刷新 test/review 后 close、topic complete | 前两种非法捷径被拒绝；有效恢复成功；完成 Ticket/implementation 历史不变 |
| R1 challenge 裁决 | 不相关 accept reason；明确点名 accept；定义修订后点名 reopen、重测/复审 | 不相关接受被拒绝；两条有效恢复均收口并完成 Topic；历史不变 |
| R1 mixed | correctness 与 challenge 共存；单独接受 challenge；实际 repair+review 后裁决 | challenge 接受不能绕过 correctness；完整恢复收口、完成 Topic，历史不变 |
| R1 optional branch 交叉 | 真实两票 standard；旧 correctness 修复、batch test/review、optional topic review、batch close、topic complete | 两次收口动作均 exit 0；两票 Ticket/implementation 历史 bytes 不变 |
| R2 普通/loader 动态导入 | `selected_plugin()` 返回拼错模块名，真实 importlib 调用；执行 marker；真实修复 | 初始非零失败不能借 unavailable 收口；close 非零；修复后 close exit 0 |
| R2 同身份不同诊断 | 全 loader 默认 runner，以及 partial+verbose runner；分别改变缺失模块、调用栈/源码行、异常为 AssertionError | 三种变化均为 new failure，不能借相同 `_FailedTest` 身份成为 known；close 非零 |
| R2 相同完整诊断 | 全 loader 直接缺依赖，baseline/current 完整诊断相同 | exit 1、unavailable=false、known 非空、new 为空、unverified 披露比较缺口；允许已有失败收口，未标为 current pass |
| R2 partial 相同诊断 | 一个真实 passing TestCase 与一个不变 loader 缺依赖共存 | 执行事实为 observed；同诊断可 known；改变的 loader 仍阻断。该可比较 partial 基线无需被误标为全 runner 不可用 |
| R2 v1/v2 缓存 | 原 v1 ordinary 动态反例；预览 CLI 实际生成 v2 loader 动态反例；完整旧 schema controls | 旧 unavailable/new_failures 分类不获盲信；反例 close 被拦，修复后通过；完整旧诊断重新计算 fingerprint |
| R2 长输出/旧截断 | 真实 >4000 字符 loader 诊断；v3 full fingerprint；删去新 fingerprint 并标 v1/v2 的旧尾日志 | v3 可依据完整执行时 fingerprint 比较；旧截断控制为 known=0/new=1，close 非零，不能推断成功 |
| R2 明确启动缺口 | Python `-m` 缺 runner；实际缺可执行文件 OSError | 保留 unavailable、unverified；OS exit 127；未声称业务测试已执行 |
| R3 当前/非当前 pass | 旧几何停止有效 pass；相同场景 nonpass；有效 pass 后另作源码 commit 使证据过期 | 当前 pass 的 status 下一动作实际 exit 0；nonpass、过期 pass 的 topic complete 非零且未归档 |

## 合同与实现判断

R2 的最终合同合理：unittest loader wrapper 和 ModuleNotFoundError 类型都不证明初始化代码未运行。`evidence.py` v3 将完整报告中的各 loader 诊断块绑定为 fingerprint；`batches.compare()` 在全 loader 缺口分支及 partial 比较分支都要求旧/新 fingerprint 相等。缺失、改变或旧日志截断无法重建的 fingerprint 不能借模块身份成为 known。解释器 `-m` 启动诊断和 OS 启动异常继续保留明确环境缺口。known 表示有完整证据的既有失败，绝不表示当前测试 exit 0。

R1 的新 `self_observations`、repair 绑定与挑战裁决在活动 batch 路径共同消费；optional branch 在 batch 处置后仍按相同内容核验其材料，实跑没有出现收口后的历史改写或 branch pass 失效。范围检查确认 nonbatch 保留原 `fix-in-batch` 发现选择，`require_self_repairs` 在未启用 batch 时返回；本轮 nonbatch R3 三种恢复控制也实际运行，没有将 batch repair 门禁错误施加给它们。

R3 status 与 mutation 调用同一 effective-state 恢复；恢复仍依赖当前有效 pass。独立过期内容控制和 nonpass 控制都不能进入完成。

## 探针修订及未通过夹具的处理

原 `/tmp/outcome-compensation-review-probe.py` 未覆盖，SHA256 仍为 `ec54b3bb4695648ae197dad35d2e975ac0f6c0d40f2465948e1995abfe7edbd7`。

派生 v3 探针修订两点：纯 loader 缺依赖正例改为 known+unverified、非 unavailable、非 current pass；dynamic loader 的修复改为实际 `PluginBehavior.test_selected_plugin_api`，观察实际 `json.loads` API，并要求 exit 0 和 `Ran 1 test`。真实输出为 `Ran 1 test ... OK`，避免 Python 3.14 的 `NO TESTS RAN`/exit 5 被误记成修复成功。

首轮 controls 的 optional branch 使用单 Ticket，CLI 实际 exit 1，提示 `topic review 只用于多 Ticket standard`。**该次尝试既不算产品缺陷，也不算通过**；原脚本、失败 log/json 保留。只修正为真实两票 standard，并用 `REVIEW_CASES=R1_optionalbranch_close_complete` 单项复跑，进程 exit 0、close/complete 均 exit 0。这一有效复跑替代的是夹具，不覆盖原失败证据。

## 命令与证据

实际执行命令（两个完整运行及一次针对夹具的单项复跑）：

```text
python3 -B /tmp/outcome-compensation-review-probe-v3.py /tmp/outcome-compensation-final-01 /tmp/outcome-compensation-review-final-probe.json
# process exit 0
python3 -B /tmp/outcome-compensation-review-controls.py /tmp/outcome-compensation-final-01 /tmp/outcome-compensation-review-final-controls.json
# first-run process exit 1: six controls pass, one invalid single-Ticket fixture
REVIEW_CASES=R1_optionalbranch_close_complete python3 -B /tmp/outcome-compensation-review-controls.py /tmp/outcome-compensation-final-01 /tmp/outcome-compensation-review-final-optional.json
# corrected fixture process exit 0
```

脚本、修改理由、diff、log/json、开始/结束核验与结果摘要都保留在 `/tmp`；完整路径与 SHA256 见 [evidence manifest](/tmp/outcome-compensation-review-evidence-manifest.json)。主要记录：

- [修订探针](/tmp/outcome-compensation-review-probe-v3.py)、[修订理由](/tmp/outcome-compensation-review-probe-v3-reasons.md)、[主探针日志](/tmp/outcome-compensation-review-final-probe.log)、[主探针原始 CLI 证据](/tmp/outcome-compensation-review-final-probe.json)。
- [controls 脚本](/tmp/outcome-compensation-review-controls.py)、[首轮 controls 日志](/tmp/outcome-compensation-review-final-controls.log)、[首轮原始证据（含保留的夹具失败）](/tmp/outcome-compensation-review-final-controls.json)。
- [两票 optional 单项日志](/tmp/outcome-compensation-review-final-optional.log)、[两票 optional 原始证据](/tmp/outcome-compensation-review-final-optional.json)、[有效结果摘要](/tmp/outcome-compensation-review-final-summary.json)。
- [开始核验](/tmp/outcome-compensation-review-start.json)、[结束核验](/tmp/outcome-compensation-review-end.json)。

## 证据边界

合成 review pass 只是对门禁的受控输入，不是真实 reviewer 对业务的认可，也不是真实模型效果验证。实际 CLI repair、test、review、close、topic complete 及退出码证明的是这些工程合同；临时玩具仓库不证明私有业务需求已经完整验证。

本 reviewer 未重跑全量 suite、未安装真实 host、未验证真实模型业务行为。root 报告其四片完整 suite 为 352 tests / exit 0 / 231.065s，并核验源码与 final-01 匹配；这是 root 提供的独立工程证据，不列作本 reviewer 自行执行或核验的测试。此次复审未扩展安装、性能或模型能力边界，也未改写旧 Ticket/审查结论。
