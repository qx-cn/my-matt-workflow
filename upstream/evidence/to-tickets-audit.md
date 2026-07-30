# to-tickets audit evidence

## Pinned source and file accounting

- Pinned commit: `2ab958093e83e0ec752e6c1c5932da465bf23e0c`
- Canonical source path: `skills/engineering/to-tickets`
- Local counterpart: `skills/my-to-tickets`

| File | Source SHA-256 | Local SHA-256 |
| --- | --- | --- |
| `SKILL.md` | `5ecdf1d4df8a360ed39df21a2347f97ba177afd449a577da4f6b6ea8e1ebb808` | `8dc60c65d779479b9cfdbf35c1bee8a083e11a8388bb5f06f432265b1cb1ef84` |
| `agents/openai.yaml` | `21bc6215fffcd7614e9f772bb1760e87cc5fc7dcc707e7d282bc9414267a6090` | `21bc6215fffcd7614e9f772bb1760e87cc5fc7dcc707e7d282bc9414267a6090` |

## Section/source-local mapping

The audited source sections and their local counterparts are:

| Pinned upstream section | Local counterpart |
| --- | --- |
| `SKILL.md#To Tickets` | `SKILL.md#拆分 Ticket` |
| `SKILL.md#Process` | `SKILL.md#过程` |
| `SKILL.md#1. Gather context` | `SKILL.md#1. 收集上下文` |
| `SKILL.md#2. Explore the codebase (optional)` | `SKILL.md#2. 探索代码库（可选）` |
| `SKILL.md#3. Draft vertical slices` | `SKILL.md#3. 起草纵向切片` |
| `SKILL.md#4. Quiz the user` | `SKILL.md#4. 询问用户` |
| `SKILL.md#5. Publish the tickets to the configured tracker` | `SKILL.md#5. 保存或发布已批准 Ticket` |
| `SKILL.md#<NN> — <Ticket title>` | `SKILL.md#<NN> — <Ticket 标题>` |
| `SKILL.md#Parent` | `SKILL.md#父项` |
| `SKILL.md#What to build` | `SKILL.md#要构建什么` |
| `SKILL.md#Acceptance criteria` | `SKILL.md#验收标准` |
| `SKILL.md#Blocked by` | `SKILL.md#被谁阻塞` |
| `agents/openai.yaml#interface` | `agents/openai.yaml#interface` |

The source body was compared section-by-section, including examples, ordering, constraints, stop conditions, frontmatter/runtime metadata, and all listed support files. Metadata interface fields are accounted for separately from local policy metadata.

## Delta, allowed adaptation, and conclusion

- Allowed local adaptation: a renamed manual-invocation Skill may retain repository-specific metadata only when it does not alter the upstream method.
- Material delta: The local backend-specific paths, confirmation gates, and humanizer step replace the upstream tracker contract and must preserve the vertical-slice and blocking-edge method.
- Plan 4 adds a bounded local frontmatter template (`ticket_kind`, `status`, YAML-list `blocked_by`, `claimed_by`, tags and sequence). Eligibility, graph closure, ordering and completion gates live in `tools/workflow_lib/tickets.py`, not copied policy prose.
- Conclusion: **adapter-rework-required**, with local behavior limited to declared shared adapters and the executable ticket model.

## Retrieval/application scenario

`tests/fixtures/task_12_application.json` defines `to-tickets-application`. It retrieves `SKILL.md#3. 起草纵向切片`, verifies `每个切片穿过每一层` within that exact heading, and independently derives `draft-vertical-slices` only when the retrieved constraint is present.
