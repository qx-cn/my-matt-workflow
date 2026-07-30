# research audit evidence

## Pinned source and file accounting

- Pinned commit: `2ab958093e83e0ec752e6c1c5932da465bf23e0c`
- Canonical source path: `skills/engineering/research`
- Local counterpart: `skills/my-research`

| File | Source SHA-256 | Local SHA-256 |
| --- | --- | --- |
| `SKILL.md` | `af378829f015775a3bcd65ff466826722e99359017ae6bae227ca4c9bd14049c` | `946a9c280b76f4c837c804a52b9fecf24886b339d373c70ff7309fb3a76b9c7f` |
| `agents/openai.yaml` | `9b4c470d63221c1f68f22df70b83e2f12401b317babe0d1b7b5f24a974474d0d` | `fd37df5265c46fcb3b199622582b47ba6548d6525f6c0ae7f6453caa873a45dc` |

## Section/source-local mapping

The audited source sections and their local counterparts are:

| Pinned upstream section | Local counterpart |
| --- | --- |
| `SKILL.md#frontmatter.name` | `SKILL.md#My Research` |
| `agents/openai.yaml#interface` | `agents/openai.yaml#interface` |

The source body was compared section-by-section, including examples, ordering, constraints, stop conditions, frontmatter/runtime metadata, and all listed support files. Metadata interface fields are accounted for separately from local policy metadata.

## Delta, allowed adaptation, and conclusion

- Allowed local adaptation: a renamed manual-invocation Skill may retain repository-specific metadata only when it does not alter the upstream method.
- Material delta: The local workflow omits the upstream mandatory background-agent delegation and adds data-handling and writeback constraints.
- Conclusion: **adapter-rework-required**.
- Exact follow-up queue: **Plan 2 — `my-research` adapter rework**; this audit does not restore or refactor the Skill.

## Retrieval/application scenario

`tests/fixtures/task_12_application.json` defines `research-application`. It retrieves `SKILL.md#My Research`, verifies `优先官方文档、标准、源代码和第一方 API` within that exact heading, and independently derives `use-primary-sources` only when the retrieved constraint is present.

## Task 12 review repair

The source name frontmatter explicitly maps to the local title; no whole-document fallback is recorded.
