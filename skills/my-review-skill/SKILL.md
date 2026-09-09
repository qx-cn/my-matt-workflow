---
name: my-review-skill
description: 对单个 Skill 做根本性只读审查，或分诊整个 Skill 集合；先判断存在价值与正确归宿，再检查行为和指令设计。
disable-model-invocation: true
---

# 根本性审查 Skill

只读审查 Skill，不修改目标、发布结果或把“优化现有 Skill”预设为答案。合法结论包括保留、局部修复、重构、合并、外置为参考、改由 runtime 执行、退役，以及证据不足。

## 选择模式

- **Portfolio Survey**：用户给出一组或整个目录时，先固定范围并建立 Skill、共享参考、runtime 与调用者的完整 inventory，再找出职责重叠、孤立入口、调用冲突和重复事实来源，输出按影响排序的 Deep Review 队列。此模式不做逐句修改，也不替单个 Skill 下有效性结论。
- **Deep Review**：用户给出单个 Skill 时，审查它及所有会改变其行为的可达材料。一次只深审一个 Skill；需要审查多个时，先 Survey，再依次固定对象审查。

Portfolio Survey 的完成条件：范围内每个 Skill 恰好进入一次 inventory；其声明的调用者、被调用项、组合关系、共享材料和 runtime 边均已解析，或被逐项标记为证据缺口；每个 Deep Review 候选都有一条可定位的影响路径。任何未归档的范围内 Skill 或悬空关系都会阻止 Survey 完成。

## Deep Review

### 1. 固定审查对象

先解析目标宿主以及目标 Skill、`agents/`、可达 references、scripts、assets、调用者、被调用项、runtime、eval 和已知失败反馈，得到完整且按绝对路径稳定排序的文件列表。把列表中的每个文件作为重复的 `--artifact` 参数，交给安装状态记录的 `runtime_entry` 运行 `artifact-review-snapshot`；只读取返回的 `review_unit`、`content_id` 和只读 `snapshot_path`，不得自行拼接哈希或继续从 live path 取证。无法纳入快照的外部状态标记为证据缺口。

完成条件：runtime 返回 `status: ready`；每个已解析的行为依赖都恰好映射到一个 snapshot 条目；后续证据均来自该快照。若文件集合或内容变化，旧结论失效，重新构建快照并重跑审查。

### 2. 重建 Job Contract

从真实请求、调用者和行为证据重建“谁在什么情形调用它、它改变哪个 Agent 决定、产生什么可观察结果”。Skill 自己的 description 只是证据之一，不作为目标正确的证明。

完成条件：能写出“当 X 时，该 Skill 通过改变 Y 决定，使 Z 结果更可靠”；无法写出时形成契约缺失候选，不进入文字审查。

### 3. 存在性 Gate

依次检验：强 Agent 默认能力是否已足够；内容是否只是外部参考；职责是否与另一 Skill 重合或只是其分支；确定性要求是否应由 script、schema 或 runtime 执行；是否确实需要独立调用。选出最合适的归宿，不假定现有 Skill 必须保留。

完成条件：`KEEP | TARGETED_FIX | REDESIGN | MERGE | EXTERNALIZE | REPLACE_WITH_RUNTIME | RETIRE | INCONCLUSIVE` 每种结论都有接受或排除依据。

### 4. 审查因果机制与边界

对承重指令建立“指令 → Agent 判断 → 动作 → 可观察结果 → 用户结果”链；断链是无效操作、仪式步骤或错误补偿的候选。再把模型判断、共享规则、机械操作、硬不变量和产物模板分别归到 Skill、shared reference、script、runtime 和 asset，检查调用方式、职责所有权、事实来源及与宿主规则的冲突。

完成条件：主要机制能解释用户价值，每项承重职责只有一个合理归宿。

### 5. 走查并分级证据

走查正常、边界和失败三种代表性请求，覆盖实际分支、材料读取、权限、暂停和完成条件。区分证据等级：

- **static**：仅由文本、依赖或宿主机制推出；
- **observed**：有真实运行或失败记录；
- **comparative**：相同模型、reasoning、请求、快照和权限下，对比无 Skill、当前 Skill，以及需要时的候选修订版。

只有 comparative 证据才能证明 Skill 相对 baseline 有效或无效；其余等级只陈述可证明的结构问题与风险。需要独立 forward test 时，仅在该能力可用且已获授权时运行，并不给评估者预置怀疑点或期望答案。

完成条件：正常、边界、失败三类请求均至少有一个代表 case；每条实际分支以及材料读取、权限、暂停和完成路径都映射到 case 与证据等级，或被明确列为会限制对应结论的 Evidence Gap。存在未映射路径时，不得进入该路径所影响的 Verdict。

### 6. 最后检查指令设计

仅当存在性 Gate 得出 `KEEP` 或 `TARGETED_FIX` 时，读取并应用[优秀 Skill 设计参考](references/composed/my-writing-great-skills/COMPOSED.md)，检查调用、信息层级、完成条件、主导词、单一事实来源和失效模式。若结论是其他归宿，不输出即将随重构消失的文字建议。

完成条件：所有进入报告的候选都通过下方 Finding Gate，并按根因去重。

## Finding Gate

候选必须同时满足：对调用、正确性、权限、完成度或维护成本有实质影响；有可证明的失败路径或不变量；位于审查对象内；指向可行动的根因；不是猜测、普通偏好、无影响 style nit 或工具已可靠覆盖的事项；作者知道后大概率会改变设计。同一失败链只保留最接近根因的一项，不限制通过 Gate 的真实发现数量。

按干预杠杆归类：`FOUNDATIONAL`（存在性、目标、归宿）、`BEHAVIORAL`（真实分支结果）、`STRUCTURAL`（调用、组合、步骤、信息层级）、`INSTRUCTIONAL`（确实改变行为的文字）。存在 `FOUNDATIONAL` finding 时，抑制由它派生的下游措辞建议。

## 输出

输出前，用相同的稳定排序文件列表、`content_id` 和 `snapshot_dir` 交给 `runtime_entry` 运行 `artifact-review-finalize`。只有返回 `status: match` 才可发送报告；返回 `stale` 时丢弃结论、重建快照并重跑。finalize 同时释放临时快照，不得绕过。

先写 `Review-Unit`、`Target-Host`、`Evidence-Level` 与一个 Verdict。每个 finding 用一个短段落说明根因、失败路径或不变量、证据、影响及最小干预方向。只列会改变 Verdict 的 `Evidence Gaps`，并给出取得最终判断的最小 `Next Validation`。

没有合格发现写 `No findings.`；缺少足以判断有效性的行为证据时用 `INCONCLUSIVE`，不得把静态检查通过写成“Skill 已验证有效”。不复述完整审查过程、逐项通过清单、被拒绝候选或未经请求的改写稿。
