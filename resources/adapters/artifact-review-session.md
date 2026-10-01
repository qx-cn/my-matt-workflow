# 产物审查适配

从宿主安装状态取得绝对 runtime_entry，运行 artifact-review-open --artifact <path>（多个文件重复参数），设计类使用 --kind design。消费其固定review_unit、content_id和所需方法，不另建未绑定结论。

方法名和适用维度遵循[审查循环](../review-loop.md)的产物接口，不适用给理由。humanizer 是审查方法，不是工作流强制润色步骤。

普通产物结果用 content_id、checks、findings、inconclusive；design 另须 design_report，四部分为 assertions、findings、excluded_risks、semantic_assumptions，无内容用 {none: 理由}。断言条目 assertion/status（verified/mismatch/unknown）/evidence/finding_id；与现状不符必须关联发现。设计发现字段 id/location/view（correctness/impact/spec-challenge）/basis/summary/severity，以及 advisory 处置和归属/理由。排除风险附理由和依据，待确认语义假设说明用户需要决定什么；挑战或未决假设不能记 pass。checks逐项闭合pass/finding/inconclusive/not-applicable。artifact-review-submit提交固定内容，快照和哈希由runtime验证，expect-content-id仍可用于验证/释放。文档轮次、日志和停止由[审查循环](../review-loop.md)约束，命令不计轮数；不得靠重新开快照重置文档限制。

JSON 排除风险条目 risk/reason/evidence 均为非空文字；semantic_assumptions 用非空文字逐条写假设及需要用户决定的内容。
