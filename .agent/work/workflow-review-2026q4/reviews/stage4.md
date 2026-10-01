# 第四段：Spec/Ticket、设计审查、访谈交接

基线7625add；范围AC27–38、I10/I11。

Spec现状事实、七项系统影响、修订整合/单一current、参考篇幅3,000+1,000×预计Ticket数（无实测初值）与短承重论证。Ticket移除必需rule_*、保留旧字段读取、触点非边界、可发布中间状态与非契约实现细节不写死。运行时启动保守解析现有路径，审查按实际改动路径解析；迁移同步可选字段。

设计检查与报告按四组/四部分，强制代码核实、排除风险留证、语义假设交既有对齐点；to-spec/tech-design自动触发，to-tickets只切分。设计产物提交新增design_report结构守卫，通用产物四字段不变。文档预算为一次全面+最多一次修复差异复审，由宿主记录，不靠重开快照/产物阶段/“直到通过”重置。

初审 stage4_review 新上下文：1 blocking（ticket-selection仍强制旧字段）、2 advisory（设计result适配旧四字段、outside_scope错误边界信息）；均修复。独立48+26测试与公共CLI复现。

复审 stage4_rereview 新上下文：0 blocking/0 advisory；69项相关测试及设计报告、新无字段Ticket、高风险审查、无字段存量迁移探针通过。

主Agent全套检查另外发现资源consumer包装声明与新引用不一致、旧调用图测试未含tech-design→review-design；修正直接依赖与契约预期，不改部署机制。复审已核查包装；调用图预期补强后运行最终全套。修正第二段遗留my-grill-with-docs强制整分支措辞，原因是它在本段修改的主链入口仍传播已替代协议。

文本闭包33,801字符，记录stage4-text.json；静态文本检查全部通过stage4-text-checks.json。设计演练design_drill为新上下文一次，预期三项均命中；原玩具未修改，结果在evidence/design-drill/result.md。额外语义挑战不是实际需求裁决。

全套命令 python3 -m unittest discover -s tests -f，最终结果 evidence/stage4-tests.txt。无未解决阻断。
