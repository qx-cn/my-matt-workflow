---
name: my-artifact-finalization
description: 在写入、发布或交接前只读审查承重文档；检查来源、内部一致性、读者重建和事实正确性四项 gate。
disable-model-invocation: true
---

# 产物最终校验

只读评审用户指定的 Spec、handoff 或其他承重文档，不修改文档、不替作者补充事实，也不把普通文风问题升级为 blocker。阅读并执行[产物最终校验](references/shared/artifact-finalization.md)；该共享规则是唯一权威来源。

只检查会改变目标、范围、公开接口、数据语义、验收、风险承担或下一步动作的主张。分别运行来源账本、内部一致性、读者重建和事实正确性四项 gate；一项失败不能被其他项抵消。需要核实仓库、执行或外部来源时读取相应证据，不能获得的承重证据标为未知。

每个发现给出主张位置、失败的 gate、可定位的证据、影响及解除方式；同一根因跨 gate 出现时合并，并列出所有受影响 gate。四项全部通过时写 `No findings.`；不得用总分、笼统正确率或无证据的通过清单代替结论。
