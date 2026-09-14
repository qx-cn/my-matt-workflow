# Code Review Signal Smoke

- Date: 2026-09-07
- Execution: independent default-model agents; no model override
- Exact model id: unavailable
- Model override: none
- Source release under final targeted check: `agent-aware-review-v1`

## change-only (`code-review-signal-v2`)

Status: pass for the checked rubric.

- Used `content_id` `4e89266fb3335c4628e6c24c73ec36859ea201b619a0c051891f50b72986f6ab` and default `change-only`.
- Found the seeded empty-cart Code regression.
- Found the seeded negative-quantity Spec omission.
- Did not report the pre-existing `legacy_discount`, intentional SAVE10 behavior, style noise, or duplicate test-gap findings.
- Returned two compact findings under separate Code and Spec headings.

Raw final report:

```text
Review-Snapshot: 4e89266fb3335c4628e6c24c73ec36859ea201b619a0c051891f50b72986f6ab
基线: HEAD (f3ef65ae361ca6bb0c0931cafa4f919dbffdd92f)
head: f3ef65ae361ca6bb0c0931cafa4f919dbffdd92f
Review-Scope: change-only

## Code

[P1][high] 未使用的均价计算导致空购物车崩溃 — pricing.py:15
`average_price` 不参与返回值，却无条件执行除法；当 `items=[]` 时，原实现返回 `Decimal("0")`，当前实现会抛出 `decimal.InvalidOperation`。这破坏了既有输入行为并阻断正常结算。删除该计算，并用空列表调用 `checkout_total` 验证返回零。

## Spec

[P1][high] 负数数量未按规范拒绝 — pricing.py:12
`spec.md:4` 要求负数数量抛出 `ValueError`，但当前求和逻辑会直接接受负数并返回负总价，例如单价 `20`、数量 `-1` 返回 `-20`。应在计算前校验每项数量，并增加断言 `ValueError` 的测试。

汇总：Code P0/P1/P2 = 0/1/0；Spec P0/P1/P2 = 0/1/0；blocker：是；Spec 状态：已评估。
```

## without-spec (`code-review-signal-v1`)

Status: pass for the checked rubric. The v2 change only strengthens Spec evidence mapping, so this run was not repeated to avoid unnecessary model cost.

- Used `content_id` `a9b80a978dfc487be9185b784ed360b74561e1bac10c6c34742162b60678e51a`.
- Found the seeded Code regression and marked Spec not evaluated.
- Did not invent a requirement or Spec pass conclusion.

Raw final report:

```text
Review-Snapshot: a9b80a978dfc487be9185b784ed360b74561e1bac10c6c34742162b60678e51a
Baseline: c7eb30b86cf467d6aa42cb7fcdb979fde7bbd5d4
Head: c7eb30b86cf467d6aa42cb7fcdb979fde7bbd5d4
Review-Scope: change-only

## Code

[P1][high] 移除无条件执行且未使用的平均价计算 — pricing.py:9
新增除法使原本有效的空购物车触发 `decimal.InvalidOperation`，也使此前支持的生成器输入在求和后因 `len()` 触发 `TypeError`，但计算结果 `average_price` 从未使用。删除该计算，并至少验证 `checkout_total([]) == Decimal("0")` 以及生成器输入仍能返回总价。

## Spec

未评估：未找到可用 Spec

Summary: Code P0=0, P1=1, P2=0; Spec P0=0, P1=0, P2=0; blocker=yes; Spec status=未评估（未找到可用 Spec）
```

## touched-context (`code-review-signal-v1`)

Status: pass for the checked rubric, with the limitation that this exact case was not repeated after the v2 Spec-mapping-only edit.

- Used `content_id` `d223707dc835d92045f4e4f2715e16b3ab4179b8b17a783c26292166c0acd1e8` and `touched-context`.
- Reported the directly related pre-existing negative-reservation defect and labelled it “既有/非本次引入”.
- Suppressed the unrelated pre-existing `unrelated_label` issue and did not invent an atomicity requirement.

Raw final report:

```text
Review-Snapshot: d223707dc835d92045f4e4f2715e16b3ab4179b8b17a783c26292166c0acd1e8
基线: cbb136f3f8dfc89bdd69193f43869e733bac0697
head: cbb136f3f8dfc89bdd69193f43869e733bac0697
Review-Scope: touched-context

## Code

[P1][high] 拒绝负数预留量，避免库存反向增加（既有/非本次引入） — inventory.py:7
`reserve_many` 会把每项 `quantity` 原样传给直接调用路径中的 `reserve`。当数量为负数时，现有检查不会拒绝请求，随后 `stock[key] -= quantity` 反而增加库存；例如库存 5、数量 -2 会返回 `[True]` 并把库存改为 7，破坏库存一致性。应在变更库存前拒绝负数，并用批量负数请求验证返回失败且库存不变。

## Spec

No findings.

汇总：Code P0/P1/P2 = 0/1/0；Spec P0/P1/P2 = 0/0/0；blocker = 1；Spec 状态：已评估。
```

## Evidence boundary

These runs are useful default-Agent behavior observations, not a real business-project smoke. Static/unit checks and this synthetic fixture cannot guarantee behavior on every repository.
