# AC20–22 安装升级独立工程审查

结论：发现 2 个 P1、1 个 P2；以下三项均与本次要求的正确性/安全保证直接冲突，应在声称 AC20–22 全部满足前处理。这是普通工程审查意见，不是 workflow runtime 签发的验收。

## 输入与方法

- 唯一源码输入：`/tmp/outcome-review-code-01`。`source-manifest.json` SHA256 为 `2bb61d48e58af1aef97d9491445a3ab5d1848a9d1d4312a38bbc9ad451506d5b`，与指定值一致；开始与结束均核验登记的 283 个文件，内容摘要无不匹配。
- 需求依据：`/tmp/outcome-review-code-01/.agent/work/workflow-outcome-optimization/specs/specs-workflow-outcome-optimization-02.md`，尤其 165–174 行与 243–245 行（AC20–22）。
- 阅读 `tools/workflow.py`、`tools/workflow_lib/{release,installer,projection,doctor}.py`、`tests/test_install_simplification.py` 和 `changes.patch`；为核验实际机制补读 `fs_safety.py`、`release_references.py`、`source_walker.py`、`check.py` 的相关逻辑。
- 所有 shell 执行均 `login:false`，读取使用绝对路径；未编辑主仓库或冻结源码。没有使用 my-matt-workflow Skill，也未用 runtime 管理工作单元或签发验收。仅以普通 Python 调用候选函数做临时隔离 fixture 和定向测试，未安装真实宿主。
- 可重跑探针：`/tmp/outcome-review-install-probes.py`；输出：`/tmp/outcome-review-install-probes.txt`。命令：`PYTHONDONTWRITEBYTECODE=1 python3 -B /tmp/outcome-review-install-probes.py`。临时 fixture 在退出时清理。

## 阻塞发现

### F1 · P1 · 旧 manifest 的同版短路漏验 runtime，损坏后仍返回 current

**位置**：`/tmp/outcome-review-code-01/tools/workflow_lib/installer.py:771–776`；漏验前提在同文件 `201–220`，原本后续的同名 runtime 校验在 `886–892`。

**触发路径**：支持的旧 release manifest 没有 `target_manifests`（探针同时去掉 `source_input_digest`），但仍有合法的 `skills`、`runtime` 及文件 hash。首次安装成功并生成 v2 install-state；随后改写实际安装的 `runtime/v1/tools/workflow.py`，再安装同一 release。

`verify_installed_state` 仅在 `expected_target is not None` 时检查宿主 runtime。旧包缺该字段时跳过 runtime 核验，而新增短路只判断 state version、source 路径、manifest hash、projection 和 skills_home，直接返回 `current`。它因此绕过原本后续对同名 runtime 每个文件的检查。

**证据**：普通 fixture 将入口改为 `raise RuntimeError("TAMPERED")`；第二次安装正常返回：

```text
LEGACY_RUNTIME_DRIFT {"result": "current", "tampered_runtime_remains": true}
```

对照仅在内存中禁用新增的 `return current` 分支，其余候选代码保持相同，同一损坏被后续检查拒绝：

```text
SHORTCUT_DISABLED_CONTROL 安装中断，已恢复旧版本 cause 已安装的同名 runtime 已损坏：v1
```

**影响**：受支持旧包可以把已经损坏或替换的可执行 runtime 报为 current；违反 AC21 对实际托管内容的要求。这是新增短路造成的可复现退化，不能以旧 manifest 回退了源码比较来补足宿主内容核验。

**修复方向**：进入 current 分支前必须核验实际 runtime 与 release 的 `runtime` 清单，并在无 target manifest 时从实际 release 推导可信的宿主 Skill 投影，而不是将缺字段当成无需检查。覆盖旧包安装后 runtime 修改、删除、增加文件的负向用例。

### F2 · P1 · v4 中断恢复只绑定 journal，不核验备份内容，恢复损坏备份后删除证据

**位置**：`/tmp/outcome-review-code-01/tools/workflow_lib/installer.py:605–612`、`704–709`、`723–729`；身份校验的语义在 `/tmp/outcome-review-code-01/tools/workflow_lib/fs_safety.py:169–214`。

**触发路径**：v1 已安装，升级 v2 时旧 Skill 已移入 `transaction/backup`，在刷新事务登记后进程中断。中断期间备份被损坏或修改，journal、事务目录 inode 及独立登记的 journal hash 保持原样。随后通过安装入口恢复，或直接调用恢复函数。

v4 恢复仅调用 `verify_owned_directory_identity(... required_controls=("journal.json",))`。这证明 journal 的控制绑定，但不检查备份树摘要，也不按旧 release 核验各备份 Skill。恢复直接删除当前目标、将备份 rename 回目标，随后 refresh 将剩余内容重新登记并删除事务。

**证据**：探针以 `KeyboardInterrupt` 模拟移动后中断，然后把备份的 `SKILL.md` 改为 `CORRUPTED BACKUP`。完整 ownership 检查实际会拒绝该事务，但恢复函数仍成功恢复损坏内容并删除事务：

```text
BACKUP_FULL_BINDING_REJECTS 托管目录 ownership 或 identity 不匹配
ROLLBACK_TAMPER {"restored_text": "CORRUPTED BACKUP", "transaction_removed": true, "state_release": "v1"}
```

**影响**：回滚不能保证恢复旧可信内容，且持久 install-state 仍标识 v1。自动安装入口之后可能再因 ownership 漂移报错，但那时错误备份已覆盖目标、事务证据已删除；后置报错无法补足安全恢复。违反 AC22 和 4.10 的安全回滚保证。

**归因**：`changes.patch` 没有修改这个恢复分支；这是本次明确审查的安装安全范围内的既有缺口，不宣称由优化新增。

**修复方向**：在任何目标删除/备份移动前，根据可信旧 release 或独立控制绑定的备份清单核验恢复材料；失败时保留事务与目标供诊断。不能无条件把当前事务的整体摘要视为恢复依据，因为合法中断也可能发生在登记刷新之前；需要允许合法中间态，同时证明实际要恢复的每份旧内容。

### F3 · P2 · 新包实际宿主 runtime 的额外 symlink 被过滤，仍报告 current

**位置**：`/tmp/outcome-review-code-01/tools/workflow_lib/installer.py:216–220`、`771–776`；过滤逻辑在 `/tmp/outcome-review-code-01/tools/workflow_lib/projection.py:69–74`。

**触发路径**：正常安装带有完整 target manifests 的新 release；在实际宿主 `my-matt-workflow/runtime/v1` 下增加一个 `unexpected-link -> /tmp`，再安装同版。

runtime 校验使用 `directory_inventory`，该帮助函数只收集普通文件并显式排除 symlink。与 release 校验和 `_skill_inventory` 不同，实际宿主 runtime 没有先拒绝 symlink。因此新增链接不改变用于 current 判断的清单。

**证据**：

```text
RUNTIME_EXTRA_SYMLINK {"result": "current", "symlink_remains": true}
```

**影响**：实际托管 runtime 的路径/链接漂移没有被发现，current 结论无法保证 AC21 的实际内容正确和 AC22 的链接保护。本探针证明漏检链接，未证明该额外链接已经被执行或造成外部写入。

**归因**：runtime 使用普通文件清单的缺口既有；新增 current 分支继续依赖它。不能将本项全部归为新投影算法引入。

**修复方向**：实际 runtime 内容检查应在计算 hash 前明确核验目录与入口的路径归属、拒绝不允许的 symlink，再比较完整普通文件集合；保留仅针对明确定义执行副产物的忽略规则。

## 已核验的机制与边界

| 关注项 | 实际检查与证据 | 限制 |
|---|---|---|
| 锁与缓存 | installer 外层校验后在 release-reference 锁及安装锁内重新使用带实时内容身份的 context；同路径内容变更会重新验证，不同包分别缓存；返回对象使用 deepcopy。定向测试含锁内篡改与验证过程漂移，均通过。 | 未做多进程竞争、文件系统故障注入或全时序模型检查；不据此宣称所有 race 已排除。 |
| 摘要输入 | 阅读 source inventory、模式、implementation、review-loop、upstream 与相对路径参数绑定；定向测试覆盖测试/配置增加、构建文件增加、链接、权限与 upstream 变化。 | 没有穷举所有可选库调用布局和外部环境。摘要不是测试通过 receipt。 |
| 可信摘要控制 | 摘要短路要求独立 ownership identity 和 manifest control hash；无可信控制绑定/伪造摘要时回退实际生成清单比较。对应定向测试通过。 | 不把可被同权限任意改写的 registry 视为抵抗恶意全盘改写的密码学信任根；本审查未假设这种威胁。 |
| 完整 test gate | changed deploy 在打包快照运行 gate；定向测试中实际 suite 计数为一次，失败不发布/安装。另独立构造源码完全不变、测试按环境输入失败的场景，无变化 deploy 实际执行测试并 exit 1，宿主 state 字节未变。 | 无变化路径的 gate 不构成跨调用测试凭据；未运行整个仓库 suite。 |
| 源码/旧摘要回退 | 旧摘要缺失及摘要控制失效会调用完整 source_manifest 比较；定向测试有实际调用计数。 | 这只证明包与源码比较；不能补足 F1 的宿主 runtime 漏验。 |
| 物理投影等价 | 定向测试覆盖 CRLF、调用宏和 metadata 删除。独立遍历冻结源码的 32 个 Skill，对 portable/codex/cursor/claude 做 128 次物理复制投影与新摘要算法逐路径 hash 比较，全部一致。 | 128 次是源码 Skill 树，未对完整资源打包产物的所有边界组合做穷举；文件 mode 不属于这次字节比较。 |
| 同版与漂移 | 定向测试证明常规同版不重写 Skill/state，普通 Skill 内容篡改被拒绝。 | F1/F3 是未被该覆盖发现的实际反例。 |
| 回滚 | 独立中断探针检查可信控制、备份损坏与恢复后实际目标/state/事务。 | F2 已失败；未模拟 kill -9、断电、fsync 损失或跨设备迁移。 |
| doctor | 阅读共享 context 与各宿主独立内容核验；定向测试检查同包一次 verify、正常宿主 valid、篡改宿主单独 invalid。 | 未接触真实宿主；未实测并发诊断的所有漂移窗口。 |

执行结果：`test_install_simplification.py` 共 14 项测试通过，unittest 输出耗时 1.464 秒；独立投影比较耗时约 0.275 秒。这两个数字是本次局部验证耗时，不是部署提速 benchmark。全部独立探针命令退出 0，其中明确捕获的无变化 gate 失败退出码为 1。测试通过没有消除上述反例。

## 非阻塞建议与剩余证据

1. 将 F1/F3 的负向检查以及 F2 的损坏备份恢复纳入回归；预期来源应为原 release 清单和实际恢复内容，避免以 helper 返回值自证正确。
2. 性能主张应另附稳定正常路径的阶段计数和耗时，至少区分 snapshot/check、release verification、projection/staging 与最终 host verification。本次确认了一些次数减少和局部投影等价，未证明端到端速度改善；不预填提升百分比。
3. 真实宿主安装、统一 runtime 切换、多宿主真实运行、完整 suite 和真实进程中断恢复均未在本审查执行，不应从这份报告推导已经通过。

报告已完成；主仓库与冻结源码未修改。
