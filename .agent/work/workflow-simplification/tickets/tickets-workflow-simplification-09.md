---
id: "workflow-simplification-09"
title: "按新 Skill 清单构建三种宿主安装件"
ticket_kind: "implementation"
spec_id: "workflow-simplification"
spec_revision: 1
spec_ref: ".agent/work/workflow-simplification/specs/specs-workflow-simplification.md"
supersedes_ticket: []
compensates: []
status: complete
blocked_by: ["workflow-simplification-08"]
claimed_by:
tags: []
sequence: 9
test_commands: ["python3 -m unittest discover -s tests"]
rule_sources: [".agent/work/workflow-simplification/specs/specs-workflow-simplification.md", "resources/testing-seams.md"]
rule_scope: ["skills/**", "resources/**", "composition/**", "portfolio/**", "tools/**", "tests/**"]
rule_constraints: ["Spec 核心模型为状态与命令唯一权威；范围外工作不实施。", "验证仅断言可观察命令结果、状态、提交、归档和度量，不复刻内部算法。", "方法正文的主链行为和上游语义后续切片负责；本 Ticket 将结构、引用和校验一起改完，不产生引用不存在 Skill 的安装件。"]
rule_conflicts: []
review_probes: []
execution_agent: "auto"
---

# 09 — 按新 Skill 清单构建三种宿主安装件

**要构建什么：** 构建输出恰好 32 个 Skill，调用方式由组合清单确定，资源仍可读取；无需正文副本，release 保留规则自动生效。

**被谁阻塞：** 08 — 预览并安全迁移旧项目产物

## 适用规则与影响区域

- 规则来源：源 Spec revision 1（第 7 节结构/调用边/冻结、第 11 节构建及构建前置校验；AC-29、30、40）；共享测试 seam 约定。当前 Codex resolve-rules 未发现仓库原生规则；execution_agent 保持 auto，实施前按实际绑定 Agent 和修改路径重新解析。
- 影响区域：skills/**、resources/**、composition/**、portfolio/**、tools/**、tests/**。
- 实施约束：方法正文的主链行为和上游语义后续切片负责；本 Ticket 将结构、引用和校验一起改完，不产生引用不存在 Skill 的安装件。 关键契约以源 Spec 原文为准；不推送、不建 MR、不写外部系统。
- 验证：三宿主投影、精确 Skill/调用集合、Markdown 链接、资源归属和临时 release 保留测试；冻结正文差异核对。
- 测试边界：以上 test_commands 为声明；与项目配置的匹配在新 runtime 生效后校验。旧 runtime 施工并非本 Spec 的必需条件，不能伪造实施 receipt。

## 已确认的拆分调整

用户确认将构建前置校验迁移及必要的 check 入口解耦从 13 前移到 09；Spec revision 1 不变。build/preflight/source_gate 不再读取 evals、smoke 或行为证据注册表；静态集合、元数据、链接、资源、调用与安装投影校验由 tests 承担。保留来源与文件安全校验，同步受影响测试，不修改 evals 历史内容。13 负责目录及剩余命令/模块删除和最终集成。

## 验收标准

- [x] 完成第 7 节所有合并与改名，保留被合并方法的必要规则于共享资源；资源清单与 governance 归属同步；源码 Skill 集合恰好为指定 32 个。
- [x] 组合清单支持 method/handoff/chain 的精确调用边，被调用方恰好指定 11 个；ask-matt 路由其余 31 个但不算调用边；不新增调用边。
- [x] Cursor/Claude 手动入口保留 disable-model-invocation true、被调用方不设置；Codex allow_implicit_invocation 按同一清单投影；构建/安装校验均用组合清单。
- [x] 源码删除正文复制机制，构建件没有 references/composed；调用改用宿主语法，共享资源按清单分发，所有本地链接有效；删除 portfolio 及依赖它的校验代码。
- [x] my-research 方法原文移到共享资源，由 research/wayfinder 指向；8 个冻结 Skill 仅发生 Spec 许可的全局改动，保留用于最终比较的施工前正文。
- [x] build 后只保留当前、上一版及被安装状态引用的 release；通过临时安装根验证构建与安装校验，不写真实宿主目录。

- [x] 从施工前基线转换为新清单后，build 与临时三宿主 install 校验不读取旧 Skill eval 路径；破坏新集合、调用元数据或本地链接时仍拒绝构建；tests 验证实际产物。
