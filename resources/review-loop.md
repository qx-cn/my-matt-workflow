# 审查循环规则

适用于 runtime 管理的 Ticket 与多 Ticket standard 整分支审查，以及设计、产物、指令、技术方案自检和主 Agent 临时派发的文档审查。runtime 管理内容绑定与两类代码审查计数；文档轮数由宿主记录，artifact-review 命令本身不计轮数。

## 输入与独立性

standard 下宿主派新上下文只读审查者，继承实施者的模型和思考档位，不为省额度降级；结果写实际模型。材料包包含冻结改动、当前验收（整分支为全部 Ticket 验收并集）、下游 Ticket、已决事项清单、本规则和结果骨架。审查者不读实施者总结或执行简报中的实施计划。派不出时完成增强自审并如实记录 `self` 与独立性缺口；不声称隔离。更强模型只能由用户临时指定。

宿主在对齐点和用户裁决后向 `.agent/work/<topic>/decided/decided-<topic>.md` 追加已决事项。审查者不得重开；异议以 `inconclusive` 交给用户。

## 第一轮、复审与修复

第一轮穷尽整个固定范围，附覆盖清单：每条验收、每个 review probe、每个不变量均为无问题、对应 finding，或不适用（附理由）。发现给出位置、视角、依据与严重度。可达的出错路径或明确验收、不变量、项目规则足以成为阻断，不要求验收锚点。覆盖只是 spec 视角的一部分，不是发现准入门槛。

blocking 与 advisory/fix-in-batch 进入修复；fix-in-batch 限已触及代码。其他建议 defer（建议归属）或 decline（理由），留到交付摘要。不能因下游拥有能力而放行当前可达故障。只有无需修复的建议时通过。复审仅检查本轮修复差异及可能受影响的地方；范围外新发现默认归建议。

修复只改正、删除或收窄。需要新增规则、场景或要求时返回 `blocked-by-design`。修复前找出同一事实在其他位置的写法一起改；同一规则只在一个共享来源定义。思路写入命令的 `--notes-file`，不另写修复方案文档。

## 轮数与停止

每次 review 算一轮，每个对象最多4轮，最多3次修复。通过后内容改变，通过记录失效，再审占一轮。第4轮仍有阻断问题，或4轮已用完而当前内容没有有效通过记录时，停止并交用户决定；不会开第5轮。

审查结论为 `blocked-by-design` 或 `inconclusive` 时，runtime 也进入需用户处理状态；文档同样停止交用户裁决。

以下任一信号也停止：

- 同一根因：连续两次复审有阻断问题，且落在紧邻的上一次修复差异内。
- 同一处连续修改：相邻两次修复在同一文件的行区间重叠，均换算到它们之间快照的行号。
- 前后矛盾：finding 的 `contradicts` 指向之前一轮的问题。
- 体积膨胀：代码相对基线的增加行加删除行超过第一轮的1.5倍；文档以第一轮字节数为基准，多产物合并计算。

runtime 进入需用户处理的状态后拒绝继续审查；整分支停止也阻止 Topic 完成。用户可接受现状、修订定义后重开，或放弃。Ticket/Spec 的有效定义修订可由 runtime reopen 重置历史，保留代码与基线；只改状态、认领或复选框不算定义变化。整分支重开也需首次审查或上次重开以来任一 Ticket/Spec 有有效变化。未通过的测试不能通过接受现状绕过。

文档每个产物最多4轮；扩大范围、补审或“直到通过”不重置。宿主逐轮写 `.agent/work/<topic>/reviews/review-log-<topic>.md`：产物、轮次、阻断数、建议数、修改范围、体积；无 Topic 时在对话报告这些字段。汇报已用轮数与剩余额度，不作趋势判断。

## 产物审查接口

artifact-review 方法名为 reader-first-writing、final-state-writing、visual-communication、artifact-finalization、humanizer；设计类再加 review-design。保留 expect-content-id；只接受普通产物或设计，不提供修复方案类型、并行或 Topic 参数，命令不计轮数。

## 结果

runtime 骨架预填 `unit_id`、`content_id`、`round`、`acceptance`、`probes`、`downstream_tickets`。审查者只填写判断字段：

- `status`: pass/findings/blocked-by-design/inconclusive；
- `reviewer`: provenance=independent/self，及实际 model；
- `coverage`: target、result=ok/finding/not-applicable、finding_id或reason；
- `findings`: id、severity=blocking/advisory、summary、location、view=correctness/impact/spec/spec-challenge/maintainability、basis（出错路径或被违反规则）。可选 anchor、failure_path、reachability、contradicts/downstream_ticket；advisory 必填 disposition=fix-in-batch/defer/decline，defer 附 owner，decline 附 reason。

发现必须有位置与依据；pass 不含阻断、待修复建议或 spec-challenge。spec-challenge 交用户决定修订 Spec、接受风险或按原 Spec 继续，不能以“Spec 要求如此”放行。影响面必查，独立核实调用方与消费者。保留预填身份与内容不变，按 runtime 返回的材料和格式提交。停止时遵循[找用户的条件](user-intervention.md)。
