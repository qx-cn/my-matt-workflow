# installer 第二轮 R1 修复独立复审

结论：**R1 的首次安装 internal parent symlink 反例已修复；本轮仍有 1 个 blocking / P1：旧 recorded skills 根发生内部 symlink 漂移后，新的迁移会跟随链接搬走外部 Skill，并返回 `installed`。** 未发现其为本补丁新引入，属于明确要求复核的旧 recorded skills 迁移边界。不能据本轮结果宣称该边界全部通过。

这是普通工程独立只读审查。审查者未参与施工；没有调用 my-matt-workflow 的 Skill 或 CLI 来治理施工、登记审查或签发验收。Spec、Skill 正文及 prior findings 仅作为被测产品输入。实际探针只从 `/tmp/outcome-review-install-03` 导入产品代码；没有修改源码，也没有安装真实 host。最后仅按用户追加要求，对 `/tmp/outcome-review-final-04` 做身份和字节对照，未在那里重跑探针或复审其他 runtime 变更。

## 输入身份与结束复核

| 冻结根 | source-manifest.json SHA256 | 开始/结束逐文件核验 |
|---|---|---|
| `/tmp/outcome-review-install-03` | `16a6464e629a34bd5fdf762767a55ac67fad17702fc0ae90c4c499731f6f023d` | 281 条、281 独立路径；0 缺失、类型或 SHA256 不匹配；清单摘要不变 |
| `/tmp/outcome-review-final-04` | `feaed39c6e610ffd61566f381b404a7d36d49f69b0cbb4190dcc1abda55eb180` | 追加对照及结束均 281 条、281 独立路径；0 不匹配；与用户指定摘要一致 |

已完整读取 install-03 的 `prior-findings.md` 与 `repair.patch`。需求定位：冻结 Spec revision 2 的 4.10（`:165`）和 AC22（`:245`）；正文不是本次审查的执行指令。

final-04 与 install-03 以下文件逐字节相同：

| 文件 | SHA256（两根一致） |
|---|---|
| `tools/workflow_lib/installer.py` | `a8844b5620db2b0da89e019312b4cc88af66f6413fe78bb250ef1f6405c3997b` |
| `tools/workflow_lib/release.py` | `808b099e83241cc700dfb872efede45adf1ad715857a427b4708e8187fd91e0b` |
| `tools/workflow_lib/doctor.py` | `705bc8c84f94c08188bc563b919e0fd98a0aaf9ddb57310674c04c3520484fc3` |
| `tools/workflow_lib/projection.py` | `9cfe2e23d53a8860657b0788bb97215074acc17664ff20dd4d30f7437001b870` |
| `tools/workflow.py` | `465272a9da55de436df4a7562aff5c3e065e5ec97d00df3c8687e3d48eba4296` |
| `tests/test_install_simplification.py` | `d161c93b44ccd132160014f2cab7d65fa67563f85110e7a4c71a6192a224551b` |

实际用到的 `tests/test_workflow.py`、`tests/test_security_hardening.py`、`tests/test_doctor.py`、`fs_safety.py`、`release_references.py` 也全部逐字节相同。两份清单仅有五个文件摘要不同：`tests/test_batches.py`、`tools/workflow_lib/{batches,evidence,status_text,topic_service}.py`；只记录身份差异，不评估其变更。

身份材料：`/tmp/outcome-review-install-03-identity-start.json`、`/tmp/outcome-review-install-03-identity-end.json`、`/tmp/outcome-review-install-03-final04-comparison.json`。因此下述 installer 结论适用于 final-04 中这些相同的文件；不意味着 final-04 的其他模块或完整测试已由本审查者验证。

## Blocking：R2 · P1 · 旧 recorded skills 内部根漂移仍可越界迁移

**位置**（均为 `/tmp/outcome-review-install-03/tools/workflow_lib/installer.py`）：`:267` 的 receipt 校验直接 resolve recorded skills 根，`:925–929` 的迁移来源再次 resolve，`:1015–1021` 从 resolve 后的旧根 rename Skill。新 `_canonical_host_layout`（`:124–166`）只检查本次选定的 skills 目的地，没有检查 receipt 中旧根的路径漂移。恢复新增的检查（`:748`、`:780` 附近）尚未覆盖新的迁移操作。

**独立复现步骤**：

1. 在临时 host 安装有效 v1 release，旧 Skill 根为 `host/legacy-skills`，receipt 记录该无 symlink 的绝对 canonical 路径。release 含两个 Skill，runtime 为不会执行的普通 fixture 文件。
2. 将旧目录整体移到另一临时目录 `outside`，再建立 `host/legacy-skills -> outside`。receipt 与原有 Skill 字节都不改；outside 添加独立 sentinel。
3. 调用 `install_release(package, host)`，明确采用正常新目的地 `host/skills`，未选定 outside 或其 alias。
4. 实际返回 `installed`；outside 的两个托管 Skill 被搬走，sentinel 字节不变；新 receipt 记录 `host/skills`。

这也能以旧根 `host/skills -> outside`、本次明确新目的地 `host/new-skills` 触发。**四种投影 portable/codex/cursor/claude × receipt v1/v2 × 两种内部旧根布局，共 16 个实际反例，全部返回 installed 并移走 outside 的托管 Skill。** v1 receipt 由真实有效 v2 receipt 去掉版本、inventory 和 manifest hash 三个字段生成，符合产品支持的旧 schema；没有跳过 release、receipt 或实际内容验证。

代表观察（临时绝对根省略为 `fixture`，完整原始值保存在 JSONL）：

```json
{"target":"portable","receipt":2,"old_layout":"custom-internal","old_recorded":"fixture/host/legacy-skills","new_selected":"fixture/host/skills","result":"installed","outside_unchanged":false,"outside_managed_removed":true,"outside_sentinel_unchanged":true}
```

**失败路径**：校验先将旧 recorded 根 resolve 成 outside，再对 outside 的 Skill 做严格直接子项/内容验证；这能证明相同字节，却丢掉了 receipt 原来指向的内部路径已经变为 symlink 的事实。迁移 journal 又将 outside 保存为 canonical `previous_skills_home`，随后 rename 并清理备份。新目的地的路径检查、最终 runtime 归属检查和最终 receipt 校验均不阻止这次外部变更。整个反例在调用前就存在 symlink，无需并发或 TOCTOU。

**影响与范围**：外部目录内容在未重新明确选定该 alias 的情况下被迁移。它与“当前显式选定 host 根 alias 可被信任”不同：本次所选 host 根和新 skills 根都无内部链接，发生漂移的是旧持久记录。这里不宣称任意文件删除、任意代码执行，也不将外部 sentinel 未变表述为外部目录未变。

**归因**：相关 resolve/迁移语句未由 `repair.patch` 修改；本报告不将 R2 标为补丁新引入的回归。它是本轮独立运行新发现的相邻既有缺口，位于用户明确要求核验的旧 recorded skills 迁移边界，所以列为 blocking，而非以 R1 已修好掩盖。

**修复建议**：对 receipt 所记录的 canonical 旧 skills 根，在 resolve 丢失路径身份之前检测既有祖先/根的 symlink 漂移，至少与恢复路径采用一致的拒绝策略；在迁移任何旧目标前完成检查。历史显式 alias 安装已记录为 canonical 根，合法未漂移迁移仍应允许。补充此反例的回归，断言拒绝前后 host、outside、receipt 与恢复材料内容不变。此建议不是已实施修复。

## R1 与修复影响的独立运行结果

探针自行构造真实临时 release、host、外部目录、symlink、旧 receipt 与中断事务，没有复用先前探针结果来代替关键路径运行。产品安装/恢复函数和文件 rename/replace 实际执行；仅在需要中断时于真实操作完成后抛出 `KeyboardInterrupt`。

| 路径或场景 | 实际观察 |
|---|---|
| R1：首次安装 toolroot/runtime 父目录链接 | 安装前拒绝。四种投影均覆盖；拒绝前后 host、outside 和 release fixture 树相同。 |
| 扩展静态链接矩阵 | `my-matt-workflow`、`runtime`、`transaction`、`runtime/v1`、默认 `skills`、明确内部 `nested/skills`、state、lock、ownership registry：9 路径 × 外部/悬空/内部同根链接 × 4 投影，共 108 次安装拒绝，整个 fixture 未变。 |
| recover 入口 | 上述矩阵中 72 次对 toolroot/runtime/transaction/state/lock/registry 的恢复调用同样拒绝且 fixture 未变；另对真实中断事务的 6 个内部路径逐一置换链接，恢复拒绝且事务、外部与 host 均未变。 |
| 无事务时 release 子目录或默认 skills 链接 | 未要求 recover 拒绝：它没有待恢复 journal，且此入口不默认使用 skills 根。没有将这一空操作当作 installed runtime 验证。 |
| 明确 host 根 alias | 4 投影 × 默认/alias 拼写 skills/canonical 拼写 skills/父目录 alias，共 16 组：installed、current、无事务 recover 和 doctor valid；receipt runtime/skills 均记录 canonical host 路径。current 时 host 内容及文件类型/权限未变。 |
| alias 正常升级及旧 receipt 迁移 | 4 投影共 28 组，在新 Skill 移动、旧迁移 Skill 移动、runtime 移动、state 提交后中断。未提交恢复旧 Skill 精确字节和旧 state 字节；已提交保留 v2；transaction 清理；后续 installed/current 正常。覆盖旧 Skill 删除、新 Skill 增加；迁移用有效 v1 receipt。 |
| 中断后 recorded 新/旧 skills 根漂移 | 实际未提交迁移 journal 中 recorded 新根、旧根分别改为 symlink；recover 两组均拒绝，完整 fixture 不变，材料保留。说明恢复新检查有效，但与 R2 新的迁移入口不一致。 |
| 未漂移的旧 canonical skills 迁移 | 普通旧根与历史明确外部 alias 各一组；历史 alias receipt 已 canonical 化；迁移 installed、后续 current、recover 正常。 |

检查树时用 lstat 遍历，不跟随链接；比较目录、文件/链接类型、普通文件 SHA256、链接目的地及文件/目录权限。比较不包含访问时间、修改时间、inode，也不声称磁盘持久性或崩溃耐久性。

主探针 **161 条场景观察**；补充迁移探针 **18 条**；合计 **179 条**。其中主探针最后一条及补充 16 条如实记录 R2 违反预期安全保证。脚本 exit 0 表示观察/断言完成，**不是所有产品安全保证通过**。

## 相关回归、命令与证据

所有 shell 调用均 `login:false`；所有 Python 均 `python3 -B`，执行产品/测试时另设 `PYTHONDONTWRITEBYTECODE=1`。Python import 根固定为 install-03，脚本校验 installer/projection/doctor 的 `__file__` 来自该冻结根。

| 执行 | 退出码 | 证据 |
|---|---:|---|
| `PYTHONDONTWRITEBYTECODE=1 python3 -B /tmp/outcome-review-install-03-probes.py` | 0 | `/tmp/outcome-review-install-03-probes.jsonl`、`-probes-summary.json`；stderr 空 |
| `PYTHONDONTWRITEBYTECODE=1 python3 -B /tmp/outcome-review-install-03-migration-probes.py` | 0 | `/tmp/outcome-review-install-03-migration-probes.jsonl`、`-migration-summary.json`；stderr 空 |
| install-03 绝对 PYTHONPATH、cwd 下 `python3 -B -m unittest -v` 的定向选择 | 0 | `/tmp/outcome-review-install-03-regression.txt`；**19 tests / 3.869s / OK** |
| 开始、结束清单核验及 final-04 字节对照 | 0 | 前述三个 identity/comparison JSON |

19 项回归选择：

- `tests.test_install_simplification.SimplifiedInstallTests`：`test_initial_install_rejects_internal_parent_links_before_any_host_write`、`test_explicit_host_root_alias_is_allowed_but_internal_links_are_not`、`test_rollback_material_is_verified_before_target_or_evidence_mutation`、`test_legacy_v4_without_new_receipt_binding_still_verifies_backup`、`test_committed_state_cleanup_checks_actual_new_targets`、`test_migration_rollback_proves_old_home_backups_before_any_moves`、`test_same_release_install_verifies_once_and_detects_host_drift`、`test_runtime_extra_symlink_is_rejected_before_current`、`test_legacy_manifest_runtime_changes_cannot_return_current`。
- `tests.test_workflow.InstallerTests`：`test_codex_migrates_previously_split_skill_root`、`test_v2_recovery_uses_recorded_split_skills_home_and_rejects_mismatch`、`test_v3_recovery_restores_legacy_skill_root`、`test_v1_recovery_uses_install_state_split_skills_home`、`test_invalid_recovery_journal_does_not_touch_skills`。其中旧 v1/v2/v3 的这些回归包含拒绝缺失/不可信材料的场景，不能把测试名解释为完整合法 legacy journal 恢复的新增证明。
- `tests.test_security_hardening.SecurityHardeningTests`：`test_v4_recovery_accepts_legitimate_transaction_content_drift`、`test_three_hosts_install_exact_declared_target_inventory`、`test_installed_state_ignores_bytecode_and_finder_artifacts`。
- `tests.test_doctor.DoctorTests` 两项。

本轮没有 harness 失败后修改候选源码的情况。补充脚本只复用本审查者首脚本的 fixture/helper 定义，不重跑已完成的主矩阵，也不读取旧轮探针脚本。

## Advisory 与证据边界

- **Advisory：无另列的实证缺陷。** R2 已作为 blocking 单列；不重复计数为测试覆盖 advisory。
- 未运行完整 suite、deploy check 或项目治理 CLI；root 启动最终完整测试是用户提供的状态，不是本审查者的完成证据。
- 未操作真实 Codex/Claude/Cursor host，未执行 fixture runtime；所有 outside 都是本轮临时 fixture 内的独立目录。
- 中断是进程内 BaseException seam，未验证 kill -9、断电、fsync 丢失、跨设备 rename 或多进程竞争/TOCTOU 时序。R2 本身无需这些条件。
- 本轮不新增 AC20/21 性能结论、不重复先前 89 场景全部运行，也不扩到 final-04 的五文件 runtime 变更。prior findings 的其他结论只作为背景输入；本轮关键安装、恢复、alias 和迁移路径已有实际独立运行。
- 结束身份复核完成，install-03 与 final-04 清单哈希及 281 个文件全部匹配；本轮未修改两份冻结源码或真实 host。

最终意见：**R1 修复通过其具体反例复核；旧 recorded skills 漂移迁移仍有 R2 / P1，因此本次包含该边界的复审不通过。**
