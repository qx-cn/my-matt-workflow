# handoff audit evidence

## Pinned source and file accounting

- Pinned commit: `2ab958093e83e0ec752e6c1c5932da465bf23e0c`
- Canonical source path: `skills/productivity/handoff`
- Local counterpart: `skills/my-handoff`

| File | Source SHA-256 | Local SHA-256 |
| --- | --- | --- |
| `SKILL.md` | `57c9f1f392d7352cdc85b1e39ca49eddc70ce1dc278bd9653fb4f23dfc2560fc` | `90f5867be75fa09e403c77ef574dedef50aaf7cb3aceef9b2a63f53f9ea9b328` |
| `agents/openai.yaml` | `5c479fd562c691851690e8b18c8501045bef0943c10743d636b2fae26add1d28` | `5c479fd562c691851690e8b18c8501045bef0943c10743d636b2fae26add1d28` |

## Section/source-local mapping

The audited source sections and their local counterparts are:

| Pinned upstream section | Local counterpart |
| --- | --- |
| `SKILL.md#document-body` | `SKILL.md#document-body` |
| `agents/openai.yaml#interface` | `agents/openai.yaml#interface` |

The source body was compared section-by-section, including examples, ordering, constraints, stop conditions, frontmatter/runtime metadata, and all listed support files. Metadata interface fields are accounted for separately from local policy metadata.

## Delta, allowed adaptation, and conclusion

- Allowed local adaptation: a renamed manual-invocation Skill may retain repository-specific metadata only when it does not alter the upstream method.
- Material delta: The local project-directory ownership and filename convention replace the upstream OS-temporary-directory destination and add policy-controlled behavior.
- Conclusion: **adapter-rework-required**.
- Exact follow-up queue: **Plan 2 — `my-handoff` adapter rework**; this audit does not restore or refactor the Skill.

## Retrieval/application scenario

`tests/fixtures/task_12_application.json` defines `handoff-application`. It retrieves `SKILL.md#My Handoff`, verifies `已有产物只引用，不复制正文` within that exact heading, and independently derives `reference-existing-artifacts` only when the retrieved constraint is present.
