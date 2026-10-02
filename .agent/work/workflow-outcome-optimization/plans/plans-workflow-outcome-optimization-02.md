# Revision 2 并行施工与集成计划

授权依据：用户已接受方向，完成 Spec 复审后明确要求并行施工。本阶段完成 Spec revision 2 的源码候选、机制验证和独立审查；不借此执行真实宿主升级或真实模型效果试验。已有 Spec 正文逐字保留，当前授权与实施进展记在本计划与普通工程记录，不追写历史 Spec。

一个集成批次包含四张 Ticket。前三张没有依赖，分别在隔离 worktree 并行准备；第四张依赖前三张的完整候选并承担跨组契约、README、最终对象归宿和评估说明。文件数虽超过启发式，三组共享语义与最终打包闭包，因此保持同一批次，避免给未集成候选制造三次独立全量审查。前三组按准备就绪顺序串行集成，第四组最后集成，逐项验证实际测试并本地提交，最后完整测试和新上下文全范围代码审查。

| Ticket | 负责组 | 边界与协调 | 源验收owner |
|---|---|---|---|
| 01 | runtime Agent | workflow_lib 中项目执行/证据/审查，不改构建安装模块或CLI根文件 | AC01–03/09/18/19 |
| 02 | install Agent | workflow.py、release/installer/doctor/projection 与对应测试；不改项目Ticket/批次模块 | AC20–22 |
| 03 | instruction Agent | Skill/resources/policies/composition 和专属文本契约测试；不改Python runtime | AC04–08/10–15/23–25 |
| 04 | 主 Agent | README、对象归宿和变化索引、跨组共享测试与集成行为、效果验证说明 | AC16/17/26 |

各子组不得编辑另组文件；共享测试tests/test_workflow.py与tests/test_portfolio.py由主 Agent 改，子组报告必要调整。资源治理由指令组检查真实消费者，主 Agent协调机械/行为证据分类。实现中发现新范围或真实Spec挑战才请求决定；普通修复自行继续。各组保留red/green证据、改动与剩余风险，不宣称本地通过证明真实宿主或七项能力提升。

先提交现有诊断/Spec/审查/本计划和Tickets作为基线，再创建worktree；历史Topic不修改。施工使用普通工程工具与独立代码审查，不调用本仓库 Skill 或 runtime 管理真实施工；被测 CLI 只在隔离夹具中验证。审查使用固定代码快照的新上下文，实际来源与内容匹配可核验。

## 用户补充的施工约束

用户明确要求“不用workflow本身的skill来施工，会陷入循环自证”。此指令优先于本产品默认自托管流程：Spec/Skill/runtime全部作为被开发对象，不作为施工控制器；不创建或伪造真实Topic运行回执。Ticket仅为分工及证据索引，状态据实际测试与独立审查记录，注明direct-engineering来源。独立代码审查者按普通正确性/兼容性判断，不以被测workflow自行输出pass作为充分证据。通用Python测试、Git、代码阅读和通用skill-creator不属本workflow自身Skill。

## 普通工程收口

四项分工已完成；338 项最终完整 unittest 退出 0，最终源码 281 文件与冻结 final07 匹配。17 项独立阻塞已逐项修复并在限定范围复审，当前未解阻塞 0。安装和指令未变文件绑定原通过结论；runtime 最新三文件另做新上下文窄复审，避免重复全量检查。完整源码包和验收索引见本 Topic deliveries/evidence。原 Spec 逐字保留，施工不自托管；没有执行真实发布、宿主升级或模型效果试验。
