# 归档冻结审查材料补偿工作：独立差异复审

结论：**pass，无合格 findings，3/3目标覆盖**。本结论仅适用于指定冻结补偿差异与直接受影响的归档校验消费者；不重新审查原自主刷新核心，不改写原已收口结果。

- unit_id：c450f6de00d74bc19efb815061747616
- content_id：02275e47907c77d07b5fd06eee719a49924824a7c4675c983985413f9660b7d6
- baseline：56adc4e2de4acd35d501eaf6733cb2bd9f272be2
- manifest：`/tmp/workflow-ticket-autonomy-compensation-review/manifest.json`
- manifest SHA256：69933327d9386aa26fe067cb37b1846582e190f062a2f01c131597b75562140f
- 新补偿审查骨架 round=1；不是原已收口series重开。
- reviewer：independent；真实来源 `native-collaboration:/root/ticket_autonomy_batch_review`。
- model：GPT-6 (inherited session; exact provider model ID unavailable)。逐字使用manifest声明；精确provider型号不可核实，没有编造Paseo UUID或升级能力。

## 隔离与完整性

仅消费本次manifest、骨架、compensation.md及base_repository/current repository精确声明文件。两个仓库各651项SHA256与size全部核对，最终再次核对原冻结文件及两个临时重建目录的字节。实际差异恰为 `tools/workflow_lib/validator.py` 和 `tests/test_validator_markdown_scope.py`；366个 `.agent/archive/` 文件在正式基线与当前输入中逐文件哈希一致，根配置也来自本次冻结文件。未读取主仓库mutable文件、memory、其他Agent报告或安装的Skills。

临时完整重建目录：

- baseline：`/tmp/autonomy-compensation-base_repository-tvj3ttdo`
- current：`/tmp/autonomy-compensation-repository-a5khjce2`

负向探针在独立临时副本修改夹具，不修改原冻结文件或上述验证源码。未操作原结果、提交runtime、修复实现、创建后续审查单元或派发Agent。

## 五个视角及消费者

- **correctness：无发现。** `_archived_review_inputs` 从归档的implementation/batch/branch记录读取reviews及past_reviews，核对unit/content/round；活动manifest核对原登记sha256，历史材料逐blob核对sha256/size。只把原manifest目录下直接声明的文件映射至归档目录；目录解析、symlink及逃逸路径拒绝。未登记blob和普通Markdown不能取得链接豁免。
- **impact：无发现。** 核实 `_markdown_references → validate_markdown_references → validate_repository`，再核实doctor/diagnose_repository、CLI validate以及release/preflight_build消费者。未改变源Skill、资源、普通配置与文档的检查，也未修改archive搬迁或历史写入逻辑。此次变更只纠正序列化输入blob的原始链接上下文与归档后的校验语义。
- **spec：无发现。** 真实归档fixture证明正式baseline的缺链接错误可达，current恢复source valid；精确登记与完整性要求及普通源边界由相关回归和独立负向探针覆盖。
- **spec-challenge：无发现。** 修复保留原完成历史与验收，不需改变用户已确认行为、约束或风险承诺。
- **maintainability：无发现。** 归档输入识别集中在一个validator辅助函数，现有Markdown扫描复用判定；测试涵盖新豁免及原严格边界。未发现本差异造成的实质维护缺陷。

## 覆盖

| target | 结论 |
| --- | --- |
| archive-runtime-data | ok：正式baseline真实归档doctor源码层invalid→current valid；登记、身份、活动manifest哈希及blob字节校验有效。 |
| strict-source-boundary | ok：8项回归及9组独立负向探针通过；普通archive、近似目录、配置和未登记文档仍严格，篡改/错身份/越界/symlink拒绝；原历史字节保持。 |
| archived-source | ok：全部声明文件重建；核实直接调用消费者，实际归档失败链得到修复；没有泛化为release/host通过。 |

## 真实执行证据

1. 当前重建执行 `python3 -m unittest discover -s tests -p test_validator_markdown_scope.py -v`，**退出0，8 tests，OK**。包括活动manifest/输入篡改、历史材料、错误身份/越界/未知Markdown/symlink/畸形record与普通源链接检查。
2. 正式baseline和current分别通过doctor公共诊断入口 `diagnose_repository(Path('.'), {})` 验证实际冻结归档fixture，两个观察断言脚本均退出0：
   - baseline.source.status=`invalid`；reason为 `.agent/archive/workflow-ticket-autonomy/reviews/branch-45dc6631d3204a438c066bf31ebb8531/review-loop-rules.md: Markdown reference missing: user-intervention.md`。
   - current.source=`{status: valid, skills: 32, scripts: 2}`。
   - `agent_homes={}` 明确不读取任何真实宿主；两者current_release均not-applicable/current-pointer-missing，不能解释成实际发布状态。
3. `python3 /tmp/autonomy-compensation-probes.py`，**退出0，9组独立负向探针通过**。使用真实冻结归档的已登记批次记录及manifest，每个场景复制完整current fixture；不依赖实施者声明或自造runtime review身份。
   - 已登记 `review-loop-rules.md` 改为无链接篡改内容：拒绝，snapshot byte integrity mismatch。
   - 活动manifest追加空白：拒绝，recorded manifest hash mismatch。
   - 原review记录round错位：拒绝，recorded review identity mismatch。
   - blob换为symlink：拒绝，unsafe or missing snapshot blob。
   - snapshot_path跨出原manifest目录：拒绝，archived review integrity/path not in subpath。
   - manifest旁未登记ordinary.md坏链接：拒绝，Markdown reference missing。
   - 普通archive Topic文档坏链接：拒绝，Markdown reference missing。
   - `.agent/archive-near/`近似目录坏链接：拒绝，Markdown reference missing。
   - 原冻结根 `.agent/matt-workflow.md` 追加坏链接：拒绝，Markdown reference missing。

上述篡改均在临时副本中进行。最后逐文件复核两份完整重建源码与原冻结输入无漂移；原已收口Topic字节未写入。

## 适用与未验证范围

本轮只验证两个文件的补偿差异、归档blob身份/字节/路径边界与直接消费者。未启动全量unittest、build或规范发布门禁，未验证canonical release/current、真实Codex/Claude安装或长期行为；这些状态不由本报告推定。精确provider型号仍不可核实。未发现影响本补偿差异判断的剩余实质证据缺口。
