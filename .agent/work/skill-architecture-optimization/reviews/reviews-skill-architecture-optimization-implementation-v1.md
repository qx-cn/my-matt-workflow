---
review_id: skill-architecture-optimization-implementation-review
spec_id: skill-architecture-optimization
spec_revision: 4
candidate_release: skill-architecture-optimization-v2
result: pass-with-declared-evidence-gaps
date: 2026-09-09
---

# Skill 架构优化实施复核

## 结论

Spec revision 4 的代码、Skill、portfolio、资源图、release/install 与验证改造已经完成。最终独立复核未发现本地威胁模型内仍可复现的绕过。候选 release `skill-architecture-optimization-v2` 已构建并成为 current；真实 Codex/Cursor/Claude home 未写入。

## 关键订正

- 活动共享工作树不再直接作为 build 输入。runtime 复制前后核对 byte-exact inventory，门禁与打包只读取同一稳定快照；持续变化时 fail closed。因此并发暂时移走 `my-requirement-analysis/SKILL.md` 不再被错误归因成 source walker 缺陷。
- build、prune 与 current 切换共用 releases mutation lock；candidate rename 和 `current.json` 原子替换处于同一临界区。
- installer 与 work-artifact recovery 使用独立 ownership registry、稳定 identity/control digest 和可恢复 transaction journal；合法事务内容变化不再阻断硬退出恢复。
- Ticket 准入统一校验依赖、claim、验收、规则字段及同 topic Spec frontmatter lineage；run completion 绑定稳定 definition、profile/rules/standards/domain、代码和 runtime evidence。
- test evidence 由 runtime 执行 profile 预声明命令。review evidence 不再接受调用者结果文件：runtime 验证 owned snapshot、执行冻结 work unit 中的精确 reviewer argv、采集真实 exit/stdout/stderr、保存结果并在 completion 重验。
- portfolio 对 37 个 Skill 一一闭合；composition、共享资源 direct/effective consumers、宿主投影与 target manifest 由 validator 交叉验证。

## 最终证据

- `python3 -m unittest discover -s tests`：262/262 通过。
- `python3 tools/workflow.py validate`：37 Skills 通过。
- `python3 tools/workflow.py validate-evals`：8 scenarios，通过；其中 7 required。
- `python3 tools/workflow.py check`：static、unit、deterministic eval 与 current release `skill-architecture-optimization-v2` 全部 valid。
- 临时 home 矩阵：Codex、Cursor、Claude 各完成 `v2 → runtime-session-contract-v6 → shared-rule-review-v1 → v2`；12 次安装/升级/回滚均成功，最终三者均为 37 Skills、v2、valid。
- 独立最终复核：build/prune/current、硬退出恢复、Markdown title/angle/fragment、Spec lineage 与 runtime review evidence 全部 PASS；review-evidence 聚焦测试 16/16 通过。
- `git diff --check`：通过。

## 部署与证据边界

- 真实 Codex 与 Claude 仍为 `shared-rule-review-v1`、34 Skills、drift；Cursor 为 not-installed。此状态是只读诊断结果，不影响源树和候选 release 健康，也不冒充已部署。
- deterministic/unit 证据不证明 37 个 Skill 的真实模型行为全部改善。测试 reviewer 是预声明 stub，只验证 runtime provenance 与绑定机制；真实模型审查质量仍属于 fresh-agent 行为证据。
- 本地 runtime 不对抗拥有同一 OS 用户权限、能够改写可执行程序或 runtime 本身的恶意进程。更强 reviewer 独立性需要宿主隔离与签名 attestation。
- 未升级模型、reasoning 或服务档位；未 commit、push、安装到真实宿主 home。
