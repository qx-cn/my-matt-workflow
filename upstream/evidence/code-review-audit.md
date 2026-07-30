# code-review audit evidence

## Pinned source and file accounting

- Pinned commit: `2ab958093e83e0ec752e6c1c5932da465bf23e0c`
- Canonical source path: `skills/engineering/code-review`
- Local counterpart: `skills/my-code-review`

| File | Source SHA-256 | Local SHA-256 |
| --- | --- | --- |
| `SKILL.md` | `6a65cc61114f96db07ec41e3920e67c9c5bf70dd6e0901eb9460ebcb2bdc209f` | `3514c7d81f5da0d5f7e41bd9fd9205aac9e0b529ea982d93be9389c5bdacbce0` |
| `agents/openai.yaml` | `8229ca854e11dc8e6aef2131ee03f31fb1561cf905fab9ccc325180cf3331352` | `527fc83e8ad11a49feddf81b5e464c05b4f951c74171f04bfc6491fd09d25799` |

## Section/source-local mapping

The audited source sections and their local counterparts are:

| Pinned upstream section | Local counterpart |
| --- | --- |
| `SKILL.md#frontmatter.name` | `SKILL.md#代码审查` |
| `SKILL.md#Process` | `SKILL.md#过程` |
| `SKILL.md#1. Pin the fixed point` | `SKILL.md#1. 固定基线` |
| `SKILL.md#2. Identify the spec source` | `SKILL.md#2. 定位 Spec 来源` |
| `SKILL.md#3. Identify the standards sources` | `SKILL.md#3. 定位 Standards 来源` |
| `SKILL.md#4. Spawn both sub-agents in parallel` | `SKILL.md#4. 分别审查` |
| `SKILL.md#5. Aggregate` | `SKILL.md#5. 汇总` |
| `SKILL.md#Why two axes` | `SKILL.md#为什么是两轴` |
| `agents/openai.yaml#interface` | `agents/openai.yaml#interface` |

The source body was compared section-by-section, including examples, ordering, constraints, stop conditions, frontmatter/runtime metadata, and all listed support files. Metadata interface fields are accounted for separately from local policy metadata.

## Delta, allowed adaptation, and conclusion

- Allowed local adaptation: a renamed manual-invocation Skill may retain repository-specific metadata only when it does not alter the upstream method.
- Material delta: The local fallback to an implementation-start record and policy-controlled parallelism can bypass the upstream requirement to ask for an omitted fixed point and to run both independent review axes.
- Conclusion: **adapter-rework-required**.
- Exact follow-up queue: **Plan 2 — `my-code-review` adapter rework**; this audit does not restore or refactor the Skill.

## Retrieval/application scenario

`tests/fixtures/task_12_application.json` defines `code-review-application`. It retrieves `SKILL.md#1. 固定基线`, verifies `继续前确认固定点可解析` within that exact heading, and independently derives `validate-fixed-point` only when the retrieved constraint is present.

## Task 12 review repair

The explicit `frontmatter.name` → local title mapping prevents the numbered process sections from shifting. Both pinned-upstream and local headings resolve for every recorded mapping.
