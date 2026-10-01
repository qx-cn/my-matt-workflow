---
id: "workflow-simplification-13"
title: "完成命令收缩与全量行为验证"
ticket_kind: "implementation"
spec_id: "workflow-simplification"
spec_revision: 1
spec_ref: ".agent/work/workflow-simplification/specs/specs-workflow-simplification.md"
supersedes_ticket: []
compensates: []
status: complete
blocked_by: ["workflow-simplification-10", "workflow-simplification-11", "workflow-simplification-12"]
claimed_by:
tags: []
sequence: 13
test_commands: ["python3 -m unittest discover -s tests"]
rule_sources: [".agent/work/workflow-simplification/specs/specs-workflow-simplification.md", "resources/testing-seams.md"]
rule_scope: ["tools/**", "tests/**", "evals/**", "skills/**", "resources/**", "policies/**", ".gitignore", ".github/workflows/**"]
rule_constraints: ["Spec 核心模型为状态与命令唯一权威；范围外工作不实施。", "验证仅断言可观察命令结果、状态、提交、归档和度量，不复刻内部算法。", "最终全量验证是集成承诺，不以静态核对代替行为验证；不构建或安装到真实宿主来证明测试。"]
rule_conflicts: []
review_probes: ["recovery"]
execution_agent: "auto"
---

# 13 — 完成命令收缩与全量行为验证

**要构建什么：** check 只运行 tests，完整验证新 CLI、迁移和安装件；旧命令不可调用，主链满足文本量上限，度量可供后续观察。

**被谁阻塞：** 10 — 接通两个对齐点与统一审查收尾；11 — 吸收上游五项方法改动；12 — 让技术方案保留契约并可独立阅读

## 适用规则与影响区域

- 规则来源：源 Spec revision 1（M1–M7、第 9–11 节、验证策略；AC-20 artifact 部分、22、27 新配置、28、31、34、37、38、39）；共享测试 seam 约定。当前 Codex resolve-rules 未发现仓库原生规则；execution_agent 保持 auto，实施前按实际绑定 Agent 和修改路径重新解析。
- 影响区域：tools/**、tests/**、evals/**、skills/**、resources/**、policies/**、.gitignore、.github/workflows/**。
- 实施约束：最终全量验证是集成承诺，不以静态核对代替行为验证；不构建或安装到真实宿主来证明测试。 关键契约以源 Spec 原文为准；不推送、不建 MR、不写外部系统。
- 验证：两 Python 版本全量 check、git diff 与文件状态比较，精确命令/字段/Skill 集合测试和文本量闭包用例；源 AC 核对项单独人工审阅。
- 测试边界：以上 test_commands 为声明；与项目配置的匹配在新 runtime 生效后校验。旧 runtime 施工并非本 Spec 的必需条件，不能伪造实施 receipt。

## 验收标准

- [x] 最终 CLI help 精确等于保留加新增命令，删除清单中每个命令均报未知；不存在旧版包新门面；artifact-review 保留旧参数和 expect-content-id，去掉 repair-plan/parallel/topic，按新方法名工作且不计轮数。
- [x] runtime 不读写长期 Spec，删除全部旧归档接口、长期发布链与已删除命令对应模块/测试；skills/resources/policies 不再出现已删除配置键和命令引用。
- [x] 样例已保留后删除 evals 及 fixture ignore 例外；确认 check 只运行 tests，完成剩余旧模块/命令清理和全量集成。构建前置静态校验及对应测试沿用 09 的已交付结果，不再加载 evals 或行为证据注册表。
- [x] 以 unittest 和 subprocess 在临时 git 仓库验证 quick/standard、private/shared，各 AC 缺陷注入及 M2–M5 每行迁移/前置条件、不变量；测试随各切片已交付，此处补跨切片缺口并运行全量。
- [x] 提供主链字符数测量函数及口径测试，Cursor 安装件 Markdown 传递闭包按内容去重，总数不超过 35000；测试注释写 Ticket 01 真实旧基线，不得删承重内容达标。
- [x] 度量每条包含第 11 节全部字段，Ticket/Topic/quick 的 kind/outcome、不可观察 null 和 self/independent/mixed 来源正确；metrics 按 Topic 汇总，command_errors 不含测试失败。
- [x] 最终对 8 个冻结 Skill 比较施工前正文，仅许可全局改动；method 移动、合并、资源和全局清理都没有夹带冻结方法改写。
- [x] Python 3.10 与 3.14 上 check 通过，执行前后被跟踪文件零变化；CI 保持 check 后 git diff exit-code 的验证，未运行的版本明确报告未验证。
