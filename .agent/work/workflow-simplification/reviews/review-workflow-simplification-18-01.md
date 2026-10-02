# 补偿18独立只读审查（第一轮）

结论：findings；2条blocking，未完成验收3/4。未改仓库代码或历史工件。独立子Agent新上下文、继承模型及推理档位，未升级。本轮不使用本仓runtime登记施工，不伪造生命周期回执。

范围：HEAD 77246b4225a48c6d177ff830c7c00ffb07f7666d 至当前未提交四源码改动及新测试/fixture/补偿票据、报告。原Spec revision1及Ticket18四项验收为依据，保持Q4批次/可选审查协议。本轮测试中的independent pass JSON仅为机械测试fixture，与本子Agent独立语义审查分开。

## R18-F1 — blocking：旧v2 Topic在两张Ticket之间仍误导用户执行complete

位置：tools/workflow_lib/topic_service.py:283-288、316-328。

路径：恢复实际旧v2 needs-user记录至两票Topic（feature-02依赖feature-01）→ implement test --ticket feature-01 → resolve --ticket feature-01 --accept --reason ... → topic status。此时tickets确实列出feature-01=complete、feature-02=ready-for-agent，但next_command仍为topic complete。实际执行输出“Ticket 尚未 complete；请运行 implement status”，exit1。feature-02的依赖已满足，可以开始；正确下一步应指向它。没有通过删除新batches文件伪造支持来源，本探针直接使用本次固定的旧v2 fixture，并通过公共CLI完成接受。

原因：新增恢复分支只处理implementing/needs-user，没有为active、无batches且有ready票的已开始Topic计算后继。违反Ticket18验收3“旧版已开始会话…正确下一步”及原M6。属于H-F1恢复缺口残留，非新增Topic范围。

证据：/tmp/compensation18-probes.py；/tmp/compensation18-probes.log中的legacy_between_tickets与following_next。

## R18-F2 — blocking：共用中文renderer假定tickets是对象数组，batch status --human崩溃

位置：tools/workflow_lib/status_text.py:14-15。

路径：合法新批次执行batch status --human，包括有Spec挑战需要用户决定的状态。batches.status的tickets为票据ID字符串数组；renderer新循环无条件访问ticket['ticket']/ticket['status']，TypeError: string indices must be integers, not 'str'，公开命令exit1。原batch状态JSON格式仍是合法且稳定的字符串列表。

违反Ticket18验收3“新批次下一步…中文输出不回归”及验收4测试通过。此项是本次改动引入，所有带非空tickets的新批次中文状态均可达。应保留两类消费者协议，不能只修改fixture绕过。

证据：独立python3 -m unittest discover -s tests -p test_quality_metrics.py -v：6测试、1失败、exit1；test_human_status_reports_challenge_without_internal_state_names真实CLI traceback；/tmp/compensation18-review-quality.log。

## 四项验收及影响面

1. 已验证：新7条补偿CLI测试独立通过（16.248s，exit0）。真实Gitlink mode160000在批次、高风险Ticket、可选整分支材料中保留，普通变更可完成结果提交及close/archive。源码Ticket审查及branch_review（批次/整分支复用）同用baseline_files/current_files seam。
2. 已验证：新Gitlink提交改变后测试/自审身份失效，批次旧审查不能close，dirty子树拒绝test/review。额外将子仓通过git submodule absorbgitdirs转为真正.git文件的常规子模块，独立确认identity/frozen_mode160000及dirty拒绝。额外构造.agent私有Gitlink，未提交metadata修改不改变content_id，且不进入冻结repository。普通文件/链接/可执行位路径保持原分支，完整测试覆盖这些边界。没有联网获取子模块，材料绑定提交指针，不宣称递归审过子模块内部代码。
3. 部分满足：needs-user对象/原因和测试→接受恢复、缺失record诊断、归档只读、文档Topic、新批次JSON下一步独立7测试验证。R18-F1仍缺后继；R18-F2破坏共用中文入口。
4. 未满足：有2条未解决blocking。483个基线已有.agent/work/workflow-simplification文件逐个与git show 77246b4:<path>字节比较，changed=[]，exit0；保留原17票据/Spec/run/review/交付历史，没有历史状态重写。

审查内容绑定调用面：topics.content_id用于Ticket测试、增强自审、三类审查submit/require_pass、batch测试/close以及Topic收尾；gitlink_entry清洁工作树guard现在被统一复用。旧Gitlink缺失身份的记录应重新测试审查，不能直接信任；普通目录未转换成Gitlink的原支持边界没有扩大。

没有其他已证实blocking/advisory；未把纯风格、猜测、测试机械fixture的independent标签或历史工程完成记录当成真实模型独立来源。

## 独立执行与范围冻结摘要

- Python：3.14.4（未在本机跑3.10）。
- 定向补偿：python3 -m unittest discover -s tests -p test_completion_compensation.py -v：7 passed，exit0。
- 定向已有质量/中文输出：python3 -m unittest discover -s tests -p test_quality_metrics.py -v：6 tests、1 failure，exit1。
- 额外探针：PYTHONPATH=. python3 /tmp/compensation18-probes.py：exit0；日志如上。探针第一次未设PYTHONPATH报ModuleNotFoundError，纠正后成功，不当作产品发现。
- 历史逐字核对：483 files changed=[]，exit0。
- 全量python3 -m unittest discover -s tests：结果在文末追加；原始日志/tmp/compensation18-review-tests.log。

首轮读到的SHA256：
- review_snapshot.py：69809a420b4f19296c7442b90b97131199d15161ad1b2fed3bf9bc2f1004dcbb
- status_text.py：fad506c17c4d319ff4fe29d660e59c292ebad7aff17abae0671620ec5c2da46e
- ticket_review.py：f2d8d4952febd434aee4af3dec0017ee4e45161aa112fa2ce47067c07464a1d9
- topic_service.py：50670da56a3640e291e57990a281bcda02d56d8292861a70e3dd83d34fa7dae4
- test_completion_compensation.py：a71ba323434ee3bcc3815ff82aedf3411c8a67b0170f3b1e240d8b8e03ccee05

## 全量最终结果

独立命令 `python3 -m unittest discover -s tests > /tmp/compensation18-review-tests.log 2>&1`：exit1。

```text
----------------------------------------------------------------------
Ran 284 tests in 285.579s

FAILED (failures=1)
/var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/tmpdc_1iy3v/releases/r4
INSTALLED r4
/var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/tmpq9nif50i/repo/releases/r2
/var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/tmpq9nif50i/repo/releases/r3
/var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/tmpq9nif50i/repo/releases/r4
/var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/tmp9od2g1v9/workflow/releases/v1
INSTALLED v1
/var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/tmpr0_ilu6f/workflow/releases/v2
INSTALLED v2
REUSED /var/folders/19/czyfn0rn7yz0gnbrkff0lgd40000gn/T/tmpautpexg9/workflow/releases/v1
INSTALLED v1
```

唯一失败为上述R18-F2真实CLI TypeError；没有以作者的全量结果替代本次独立运行。首轮到此结束，建议修复后另派新上下文差异复审，保留本报告第一轮发现。
