# edit-article audit evidence

## Pinned source and file accounting

- Pinned commit: `2ab958093e83e0ec752e6c1c5932da465bf23e0c`
- Canonical source path: `skills/personal/edit-article`
- Local counterpart: `skills/my-edit-article`

| File | Source SHA-256 | Local SHA-256 |
| --- | --- | --- |
| `SKILL.md` | `e10fba546f45357fe0aaa7494b9e186910d4525818d19f9b2ad6f28cc506aa5e` | `b76b886f8a5664ff3ea7ecf2041a62bc0c9f93c5fd6703fe4acaefdc32b6e995` |
| `agents/openai.yaml` | `075b2f1305938182c3aa4aa9b139fff0b7cfacb33b774c2e3e42180794e87394` | `4873c8a1310b0159b404b42de01ba069b899dda4a4d2bd214c6881bc6305d45d` |

## Section/source-local mapping

The audited source sections and their local counterparts are:

| Pinned upstream section | Local counterpart |
| --- | --- |
| `SKILL.md#document-body` | `SKILL.md#document-body` |
| `agents/openai.yaml#interface` | `agents/openai.yaml#interface` |

The source body was compared section-by-section, including examples, ordering, constraints, stop conditions, frontmatter/runtime metadata, and all listed support files. Metadata interface fields are accounted for separately from local policy metadata.

## Delta, allowed adaptation, and conclusion

- Allowed local adaptation: a renamed manual-invocation Skill may retain repository-specific metadata only when it does not alter the upstream method.
- Material delta: The local default-new-draft and approval flow extend the upstream article-editing process; the unbounded policy footer can weaken its section-confirmation gate.
- Conclusion: **adapter-rework-required**.
- Exact follow-up queue: **Plan 2 — `my-edit-article` adapter rework**; this audit does not restore or refactor the Skill.

## Retrieval/application scenario

`tests/fixtures/task_12_application.json` defines `edit-article-application`. It retrieves `SKILL.md#编辑文章`, verifies `每段不超过 240 个字符` within that exact heading, and independently derives `rewrite-with-paragraph-limit` only when the retrieved constraint is present.
