---
id: workflow-outcome-optimization-06
title: 补偿 Python 3.10 loader 分类兼容与安装诊断范围
status: completed
ticket_kind: compensation
completion_source: direct-engineering
spec_ref: .agent/work/workflow-outcome-optimization/specs/specs-workflow-outcome-optimization-02.md
compensates: ["workflow-outcome-optimization-05"]
---

# 06 — CI 与本机安装补偿

用户授权安装到本机 Codex/Claude，随后要求修复安装问题和推送后的流水线错误。采用普通工程施工；不使用被测 workflow 的 Skill/runtime 治理本票，原 Spec、完成 Ticket 和原始审查记录保持字节不变。

## 范围与验收

- [x] 兼容 Python 3.10 的 unittest loader class-only 身份与 Python 3.14 的 class.method 身份；统一识别，保持完整 typed 诊断证明和 v3 指纹比较。
- [x] 新失败、改变的 loader 诊断、真实 Assertion 与旧错误缓存不能借粗粒度身份成为 known 或环境豁免；可比较同诊断正例保留。
- [x] Markdown 校验仅排除根 `.agent/work` 的活动数据与归档证据；正式文档、其他 `.agent` 文档、项目配置及源码 fixture 继续拒绝缺失/逃逸链接。
- [x] 定向检查、最终冻结源码的独立复审及完整构建检查通过；推送后的 Python 3.10/3.14 CI 均明确成功。
- [x] 同一最终 release 安装到本机 Codex 与 Claude；各宿主实际内容、runtime、source_match 与工作区/远端身份分别核验。

## 协调

CI 作者负责 evidence/batches 及 loader 专用测试；安装诊断作者负责 validator 与文档范围测试；独立 reviewer 不参与生产修改，仅审核冻结候选；主 Agent 负责集成、提交推送、串行 release 变更与双宿主验证。全部作者/独立 reviewer 使用用户指定的 gpt-6.1-sol。

不删除 Python 3.10 矩阵，不通过重写原始证据使校验转绿。保留本机缺少 Python 3.10 的事实，以真实 GitHub Python 3.10 执行补足验证。

## 完成证据

最终构建完整检查通过；最终 CI run 37032744557 的 Python 3.10/3.14 两个 job 均成功。独立复审 7+2 组通过，并核验 final02 唯一变化为临时 migration fixture 配置。Codex/Claude 均安装 `20261003-001558`、32 Skills；doctor 实际内容有效、source_match=true，两个 runtime --help exit 0。

- [交付说明](../deliveries/deliveries-workflow-outcome-optimization-04.md)
- [完成证据](../evidence/compensation-06/completion-evidence.json)
- [双宿主验证](../evidence/compensation-06/host-verification.json)

后续完成记录仅修改本 Topic 的活动记录和工件，不改变经测试/复审的源码。原失败日志保留，未算作通过。
