# workflow-simplification 分支收尾摘要

17张原 Ticket 已完成。整体审查新增的两项迁移 P1 已经补偿修复并验证，原 Ticket 和施工历史不改写。本摘要记录工程收尾；按 Spec 第10节，本仓库旧 Topic 保持原位置，不运行 migrate 或伪造 topic complete/归档回执。

## 改动概述

兼容旧 Spec 普通验收格式：无法提取带编号条目时，简报携带完整原文。整分支审查兼容已完成旧 Ticket：读取旧 journal 的实际 Agent 绑定；无法唯一确定时拒绝猜测。新增两项公共 CLI 回归测试。

## 测试结果

迁移测试初次15项中新增2项失败，分别复现原两项P1；修复后15项全部通过。完整 workflow.py check、32 Skills 校验、git diff --check 均通过。迁移后完成剩余 Ticket、整分支 test/review/submit、Topic complete及归档链路均验证；旧Spec、完成Ticket及旧journal字节保持一致。

证据与代码摘要：../reviews/branch-migration-fix-evidence/；复审：../reviews/review-branch-migration-fix.md。

## 审查发现与修复

整体审查发现的两项P1均已修复。修复差异按Code和Spec顺序自审，无新增有效finding，来源self。测试中的校准审查结果不作为独立模型审查证据。

## 建议

合并、推送、构建和真实宿主安装另按用户授权执行。宿主仍是旧39 Skills release，本分支源码为32 Skills；此前doctor显示drift，这是未部署状态。

## 已知问题

原整体审查的两项阻断已解决。本仓库旧Topic在新runtime中仍显示pending；它没有新格式topic-state，按已批准Spec保留历史，不为消除显示状态而迁移或补造记录。

## 长期知识沉淀

兼容消费者应读取历史真实绑定，不能由当前默认宿主回推；旧文档格式不应被简报提取器当作无效需求。上述规则已体现在实现与行为测试中，不新增门禁或重复ADR。

## 用户介入记录

沿用“收尾本分支”和“修复这些问题”的明确授权，完成本地修复、测试、复审及提交。原有未提交审核文档修改保留且不纳入修复提交。未推送、合并、安装或迁移本仓库历史。

## 未验证项

本轮仅运行Python3.14.4；未重跑3.10。未验证真实宿主更新后的模型行为、其他真实项目迁移或远端最新状态。
