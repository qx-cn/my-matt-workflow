# wayfinder audit evidence

## Pinned source and file accounting

- Pinned commit: `2ab958093e83e0ec752e6c1c5932da465bf23e0c`
- Canonical source path: `skills/engineering/wayfinder`
- Local counterpart: `skills/my-wayfinder`

| File | Source SHA-256 | Local SHA-256 |
| --- | --- | --- |
| `SKILL.md` | `257e40665b28ae959ffdcb97d7a72b074360f4a3d201bd84786505308546e434` | `683c24880e57644e9efa0b2269dc8eb5fbc8c07df562bdaccedf8c98e62ce446` |
| `agents/openai.yaml` | `88bc81a11a6d52ac67aeaa76b8b619e387020d47c5133a4dd4927fd15c4ad073` | `88bc81a11a6d52ac67aeaa76b8b619e387020d47c5133a4dd4927fd15c4ad073` |

## Section/source-local mapping

The audited source sections and their local counterparts are:

| Pinned upstream section | Local counterpart |
| --- | --- |
| `SKILL.md#Plan, don't do` | `SKILL.md#My Wayfinder` |
| `SKILL.md#Refer by name` | `SKILL.md#规划，而不是交付` |
| `SKILL.md#The Map` | `SKILL.md#始终用名称引用` |
| `SKILL.md#The map body` | `SKILL.md#地图` |
| `SKILL.md#Destination` | `SKILL.md#目的地` |
| `SKILL.md#Notes` | `SKILL.md#备注` |
| `SKILL.md#Decisions so far` | `SKILL.md#已作决定` |
| `SKILL.md#Not yet specified` | `SKILL.md#尚未明确` |
| `SKILL.md#Out of scope` | `SKILL.md#范围外` |
| `SKILL.md#Tickets` | `SKILL.md#Tickets` |
| `SKILL.md#Question` | `SKILL.md#问题` |
| `SKILL.md#Ticket Types` | `SKILL.md#Ticket 类型` |
| `SKILL.md#Fog of war` | `SKILL.md#战争迷雾` |
| `SKILL.md#Out of scope` | `SKILL.md#范围外` |
| `SKILL.md#Invocation` | `SKILL.md#调用方式` |
| `SKILL.md#Chart the map` | `SKILL.md#绘制地图` |
| `SKILL.md#Work through the map` | `SKILL.md#沿地图工作` |
| `agents/openai.yaml#interface` | `agents/openai.yaml#interface` |

The source body was compared section-by-section, including examples, ordering, constraints, stop conditions, frontmatter/runtime metadata, and all listed support files. Metadata interface fields are accounted for separately from local policy metadata.

## Delta, allowed adaptation, and conclusion

- Allowed local adaptation: a renamed manual-invocation Skill may retain repository-specific metadata only when it does not alter the upstream method.
- Material delta: The local local-markdown tracker fallback and policy-controlled subagent/transition behavior adapt upstream tracker operations and require bounded preservation of one-ticket and decision-only stops.
- Conclusion: **adapter-rework-required**.
- Exact follow-up queue: **Plan 2 — `my-wayfinder` adapter rework**; this audit does not restore or refactor the Skill.

## Retrieval/application scenario

`tests/fixtures/task_12_application.json` defines `wayfinder-application`. It retrieves `SKILL.md#规划，而不是交付`, verifies `否则只产出决定，不直接交付最终成果` within that exact heading, and independently derives `plan-not-deliver` only when the retrieved constraint is present.
