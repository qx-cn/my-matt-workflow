---
name: my-review-design
description: 在 my-to-spec、my-tech-design、my-review-artifact 流程中作为指定阶段的方法被调用。
---

# 独立设计审查

拆 Ticket 前唯一的独立设计关口。只评审，不改文档、不重新访谈、不替用户补齐决策。独立调用按[工作产物访问](references/shared/adapters/artifact-access.md)读取用户指定的方案；组合调用只读宿主固定 review_unit，发现归入 review-design check。读取适用项目规则、已决事项和引用的仓库/文档；读代码核实承重现状断言是必做项。

按[审查循环](references/shared/review-loop.md)派新上下文审查者，继承作者模型和思考档位；派不出时按增强自审完成，如实记 self。一次全面审查加最多一次复审，只看修复差异和受影响断言/影响面；“直到通过”、扩大范围或换阶段均不重置预算。剩余问题在下一个现有对齐点按[共同条件](references/shared/user-intervention.md)交用户裁决，不新增对齐点。

## 四组必查项

1. **承重现状断言核验**：逐条在代码及引用材料中核实会改变方案成立、接口、数据语义或验收判断的断言，不能只靠推理排除。可查事实自行查证，无法验证的进入依据与未知。
2. **影响面与上线兼容**：独立找调用方、消费者、现有写路径与并发控制；检查存量数据、发布/回滚期间新旧实例并存（锁键、配置键、表结构变更顺序）、权限、性能及数据量。
3. **方案内部成立**：待决策项、推导/依赖、内部一致性、异常与状态闭环。公开接口、数据语义、迁移或持久状态变更要核对更小方案/维持现状能否得到同等结果，按[第一性原理推理](references/shared/first-principles-reasoning.md)核对复杂度是否必要。
4. **需求语义与 Spec 挑战**：列出无法从代码或已决事项验证的产品/业务假设；审查请求顺带给出的规则也不能直接当作已决前提。方案与系统冲突或照做导致可达故障，提出 spec-challenge，由用户决定修订、接受风险或照原方案继续。已决事项不得重开。

措辞、格式、最终态写作和篇幅不属于设计审查，由作者自检与普通产物审查负责。

## 报告四部分（缺一不可）

- **承重断言核验表**：每条断言标为已核实（附代码/文档位置）、与现状不符（关联发现 id）、无法核实（转入依据与未知）。
- **审查发现**：id、位置（Spec章节及代码位置）、视角 correctness/impact/spec-challenge、依据（可达路径或规则）、严重度 blocking/advisory；建议附 fix-in-batch/defer（归属）/decline（理由）。每条用具体场景或时序说明影响，不能仅写结论。不以“Spec要求如此”放行故障。
- **已考察但排除的风险**：每条排除理由及依据，不能推理后静默丢弃。
- **待用户确认的需求语义假设**：每条写明用户需要决定什么。

无内容的部分写“无”并附理由。宿主缺任一部分、断言与现状不符却无对应发现、仍含挑战或未决语义假设，均不得记通过；核验表未知项如实留在依据与未知。挑战和语义假设由宿主在下一个现有对齐点用平实中文列出，裁决写入已决事项。组合模式的结果附 design_report：assertions、findings、excluded_risks、semantic_assumptions 四部分（无内容用 {none: 理由}），核验表条目 assertion/status/evidence/finding_id，状态 verified/mismatch/unknown；发现沿用上述字段。

JSON 排除风险条目 risk/reason/evidence 均为非空文字；semantic_assumptions 用非空文字逐条写假设及需要用户决定的内容。
