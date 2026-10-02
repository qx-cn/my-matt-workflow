# Revision 2 并行施工与集成计划

授权依据：用户已接受方向，完成 Spec 复审后明确要求并行施工。本阶段完成 Spec revision 2 的源码候选、机制验证和独立审查；不借此执行真实宿主升级或真实模型效果试验。已有 Spec 正文逐字保留，当前授权与实施进展记在本计划和运行状态，不追写历史 Spec。

一个集成批次包含四张 Ticket。前三张没有依赖，分别在隔离 worktree 并行准备；第四张依赖前三张的完整候选并承担跨组契约、README、最终对象归宿和评估说明。文件数虽超过启发式，三组共享语义与最终打包闭包，因此保持同一批次，避免给未集成候选制造三次独立全量审查。主工作区按01→02→03→04集成，逐票定向测试、自审、本地提交，最后一次批次完整测试和独立全范围审查。

| Ticket | 负责组 | 边界与协调 | 源验收owner |
|---|---|---|---|
| 01 | runtime Agent | workflow_lib 中项目执行/证据/审查，不改构建安装模块或CLI根文件 | AC01–03/09/18/19 |
| 02 | install Agent | workflow.py、release/installer/doctor/projection 与对应测试；不改项目Ticket/批次模块 | AC20–22 |
| 03 | instruction Agent | Skill/resources/policies/composition 和专属文本契约测试；不改Python runtime | AC04–08/10–15/23–25 |
| 04 | 主 Agent | README、对象归宿和变化索引、跨组共享测试与集成行为、效果验证说明 | AC16/17/26 |

各子组不得编辑另组文件；共享测试tests/test_workflow.py与tests/test_portfolio.py由主 Agent 改，子组报告必要调整。资源治理由指令组检查真实消费者，主 Agent协调机械/行为证据分类。实现中发现新范围或真实Spec挑战才请求决定；普通修复自行继续。各组保留red/green证据、改动与剩余风险，不宣称本地通过证明真实宿主或七项能力提升。

先提交现有诊断/Spec/审查/本计划和Tickets作为基线，再创建worktree；历史Topic不修改。主 Agent持有本Topic唯一runtime写入口，子组仅准备代码，避免并行mutation污染状态。审查使用固定快照的新上下文，来源与内容匹配可核验。
