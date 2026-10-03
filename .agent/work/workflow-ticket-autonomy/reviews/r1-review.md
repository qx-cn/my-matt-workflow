# 冻结独立代码审查

结论：findings。发现 1 项 P1 阻断、1 项 P2 建议（fix-in-batch）。

- content_id：`9da78010ed28ab8147ce66ddebf02cc4ac39d6cca818edf953bd730ee3383caf`
- unit_id：`f3465fbe5bf0447aad971301448e5c8d`
- 正式基线：`24e4f7081509660b37771b19b1b89d796059e93c`；范围：touched-context，25 个变更路径。
- 仅消费指定固定根的 manifest、批准 Spec、Ticket 与 base/current。审查前后所有 manifest 声明文件哈希一致。未读主仓库、记忆或实施上下文；未另选基线/重建审查快照，未派 Agent、修改冻结源、运行时提交、安装或开复审轮。

## 发现

### F1 · P1 · spec · 实际生成简报保留旧技术停止指令

位置：`current/tools/workflow_lib/ticket_implementation.py:267-268`。

`my-implement` 要求先读取运行时执行简报；`implement start` 实际生成“事实冲突按 spec-challenge 停止，不任选一边实现。”。当 Agent 发现可直接核实的技术事实错误时，该简报要求停止；AC-01 和更新后的 Skill 则要求按普通 spec/correctness 修复，只有改变用户约定才提出产品挑战。直接生成者未同步新的共同规则。

这是正式 base 已有文案在本次共同行为合同变更后的相关漏同步，并非新插入该句。独立仓库 `briefing` 经冻结 CLI 生成的完整简报位于 `/tmp/workflow-ticket-autonomy-audit-probes/briefing-emitted.txt`；命令与退出码在 `probe-log.json`。该证据证明当前 Agent 输入合同冲突，不声称已测量长期 Agent 行为。

建议：fix-in-batch。同步简报模板，并验证实际 CLI 输出与共同授权规则一致。

### F2 · P2 · correctness · 整分支刷新的下一步未更新批次测试资格

位置：`current/tools/workflow_lib/technical_refresh.py:308-311`。

多 Ticket 批次模式下，整分支技术刷新使相关批次的旧测试 epoch 失效，却固定返回 `workflow.py topic test --topic audit`。该命令只写 topic-tests.json；整分支审查在批次启用时读取 batch-tests-01.json。因此执行返回命令成功后，下一次 topic review 实际 exit 1：`test: 审查需要当前全量测试相对基线无新增失败记录`。改跑 batch test 后可开第 2 轮。

独立复现：`/tmp/workflow-ticket-autonomy-audit-probes/probe-more-log.json` 的 `branch-next` 仓库。建议：fix-in-batch。启用批次时返回 batch test，旧无批次协议返回 topic test，回归测试应执行返回步骤后再开启审查。

## 验收与其他视角

| 验收 | 本轮结果 | 主要依据 |
| --- | --- | --- |
| AC-01 | F1 | 全部共同规则与实际生成简报；真实路径规则不以旧scope为门槛 |
| AC-02 | 无其他发现 | 追加技术记录、旧定义/原始审查/自审历史保留；完成历史合同明确 |
| AC-03 | 无其他发现 | 三个公共CLI入口、必填材料、身份/状态验证及显式reopen区别 |
| AC-04 | 无其他发现 | 测试/自审/审查资格失效；已开轮次/series/基线保留；四轮后拒绝新轮 |
| AC-05 | F2 | 三入口混合挑战仅处置技术项；inconclusive仍停止；下一步错误复现 |
| AC-06 | 无其他发现 | 3轮旧历史→第4轮；重复刷新字节不变；错误身份和缺证据拒绝 |
| AC-07 | 完整交付未验证 | 本轮核实17项技术刷新回归与资源闭包；外部全量/发布/安装/独立场景不在输入 |

impact 已核实实际调用方：CLI dispatch、Ticket状态/测试/完成/审查、批次状态/修复/关闭、整分支状态/测试/审查、Topic路由，以及资源consumer闭包/runtime复制。发现已覆盖直接调用链；没有额外合格的 spec-challenge 或 maintainability 发现。

## 执行证据与限制

- 自建公共 Git 仓库的全部命令、stdout/stderr/退出码保存于 `probe-log.json`、`probe-more-log.json`、`stop-log.json`；运行入口始终是冻结 `current/tools/workflow.py`。
- 三个入口保留未点名产品挑战、拒绝错误身份；inconclusive 与技术finding同时存在时刷新不解除停止。legacy三轮恢复下一轮为四且拒五，batch/branch四轮刷新后仍停止。
- `python3 -B -m unittest discover -s tests -p test_technical_refresh.py`：17/17，82.536s。
- 资源测试21项：19通过，2个PermissionError来自copytree继承冻结只读权限、随后测试试图改写自己的负向夹具。完整stage同样碰到只读复制目标；不将它们认定为实现缺陷，也不报告完整打包执行已通过。
- 独立 `resource_probe.py` 对冻结源码执行 validate_skills，并按有效consumer闭包复制七项改动共享规则；所有consumer目标字节与固定源相同，报告在 `resource-bundles/report.json`。完整宿主投影/安装未执行。
- notes非空、文件存在、结构校验不证明技术/产品语义判断正确。事务中途磁盘异常与并发竞态未动态注入；已审阅准备后复核、原文比较及回滚路径。实际Agent场景演练、完整发布、宿主状态和长期效果不在本轮证据范围。

本次为 standalone frozen audit，没有运行时复审计数、提交、自动修复或续开权限。结构化结果保存后停止。
