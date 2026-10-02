# Runtime 与完成语义独立复审

- verdict: pass
- content_id: b1e3b56de8bbec03de4a5aea87b362c9c99dda514a422e0e86905971f27996a0
- reviewer_provenance: independent（由父会话派发的新上下文，只读固定材料）
- 范围：Spec revision 2 §4.1–4.6、§4.9，AC01–11、AC13、AC18–19 及状态恢复。AC12/14–17 留根 Agent 与其他分工；安装算法、全量资源 inventory 不在此结论内。
- 冻结完整性：核对元数据内全部 279 个 snapshot_path 的 SHA-256，全部匹配。所有源码读取均为固定绝对 snapshot_path，exec login:false。未读取活源树、未改源码、未运行安装或完整 suite。
- 方法：已读冻结 my-review-design/SKILL.md 及 resources/review-loop.md。本结论是 Spec 可成立性复审，不声明候选实现已经满足验收。

## 1. 承重断言核验表

| 断言及 Spec 位置 | 核验 | 冻结代码依据与判断 |
|---|---|---|
| 基线不可运行会吞掉当前失败（Spec 35、109–125；AC01） | verified | `/var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/my-matt-review-snapshots/my-matt-review-b1e3b56de8bb-39z2zy_y/251-batches.py:199–216` 在 old.unavailable 分支直接 continue；`/var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/my-matt-review-snapshots/my-matt-review-b1e3b56de8bb-39z2zy_y/251-batches.py:230–234` 仅以 new_failures 门控。候选明确区分当前失败与基线不可比，且禁止接受审查风险绕过失败测试。 |
| 自审登记 findings 不阻止 finish（Spec 36、87–92；AC02） | verified | `/var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/my-matt-review-snapshots/my-matt-review-b1e3b56de8bb-39z2zy_y/251-batches.py:122–147` 允许存 findings，但 require_self 只检查绑定与章节；`/var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/my-matt-review-snapshots/my-matt-review-b1e3b56de8bb-39z2zy_y/272-ticket_completion.py:28–52` 调用它。候选要求未解决 blocking 阻断、challenge 裁决、修复后当前绑定证据解锁。 |
| 最后一张 Ticket 的 mutation 返回可能过早指向 Topic complete（Spec 79；AC03） | verified | `/var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/my-matt-review-snapshots/my-matt-review-b1e3b56de8bb-39z2zy_y/272-ticket_completion.py:95–102` 调用 next_start_command；`/var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/my-matt-review-snapshots/my-matt-review-b1e3b56de8bb-39z2zy_y/273-ticket_implementation.py:389–397` 无 ready Ticket 即建议 topic complete；`/var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/my-matt-review-snapshots/my-matt-review-b1e3b56de8bb-39z2zy_y/277-topic_service.py:431–438` 又拒绝未收口批次。共享下一步规则正对实际调用链。 |
| 几何停止可在 pass 时触发（Spec 37、129–135；AC09） | verified | `/var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/my-matt-review-snapshots/my-matt-review-b1e3b56de8bb-39z2zy_y/266-review_loop.py:88–109` 行重叠与体积阈值未以当前未解决问题为前提；`/var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/my-matt-review-snapshots/my-matt-review-b1e3b56de8bb-39z2zy_y/275-ticket_review.py:337–365` 先登记 pass 再算信号；branch 同样在 `/var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/my-matt-review-snapshots/my-matt-review-b1e3b56de8bb-39z2zy_y/252-branch_review.py:190–208`。候选保留预算与真实语义停止，移除仅几何硬停。 |
| 当前测试路径存在不同成功语义（Spec 160–163；AC19） | verified | Ticket 在 `/var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/my-matt-review-snapshots/my-matt-review-b1e3b56de8bb-39z2zy_y/273-ticket_implementation.py:300–311` 要求完整单次声明全部通过；batch 在 `/var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/my-matt-review-snapshots/my-matt-review-b1e3b56de8bb-39z2zy_y/251-batches.py:199–234` 比较新增失败；quick 在 `/var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/my-matt-review-snapshots/my-matt-review-b1e3b56de8bb-39z2zy_y/277-topic_service.py:469–487` 执行配置测试并拒绝非零。共用证据而保留策略可行，不应统一成单一 passed 布尔。 |
| 中断必须使旧成功失效（Spec 161；AC19） | verified | Ticket `/var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/my-matt-review-snapshots/my-matt-review-b1e3b56de8bb-39z2zy_y/273-ticket_implementation.py:325–330` 先持久化 completed=False；batch `/var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/my-matt-review-snapshots/my-matt-review-b1e3b56de8bb-39z2zy_y/251-batches.py:219–227` 在完整运行返回后才覆盖记录，当前未具有相同保护。候选明确要求适用于共用执行内核，未错误声称现版已全部具有该能力。 |
| 不同审查对象有不同 scope/身份约束（Spec 162；AC19） | verified | Ticket `/var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/my-matt-review-snapshots/my-matt-review-b1e3b56de8bb-39z2zy_y/275-ticket_review.py:287–312` 绑定定义、规则、下游；branch `/var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/my-matt-review-snapshots/my-matt-review-b1e3b56de8bb-39z2zy_y/252-branch_review.py:117–139` 另校验 HEAD；artifact `/var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/my-matt-review-snapshots/my-matt-review-b1e3b56de8bb-39z2zy_y/250-artifact_review.py:158–198` 校验 ownership、生命周期和逐文件内容。候选要求保留差异，未以内容哈希替代 scope。 |
| 存在验收一对一与存储旁路禁令（Spec 96–107；AC06–08） | verified | `/var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/my-matt-review-snapshots/my-matt-review-b1e3b56de8bb-39z2zy_y/069-SKILL.md:10–14`、`/var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/my-matt-review-snapshots/my-matt-review-b1e3b56de8bb-39z2zy_y/040-workflow-delivery.md:24` 限制共用测试；`/var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/my-matt-review-snapshots/my-matt-review-b1e3b56de8bb-39z2zy_y/094-SKILL.md:26` 广泛排除直接查库。候选多对多和风险驱动 seam 保留独立 oracle，而非取消行为证据。 |
| triage 无 Spec 时直达 to-tickets（Spec 76；AC04） | verified | `/var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/my-matt-review-snapshots/my-matt-review-b1e3b56de8bb-39z2zy_y/129-SKILL.md:49–56` 无分支直接交 to-tickets。候选补 current Spec 路由且不重访确认内容，不要求凭 brief 伪造 lineage。 |
| quick/standard 与 legacy 存在现行区别（Spec 54–58、74–79、85、163；AC13/18/19） | verified | `/var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/my-matt-review-snapshots/my-matt-review-b1e3b56de8bb-39z2zy_y/014-assurance-levels.md:5–9` 规定 quick 准入；`/var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/my-matt-review-snapshots/my-matt-review-b1e3b56de8bb-39z2zy_y/016-implementation-session.md:5–11` 描述两种等级及旧协议；`/var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/my-matt-review-snapshots/my-matt-review-b1e3b56de8bb-39z2zy_y/251-batches.py:85–104` 识别已有实施历史并保留 legacy。候选允许兼容读旧记录、重采必要证据且不强制格式迁移。 |

证据边界：现版已有漏洞的判定来自直接源码和真实公开调用链读取；本轮没有重跑此前探针，因此未把“已核验可达机制”写成“本轮已复现执行结果”。原 Spec 的历史频率/模型效果主张本分工不新增背书。

验收覆盖：AC01 当前失败/基线比较，AC02 自审门禁，AC03 下一步，AC04 triage 缺 Spec，AC05 阶段与动作授权，AC06 多对多证据，AC07 存储/实际入口，AC08 抽象与替身，AC09 审查停止，AC10 合法回归不等于新要求，AC11 独立来源，AC13 quick 证据，AC18 活动恢复，AC19 共用内核与 scope 均已检查。AC10 对应现版 review-loop.md:17 的新增“场景”一律返设计风险，Spec 98/133/231 明确仅修正该误判；AC11 要求真实宿主来源而不将声明字段当宿主独立性的充分证明，与现有新上下文派发和 runtime 绑定机制可并存。

## 2. 审查发现

无。blocking=0，advisory=0，无需 fix-in-batch/defer/decline。未找到 revision 2 在本分工内必然导致的可达冲突；已知现版缺陷均有明确候选行为与验收覆盖，不把尚未实现当作 Spec 缺陷。

## 3. 已考察但排除的风险

1. **已 complete Ticket 位于活动 batch，旧自审仍有 blocker，是否只能改历史？** 排除必然死路。`/var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/my-matt-review-snapshots/my-matt-review-b1e3b56de8bb-39z2zy_y/252-branch_review.py:27–37` 的批次审查本就以所有 Ticket complete 为前提；`/var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/my-matt-review-snapshots/my-matt-review-b1e3b56de8bb-39z2zy_y/251-batches.py:260–276` 在 reviewing 批次依据发现提交修复，不要求重开 Ticket。Spec `/var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/my-matt-review-snapshots/my-matt-review-b1e3b56de8bb-39z2zy_y/001-specs-workflow-outcome-optimization-02.md:54–58`、`/var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/my-matt-review-snapshots/my-matt-review-b1e3b56de8bb-39z2zy_y/001-specs-workflow-outcome-optimization-02.md:239` 要求把旧未解发现纳入活动门禁，允许重采与当前证据重评。实现可把发现带入活动批次审查/修复/处置记录，保留原 Ticket 历史；当前协议也允许该形状。Spec 无要求必须回写旧 Ticket；因此不能仅因未细写恢复字段报 blocking。
2. **旧 writer 绕过新门禁**：Spec 57 明确排除混写，要求盘点参与宿主和候选 runtime 切换方案；安装/迁移另授权。该边界已明确，不能要求候选代码控制不受其管理的旧 writer。
3. **未知旧自审缺字段默认无发现，或旧 new_failures=[] 豁免实际失败**：Spec 54–56 及 AC18 明确拒绝，两条恢复要求覆盖现版数据形状；旧记录只读不等于获得候选完成保证。
4. **runtime 下一步产生实施授权**：Spec 66–79 明确区分机械可执行性与用户止点，12/298 明确本轮仅 Spec；不要求 runtime 解析自然语言或增设授权数据库。当前 CLI 始终由 Agent 调用（`/var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/my-matt-review-snapshots/my-matt-review-b1e3b56de8bb-39z2zy_y/248-workflow.py:423–489`），该职责分离成立。
5. **用户 accept 绕过失败测试**：Spec 123 明确禁止，现版 `/var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/my-matt-review-snapshots/my-matt-review-b1e3b56de8bb-39z2zy_y/251-batches.py:283–295` 在 accept 分支前检查 tests_passed，`/var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/my-matt-review-snapshots/my-matt-review-b1e3b56de8bb-39z2zy_y/274-ticket_resolution.py:20–27` 同样先检查当前测试。候选修正 tests_passed 的证据判断后可保留该顺序。
6. **一次相同行修复后 pass 被预算无限豁免**：Spec 131/133、AC09 同时保留四轮/三次修复预算；仅几何信号不再单独阻止 pass，不构成取消审查预算。
7. **共享判断抹掉原有快照安全或 state/mutation 漂移**：Spec 58、160–163 和 AC19 明确写入前重评及保留对象差异，未要求全库先重构；§6 216 要求在同一改点同步抽取并按依赖实施。适合后续公共入口与中断回归验证，不需此阶段先选实现结构。
8. **新版标准吞掉 legacy 协议或强迫历史迁移**：Spec 55–57、163、AC18 明确保留读取与历史、重评活动保证、禁止缺字段补成功；它要求行为恢复而非仅文件可读，但不要求旧 writer 执行新规则。

## 4. 待用户确认的需求语义假设

无。本分工可基于已接受方向和 revision 2 的显式止点完成判断，没有需要新增产品决定的歧义。未来施工测试必须证明实际门禁与恢复行为，不能以本设计复审 pass 代替 AC01–03/09/18/19 的公共入口证据。
