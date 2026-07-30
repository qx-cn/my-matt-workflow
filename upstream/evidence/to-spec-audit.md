# to-spec audit evidence

## Pinned source and file accounting

- Pinned commit: `2ab958093e83e0ec752e6c1c5932da465bf23e0c`
- Canonical source path: `skills/engineering/to-spec`
- Local counterpart: `skills/my-to-spec`

| File | Source SHA-256 | Local SHA-256 |
| --- | --- | --- |
| `SKILL.md` | `267638edd513b5918de626ad5605d261952abb7428cb308869c663ca924e93e7` | `35fbee96bcc6d6b8759aa91759de8f18baf8e8da4bc71d2c9b4023409dd03aeb` |
| `agents/openai.yaml` | `1c5b4d1e3d8e52287ef19cc2742fdbbfae1914ac75d33af3e4c8174f08cc55bb` | `1c5b4d1e3d8e52287ef19cc2742fdbbfae1914ac75d33af3e4c8174f08cc55bb` |

## Section/source-local mapping

The audited source sections and their local counterparts are:

| Pinned upstream section | Local counterpart |
| --- | --- |
| `SKILL.md#Process` | `SKILL.md#过程` |
| `SKILL.md#Problem Statement` | `SKILL.md#问题陈述` |
| `SKILL.md#Solution` | `SKILL.md#解决方案` |
| `SKILL.md#User Stories` | `SKILL.md#用户故事` |
| `SKILL.md#Implementation Decisions` | `SKILL.md#实施决策` |
| `SKILL.md#Testing Decisions` | `SKILL.md#测试决策` |
| `SKILL.md#Out of Scope` | `SKILL.md#不在范围内` |
| `SKILL.md#Further Notes` | `SKILL.md#补充说明` |
| `agents/openai.yaml#interface` | `agents/openai.yaml#interface` |

The source body was compared section-by-section, including examples, ordering, constraints, stop conditions, frontmatter/runtime metadata, and all listed support files. Metadata interface fields are accounted for separately from local policy metadata.

## Delta, allowed adaptation, and conclusion

- Allowed local adaptation: a renamed manual-invocation Skill may retain repository-specific metadata only when it does not alter the upstream method.
- Material delta: The local backend and external-write policy add routing behavior; its policy footer can change the upstream seam-confirmation and publication sequence.
- Conclusion: **adapter-rework-required**.
- Exact follow-up queue: **Plan 2 — `my-to-spec` adapter rework**; this audit does not restore or refactor the Skill.

## Retrieval/application scenario

`tests/fixtures/task_12_application.json` defines `to-spec-application`. It retrieves `SKILL.md#frontmatter.description`, verifies `不重新访谈，只综合已有讨论` within that exact heading, and independently derives `synthesize-without-interview` only when the retrieved constraint is present.

## Task 12 review repair

The scenario now resolves an explicit frontmatter heading; no whole-document fallback is used.
