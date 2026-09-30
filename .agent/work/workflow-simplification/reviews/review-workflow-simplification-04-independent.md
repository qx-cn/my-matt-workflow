Review-Snapshot: 66693412d23c8199867932e963ef35e63705db769a2359f6964bb9e15f230d74
基线：9fdbcda28f39548562186ee6d56af7fe18b79b27
head：dfc3532f96a442de6584770e945bee469f35b181
Review-Scope: change-only

## Code

No findings.

冻结项目重建后的 45 个针对性公共 CLI 测试通过，真实退出码均为 0。覆盖完整差异冻结、字段形状、旧内容拒绝、篡改拒绝、重启恢复、幂等提交与 advisory 展示；没有执行实际发布或外部审查者派发。

## Spec

[P1][high] 允许覆盖全局不变量，并拒绝缺失的覆盖项 — tools/workflow_lib/ticket_review.py:144–145

首轮规则要求每条验收、探针和每个不变量都有判断（冻结 Spec 第 389 行），但目标提取只识别 `I-K1`/`I-T1` 等，漏掉 Spec M7 的 `I-1` 到 `I-11`，包括当前 Ticket 正在兑现的来源真实性 `I-6`。因此遗漏这些项的结果可登记 pass；审查者按规范补 `I-6` 后，submit 反而退出 1 并报告 target 未声明。当前 04#A4 拥有 coverage 校验，此发现没有要求它提前实现下游 Ticket 的业务能力。`PYTHONDONTWRITEBYTECODE=1 python3 /tmp/workflow-independent-04-probe.py` 可复现：遗漏项 submit 退出 0/pass；补 I-6 submit 退出 1；探针整体退出 0。

finish/pass 消费由 05 拥有，停止与 reopen 由 06，整分支由 07，实际宿主派发和统一资源接入由 10；这些未来消费者没有列为本 Ticket 阻断。来源为独立 agent `/root/independent_ticket04`，精确模型不可观察，model=null，模型和思考档位继承。Code/Spec 两遍在同一 reviewer 上下文顺序执行，不声称两遍上下文隔离。

Code：P0=0/P1=0/P2=0，blocker=否；Spec：P0=0/P1=1/P2=0，blocker=是。
