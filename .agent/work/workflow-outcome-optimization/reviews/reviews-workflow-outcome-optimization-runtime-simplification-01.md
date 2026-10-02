# Runtime 精简追加分析（只读）

审查输入：固定审查单元（持久来源索引见 `../evidence/extension-source-manifest.json`） 的固定快照，content_id `e37074a3d70f4215d62fdb0f8a0cae14138c5477f7f6b2afa1618de6e845ecea`。只读对应 snapshot_path，未执行原仓库 runtime、未修改源码。下列行号引用 source_path，内容来自快照；主 Agent 负责最终 finalize。范围为实施/测试/审查/状态主路径抽查，非全部模块逐行审计；未做性能测量，不把源码长度视为失败证据。

## 结论

可以精简。更合适的方向是 **更少的独立规则实现、更少的下一步分支、更少需要 Agent 记住的机械命令**，同时保留 runtime 对实际证据与状态的确定性约束。把 runtime 全部换成 Prompt，会失去可靠的内容绑定、失败门禁、断点恢复和历史保护。现有 Spec 修的是正确性与指令结构；尚未承诺下面的测试执行内核、下一步统一计算、状态存储归一，因此按现有 Spec 做完不会自动大幅缩小 runtime。

## 发现与方案（按交付影响排序）

### R1：下一步和完成条件分散，规则修正容易只修一处

- `tools/workflow_lib/ticket_implementation.py:356-386` 自行推导 `test/review/self-review/finish/resolve`。
- `tools/workflow_lib/batches.py:237-257` 再推导 `test/review/close/accept`。
- `tools/workflow_lib/topic_service.py:273-355` 再覆盖 Topic 的下一步，汇聚 Ticket 和 batch 结果。
- `tools/workflow_lib/ticket_completion.py:100-102` 完成后直接返回 `impl.next_start_command(repo, topic)`；后者 `ticket_implementation.py:389-397` 没找到 ready Ticket 就返回 `topic complete`。然而 `topic_service.py:433-438` 明确要求所有 batch 已 closed、且内容匹配。因此最后一张 Ticket 完成后，返回的下一步可能尚不可执行。这一点已有 Spec §4.2 覆盖。

**改法：**建立一个只读 `evaluate_work_state`，返回当前作用域、证据状态、未解决发现、允许动作与下一条建议。status、mutation 返回值、finish/close 的门禁复用同一组谓词。无需新增通用工作流 DSL。命令执行仍应在写入前复核当前事实，不能直接信任先前 status。

**收益：**降低 Agent 误走命令、重复查询与规则漂移；改善完成可靠性。成本中等，需要覆盖 Ticket 最后一步、batch 最后一步、needs-user、旧会话恢复。性能改善需实测。

### R2：测试运行机制有三套，执行事实与通过策略混在一起

- `ticket_implementation.py:325-353` 负责逐命令执行、run_id、逐条写入、completed、失败抛错；`300-311` 要求完整声明命令集合、同内容、退出码全零。
- `batches.py:181-196` 再实现一套 subprocess/退出码/内容身份/输出尾部，并增加 unavailable 与 failure identity；`199-216` 比较基线。
- `topic_service.py:469-487` 为 quick 又直接跑 subprocess 和内容身份检查。
- `branch_review.py:66-80` 已经复用 Ticket runner，是正确方向，不必另造第四套。

**改法：**抽出共同“执行并记录事实”的内核：命令集、开始/结束内容、退出码、完整运行标识、日志位置/摘要、中断状态。上层保留不同通过策略：Ticket 定向测试要求当前全通过，batch 对照基线，quick 采用当前完成要求。先统一证据生产，再修比较语义；不能为了合并代码把三种成功语义抹平。

**收益：**同类环境错误、部分执行、崩溃和内容改变只需维护一处，减少漏修。成本中等。仅抽取函数不会使全量测试本身更快；若要省掉重复测试，只可复用绑定完全相同内容、命令和必要环境身份的有效证据，并须验证环境变化边界，不能先承诺缓存收益。

### R3：快照检查可共用，但审查作用域不能一概合并

- `ticket_review.py:287-324` 与 `branch_review.py:117-154` 都检查 manifest hash、冻结文件 hash、当前 content_id、定义/规则，再检查 accepted 回执与 result schema。
- 区别是 Ticket 要核验下游 Ticket (`ticket_review.py:311-312`)，branch 还要约束 HEAD (`branch_review.py:128-129`)。这些不是可删冗余。
- `artifact_review.py:158-178` 的 finalize 还涉及 ownership capability 与生命周期标记，不能拿文件名相似作为删除依据。

**改法：**共用 snapshot integrity 与 accepted receipt 核验函数；Ticket/branch/artifact 保持薄的作用域策略。只在同一次只读评估内复用稳定采样结果；跨 mutation 必须重读。先测量 Git/哈希/冻结耗时再决定是否做内容存储去重。

**收益：**减少维护分叉、降低某条审查路径忘记校验的风险。成本中等，性能收益未测。不要把“完整仓库供审查可读”误改成“只审 diff”。

### R4：旧协议与双份状态可隔离，不能直接删除

- `batches.py:85-90` 原文：`Existing implementation histories keep their legacy protocol.`，有旧 implementation 历史就返回 None，新任务才默认建 batch。这说明旧分支目前有真实兼容职责。
- `topic_service.py:305-324,442-475` 同时承担旧 Ticket/多 Ticket 与新 batch 的路由、全量测试、完成检查。
- `batches.py:19-30` 把 batch 同时保存在 `batches.json` 与 `batches/<id>.json`，读取时单文件覆盖总文件，写入时先逐文件再总文件。这里是可见的多副本协议复杂度，尚未证明发生过状态损坏。
- `migration.py:242-270` 具有预览、显式 apply、备份和失败恢复；不能因“旧”就删。

**改法：**为新记录明确 schema/protocol version，现代主路径只处理当前协议；旧记录由兼容 reader/adapter 解释，必要写入仍走原语义或明确授权迁移。batch 新格式选一个权威状态源，索引只保留 ID/顺序或可重建摘要，避免整份状态双写。旧记录、归档与完成历史不批量改写。

**收益：**未来维护和解释更简单；短期可能多一个 adapter，源码不一定立即更短。成本较高、恢复风险高，应独立变更和真实旧记录回放验证，不与可靠性紧急修复捆绑。

### R5：硬编码的质量代理可删除，机械证据约束应保留

- `review_loop.py:98-107` 按连续修复行重叠、1.5 倍体积直接返回停止原因；`ticket_review.py:361-363` 对任何返回原因执行 stop。已有 Spec §4.6 规定它们降为观察信号。
- `workflow.py:740-748` `artifact-review-snapshot` 与 `artifact-review-open` 参数和 handler 完全相同。可用 argparse alias 合并定义，保留两个公开名字。这里只是低风险维护清理，不能声称显著影响交付。
- `ticket_implementation.py:328-330` “Persist before executing: a crash must invalidate previous success.”、`300-311` 的整组测试完整性、`ticket_completion.py:64-70` 私有模式代码提交回执及元数据失败恢复，都是值得保留的防线。

## 三类处置

| 类型 | 建议 |
|---|---|
| 可先做的小改动 | 按已有 Spec 去掉几何信号的硬停作用，保留诊断；将两个完全同 handler 的 artifact open CLI 定义合并为 alias，保留兼容名字；提取不改变语义的重复快照完整性检查。所谓可先做仍需对应回归验证，不代表已经实施或零风险。 |
| 需隔离兼容后做 | 三套测试执行证据内核、统一下一步与门禁谓词、旧生命周期 adapter、batch 单一权威状态格式。旧 CLI 名称可以先保留为兼容入口，不要求 Agent 继续记住所有别名。 |
| 必须保留 | 内容/Spec/规则身份绑定，实际退出码及运行完整性，未解决阻断与 Spec 冲突门禁，独立审查真实来源，冻结快照和回执，安全路径/ownership，提交失败恢复，完成历史不可改写。 |

## 最小目标结构

第一步只抽公共函数并隔离模块，不引入新状态机/协议、进程或服务。执行 runtime 和源码构建/分发是不同职责，可先在同一 CLI 内分开模块入口。R4 新格式属于后续可选方向，必须先有实际恢复痛点和迁移证据才立项，不计入最小改动。

不建议大重写或设计一个通用流程引擎。内部边界保持四个职责即可：

1. 状态与写入：读取协议、合法状态变化、可恢复写入、历史。
2. 证据：测试执行、内容身份、快照、回执；输出事实。
3. 完成判断：按作用域计算允许动作、阻断与 next_command；不猜模型语义判断。
4. CLI/兼容适配：公开命令和旧记录映射到上述服务；发布安装工具保持独立责任。

语义判断仍由 Agent 作出：需求是否正确、bug 根因、审查发现是否真实、哪些验证足够；runtime 检查声明是否完整、是否属于当前内容、已知阻断是否处理，不能用固定字数/行数/章节数量替代质量。

## 建议补充的验收

- 每种标准状态的 mutation 返回 next_command，要么可执行，要么明确缺用户/环境输入；最后一张 Ticket 不跳过 batch 收口。
- 同一种测试执行异常在 quick/Ticket/batch 保留一致事实，同时各自成功策略不改变；中断/部分执行不能复用旧成功。
- Ticket/branch 共用完整性函数后，篡改快照、变更内容、Spec、规则、下游定义与 HEAD 的原有必要拒绝分别保留。
- 当前新协议和至少一份真实旧活动 Topic 均可只读判断与正确恢复，已完成历史字节保持不变。
- 记录代表性任务的 runtime 命令数、无效下一步次数、runtime 自身耗时、重复测试耗时、所需用户介入。改善维护结构不等于已经证明开发完成率提升。
