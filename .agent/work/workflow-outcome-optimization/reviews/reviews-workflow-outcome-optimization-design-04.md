# Spec revision 2 用户请求复审

结论：**pass；无阻断、待修复建议、Spec 挑战或待用户决定的语义问题。** 本轮不修改 Spec，revision 2 继续是唯一 current。此结论表示设计在审查范围内成立，不代表候选 workflow 已实现、验收或提高七项能力。

用户明确请求“对 spec 进行复审”，沿此前要求使用三组并行新上下文审查。它们不读取作者总结或旧审查结论，独立核对冻结 Spec 与源码；主 Agent 汇总并补查跨组影响。三个子审合为本次一轮，不按子 Agent 数新增轮次。不更改模型或思考档位；宿主未公开具体模型标识字符串，记录继承而不编造型号。

- 审查单元：`b1e3b56de8bbec03de4a5aea87b362c9c99dda514a422e0e86905971f27996a0`，279 个冻结工件；finalize 为 match，临时 snapshot 已释放。
- 被审 Spec SHA-256：`efd7c71b787657623b1d5d58a817330cdbf32b5f532b5d55192db2c3cbe72d13`，审前审后一致。
- 方法：[my-review-design](../../../../skills/my-review-design/SKILL.md) 的承重断言、影响与兼容、内部成立和需求语义四类检查。
- 本轮只读源码与相关测试定义，没有执行全套测试、旧探针、性能测量、模型对照、发布或安装。

## 1. 承重断言核验

| 断言/设计要求 | 状态 | 核验依据 |
|---|---|---|
| 当前失败与基线不可比必须分开，自审未解 blocker 必须约束完成 | verified | `batches.py:122–147,199–234`、`ticket_completion.py:28–52` 确认现版缺口；Spec §4.3/4.5 与 AC01–02 准确承接 |
| 下一步应可执行但不能产生用户授权 | verified | `ticket_implementation.py:389–397` 对比 `topic_service.py:431–438`；Spec §4.1/4.2/4.9、AC03/05/19 分离机械事实与授权 |
| 完成 Ticket 的历史保留与活动批次修复可兼容 | verified | `branch_review.py:27–37`、`batches.py:260–276` 已有全部 Ticket complete 后的批次审查/修复入口；Spec §3/AC18 要求旧未解发现参与当前门禁，无需强制重写旧 Ticket |
| 共用证据内核不能抹平入口策略、scope 或中断状态 | verified | Ticket、batch、quick 与 artifact/branch 核验职责确有区别；Spec §4.9/AC19 明确保留，详见 runtime 子报告 |
| 安装重复检查可以去重，必要完整性和恢复不能删 | verified | `workflow.py:365–392`、`release.py:747–807`、`installer.py:706,909–923`；Spec §4.10/AC20–22 保留稳定快照、锁内内容身份、旧新包分别验证、staging 与实际目标校验 |
| 新投影清单可替代为验证而复制，但必须保持字节等价 | verified | `projection.py:13–42`、`installer.py:453–470`；AC22 与既有篡改/中断/引用锁测试 seam 可衔接，未把现成测试当候选已通过 |
| 需求、写作与排障的改动针对真实规则冲突 | verified | requirement-analysis 已支持简单直过；test-report:76 过宽静态禁令、diagnosing-bugs:62/75 冲突和固定门槛存在；Spec §4.7–4.8 保留证据强度和原场景边界 |
| 加载与表达不应把分发文件当已加载，恢复不依赖永不中断 | verified | resources.py 的消费者复制与读取不同；context-hygiene:3/7、ask-matt:22–28、visual-communication:3–13 均由 §5、AC12/14/15 明确承接 |
| 七项效果可分别评价，不能以防错、模板或命令数代替交付 | verified | §8/AC26 已定义全部任务分母、用户阶段、固定预算、首次/最终正确、隐藏验收、读者任务与越权失败 |
| 候选真实成功率、能力收益和提速幅度 | unknown，已披露 | 没有候选实现和真实对照，本次不作效果通过结论；Spec §8/9 已将其列为后续证据 |

验收覆盖：runtime 子审覆盖 AC01–11、13、18–19；安装子审覆盖 AC20–22；能力子审覆盖 AC23–26 及相关 AC05/12/14/15/17。根审查补核 AC12/14/15 的调用/加载/恢复与表达，AC16 的完整可替换交付和发布授权、AC17 的证据边界；26 项均已纳入，无未分配项。这是合同覆盖，不是26项实现验收已经通过。

## 2. 审查发现

**No findings.** 没有足以要求修改的实质矛盾、不可达验收或未决产品假设，故不为产生改动新建 revision 3。

安装子审有一处可选措辞建议：§4.10 与 AC21 的“仍可运行一轮 check”以后可写为“首版保留一轮完整 check”。同段已经明确禁止跨调用复用，并将跳过检查留到未来单独扩展 receipt，当前合同未允许零 check。因此不列 design finding，本轮保留正文。

## 3. 已考察但排除的风险

- **升级恢复卡在完成历史**：活动 batch 已有修复入口，旧发现参与门禁不必重写 Ticket 历史；旧 writer 混写明确不获新版保证。
- **共享校验漏掉并发漂移或篡改**：Spec 明确禁止锁外布尔值进锁内即信任，旧包、新包、staging 与实际安装内容各有独立验证对象。
- **无变化优化暗中删除完整检查**：首版禁止跨调用测试凭据复用；无变化免临时打包/重写不等于免测试，已有包 install 不跑源码 suite 的职责保持。
- **灵活排障变成猜测修复**：观察、假设、支持证据与未验证原场景已分开；必要证据缺失不能计成功。
- **通过少做、越权或隐藏返工提高指标**：全部分配任务、授权阶段、固定预算和首验/最终/错误完成分别记录；未知外部动作先核对，越权不算成功。
- **精简演变为新平台工程**：Spec 明确排除跨进程缓存、自动测试选择平台、状态格式迁移和通用流程引擎，内部实现选择未被过度锁死。

更详细的调用链与排除依据见三个子报告。

## 4. 待用户确认的需求语义假设

无。本轮没有需要新授权或产品裁决的 Spec 问题。下一阶段仍需用户给出实施指令；本轮复审不自动拆 Ticket、开工或安装。

## 分工与收据

- [Runtime 与完成语义](reviews-workflow-outcome-optimization-design-04-runtime.md)
- [安装升级与恢复](reviews-workflow-outcome-optimization-design-04-install.md)
- [七项能力与需求覆盖](reviews-workflow-outcome-optimization-design-04-capabilities.md)
- [本轮验证收据](../evidence/r2-rereview-verification.json)
- [当前 Spec](../specs/specs-workflow-outcome-optimization-02.md)
