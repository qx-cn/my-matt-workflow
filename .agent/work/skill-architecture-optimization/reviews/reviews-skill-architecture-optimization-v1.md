---
review_id: skill-architecture-optimization-spec-review
spec_id: skill-architecture-optimization
spec_revision: 4
baseline: 7825887d4bcdedbcd745aa45aaad25f00e55217d
result: approved-with-corrections-applied
---

# Skill 架构优化 Spec 正确性复核

## 复核结论

Spec 的问题判断、优先级和总体分层方向成立；复核累计发现十七处会造成错误安全承诺、迁移歧义或验证假阳性的设计缺口。所有阻断项均已直接订正到 revision 4；实施与最终复核完成后，当前状态为 `implemented-with-declared-evidence-gaps`。

本复核不把“静态检查通过”解释为 Agent 行为已经通过，也不把真实宿主当前 34-Skill 安装状态解释为本轮候选 release 已部署。

## 已订正问题

1. **目录内 marker 不能自证删除权限**：改为专用可信根、独立 ownership registry、canonical path/identity/inventory 复核和同根 quarantine；所有 recursive-delete sink 必须接入。
2. **Ticket 定义与执行状态不能使用同一 immutable hash**：拆分稳定 definition 与 mutable execution state；合法 claim/status/observation 不使 definition receipt 失效。
3. **两个普通文件不能被宣称为原子提交**：改为 WAL/transaction journal 驱动的可恢复协调更新，并要求中断恢复测试。
4. **本地 capability 不能证明用户授权**：external write 需要宿主可信 confirmation receipt；宿主无法提供时回到实时 gate。
5. **release identity 约束范围不清**：任意 release 都要求 manifest ID 与目录名一致；仅默认/current 校验约束 current 指针，显式旧版安装和回滚保持合法。
6. **只扫描标准子目录会漏掉现有根级 sidecar**：source walker 改为引用可达闭包加 per-Skill inventory，并显式覆盖当前根级参考、脚本与模板。
7. **投影后只验证 metadata 不足**：Codex/Cursor/Claude 分别生成 target manifest，安装与 doctor 校验完整集合和 digest。
8. **portfolio 证据可能把 deterministic 冒充行为证据**：证据改成分层映射或带风险/解除条件的 exemption，并为 critical Skill 单独约束 fresh-agent 结果。
9. **manual handoff 只有调用宏会破坏 automatic composition**：每条 handoff 同时保留 composed-body 指针和 portable invocation macro，validator 与 composition edge 双向校验。
10. **direct resource consumers 不能遗漏资源间依赖**：effective consumers 同时从 Skill composition closure 与资源源码链接闭包派生；manifest 保存 direct/effective 图，validator 要求 direct 声明与直接引用一致。
11. **活动工作树不是一致的 build 输入**：并发分支暂时移除 `my-requirement-analysis/SKILL.md` 曾让全仓 build 随时序失败。build 改为复制前后 inventory 一致的 byte-exact 快照，门禁和打包只读该快照；并发变化重试，持续变化 fail closed。
12. **build/prune 分锁与 current 切换窗口**：二者统一使用 releases mutation lock，并把 candidate rename 与 `current.json` 原子切换放入同一临界区。
13. **可变 transaction tree digest 会阻断硬退出恢复**：ownership capability 分离稳定 identity/control digest 与可变完整 tree digest；恢复先核对 immutable journal control，再恢复并刷新完整 digest。
14. **资源闭包的 Markdown parser 不完整**：资源派生与 staged link validation 统一使用支持 title、尖括号和 fragment 的 parser。
15. **Ticket 自报 Spec 血缘不可采信**：准入解析同 topic Spec frontmatter，并核对 id/revision/path。
16. **结构化 pass dict 仍可自证测试/审查**：completion 改为只接受 journal runtime registry 中的 evidence id；测试由 runtime 执行并记录 exit/output digest，审查绑定 code snapshot 与结果文件 receipt，提交前重验。
17. **owned snapshot 仍不能证明审查实际执行**：不再接受调用者写入的 review result 文件；runtime 只运行 profile 在 work unit 建立前预声明的 reviewer command，通过环境变量传入 snapshot/id，采集真实 exit/stdout/stderr，并把 stdout JSON 保存、登记、提交前重验。该保证仍服从同一 OS 用户不作为恶意攻击者的本地威胁边界；更强独立性需要宿主隔离和签名 attestation。

## 实施判定

- 批次 A/B 是安全与状态一致性的前置条件，应先于 Skill 文案清理进入主分支候选。
- 批次 C/D 可并行开发，但最终 release 必须在 A/B 合入后统一构建和验证。
- 批次 E 中 fresh-agent 只能使用当前模型与默认 reasoning；`blocked`、`inconclusive` 不计为通过。
- 真实 Codex/Cursor/Claude home 不在本轮写入授权内；安装、升级、回滚证据必须来自临时 home。

## 剩余认识边界

- 独立 registry 只能在本仓库声明的本地威胁模型下提供删除 capability；它不是针对拥有同一用户权限的恶意进程的安全边界。
- 跨文件 WAL 提供可恢复一致性，不提供底层文件系统意义上的多文件原子性。
- 不做 fresh-agent/真实项目样本时，只能确认合同和验证基础设施闭合，不能确认全部 37 个 Skill 的行为收益。
