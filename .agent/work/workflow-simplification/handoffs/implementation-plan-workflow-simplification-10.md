# Ticket10 实施计划

边界：Spec revision1，第1–6、9节，当前七条验收。仅改 Skill、共享资源、相关 policy 与 tests；不改施工 profile 或 runtime，不吸收11/12/13的方法/配置/CLI范围。

## 文件与行为

- grilling/grill-with-docs/grill-me：依赖分轮批量提问、需求核对、来源摘要、等级提议；主链两次对齐后自动调用。
- to-spec/to-tickets/implement：去长期Spec依赖，统一主链自动继续；实施前补写计划，状态恢复，交付摘要及项目知识沉淀。
- domain-modeling 的正文及格式：项目级 CONTEXT/ADR；handoff：仅换宿主/目录/人或访谈未成Spec，取消ready/draft与独立重建门槛。
- 新增 user-intervention 和 review-loop 两份唯一规则；六个审查Skill与相关权威适配/策略引用。共享资源的 manifest/governance 同步。
- 保证等级及实施/产物审查适配：采用 Spec 已实现的 v2 命令、独立性如实记录和文档日志；施工仍使用已安装的旧 runtime，二者不混用。

## 验收与验证

A1/A2：静态审查批量提问、摘要来源和两个对齐点；真实构建验证宿主调用投影与本地链接。
A3/A4/A5：逐项对照 Spec 唯一共享规则、六个读取入口、独立上下文/实际模型与四轮停止；实际资源闭包打包验证，语义审查不把字串存在当行为证据。
A6：逐项映射实施计划、quick不同测试/代码、八项固定摘要与知识路径；A7：对照长期知识和handoff边界及格式。
输入边界：复杂/类比请求、没有代码库、依赖问题、缺新上下文能力、环境阻塞、已决事项、第四轮后漂移、下游所有权、Topic尚未配置。

文档改动采用语义审查与真实打包/投影检查；不运行模型效果评估，不新建外部目标，不推送或真实部署。声明的完整 unittest 在最终源码稳定后通过施工runtime登记回执。
