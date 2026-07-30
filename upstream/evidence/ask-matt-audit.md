# ask-matt audit evidence

## Pinned source and file accounting

- Pinned commit: `2ab958093e83e0ec752e6c1c5932da465bf23e0c`
- Canonical source path: `skills/engineering/ask-matt`
- Local counterpart: `skills/my-ask-matt`

| File | Source SHA-256 | Local SHA-256 |
| --- | --- | --- |
| `SKILL.md` | `b1a134ada29cbfded84bc9a7f93356ab7a3d7f800edf1f541a2a964118ad45a7` | `50d23a5df9783adeb7c544b1fcadf8978f56e5de0a53340e1f96ef4ca4b12f03` |
| `agents/openai.yaml` | `bdffbc5a0a99ed1b6ef3253d251d755fd18162b9845972e380007f844b09b05c` | `bdffbc5a0a99ed1b6ef3253d251d755fd18162b9845972e380007f844b09b05c` |

## Section/source-local mapping

The audited source sections and their local counterparts are:

| Pinned upstream section | Local counterpart |
| --- | --- |
| `SKILL.md#Ask Matt` | `SKILL.md#询问 Matt` |
| `SKILL.md#The main flow: idea → ship` | `SKILL.md#主流程：想法 → 交付` |
| `SKILL.md#Context hygiene` | `SKILL.md#上下文卫生` |
| `SKILL.md#On-ramps` | `SKILL.md#入口` |
| `SKILL.md#Codebase health` | `SKILL.md#代码库健康` |
| `SKILL.md#Vocabulary underneath` | `SKILL.md#下层词汇` |
| `SKILL.md#Crossing sessions` | `SKILL.md#跨会话` |
| `SKILL.md#Standalone` | `SKILL.md#独立使用` |
| `SKILL.md#Precondition` | `SKILL.md#前置条件` |
| `agents/openai.yaml#interface` | `agents/openai.yaml#interface` |

The source body was compared section-by-section, including examples, ordering, constraints, stop conditions, frontmatter/runtime metadata, and all listed support files. Metadata interface fields are accounted for separately from local policy metadata.

## Delta, allowed adaptation, and conclusion

- Allowed local adaptation: a renamed manual-invocation Skill may retain repository-specific metadata only when it does not alter the upstream method.
- Material delta: The local router adds workflow-specific entrances and composition policy dispatch; its policy footer can weaken the upstream uninterrupted-context and explicit-stop guidance.
- Conclusion: **adapter-rework-required**.
- Exact follow-up queue: **Plan 2 — `my-ask-matt` adapter rework**; this audit does not restore or refactor the Skill.

## Retrieval/application scenario

`tests/fixtures/task_12_application.json` defines `ask-matt-application`. It retrieves `SKILL.md#上下文卫生`, verifies `若会话在 `/my-to-tickets` 前接近该限制` within that exact heading, and independently derives `handoff-before-degradation` only when the retrieved constraint is present.
