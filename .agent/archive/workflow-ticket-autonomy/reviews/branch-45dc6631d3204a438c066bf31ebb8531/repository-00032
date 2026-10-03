# 审查循环规则

适用于 runtime 管理的 高风险 Ticket、批次及可选整分支审查，以及设计、产物、指令、技术方案自检和主 Agent 临时派发的文档审查。runtime 管理内容绑定与两类代码审查计数；文档轮数由宿主记录，artifact-review 命令本身不计轮数。

## 输入与独立性

standard 下宿主派实际新上下文只读审查者，遵守用户的独立性、模型、思考档位和成本限制；默认继承实施者能力，不擅自升降级，结果写实际模型。材料包包含冻结改动、当前验收（批次为批次 Ticket 并集，整分支为 Topic 并集）、下游 Ticket、已决事项清单、本规则和结果骨架。审查者不读实施者总结或执行简报中的实施计划。派不出时完成增强自审并如实记录 `self` 与独立性缺口；不声称隔离。更强模型只能由用户临时指定。

宿主在对齐点和用户裁决后向 `.agent/work/<topic>/decided/decided-<topic>.md` 追加已决事项。审查者不能凭偏好重开产品决定；新代码或运行证据推翻事实时核实并更新影响，涉及已批准目标、验收或风险承担才交用户裁决。

## 第一轮、复审与修复

第一轮穷尽整个固定范围，附覆盖清单：每条验收、每个 review probe、每个不变量均为无问题、对应 finding，或不适用（附理由）。发现给出位置、视角、依据与严重度。可达的出错路径或明确验收、不变量、项目规则足以成为阻断，不要求验收锚点。覆盖只是 spec 视角的一部分，不是发现准入门槛。

blocking 与 advisory/fix-in-batch 进入修复；fix-in-batch 包括解决发现所需的相关模块、调用方、消费者、测试与文档同步。其他建议 defer（建议归属）或 decline（理由），留到交付摘要。不能因下游拥有能力而放行当前可达故障。只有无需修复的建议时通过。复审仅检查本轮修复差异及可能受影响的地方；范围外新发现默认归建议。

修复可补齐已批准行为所需逻辑、场景和验证，新增负向回归测试本身不构成新增需求。只有修复需要改变已确认目标、外部行为、验收语义、明确用户限制或风险承诺时返回 `blocked-by-design`。技术事实错误及实现漏项归普通 spec/correctness；技术性设计调整自行记录与验证。修复前找出同一事实在其他位置的写法一起改；同一规则只在一个共享来源定义。思路写入命令的 `--notes-file`，不另写修复方案文档。

## 轮数与停止

代码审查每次 review 算一轮，每个对象最多4轮，最多3次修复。通过后内容改变，通过记录失效，再审占一轮。第4轮仍有阻断问题，或4轮已用完而当前内容没有有效通过记录时，停止并交用户决定；不会开第5轮。

审查结论为 `blocked-by-design` 或 `inconclusive` 时，runtime 也进入需用户处理状态；文档同样停止交用户裁决。

以下为诊断信号，提示检查是否仍有根因或设计缺口，不单独停止；最终判断依据当前有效审查、真实未解决发现和预算：

- 同一根因：连续两次复审有阻断问题，且落在紧邻的上一次修复差异内。
- 同一处连续修改：相邻两次修复在同一文件的行区间重叠，均换算到它们之间快照的行号。
- 体积膨胀：代码相对基线的增加行加删除行超过第一轮的1.5倍；文档以第一轮字节数为基准，多产物合并计算。

经证据确认同根因修复无进展、无法兼容的决策矛盾或必要验证不可获得时，以具体失败链说明停止；位置相近或变更多本身不证明这些情况。runtime 进入需用户处理的状态后拒绝继续审查；整分支停止也阻止 Topic 完成。技术性定义变化或已登记技术挑战可凭证据用 refresh 更新绑定、追加点名处置并重新验证；它保留同一 series 已开轮次及剩余预算，未提交轮次不返还，其他停止不解除。用户可接受现状、修订定义后重开，或放弃。Ticket/Spec 的有效定义修订可由 runtime reopen 开新审查 series，保留代码、基线及可追溯旧审查/自审历史；reopen 不全量消解自审发现，用户裁决只覆盖 reason 点名的 spec-challenge，未解 correctness blocking 仍需真实内容修复与重新验证；只改状态、认领或复选框不算定义变化。整分支重开也需首次审查或上次重开以来任一 Ticket/Spec 有有效变化。未通过的测试不能通过接受现状绕过。

Spec、技术方案与 Ticket 等文档每个产物只一次全面审查加最多一次复审；复审只看修复差异及受影响断言/影响面。仍未解决的问题交用户裁决，不再派第三轮；扩大范围、补审或“直到通过”不重置这个预算，也不能靠修订定义重置同一产物的文档预算。宿主逐轮写 `.agent/work/<topic>/reviews/review-log-<topic>.md`：产物、轮次、阻断数、建议数、修改范围、体积；无 Topic 时在对话报告这些字段。汇报已用轮数与剩余额度，不作趋势判断。

## 产物审查接口

artifact-review 方法名为 reader-first-writing、final-state-writing、visual-communication、artifact-finalization、humanizer；设计类再加 review-design。保留 expect-content-id；只接受普通产物或设计，不提供修复方案类型、并行或 Topic 参数，命令不计轮数。

## 语义矛盾字段的唯一准入

`contradicts` 仅用于已核实的语义矛盾：当前 finding 与引用的旧 finding 中仍有效的行为要求/决定，在同一适用条件下无法同时满足，且影响正确性、范围、验收或风险承担。reviewer 在 basis 给出双方命题、共同适用条件、不能兼容的证据及需裁决的影响；runtime 校验引用身份，不代替 reviewer 核实语义。有效 `contradicts` 会触发硬停止并请求裁决，不属于几何信号。

位置重叠、体积变化、普通建议差异、后续修正旧事实或已由有效定义消解的差异不填此字段。尚待核实的矛盾线索写入普通 finding/basis；新证据可在既有授权内纠正原事实时先核实影响，不自动等同无法兼容的决定。

## 结果

runtime 骨架预填 `unit_id`、`content_id`、`round`、`acceptance`、`probes`、`downstream_tickets`。审查者只填写判断字段：

- `status`: pass/findings/blocked-by-design/inconclusive；
- `reviewer`: provenance=independent/self，及实际 model；
- `coverage`: target、result=ok/finding/not-applicable、finding_id或reason；
- `findings`: id、severity=blocking/advisory、summary、location、view=correctness/impact/spec/spec-challenge/maintainability、basis（出错路径或被违反规则）。可选 anchor、failure_path、reachability、downstream_ticket；contradicts 仅按上述唯一语义准入填写；advisory 必填 disposition=fix-in-batch/defer/decline，defer 附 owner，decline 附 reason。

发现必须有位置与依据；pass 不含阻断、待修复建议或 spec-challenge。spec-challenge 仅用于需要改变已确认用户约定的挑战，交用户决定；技术事实错误及实现漏项归普通 spec/correctness，不能以“Spec 要求如此”放行。影响面必查，独立核实调用方与消费者。保留预填身份与内容不变，按 runtime 返回的材料和格式提交。停止时遵循[找用户的条件](user-intervention.md)。
