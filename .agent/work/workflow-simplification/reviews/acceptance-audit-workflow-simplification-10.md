# Ticket 10 文本验收核对依据

范围：Spec revision 1，当前 Ticket 的 A1–A7。核对对象是 Skill 文本及真实宿主安装件，不把文本核对等同模型执行效果。

| 验收 | 核对位置与可判定边界 |
|---|---|
| A1 | grilling 分轮、推荐与需求核对；grill-with-docs 的来源摘要、等级与无代码库分支；grill-me 只产摘要。 |
| A2 | grill-with-docs → to-spec → to-tickets → implement 的已登记调用边，第二对齐点列出行为、依赖、命令与测试边界，按依赖继续。 |
| A3 | user-intervention 唯一八项条件；instruction-authority、decision-taxonomy、write-actions/write-boundaries 只引用，共享文件随实际政策消费者交付。 |
| A4 | review-loop 对照 M4/第4节，六个指定入口指针；第一轮 coverage、影响范围复审、下游建议、修复约束、同事实联动、唯一规则。 |
| A5 | review-loop 的只读新上下文、继承模型/档位、实际模型与 self 缺口；四轮、三修复、四停止、日志与已决事项。当前施工按照已安装协议执行增强自审，不声称独立。 |
| A6 | implement 动手前计划、恢复 status；workflow-delivery 的八节和 quick 单独测试映射；domain-modeling 项目知识路径。 |
| A7 | to-spec 不读取/发布长期 Spec；domain-modeling 项目 CONTEXT/ADR；handoff 仅两类用途、无旧状态/重建门槛。 |

测试迁移：删除十项已失效的策略开关、强制 humanizer、旧全文重审和 handoff 门槛逐字断言；保留执行 Agent、Spec 血缘、风险测试、runtime 故障注入、资源引用/闭包/构建校验。新增实际 stage/install/verify 检查三宿主上的六个审查入口、交付资源和政策引用目标；不增加同义关键词评分。

已核对八个冻结 Skill 目录相对 Ticket 基线无变化。当前 Ticket 不承担 Ticket12 的技术方案方法，也不承担 Ticket13 的剩余旧 CLI/配置清理及跨切片集成。

测试和正式审查最终结果以本次 journal 的内容绑定 receipt 为准；本文件只记录核对依据。
