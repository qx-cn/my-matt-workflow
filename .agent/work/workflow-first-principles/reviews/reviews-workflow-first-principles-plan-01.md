---
review_id: workflow-first-principles-plan-01
artifact: ../specs/specs-workflow-first-principles-01.md
reviewer_provenance: self
status: approved-with-corrections-applied
---

# 开发主链优化方案自审

## 结论

方案可以进入实施。同会话自审逐项检查了目标、职责边界、兼容、验证和不改范围；它是增强自审，不是独立 reviewer evidence。

## 自审中已订正的边界

1. 不把五档自治 preset 替换为三档 assurance；两者正交，避免“更自动”等价于“更少保证”。
2. 不删除 `my-requirement-analysis`；先收窄为风险触发的方法，是否退役需 comparative evidence。
3. 不取消 audited runtime；quick 只适用于明确低风险范围，standard/audited 保留可恢复 evidence。
4. 不声称 runtime 能拦截聊天 final；目标是缩小误用面并提供唯一 next action。
5. 不一次性拆散 `run_journal.py`；先提取纯验证职责，保持现有 CLI、journal 和 fixtures 兼容。
6. 不把历史 Astra evidence 自动升级为当前 release 的 evidence；执行 registry 必须绑定 release 和 digest。
7. 构建 release 属于源码交付闭环；安装 Codex/Claude/Cursor 是另一个授权边界。

## 残余风险

- assurance 分级会改变路由语义，需要 fresh-agent 行为验证；本轮先提供 deterministic contract，不伪造行为通过。
- runtime 拆分容易产生循环依赖；每次只移动纯函数并由旧入口委托。
- execution-evidence registry 若索引工作区外文件会不可复现，因此只允许仓库内相对路径。
- comparative 验证有明显模型成本，保持 planned，等待单独授权执行。

