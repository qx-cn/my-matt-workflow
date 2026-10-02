---
id: workflow-outcome-optimization-05
title: 补偿整体审查发现的完成门禁与恢复路由缺口
ticket_kind: compensation
spec_id: workflow-outcome-optimization
spec_revision: 2
spec_ref: .agent/work/workflow-outcome-optimization/specs/specs-workflow-outcome-optimization-02.md
status: completed
completion_source: direct-engineering
compensates: ["workflow-outcome-optimization-01", "workflow-outcome-optimization-04"]
---

# 05 — 整体审查补偿修复

用户明确要求“修复上述问题（注意工作效率和并发度）”。本票补偿整体审查 R1/P1、R2/P1、R3/P2，并顺手消除同报告 O1/P3 的局部路由歧义。O2 为待验证的成本建议，不据此删除既有保护。保持 revision 2 Spec、此前完成 Ticket 和审查报告的历史结论。

采用普通工程施工，不调用本 workflow 的 Skill/runtime 管理本票，不产生产品自签回执。公开 CLI 只在临时合成项目中作为被测对象运行。

## 分工与顺序

- 状态修复 Agent：R1 活动 batch 的历史未解发现，R3 branch 恢复后的状态与下一步；负责 batches、branch_review、topic_service 和单独测试文件。
- 失败分类 Agent：R2 普通脚本异常与启动缺口区分、旧缓存失效；负责 evidence 和相关测试。
- 独立审查 Agent：先准备反例/正向恢复矩阵，待集成冻结后验证，不参与生产修改。
- 主 Agent：O1 文字修正、集成核对、完整测试、独立结论协调与交付。

生产文件分区写入，交叉变更先协调。作者仅跑有针对性的测试；冻结集成版后，将完整 suite 与独立审查并行，避免多人重复跑完整 suite。

用户后续指定全部切到 `gpt-6.1-sol`。原 Agent 停止，两名同模型作者接管现有修改；主会话与 Paseo 独立 reviewer 的实际 runtime 均核对为 `gpt-6.1-sol/high`，内置作者显式指定该模型。线程数量达到上限后，独立复审用通用 Paseo 管理工具启动，不改模型/权限成本档位。R2 在预审中补齐 unittest loader 包装的同根因，不把异常类型或包装结构当成业务未执行证明。

## 修复验收

- [x] R1：旧 complete Ticket 的 blocking/spec-challenge 在活动 batch 中可见并控制普通收口；普通 pass 不消解，合法修复或点名裁决后能恢复，原完成历史保留。
- [x] R2：真实动态导入业务失败与旧 v1 分类缓存不能伪装环境缺口绕过 close；明确的解释器启动缺口仍准确披露，未知非零退出不补成功。
- [x] R3：旧 branch 有当前有效 pass 的几何停止正常恢复，status 输出合法下一步；缺失或过期 pass 仍阻断，保留恢复依据。
- [x] O1：只有当前授权阶段仍有必要工作时才选择继续，已完成止点不被空间充足条件吞掉。
- [x] 集成定向/完整验证通过，并完成基于冻结源码的独立复审；实际证据、限制与新交付单独记录。

对应原 Spec AC01/02/03/05/09/18/19。发布、真实宿主安装和模型能力对照不属于本次修复执行。

## 完成证据

冻结集成版 283 文件摘要与源码一致；完整 suite 四片并行执行 352 项，全部通过。独立复审 R1/R2/R3 的 20 个有效场景通过，限定范围无阻断。原失败夹具及作者失败进程原样留存，不计作通过。

- [本次交付](../deliveries/deliveries-workflow-outcome-optimization-03.md)
- [完整测试结果](../evidence/compensation-05/full-suite/result.json)
- [独立复审报告](../evidence/compensation-05/independent/outcome-compensation-review-final.md)
- [结构化完成证据](../evidence/compensation-05/completion-evidence.json)

本票以普通工程方式记录完成；未运行 workflow 自身的完成命令治理本票，未发布、推送或安装真实宿主。
