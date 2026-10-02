# Spec revision 2 独立复审：安装升级、身份与恢复

结论：**pass（仅本审查范围）**。blocking 0，需修复 advisory 0，未决语义 0。审查范围为 §3、§4.10、改动包 H、AC20–22 及相邻兼容/验证约束。没有发现照当前 Spec 实施必然导致的可达故障；本文不是新版实现、性能或安装效果的通过证明。

- reviewer_provenance: independent；新上下文子 Agent `/root/spec_rereview_install`；继承宿主模型与思考档位，未请求模型升级。
- content_id: `b1e3b56de8bbec03de4a5aea87b362c9c99dda514a422e0e86905971f27996a0`
- 输入：仅 `/tmp/my-matt-spec-rereview.json` 指定的 `snapshot_path`。全部读取文件已核对 SHA-256。没有读取作者总结、先前审查报告或活源树，没有执行安装或完整 suite，没有修改仓库。
- 方法：已读冻结 `088-SKILL.md`（my-review-design）与 `036-review-loop.md`。这是既有文档复审预算中的安装方向子审，不另开轮次。
- 以下文件与行号均指冻结快照。目录前缀为 `/var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/my-matt-review-snapshots/my-matt-review-b1e3b56de8bb-39z2zy_y/`。`Spec` 为 `001-specs-workflow-outcome-optimization-02.md`。

## 1. 承重断言核验表

| 承重断言与 Spec 位置 | 核验 | 冻结源码证据、实现与验收边界 |
|---|---|---|
| 现版源码变化 deploy 有活源树 check 和打包快照 check 两轮；应保留后一轮（43、169、243） | 已核实 | `248-workflow.py:365–389` 在判断复用前无条件 `_run_all_up_gate`，`190–205` 给 build 传入快照 gate；`262-release.py:747–807` 复制稳定快照、执行 gate、复核漂移后从同一快照打包。`253-check.py:9–14` 实际调用完整 unittest 并按退出码失败。移除前一轮并保持 build gate 即有直接实现位置，不必引入新 CLI。 |
| 稳定快照是现有保证，真实漂移需要拒绝/重试，不能用一次计数抹掉恢复（169、174、243） | 已核实 | `262-release.py:67–114` 比较复制前、复制后、复制件路径/内容及链接身份；`747–784` 最多三次尝试，gate 期间变化重取快照。`236-test_security_hardening.py:295–323` 在 gate 修改活源文件，断言 gate 两次且 release 包含新内容。AC20 的“正常稳定”限定与现有恢复机制兼容。 |
| release 验证在同一调用重复，可收敛为受保护的内容上下文（170、243） | 已核实 | `248-workflow.py:376` 验证 current；`257-installer.py:909` 锁外预检、`915–923` 获取引用锁/安装锁后调用 `_install_release`，`706` 再验证；`732` 经 `verify_installed_state` 又在 `190/220` 验证旧 source。同包可能重复，但升级时新包与旧包不同，不能只保留一个全局 bool。Spec 已明确区分二者与锁内建立/使用。 |
| 投影校验当前确实复制三宿主完整树，且存在可计算的确定性字节变换（171、245） | 已核实 | `262-release.py:505–524` 与 `257-installer.py:453–470` 对 codex/cursor/claude `copytree` 后投影并计算 inventory；`260-projection.py:13–42` 定义 Codex frontmatter 删除、其他宿主 metadata 删除及 Markdown 调用宏替换。可以计算同等 inventory；需遵守原文本解码/换行与写回行为，不能仅做“意思相同”的替换。AC22 已以逐路径逐字节等价约束。 |
| 当前 source-match 为构建产物等价判断，会临时打包；不代表完整测试输入/通过凭据（172–173、244） | 已核实 | `262-release.py:638–683` 调用 `_stage_release_tree` 临时构建期望 manifest；`537–620` 产物含 Skill、runtime、resources 等，未把 tests 当作发布产物。输入摘要需覆盖实际构建输入及构建/投影协议；测试/配置变化仍需新检查，不能从产物等价推出测试有效。Spec 明确区分并禁止首版跨调用复用测试凭据。 |
| 当前 deploy 即使复用 release 也重新安装；短路必须先证明实际托管目标一致（172、244） | 已核实 | `248-workflow.py:390–392` 复用后仍执行 `command_install`；`257-installer.py:780–885` 新 staging、Skill 置换及 receipt 重写。`182–215` 可核验 receipt 对应 release、manifest hash、Skill inventory、runtime inventory。因此 AC21 的 current 不能只检查 release_id，已有可复用验证 seam。 |
| doctor 分 source/release/host 报告；复用时仍须处理包漂移（170、174） | 已核实 | `255-doctor.py:26–61` 分离 release 完整性与 source_match；`64–104` 每宿主验证安装；`107–134` 分层输出。`223-test_doctor.py:23–59` source 比较不可用仍输出 release valid + source_match unavailable。保留此区别可防止把 unknown 归 current；Spec 未要求把各层合为一个布尔值。 |
| 安装已有 release 不运行源码全套，且安装/发布职责可保持（59、167、173、245） | 已核实 | `248-workflow.py:221–230` 直接 `install_release`，不存在 `_run_all_up_gate` 调用；后者只校验 release、旧状态与实际投影。`command_deploy` 可以内部选择 build/reuse 后调用安装功能，不需新增多宿主 CLI。 |
| 锁、引用保护、staging、非托管冲突拒绝、最终校验与恢复有现成协议，应继续保留（170、174、245） | 已核实 | `257-installer.py:915–923` 引用锁后安装锁；`263-release_references.py:59–63` 在副作用前登记安装 root；`262-release.py:875–896` 同引用锁内盘点/清理 release。installer `741–746` 拒绝非托管同名目录，`795–801` staging 校验，`859–867` 最终 Skill/runtime 校验，`892–898` 失败回滚，`544–695` 处理持久事务。 |
| 旧摘要、旧投影/安装记录不能补造 cache hit；可保守回退（54–58、172、244） | 已核实 | `257-installer.py:111–179` 识别 v1/v2 install receipt；`217–255` 为旧记录物理投影核对 ownership；`624–655` 旧 journal 通过可信 state 与 backup 验证才恢复。新摘要并非现有字段，需在实施时接入严格 schema 或独立受约束元数据；Spec 未指定强制原地迁移或新 reader 必须依赖摘要。保留 legacy fallback 可实现 AC21。 |

## 2. 审查发现

无 blocking 或需修复 advisory。候选行为在所审源码中均有实际修改位置；没有发现为完成 AC20–22 必须另设用户决策或违背已接受精简方向的设计冲突。

可选措辞建议（不计 design finding，不要求本轮改正文）：Spec 173、244 的“仍可保留/仍可运行一轮 check”可在以后同处编辑时改成“首版无变化 deploy 保留一轮完整 check”。理由仅为减少孤立摘录的误读；本版同段已经写明“首版不复用跨调用的测试通过凭据”和“未来若要跳过该检查，须单独扩展…成功 receipt”，并非允许当前零 check 放行。处置：decline 为本轮设计阻断；不重开已决方向。

## 3. 已考察但排除的风险

1. **锁外验证布尔值进入锁内后误信，或 cleanup 删除刚验证的 release。** 真实接缝为 installer 909 对 915–918，以及 release 875–894。Spec 170 原文明确“不能把锁外旧布尔值带入锁内后直接信任”，且 AC20 要求受保护的同内容复用；要求已覆盖此失败时序，无需再造持久缓存服务。`237-test_skill_packaging_v2.py:288–308` 已有引用锁冲突时 receipt 不变、解锁重试成功的验证 seam。未据此声称候选实现已通过并发验证。
2. **同 release_id 或先前 receipt 掩盖部分安装/事务。** installer 656 使用 transaction_id 对应提交，668–686 从备份恢复；load_install_state 严格 schema，verify_installed_state 核验实际 inventory 与 manifest hash。Spec 172/174 要求实际内容、保留恢复与最终核验，故无变化 fast path 不能越过这些条件。`236-test_security_hardening.py:158–183` 硬中断后恢复旧字节；`242-test_workflow.py:501–537` 旧不可信状态不能伪装 commit。
3. **投影优化仅信任 manifest 内声明而接受篡改，或漏掉路径/symlink 拒绝。** installer 285–347 独立验证原包路径和字节，453–470 重建投影；Spec 171/174 与 AC22 明确替换算法必须等价、路径链接保护保留。可以换掉昂贵物理复制同时保留验证，不存在二选一冲突。`236-test_security_hardening.py:458–475` 篡改 target manifest 时不得安装/遗留事务提供对抗 seam。
4. **把构建摘要当跨调用测试 receipt，测试/config 变化无声绕过 check。** 现版 source_manifest 只验证将要产出的内容，确有这种错误优化的可能；Spec 173 明确禁止、244 区分测试身份，未来跳过需要单独扩展协议。首版保留 check 能实现本次要求，无需现在设计环境缓存。
5. **旧包缺摘要或新摘要破坏 strict manifest 读取。** installer 279–280 拒绝未知字段，故实施者若把字段加入 manifest，必须更新允许字段/校验和旧包 fallback；也可以用不改变 release manifest 的受约束元数据实现。Spec 54 兼容读取现存状态、172 缺摘要回退已提供约束。没有规格要求旧二进制读新 schema；57 已声明旧 writer 混写不受保证并要求切换方案。不能把可避免的实现错误反写成新增迁移要求。
6. **删除活源 check 后发布未检查快照，或恰好一次要求禁止漂移重试。** build 本身已有快照 gate，Spec 169/243 限定最终打包快照和正常稳定路径，容许失败恢复重跑。保留 build 内门禁即可；失败先于 staged publish，见 release 762–807、823–850。
7. **多宿主优化迫使新增 CLI、扩大安装权限或跨宿主事务。** Spec 167 仅允许同协调调用共享上下文，不要求新增多宿主命令，174 明确每宿主结果及授权；现有单宿主 public CLI 可以保持。没有新增必须由用户选择的 CLI 语义。
8. **将现有测试存在等同候选通过或实际提速。** 所读测试只用于核验可实施验收 seam；没有执行测试。Spec 245 要求实际计数和阶段耗时，253 要求故障注入及完整检查，296 保留提速幅度未知，因此静态调用减少并未被当作性能效果验收。

## 4. 待用户确认的需求语义假设

无。本范围已接受首版无跨调用测试缓存、无自动测试选择平台、保留既有 CLI 职责及只操作获授权宿主。输入摘要格式、调用内上下文 API 和纯投影函数组织属于满足既定不变量的实施选择，不需提前变为用户专属裁决。

性能收益与候选实现是否真正满足 AC20–22 尚未验证，属于后续施工/验收证据，不构成本轮设计语义缺口。
