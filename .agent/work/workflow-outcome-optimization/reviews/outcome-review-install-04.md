# installer 第三轮 R2 修复独立复审

结论：**本轮限定的 R2 / P1 修复复审通过；blocking 0，advisory 0。** 原「旧 recorded skills 内部根变成 symlink，迁移跟随链接搬走 outside Skill」反例的 16 个组合均已实际复跑并在任何安装写入前拒绝。祖先目录链接也被拒绝；合法历史 host 根 alias 与未漂移 canonical 外部旧根仍可迁移。集中持久路径 identity 函数在本轮范围内未漏掉当前反例。

这是普通工程独立只读复审。审查者未参与候选施工，没有调用 my-matt-workflow Skill 或 runtime 治理施工、登记结果或签发验收。仅调用被冻结产品的 installer/projection 等库作为被测对象。唯一源码输入是 `/tmp/outcome-review-final-05`；没有读取其他冻结根的源码、旧探针脚本或施工工作树来替代本轮执行。完整读取该根的 `prior-findings.md`、`repair.patch`，并核对冻结 Spec revision 2 的 4.10 与 AC22，作为被测需求输入。没有修改候选源码。

## 身份核验

开始与结束均逐条核验 `source-manifest.json` 的 **281 条、281 独立路径**：普通文件类型及 SHA256 全部匹配；0 缺失、0 类型错误、0 摘要不匹配。清单本身、prior findings 和补丁摘要前后相同。结束未发现 `.pyc`。

| 输入 | SHA256 |
|---|---|
| source-manifest.json | `4cc4bce59526ea168f0b7f75eebe6b07b595bfd080e6091619561826e956ad03` |
| prior-findings.md | `8e16ce98403afb84df6a27be41dc912d99ee99e3e9352178b75ea4dbc6a1a62f` |
| repair.patch | `0c116d7f0f1d551ec8cf7337f66933825e4ac4b2ff15aea86e3da1c71c63e643` |
| tools/workflow_lib/installer.py | `178dce96f42fe472edb8fca63d0762e0217b068b9913aaaed629eb799f6c35a2` |
| tools/workflow_lib/projection.py | `9cfe2e23d53a8860657b0788bb97215074acc17664ff20dd4d30f7437001b870` |
| tools/workflow_lib/fs_safety.py | `9e647129421bf428f97dbf45400665222d85872edfebca02164af9562b06c4c9` |

身份原始材料：`/tmp/outcome-review-install-04-identity-start.json`、`/tmp/outcome-review-install-04-identity-end.json`。后者还记录所有导入的 `tools.*` 模块绝对路径，全部来自指定冻结根。这里核验的是用户提供冻结根与其清单的内容一致性，没有额外的上游签名或 Git 来源认证材料。

## Blocking

**无。** 没有在指定 R2 与受影响 verify/recover 范围内发现仍可越界搬走 outside 内容的实证反例，也没有观察到本补丁误拒上述合法历史迁移或恢复。

## 收敛实现评价

以下位置均为 `/tmp/outcome-review-final-05/tools/workflow_lib/installer.py`：

- `:169–185` 的 `_recorded_directory` 在 resolve 前检查根本身及全部祖先的 symlink，然后核对 canonical identity 与目录类型；没有将「已有路径 resolve 后字节正确」当作记录身份未漂移的证明。允许不存在的 canonical 目录，给已验证备份的恢复保留空间。
- `:188–191` 的 receipt 根检查由公开安装入口 `:1138–1140` 在创建 state 目录、获取写锁、登记安装引用之前调用；内部安装 `:929–931` 再检查。原 R2 现在在外层入口拒绝，独立运行确认旧锁不会被重新创建。
- `:292` 的独立 verify、`:953` 与 `:1042` 的迁移旧根，以及 recovery 的 `:702`、`:774`、`:781`、`:804`、`:818` 使用同一持久路径身份规则。当前显式选择路径仍由 `_canonical_host_layout` canonical 化；历史明确 alias 写入 receipt 后已成为 canonical 根，所以这些合法历史没有被一概拒绝。

上述是代码路径解释。通过结论来自下面的真实文件操作及前后比较，**不是代码形状、候选测试正文或作者摘要本身**。没有把该 helper 解释为 inode 身份、并发原子性或任意所有权验证的替代物。

## 独立实际运行

本审查者从零编写临时 release fixture：两个托管 Skill，各有 metadata 与独立 payload；runtime 是不会执行的普通 fixture 文件。release 清单、v2 receipt 及文件字节均由实际安装验证。v1 receipt 只从有效 v2 receipt 删除 `version`、`managed_inventory`、`manifest_sha256` 三字段，再通过产品 legacy 验证；没有跳过校验或使用伪造成功返回值。

| 场景 | 次数 | 实际结果 |
|---|---:|---|
| 原 R2：receipt v1/v2 × portable/codex/cursor/claude × old custom/default internal root；合法新目的地为 host/skills 或 host/new-skills | 16 | 将旧根整体 rename 到 outside 并建立旧根 symlink。删除旧 `.install.lock` 后，独立 verify 与 install 均抛 InstallError；完整 fixture 不变，锁未重建，新目的地未创建，transaction 的不存在状态未变。 |
| recorded skills 祖先目录 link 漂移，v1/v2 × 四投影 | 8 | 将 host/nested 整体移至 outside，建立 nested symlink；verify、install 均拒绝，完整 fixture 不变。 |
| 合法历史明确 host 根 alias，v1/v2 × 四投影 | 8 | receipt 先记录实际 canonical host/runtime/旧 skills 根；经 alias 选择默认新目的地迁移 installed，后续 current，无事务 recover；托管字节一致，旧根 sentinel 保留。 |
| 合法历史明确外部 skills alias，receipt 已记录另一目录的 canonical 外部旧根，v1/v2 × 四投影 | 8 | 外部旧根没有漂移；迁移 installed，随后 current 与 recover 正常；只搬走两项托管 Skill，sentinel 字节保留。 |
| 真实未提交 v4 迁移事务：新/旧 recorded skills 根 × 根/祖先 link × 旧 receipt v1/v2 | 8 | 在真实 old Skill rename 完成后用 KeyboardInterrupt 留下 journal/备份；再设置漂移。直接 recover 拒绝，host、outside、receipt、transaction 和整个 fixture 不变。 |
| v4 合法迁移中断恢复：未提交/已提交 × canonical 内部/外部旧根 × 旧 receipt v1/v2 | 8 | 未提交恢复精确旧 Skill 树与原 receipt 字节；已提交保留 v2；transaction 清理，后续 installed/current 正常。 |
| recorded runtime 根/祖先漂移 × receipt v1/v2 | 4 | 独立 verify 与 install 均拒绝，整个 fixture 不变；删除的 host 锁未重建。 |
| 合法 legacy journal v1/v2/v3 × receipt v1/v2 | 6 | 自建真实匹配 backup 与 partial target；恢复精确旧 Skill 字节，原 receipt 不变，transaction 清理，独立 verify 正常。 |
| legacy journal v1/v2/v3 × receipt v1/v2 × recorded 旧根/祖先 link | 12 | 直接 recover 拒绝且整个 fixture、receipt、transaction 不变。v1 使用 receipt 根，v2 使用 journal 根，v3 使用 previous_skills_home。 |
| 已搬完所有旧 Skill、canonical 旧根目录已移空并删除；内部/外部 × receipt v1/v2 | 4 | 实际执行两个旧 Skill rename 后中断；删除空旧根，recover 从已验证备份重建目录，恢复原 Skill 树和 receipt，transaction 清理。 |
| 真实已提交 v4 事务的 recorded 新根/祖先漂移 × 旧 receipt v1/v2 | 4 | recover 拒绝；提交后的 receipt、transaction、outside 和 host 全部保持调用前状态。 |

共 **86 条独立场景观察，86 通过**。其中有 80 次实际拒绝调用，每次均进行完整 fixture 前后比较；其余场景验证合法迁移/恢复。不是以前 179 场景矩阵的重新执行。

拒绝比较通过 lstat 递归，不跟随 symlink：包含目录和文件类型、文件/目录权限、普通文件 SHA256、链接目的地；遍历整个本轮 fixture，因此同时包含 host、outside、release、receipt 与 transaction。比较不包含 inode、时间戳、ACL/xattr 或磁盘耐久性。中断 seam 只在真实 rename/replace 已完成后抛 BaseException；release/receipt 校验、实际迁移与回滚未 mock。

## 执行记录与定向回归

所有 shell 均 `login:false`；所有 Python 均 `python3 -B`，执行产品探针及测试另设 `PYTHONDONTWRITEBYTECODE=1`。未调用项目治理 CLI 或完整 suite。

| 实际命令/选择 | 退出码 | 证据 |
|---|---:|---|
| `PYTHONDONTWRITEBYTECODE=1 python3 -B /tmp/outcome-review-install-04-probes.py` | 0 | 60 场景；`-main-probes.jsonl`（原主日志的完整保留副本）、`-probes.jsonl`、`-probes-summary.json`、`-probes.stdout`；stderr 空。 |
| `PYTHONDONTWRITEBYTECODE=1 python3 -B /tmp/outcome-review-install-04-recovery-probes.py` | 0 | 26 场景；`-recovery-probes.jsonl`、`-recovery-summary.json`、`-recovery.stdout`；stderr 空。仅复用本轮首脚本 helper 定义，没有重跑主矩阵。 |
| cwd 与 PYTHONPATH 均指定冻结根，`PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest -v` 选择下列 12 项 | 0 | `/tmp/outcome-review-install-04-regression.txt`：**12 tests / 5.842s / OK**。 |
| 开始/结束清单与导入身份核验 | 0 | 上述两个 identity JSON；结束 `unchanged_from_start: true`。 |

主脚本 SHA256：`6c2be78481419295ba658bef7b4f709ab8efc0b7ad5ad9ca6139cf508c1d7ba1`；补充脚本：`f9abdfc77d68251821c9425aad2cbf3434e402c94ac51f1e5100495dc2f56754`。

日志 SHA256：主 60 行 `b4b30f74c228185528d8b51ecb40486ab640c1fc61dcdfd2a5585898dbe6628c`；补充 26 行 `a9570326d21c217bba4ed664a2d68985f1d30b905bdf51b91f250336c78802d6`。fixture 是实际临时目录，完成后由 TemporaryDirectory 清理；绝对路径、拒绝原因及比较摘要保存在 JSONL，独立脚本可重新构造。

定向选择均来自冻结源码，结果作为补充证据：

- `tests.test_install_simplification.SimplifiedInstallTests`：`test_recorded_old_skill_root_drift_rejects_before_any_install_write`、`test_canonical_cross_host_old_skill_root_and_selected_alias_still_migrate`、`test_recorded_skill_root_ancestor_link_drift_is_rejected`、`test_rollback_material_is_verified_before_target_or_evidence_mutation`、`test_legacy_v4_without_new_receipt_binding_still_verifies_backup`、`test_committed_state_cleanup_checks_actual_new_targets`、`test_migration_rollback_proves_old_home_backups_before_any_moves`、`test_explicit_host_root_alias_is_allowed_but_internal_links_are_not`。
- `tests.test_security_hardening.SecurityHardeningTests`：`test_verified_legacy_journal_can_restore_matching_backup`、`test_v4_recovery_accepts_legitimate_transaction_content_drift`、`test_corrupt_install_state_fails_before_foreign_skill_changes`、`test_legacy_state_cannot_claim_foreign_bytes_via_valid_release`。

## Advisory 与证据边界

**Advisory：无另列实证缺陷。** 下列是结论边界，不作为缺陷计数：

- 结论限定第三轮 R2、相应持久路径 identity 收敛及受影响的 verify/recover。没有重新评估其他模块或 prior findings 的全部结论，没有扩大到整个项目验收。
- 未运行完整 suite；root 已开始完整 suite 是用户提供的背景，未借作本审查的通过证据。未重做 179 场景，未做性能评估、deploy 或真实 host 安装，也未执行 fixture runtime。
- 所有 outside 均是本轮临时 fixture 的独立目录；没有修改真实 Codex、Claude 或 Cursor host。
- 未测试多进程竞争、TOCTOU、kill -9、断电/fsync、跨设备 rename；本轮静态链接反例不依赖这些条件。
- 当前显式选择 alias 与持久 canonical 记录是不同信任入口；本轮验证二者预期行为，没有将历史 canonical root 的内容无变化等同于其所有祖先永远可信。

最终身份复核完成：冻结清单及其 281 个文件全部匹配并保持开始内容；本轮 R2 范围内通过，无 blocking/advisory。
