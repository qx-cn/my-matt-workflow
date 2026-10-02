# Workflow 优化提案

用户已接受建议，本轮完成补充审核及完整 SPEC revision 2；没有修改正式 Skill、resource 或 runtime。用户要求先止於 SPEC，后续实施与可替換完整版本另阶段进行。

先读：

- [诊断与修改方案](reviews/reviews-workflow-outcome-optimization-diagnosis-01.md)：按影响排序、原文与失敗路徑、应保留机制、歷史证据界限。
- [当前 SPEC revision 2](specs/specs-workflow-outcome-optimization-02.md)：完整候选行为、九个改动包、26 项验收、兼容边界与七项能力评价。
- [工作计划与分工](plans/plans-workflow-outcome-optimization-01.md)。

完整覆盖与证据：

- [32 个 Skill 的逐项归宿](reviews/reviews-workflow-outcome-optimization-skills-01.md)。
- [39 个资源/策略/组合对象的逐项归宿](reviews/reviews-workflow-outcome-optimization-rules-01.md)。
- [runtime 与效果证据审查](reviews/reviews-workflow-outcome-optimization-runtime-01.md)。
- [SPEC 首輪独立设计审查](reviews/reviews-workflow-outcome-optimization-design-01.md)：兩条邊界问题，已在候選 SPEC 修正。
- [SPEC 唯一差異复审](reviews/reviews-workflow-outcome-optimization-design-02.md)。
- [证据、快照收据与离线复现](evidence/README.md)。

三组主审并行完成；尾部差異复审、清單/引用检查和证据核验也并行。未变更模型或思考档位。分工文件保留原审查时的描述，最终 content match、覆盖和交付状态見 [结算收据](evidence/verification.json)。

本轮有限探針能证明完成判断漏洞和机械假阳性，不能证明候選版的模型效果。后续应先实施並通過机制验证，再依 SPEC 的真实任务计划比较；提交、发布、安装和模型成本变更仍分别遵循授权。

追加分析：[Runtime、安装升级精简与七项能力收益](reviews/reviews-workflow-outcome-optimization-extension-01.md)。这是 revision 2 的输入；接受的建议已整合入当前 Spec，旧报告保留原时点边界。

最新补充：[七项能力审核及条款映射](reviews/reviews-workflow-outcome-optimization-capability-audit-02.md)。revision 1 已标 superseded；本次只更新 Topic 文档，正式 workflow 尚未实施。

[Revision 2 独立设计审核](reviews/reviews-workflow-outcome-optimization-design-03.md)：pass，无阻断；[本次验证收据](evidence/r2-verification.json)。

最新：[用户请求的 Spec 复审](reviews/reviews-workflow-outcome-optimization-design-04.md)：三组独立并行核对源码，pass；无实质修改，revision 2 保持 current。
