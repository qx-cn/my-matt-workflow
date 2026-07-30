# resolving-merge-conflicts audit evidence

## Pinned source and file accounting

- Pinned commit: `2ab958093e83e0ec752e6c1c5932da465bf23e0c`
- Canonical source path: `skills/engineering/resolving-merge-conflicts`
- Local counterpart: `skills/my-resolving-merge-conflicts`

| File | Source SHA-256 | Local SHA-256 |
| --- | --- | --- |
| `SKILL.md` | `c7c9ba81362a786aac05d2223123bf1bd2f8a99c3243a72882ede9c68bedfb24` | `c17ce4b533dd6f6685b6f599c86a8577333b33c22641a735701e8fe1b308b773` |
| `agents/openai.yaml` | `a1f4f96838f2ed6282eb28abbbf99029cb8fadce552baf53da90a025b8bffddf` | `edcbd709173e6a45d9856a6756dac4333069d11163bf10dbe67a81c3b9469b83` |

## Section/source-local mapping

The audited source sections and their local counterparts are:

| Pinned upstream section | Local counterpart |
| --- | --- |
| `SKILL.md#document-body` | `SKILL.md#document-body` |
| `agents/openai.yaml#interface` | `agents/openai.yaml#interface` |

The source body was compared section-by-section, including examples, ordering, constraints, stop conditions, frontmatter/runtime metadata, and all listed support files. Metadata interface fields are accounted for separately from local policy metadata.

## Delta, allowed adaptation, and conclusion

- Allowed local adaptation: a renamed manual-invocation Skill may retain repository-specific metadata only when it does not alter the upstream method.
- Material delta: The local approval-first and destructive-command safeguards intentionally change the upstream always-resolve/finish-merge behavior and require an explicit adapter boundary.
- Conclusion: **adapter-rework-required**.
- Exact follow-up queue: **Plan 2 — `my-resolving-merge-conflicts` adapter rework**; this audit does not restore or refactor the Skill.

## Retrieval/application scenario

`tests/fixtures/task_12_application.json` defines `resolving-merge-conflicts-application`. It retrieves `SKILL.md#安全解决冲突`, verifies `批准前不得修改冲突文件、暂存、提交或 push` within that exact heading, and independently derives `wait-for-approval` only when the retrieved constraint is present.
