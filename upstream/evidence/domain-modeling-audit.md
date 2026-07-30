# Domain-modeling audit evidence

## Pinned source and support files

- Pinned commit: `2ab958093e83e0ec752e6c1c5932da465bf23e0c`
- Canonical source path: `skills/engineering/domain-modeling`
- Absolute audited snapshot: `/Users/admin/Library/Mobile Documents/com~apple~CloudDocs/Note/cs/prompt/my-matt-workflow/.worktrees/feat/upstream-first-repair/.superpowers/sdd/mattpocock-skills-pinned/skills/engineering/domain-modeling`

| File | Pinned source SHA-256 | Local SHA-256 | Result |
| --- | --- | --- | --- |
| `SKILL.md` | `152e2c97239affb12a60c5f4a7e74ab546a49ae169688c81f4e2ccc42dafa579` | `17381af6c821d090b1bf6b5d9ea64697c1ce2143c4e6016134cc826449d115d1` | Chinese translation with changed frontmatter identity and invocation metadata, plus changed repository-document and write-policy contract. |
| `CONTEXT-FORMAT.md` | `b8cc318f2a4285b530e908b6bc43901c3c5cd11100362636bbc4216639bef597` | `3502f543e3cda988f510e5f04605171eef298487113ea2e68ebf4a2777ab4780` | Chinese translation with topic-local personal-glossary routing and policy-controlled ambiguity handling. |
| `ADR-FORMAT.md` | `f1f36cd3f8d3b6474ddd5855da4e233bfc4ae1a1c5024909ccf11871819a41b2` | `d032f6a96b24664ce37c8e1d3b083b3090bd39e9377e532a85b04b220454ef9a` | Chinese translation with topic-local ADR candidates and project-policy team-write gate. |
| `agents/openai.yaml` | `f6bf2aa996c6e6f53fdd0708e18a0d16a56aed8322cca59fedbe3c0d2c75f06b` | `3c8eed94d070a1226e45f0611ca1054c878b2b7a5a4732e534fe444698235cdb` | Both interface fields match; local-only manual-invocation policy is added. |

## Section parity

| Pinned upstream section | Local counterpart | Audit finding |
| --- | --- | --- |
| `SKILL.md#Challenge against the glossary` | `SKILL.md#对照术语表提出质疑` | Complete translation: immediately surface language conflicts. |
| `SKILL.md#Sharpen fuzzy language` | `SKILL.md#收紧模糊语言` | Complete translation: propose canonical terms for overloaded language. |
| `SKILL.md#Discuss concrete scenarios` | `SKILL.md#讨论具体场景` | Complete translation: use edge cases to sharpen concept boundaries. |
| `SKILL.md#Cross-reference with code` | `SKILL.md#与代码交叉验证` | Complete translation: expose contradictions between stated behavior and code. |
| `SKILL.md#Offer ADRs sparingly` | `SKILL.md#谨慎提出 ADR` | Complete translation of the three mandatory ADR gates. |
| `CONTEXT-FORMAT.md#Structure` | `CONTEXT-FORMAT.md#结构` | Complete translation of concise context description, canonical term, and avoided-term format. |
| `CONTEXT-FORMAT.md#Rules` | `CONTEXT-FORMAT.md#规则` | Complete translation of opinionated terminology, tight definitions, context specificity, and grouping. |
| `ADR-FORMAT.md#Template` | `ADR-FORMAT.md#模板` | Complete translation of the short decision/context/why format. |
| `ADR-FORMAT.md#Optional sections` | `ADR-FORMAT.md#可选章节` | Complete translation of optional status, considered-options, and consequences guidance. |
| `ADR-FORMAT.md#Numbering` | `ADR-FORMAT.md#编号` | Complete translation of scan-highest-and-increment numbering. |
| `ADR-FORMAT.md#When to offer an ADR` | `ADR-FORMAT.md#何时建议 ADR` | Complete translation of hard-to-reverse, surprising-without-context, and real-trade-off gates. |
| `ADR-FORMAT.md#What qualifies` | `ADR-FORMAT.md#符合条件的例子` | Complete translation of qualifying architecture, integration, lock-in, boundary, constraint, and rejected-alternative examples. |
| `agents/openai.yaml#interface.display_name` | `agents/openai.yaml#interface.display_name` | Identical: `Domain Modeling`. |
| `agents/openai.yaml#interface.short_description` | `agents/openai.yaml#interface.short_description` | Identical: `Build and sharpen a domain model`. |
| `SKILL.md#frontmatter.name` | `SKILL.md#frontmatter.name` | Changed local adaptation: `domain-modeling` is registered locally as `my-domain-modeling`; this has an upstream counterpart and is not local-only. |
| `SKILL.md#frontmatter.description` | `SKILL.md#frontmatter.description` | Changed local adaptation: the Chinese description is reworded and narrows the upstream invocation scope, omitting the case where another Skill needs to maintain the model. |
| `SKILL.md#File structure` | `SKILL.md#文件结构` | Changed: upstream’s root `CONTEXT.md`, root `CONTEXT-MAP.md`, and `docs/adr/` convention is replaced by project-configured formal locations plus topic-local `.agent/work/<topic>/domain/` files. |
| `SKILL.md#Update CONTEXT.md inline` | `SKILL.md#就地更新个人术语表` | Changed: upstream directly updates the project `CONTEXT.md` upon resolution; local first writes a personal glossary, then makes team-document writes policy-controlled external actions. |
| `CONTEXT-FORMAT.md#Single vs multi-context repos` | `CONTEXT-FORMAT.md#单上下文与多上下文仓库` | Changed: upstream requires asking when multi-context routing is unclear; local permits an approved unattended plan to record an assumption instead. |
| _none_ | `SKILL.md#frontmatter.disable-model-invocation` | Local-only adaptation: `disable-model-invocation: true` is an independent manual-only invocation signal. |

No upstream content is absent; the five changed upstream sections and one local-only frontmatter addition are adaptation deltas, not restoration gaps.

## Local-only additions and adaptation assessment

- `SKILL.md#frontmatter.name` is a changed local adaptation, because it replaces an upstream field with `my-domain-modeling`; it is not a local-only addition.
- `SKILL.md#frontmatter.description` is a changed local adaptation, because it rewords and narrows an upstream field; its lost cross-Skill maintenance trigger belongs in the Plan 2 rework review.
- `SKILL.md#frontmatter.disable-model-invocation: true` is a local-only adaptation and independently signals manual-only invocation.
- `SKILL.md#项目策略优先` is local-only. It declares that instructions to ask, confirm, stop, or limit later work yield to the effective project policy (except listed safety limits).
- `agents/openai.yaml#policy.allow_implicit_invocation: false` is also a local-only manual-only policy setting. Manual-only behavior is therefore jointly represented by this setting and `SKILL.md#frontmatter.disable-model-invocation`, not by `agents/openai.yaml` alone.
- The project-configured document locations, personal working copies, and manual-only invocation settings are potentially valid local adaptations when they preserve the upstream method.
- The policy override is not faithful as written: it can weaken the upstream unconditional “If unclear, ask” routing constraint and direct inline model capture. It therefore requires a bounded adapter rework, not a restoration of translated documents.

## Conclusion and follow-up

- Conclusion: **adapter-rework-required**.
- Exact follow-up destination: **Plan 2 — `my-domain-modeling` adapter rework**.
- Do not restore or refactor `skills/my-domain-modeling` during this audit. Constrain the policy adapter so it cannot bypass upstream domain-routing clarification or the immediate model-capture requirement; retain only adaptations proven not to weaken that method.

## Retrieval/application evidence

`tests/fixtures/domain_modeling_application.json` is a structured, section-bound scenario exercise:

1. a known multi-context map is retrieved before routing a clear topic;
2. an unclear multi-context topic retrieves the routing constraint, then evaluates independent upstream and local rules: upstream asks for clarification while the local policy permits an approved unattended plan to record an assumption;
3. a resolved term without implementation detail is recorded in the local glossary; and
4. an ADR is drafted only when all three upstream-derived gates hold.

`DomainModelingParityTests` retrieves each cited local constraint and requires exactly one matching outcome for each policy-scoped rule set. The divergent unclear-routing outcomes make the **adapter-rework-required** conclusion observable.

## Review remediation evidence

- The fidelity ledger records all behavior-changing `SKILL.md` frontmatter deltas: changed `name`, narrowed/reworded `description`, and local-only `disable-model-invocation: true`.
- The manual-only behavior is tracked as two independent local adaptations—`SKILL.md#frontmatter.disable-model-invocation` and `agents/openai.yaml#policy.allow_implicit_invocation`—rather than being attributed only to the YAML policy.
- The structured unclear multi-context scenario retrieves `CONTEXT-FORMAT.md#单上下文与多上下文仓库` and exposes the upstream clarification requirement against the locally permitted unattended assumption.
