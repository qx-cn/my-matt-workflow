# 冻结整体工程审查：安装升级链路

结论：本次审查未确认应阻断交付的新增安装缺陷。就已检查的 deploy/build/install/doctor/projection/release 路径，重复工作确实减少，摘要与短路没有只凭 release ID 或 Git HEAD 信任旧结果；安装回滚及路径保护有实质增强。此结论限于冻结源码、临时目录和以下定向执行，不表示真实宿主已安装或所有并发交错均被穷尽。

## 审查身份与开场校验

- 最终源码：`/tmp/outcome-holistic-608b72b`；基线：`/tmp/outcome-holistic-base-7947cb2`。
- Spec：最终树 `.agent/work/workflow-outcome-optimization/specs/specs-workflow-outcome-optimization-02.md`，重点 4.10、AC20–22；兼容边界同时参考第 3 节、AC16/18。
- 开场校验最终 `source-manifest.json`：281 个文件逐一 SHA-256 匹配；manifest SHA-256 为 `0f7c4296a473ec1df31e3e61f87d8a861aa2ef6eaaa904a46c4c85ae4ecd3eb1`。
- 只读冻结源码及基线；没有读取可变主仓生产源码，没有调用 workflow 自身 Skill 作审查治理，没有修改冻结树或真实 host。
- 定向工程测试及 benchmark 运行时关闭 Python bytecode；release、安装与故障材料均在临时目录。
- 基线目录没有 `source-manifest.json`，因此没有声称基线经过同样的逐文件清单校验；它使用父审查者指定的冻结目录。

## 发现与风险归类

**新增缺陷：没有确认可报告的 P0/P1/P2。** 没有为了给出 findings 而把已有行为、性能边界或没有复现的竞态假说标作缺陷。

**已有缺口：** 本次没有建立需要另报的具体既有安装故障。没有全量重审未变化的完整文件系统能力协议。

**优化目标与剩余成本：** `tools/workflow_lib/installer.py:401` 每次 validation-context 命中前仍调用 `_identity`，`installer.py:414` 对 release 全树逐文件 hash；减少 `verify_release` 次数不等于免除了所有内容读取。这个成本用于漂移检测且符合 Spec 4.10，没有单独提出删除建议。下述独立实际计时仍显示净下降。真实宿主升级耗时、各种文件系统规模、并发压力和用户任务净收益未验证；不能把局部秒数推广成安装提速承诺或七项能力提升。

## 关键判断及证据

| 路径 | 最终源码锚点 | 基线比较与判断 | Spec |
|---|---|---|---|
| 变化 deploy | `tools/workflow.py:367`、`tools/workflow_lib/release.py:729` | 去掉 live-tree 预先完整 gate；仍由 build 在稳定 snapshot 上执行 gate，源内容变化时重取或拒绝。临时公共入口 suite-counter 测试实际只运行一次 suite；故意失败 suite 不发布、不安装。 | AC20 |
| 无变化 deploy | `tools/workflow.py:379`、`:398` | release 在引用锁内验证后才决定复用；仍跑一次完整 check，之后重新匹配 source；显式选定 release 安装。无变化路径不重新 stage source、不会重写合法 host。 | AC21 |
| 输入摘要 | `tools/workflow_lib/release.py:651`、`:681` | 摘要包含快照内容、文件模式、实现代码、review-loop fallback 和 upstream/相对路径参数；只有独立 ownership control 绑定 manifest 时使用摘要快速匹配，否则回退实际 source manifest 比较。测试覆盖 tests/config/link/mode/upstream 变化及伪造摘要。 | AC21 |
| 验证复用 | `tools/workflow_lib/installer.py:392`、`:1124` | 同一上下文按路径与 byte identity 复用；新包/漂移包重验。安装在取得引用锁与 host 写锁后再次验证，未把锁外旧布尔值直接带入。返回 manifest 深拷贝避免调用者污染缓存。 | AC20/22 |
| 投影 | `tools/workflow_lib/projection.py:87`、`tools/workflow_lib/release.py:508`、`tools/workflow_lib/installer.py:594` | 用 bytes 摘要取代三宿主 copytree；实际安装 staging 仍物理投影。Codex metadata 的无条件重写、其他 Markdown 有宏才重写和 CRLF 归一差别保留；定向物理 oracle 对四个 target 逐字节比较通过。 | AC22 |
| 宿主短路/漂移 | `tools/workflow_lib/installer.py:287`、`:899` | 相同包仍验证已安装 Skills、runtime、manifest 和记录根目录。仅 v2 receipt 且源/投影/目标目录等匹配时 current；旧记录保持完整验证路径。增加同名 runtime 的实际完整检查，旧 manifest 缺 target 清单也不能略过 runtime。 | AC21/22 |
| 事务回滚 | `tools/workflow_lib/installer.py:679`、`:726` | v4 通过 previous-state hash 和实际旧包投影核验 rollback bytes；验证已提交新状态后才清理备份。损坏备份保留证据，合法中断可恢复；兼容没有新摘要字段的旧 v4。 | AC22 |
| 路径与迁移 | `tools/workflow_lib/installer.py:124`、`:181` | 新选择的根 alias 可 canonicalize；已持久化 canonical 根发生 link 漂移则拒绝，不能悄悄改写 outside 目录。跨目录合法迁移、explicit alias、v1/v2 receipt 均在测试中正常。 | AC22 |
| doctor | `tools/workflow_lib/doctor.py:26`、`:64`、`:108` | 同包验证共享上下文，当前 source/release 与每个 host 的实际状态仍分别呈现；一个 host 篡改不遮盖另一个成功结果。 | AC20–22 |

## 执行证据

1. `PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover -s /tmp/outcome-holistic-608b72b/tests -p test_install_simplification.py -v`，cwd 为最终冻结树；退出 0，25 tests / 7.457s / OK。其故障注入输出中的 `FAILED (failures=1)` 来自故意失败的临时子 suite，外层用例通过并确认未发布，不能误读为最终测试失败。
2. 另外执行 7 个已有定向用例，退出 0，0.946s / OK：
   - `test_workflow.InstallerTests.test_can_install_an_older_release_for_rollback`
   - `test_workflow.InstallerTests.test_recovers_persisted_interrupted_transaction`
   - `test_workflow.InstallerTests.test_committed_transaction_cleanup_keeps_new_install`
   - `test_skill_packaging_v2.ReleaseReferenceRegressionTests.test_install_during_source_gate_is_retained`
   - `test_skill_packaging_v2.ReleaseReferenceRegressionTests.test_cleanup_lock_rejects_install_before_side_effects_then_retry_succeeds`
   - `test_security_hardening.SecurityHardeningTests.test_build_retries_when_live_source_changes_after_snapshot`
   - `test_security_hardening.SecurityHardeningTests.test_three_hosts_install_exact_declared_target_inventory`
3. 没有运行仓库完整 suite；上述公共 deploy fixture 自带的 1-test 子 suite 用于真实次数验证。没有安装真实 Codex/Claude/Cursor。

## 独立临时发布包计时

脚本 `/tmp/outcome-install-bench.py` 分别从两个冻结版本导入各自实现，用完整 Skills 源构建临时包（未传 source gate，因此此 build 时间不含完整 suite），真实执行 verify/install。没有 stub `verify_release`、hash、copytree 或 installer。基线和候选各执行一次 build、一次 first-install、三次 verify、三次相同包安装。两版自身打包内容有所不同、运行顺序固定且样本小，只作为本机工程案例，不称统计实验。

| 阶段 | 基线秒数 | 最终秒数 |
|---|---:|---:|
| build（不含 suite） | 1.456518 | 1.092651 |
| verify 三次 | 0.734444 / 0.734167 / 0.705014 | 0.328996 / 0.315194 / 0.315629 |
| first install | 1.698940 | 0.976694 |
| same-release install 三次 | 2.732270 / 2.722448 / 2.691355 | 0.720654 / 0.682828 / 0.624254 |

最终重复安装真实返回 `current`；基线 API 返回 None 且执行重装。原始结果：`/tmp/outcome-install-bench-base.json` 与 `/tmp/outcome-install-bench-final.json`。这支持“该链路成本已实际降低”，不支持真实用户环境的固定提速比例。父审查者另有隔离计数结果；本报告不把尚未在本子审查中读取的脚本输出冒充自行取得的测量。

## 收尾校验与结论边界

- 收尾再次核验最终 281 个文件全部 SHA-256 匹配，manifest SHA-256 仍为开场指定值；没有冻结源内容漂移。
- 已测试的并发保护包括引用锁拒绝、门禁期间并发安装保持旧引用、锁内包篡改重验；不等于对任意恶意非合作 writer 的形式化保证。
- 本报告没有发现必须先修的新增安装缺陷。完整 Topic 是否接受仍应结合其他独立子审查的 runtime、规则和效果证据结论。
