# AC20–22 installer/doctor 修复独立复审

结论：原 F1、F2、F3 的具体反例已在独立临时 fixture 中验证修复；相关合法恢复未观察到退化。但发现 **1 个 P1 阻塞项 R1**：首次安装未拒绝 runtime 的 symlink 父目录，会写出预期安装目录并返回 `installed`。这属于本次 F3 路径保护及宿主归属边界，不能据此宣称 AC22 的相关保证已全部满足。

这是普通工程审查，未通过 workflow Skill/runtime 管理施工或签发验收。审查者未参与修复，未读取作者修复总结；依据修复 diff、候选源码、原具体反例和 Spec 判断。没有编辑主仓库或冻结源码，没有操作真实宿主。

## 最终输入身份与输入修正

- 唯一最终源码：`/tmp/outcome-review-install-repair-02b`。
- `source-manifest.json` SHA256：`1775f5169a33cf5be57545414e27adf1b7e1b344e8babd11f5dc6b94866c6b97`，与用户最终指定值一致。
- 初次读取 02b 与审查结束均逐文件校验：**280 条记录、280 个独立路径、0 缺失/类型/字节摘要不匹配**。最终核验命令 exit 0。身份记录：`/tmp/outcome-review-install-02-identity.json`。
- 最初指定的 02 清单本身 hash 与当时指定值一致，但其中 5 条 policy/adapter 记录核验失败，**未通过完整性检查**。用户指出旧清单构造错误后，立即停止使用 02，改用 02b。先前只读取得的 installer/doctor/diff 信息保留，02b 重新核验了对应字节；所有实际探针与回归均从 02b 导入。用户先报 281，随后更正为 280，本报告采用实际 280。

| 输入 | SHA256 |
|---|---|
| `tools/workflow_lib/installer.py` | `9a1df65ebfb2c51379be51150299049cf42eddd234d63b39432ac7396bc76383` |
| `tools/workflow_lib/doctor.py` | `705bc8c84f94c08188bc563b919e0fd98a0aaf9ddb57310674c04c3520484fc3` |
| `tests/test_install_simplification.py` | `670217c5d5179e6b79b037b2d3b16a6aeaba9728e7df9314ad8125bd4447c6a8` |
| `repair.patch` | `08956e487cd1f6b5a4de7cae70b4f027f0a7427fb635e03893dbf75663ca4198` |
| `prior-findings.md` | `2e4d66c06fd1cb3f64ae18f9acd9631c9a46b8d28444b57fa3d927abb781e773` |
| Spec revision 2 | `efd7c71b787657623b1d5d58a817330cdbf32b5f532b5d55192db2c3cbe72d13` |

需求依据：`/tmp/outcome-review-install-repair-02b/.agent/work/workflow-outcome-optimization/specs/specs-workflow-outcome-optimization-02.md:165`（4.10）及 `:243`（AC20–22）。范围限 installer/doctor 修复 diff 与相关恢复、宿主归属、摘要/验证计数；其他集成模块不作结论。

## 阻塞项 R1 · P1 · 首次安装沿 runtime 父目录 symlink 写入外部，仍返回 installed

**位置**：`/tmp/outcome-review-install-repair-02b/tools/workflow_lib/installer.py:123`（新 `_runtime_inventory`）、`:984`（runtime 创建/移动）、`:1001`（最终检查）、`:1016`（receipt 入口 resolve）。归属检查在同文件 `:133`，但仅在已有状态验证/恢复时调用，首次安装提交前未调用。

**触发**：临时空宿主 `home` 预置 `home/my-matt-workflow/runtime -> outside`；`outside` 是同一临时 fixture 内的另一目录。安装完整有效新 manifest 的 v1 release。

**实际行为**：

1. `runtime_dir.parent.mkdir(exist_ok=True)` 接受父目录链接。
2. `staged_runtime.rename(runtime_dir)` 将 runtime 写入 `outside/v1`。
3. `_runtime_inventory(runtime_dir)` 检查 runtime 根自身与后代，却没有检查父路径/根的 canonical 归属，普通文件清单完全匹配，最终检查通过。
4. receipt 使用 `runtime_entry.resolve()` 记录外部入口；事务清理完毕，安装返回 `installed`。
5. doctor 随后报 `invalid`，再次安装也拒绝。后置拒绝不能撤销首次外部写入及错误成功结果。

独立探针实际输出：

```json
{"probe":"runtime-parent-link-detail","first_result":"installed","outside_written":true,"entry":"outside/v1/tools/workflow.py","doctor":"invalid","doctor_reason":"托管 runtime 入口不属于安装目录","second":{"error_type":"InstallError","error":"托管 runtime 入口不属于安装目录"}}
```

另一普通探针也确认 `my-matt-workflow` 本身预置为链接时会返回 `installed` 并写外部。这是相同祖先路径缺口的补充证据，不扩大到其他模块。

**影响与归因**：AC22 要求路径/链接与托管归属保护；本次 F3 修复的实际 runtime 检查仍漏祖先链接，新增归属校验只覆盖有 receipt 的后续操作。该安装写入路径缺口既有，**不宣称是本补丁新引入**；本次报告将其列为明确要求复审的 runtime 路径/宿主归属边界。未执行任何外部 runtime，也未证明任意代码执行。

**修复方向**：在创建 state/transaction 或移动 runtime 前核验内部 state/runtime 路径的既有祖先，拒绝内部 symlink 与非预期 canonical 目的地；最终提交前再核验入口属于当前宿主的预期 runtime 根。不能只在写出目标后报错。临时回归应断言拒绝时 outside 字节与宿主 receipt 均未被安装改变。

## 原反例与合理边界的独立结果

独立脚本自行构造两个旧 Skill、改变/删除/新增 Skill、host/state/release，并在实际 `Path.rename`、state replace、ownership refresh 后抛出 `KeyboardInterrupt`。只 patch 中断 seam 或调用计数；内容正确性直接比较 fixture 字节与持久状态，未将新增 tests green 当作修好依据。

| 检查 | 实际结果 |
|---|---|
| F1：旧 manifest 去掉 `target_manifests` 与 `source_input_digest`，同版 runtime 修改、删除、额外普通文件 | portable/codex/cursor/claude 全部拒绝；doctor 各自 invalid；install-state 字节未改。干净旧包同版均 current。 |
| F3：实际 runtime 额外 symlink | 新 manifest 四种投影均拒绝且宿主树未改；旧 manifest 四种投影也拒绝。另验证 dangling link、`__pycache__` symlink、FIFO 均拒绝。 |
| 合法执行副产物 | 普通 `__pycache__/demo.pyc` 与 `.DS_Store` 被忽略，四种投影均 current / doctor valid；链接型副产物仍拒绝。 |
| F2：备份损坏后恢复 | 在备份移动后、登记刷新前/后等时点损坏旧备份，恢复拒绝；比较 recovery 调用前后的旧/新目标、事务全文件与 state，全部不变。事务及损坏材料保留。 |
| 正常升级合法中断 | 第一份/最后一份旧目标移动、第一份新目标移动、move 后刷新、runtime 移动、state commit 后共 6 个时点；未提交时恢复旧实际字节与旧 state，已提交时保持 v2 并清理事务。同时覆盖旧名称删除、新名称增加。 |
| 老 v4，无 `previous_state_sha256` | 在 fixture 中去掉新字段并重新登记可信 journal 控制，6 个中断时点验证；正常材料恢复/清理成功，损坏材料拒绝且保留。未假装重新登记后的 journal 自带备份字节可信性。 |
| skills_home 迁移 | 第一份新目标移动、最后一份旧 home 备份移动、登记刷新、runtime 移动、commit 共 5 个时点；合法未提交迁移恢复原 home 字节、清空新 home，合法 committed 保持新 home。损坏材料拒绝且不改变两端。 |
| 初次安装中断，无 previous state | 新 Skill 移动、登记刷新、runtime 移动、commit 4 个时点；前三者清理未提交 Skill 且不造 state，commit 后核验 v2 并清理。未提交时可能保留未引用的 v2 runtime，本报告不声称清除了全部孤立 runtime。 |
| 恢复过程再次中断 | 普通升级、迁移、v1 install-state 三种情形，在第一次 backup 恢复 rename 后再中断；再次恢复成功，原字节/原 state 恢复，事务清理。 |
| committed 内容损坏 | 普通升级、迁移、老 v4 的 committed 新目标损坏均拒绝，目标/state/事务均保持调用前内容；合法 committed 恢复实际保持 v2。 |
| 旧 state/source 身份漂移 | 改写旧 state 合法字段触发旧状态 hash 拒绝；旧 release 字节改写触发 release 校验拒绝；恢复未写目标/事务/state。 |
| runtime receipt 指向其他目录 | 复制相同 runtime 字节至其他 fixture 目录，仅改 receipt 入口；安装拒绝、doctor invalid。与 R1 一致，已有 state 的归属检查有效，首次安装仍有缺口。 |

主探针 78 项，补充探针 11 项，共 **89 项场景观察/断言**；上述 R1 为脚本如实记录的失败保证，脚本 exit 0 不表示 R1 通过。

## 实际计数与局部阶段耗时

同版 `install_release` 的 `verify_release` 完整验证实际 1 次；正常 v1→v2 升级 2 次，分别对应旧/新包；doctor 用同一个 context 检查两宿主同包时 1 次，两宿主分别引用旧/新包时 2 次。一个宿主 runtime 损坏时，结果独立呈现 a=valid、b=invalid。

另一次稳定小 fixture 的实测如下（秒；单次局部取样，不是端到端 benchmark）：

| 阶段 | `verify_release` 次数 | `source_manifest` 次数 | 耗时 |
|---|---:|---:|---:|
| 首次安装已有包 | 1 | 0 | 0.075252 |
| 同版 current 安装 | 1 | 0 | 0.042669 |
| 两宿主同包只读诊断 | 1 | 0 | 0.038345 |
| 可信构建输入摘要比较 | 0 | 0 | 0.005827 |
| 缺 `source_input_digest` 的完整比较回退 | 0 | 1 | 0.022215 |

最后两项直接调用 `release_matches_source`，**不是独立完整 release 验证入口**，0 次 verify 不表示包已验证；调用方仍需验证包。回退实验仅去掉摘要，保留 target manifests，实际返回 true。完全旧 manifest 的安全安装另由 F1 独立矩阵覆盖。

AC20 正常变化 deploy 的一次实际 fixture suite、失败不发布以及 AC21 无变化 deploy 仍 check 的机制由相关现有回归覆盖；本次未另开展全库 deploy 性能实验，也不预填提速比例。

## 命令、退出码与证据

所有 shell 调用 `login:false`；源码读取及 Python 导入路径均为绝对路径。Python 使用 `-B` 和 `PYTHONDONTWRITEBYTECODE=1`，fixture 自动清理；没有向冻结源码生成 bytecode。

| 执行 | 最终退出码 | 证据 |
|---|---:|---|
| `PYTHONDONTWRITEBYTECODE=1 python3 -B /tmp/outcome-review-install-02-probes.py` | 0 | `/tmp/outcome-review-install-02-probes.jsonl`，78 项，19.440 秒；stderr 空 |
| `PYTHONDONTWRITEBYTECODE=1 python3 -B /tmp/outcome-review-install-02-extra-probes.py` | 0 | `/tmp/outcome-review-install-02-extra-probes.jsonl`，11 项，3.028 秒；stderr 空 |
| `python3 -B -m unittest tests.test_install_simplification tests.test_workflow.InstallerTests tests.test_doctor`（PYTHONPATH=02b，cwd=02b，上述 bytecode 环境） | 0 | `/tmp/outcome-review-install-02-regression.txt`，38 tests / 4.838 秒 / OK |
| 5 项相关 security/packaging 回归（下列选择） | 0 | `/tmp/outcome-review-install-02-boundary-regression.txt`，5 tests / 5.571 秒 / OK |
| 独立阶段计数/计时普通 Python 探针 | 0 | `/tmp/outcome-review-install-02-stage-counts.json` |
| 最终 280 文件身份复核 | 0 | `/tmp/outcome-review-install-02-identity.json` |

5 项选择：`tests.test_security_hardening.SecurityHardeningTests` 的 `test_v4_recovery_accepts_legitimate_transaction_content_drift`、`test_three_hosts_install_exact_declared_target_inventory`、`test_installed_state_ignores_bytecode_and_finder_artifacts`、`test_install_rejects_tampered_target_manifest_and_cleans_staging`；以及 `tests.test_skill_packaging_v2.PackagingV2Tests.test_three_host_installs_use_declared_invocation_permissions`。

共有 **43 项相关仓库回归通过**。回归日志中故意失败的子 suite 是 failure-gate 用例的预期输出，顶层 unittest exit 0；不将该输出隐藏或当真实发布成功。

探针编写阶段有三类 harness 修正，未计为候选代码缺陷：`/tmp` 与 `/private/tmp` canonical 路径断言不一致（exit 1）；fixture 的 `extra.txt` 未从 Skill 引用，build preflight 拒绝（exit 1）；补充摘要实验同时删除 target manifests 后错误期待完整内容比较仍 true（exit 1，原 stderr 保存为 `/tmp/outcome-review-install-02-extra-probes-initial.stderr`）。已修正为 canonical 身份、有效 fixture 引用、仅缺摘要的回退场景，并从头复跑得到上表最终结果。没有改候选源码来让探针通过。

## 未验证边界与建议

- 未运行全库 suite，留给主 Agent 统一执行；未运行 workflow 治理命令或 Skill。
- 未安装、迁移、切换或执行真实 host runtime；所有 host 及 symlink 外部目录都是本次临时 fixture。
- `KeyboardInterrupt`/相关现有 `SystemExit` seam 是进程内中断模拟，不等价于 kill -9、断电、fsync 丢失或跨设备 rename；未开展多进程竞争/TOCTOU 全时序分析。
- 旧 release 不可用或内容漂移时 fail closed；本次未承诺能在丢失信任材料的情况下自动完成回滚。
- 没有复审后续 runtime/指令集成修复，未以其测试或未测试状态改变 installer 字节结论。
- 建议将 R1 的预置父目录 symlink 反例加入相关回归，并保留拒绝前外部目录未变的断言；其余无本次范围外阻塞发现。

## 最终集成冻结 03 的身份对照

用户在审查结束前提供 `/tmp/outcome-review-final-03`，说明集成 full suite 的 325 项中有一项技术设计 routable entry 旧断言失败，主 Agent 仅修正该断言并定向通过。该执行状态来自用户消息，本审查者未自行复跑或独立核验完整 suite 结果。

只读身份对照实际 exit 0：03 manifest SHA256 `c8af43e2c97ed827f697d336f8a3c87365a6b49318be6281b9034990cc10cfa2` 与指定值一致，登记 280 文件全部逐字节核验，0 不匹配。03 与已审 02b 的以下 **10 个相关生产文件逐字节相同**：`tools/workflow_lib/{installer,doctor,release,projection,fs_safety,release_references,source_walker,validator,check}.py` 和 `tools/workflow.py`；专属 `tests/test_install_simplification.py` 也相同。完整对照：`/tmp/outcome-review-install-02-final03-comparison.json`。

因此保持本报告的 02b 探针身份和审查结论；R1 同样适用于这些相同生产字节的最终 03。没有改用 03 冒称探针曾在那里运行，没有重复全范围审查或全量 suite。

最终意见：**原三项反例修复有效；因 R1，不通过本次相关 AC22 路径/宿主归属边界复审。** 源码、快照与真实宿主均未修改。
