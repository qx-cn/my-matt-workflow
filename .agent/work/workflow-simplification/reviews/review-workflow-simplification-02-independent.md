Review-Snapshot: 27d42ef20f0a79309444dfe4bafbe1e7bf4ce5c35d686eea60a17d520ca4c902
Base: 1e1cc4a8837e116aef72bd10126ab5f2ce1a3f45
Head: dba5ef7380f4713481b110728a5387dfd8d3a730
Review-Scope: change-only

## Code

[P2][high] 保留 setup 写出的合法分支名 null 的字符串类型 — tools/workflow_lib/topic_service.py:104

在默认分支名为 `null` 的有效 Git 仓库，`setup --apply --base-branch null --agent-directory-mode shared` 成功，配置写为 `default_base_branch: null`；新 `read_config` 使用 `json.loads` 把分支名解析为 `None`，使下一次 `topic start`、`work-overview` 立即报“default_base_branch 必须为非空字符串”。这使 setup 接受并写出的合法配置不能使用，锚定当前验收 workflow-simplification-02#A1。冻结正式基线同序列的 setup 与 overview 均退出 0；冻结 head 的 setup 退出 0，但 overview/start 退出 1。最小复现：`PYTHONDONTWRITEBYTECODE=1 python3 /tmp/independent02/repro_null_branch.py`，比较断言退出 0；修复应使 setup 字符串序列化与读取保持类型。数字/true 的既有解析问题未作为本次回归报告。

## Spec

No findings.

当前 Ticket 的 quick/文档生命周期与提交边界已有冻结源和 CLI 证据；quick 摘要标题检查与后续 Skill 的逐条验收映射责任已分清。standard 自动补建/测试由 Ticket03、完成由 Ticket05/07 接入，迁移与最终 CLI 清理由 Ticket08/13 承担；这些未来能力没有作为 Ticket02 缺失项。

Code: P0=0, P1=0, P2=1, blocker=否；Spec: P0=0, P1=0, P2=0, blocker=否。

验证：冻结 artifact 145 项 SHA256 前后 match；相关原有测试 40 项与独立恢复/提交/分支探针 6 项均退出 0。完整构建资源树不在冻结材料中，未声明整个历史测试集合通过。审查者为新 Agent session `/root/independent_ticket02`；具体模型 ID 不可观察，记 null，保持 inherited。
