# TDD audit evidence

## Source

- Pinned commit: `2ab958093e83e0ec752e6c1c5932da465bf23e0c`
- Absolute pinned source checkout:
  `/Users/admin/Library/Mobile Documents/com~apple~CloudDocs/Note/cs/prompt/my-matt-workflow/.worktrees/feat/upstream-first-repair/.superpowers/sdd/mattpocock-skills-pinned`
- Canonical source path: `skills/engineering/tdd`

### Source files and SHA-256

| Source file | SHA-256 |
| --- | --- |
| `SKILL.md` | `5363bb2775679fe9311fbb67947f95359169c6e7f1fac77c0f25e190bca6cf2f` |
| `mocking.md` | `3ceb807fdf4a47d6a93d4d9a891e5ba6d362a6247bd08adc451feebfc17361ef` |
| `tests.md` | `859f9e592c188fda4fc7277dd180e4ce9c7a2e13f6efe1f6f29eccc9d28c106a` |
| `agents/openai.yaml` | `ea6f01cf1b8c06a4b0f5b649d74b1b8ce8685e72af1b38d70d877693e092af0b` |

### Local files and SHA-256

| Local file | SHA-256 | Classification |
| --- | --- | --- |
| `skills/my-tdd/SKILL.md` | `0bbe3c5acbdff94058b10e4202274696caf19b5737d6b152db4252866b4d2684` | translated body plus local metadata/policy additions |
| `skills/my-tdd/mocking.md` | `3ceb807fdf4a47d6a93d4d9a891e5ba6d362a6247bd08adc451feebfc17361ef` | byte-identical |
| `skills/my-tdd/tests.md` | `859f9e592c188fda4fc7277dd180e4ce9c7a2e13f6efe1f6f29eccc9d28c106a` | byte-identical |
| `skills/my-tdd/agents/openai.yaml` | `00be42a1828a07fdbcd33a4f5fad8360256986f7ff85aafac919db9910ee186c` | local policy metadata added |

## Section and support-file comparison

| Pinned upstream | Local counterpart | Audit finding |
| --- | --- | --- |
| `SKILL.md#frontmatter.name` | `SKILL.md#frontmatter.name` | Changed local adaptation: `tdd` is registered as `my-tdd`; the method is unchanged. |
| `SKILL.md#frontmatter.description` | `SKILL.md#frontmatter.description` | Changed local adaptation: Chinese description retains test-first feature/fix, red-green-refactor, and integration-test triggers. |
| `SKILL.md#preamble` | `SKILL.md#测试驱动开发` | Complete translation retains the durable-test purpose, before/during-cycle retrieval, project terminology, and ADR awareness. The source’s literal `CONTEXT.md` location is generalized to existing project terminology/ADR sources. |
| `SKILL.md#What a good test is` | `SKILL.md#好测试是什么` | Complete translation preserves public-interface behavior, refactor stability, specification-like names, and links to both support files. |
| `SKILL.md#Seams — where tests go` | `SKILL.md#Seam——测试放在哪里` | Complete translation preserves public seams, the pre-agreement requirement, the stop condition that no test is written before confirmation, and the required user question. |
| `SKILL.md#Anti-patterns` | `SKILL.md#反模式` | Complete translation preserves implementation-coupling, tautology, horizontal-slicing, and vertical tracer-bullet constraints and examples. |
| `SKILL.md#Rules of the loop` | `SKILL.md#循环规则` | Complete translation preserves red-before-green, one seam/test/minimal implementation per slice, no speculative features, and moving refactoring to code review. |
| `mocking.md#When to Mock` | `mocking.md#When to Mock` | Byte-identical: mock only system boundaries; do not mock owned code or internal collaborators. |
| `mocking.md#Designing for Mockability` | `mocking.md#Designing for Mockability` | Byte-identical: dependency injection and SDK-style interfaces, including both TypeScript examples and their constraints. |
| `tests.md#Good Tests` | `tests.md#Good Tests` | Byte-identical: integration-style, public-interface tests and all five characteristics. |
| `tests.md#Bad Tests` | `tests.md#Bad Tests` | Byte-identical: implementation-detail, side-channel, and tautological-test examples with every stated red flag. |
| `agents/openai.yaml#interface.display_name` | `agents/openai.yaml#interface.display_name` | Complete and byte-equivalent: `TDD`. |
| `agents/openai.yaml#interface.short_description` | `agents/openai.yaml#interface.short_description` | Complete and byte-equivalent: `Test-driven red-green-refactor`. |

## Local deltas and conclusion

- `SKILL.md#frontmatter.disable-model-invocation` is a local-only,
  manual-invocation metadata adaptation.
- `agents/openai.yaml#policy.allow_implicit_invocation: false` is the
  corresponding local-only manual-invocation metadata adaptation.
- `SKILL.md#项目策略优先` is a local-only project-policy entry point. Its rule
  that instructions to ask, confirm, stop, or limit subsequent work defer to
  the effective policy can weaken the upstream stop condition in
  `SKILL.md#Seams — where tests go`: no test at an unconfirmed seam.

The naming, description translation, and manual-invocation metadata are
permitted adaptations. The policy override is not currently bounded so that it
preserves the upstream seam-confirmation gate.

Conclusion: **adapter-rework-required**.

Exact follow-up queue: **Plan 2 — `my-tdd` adapter rework**. Constrain or
remove the policy override so it cannot bypass pre-agreed seam confirmation;
do not restore or refactor this Skill in this audit task.

## Retrieval/application evidence

`tests/fixtures/tdd_application.json` has two independent, section-bound
constraint retrieval scenarios:

1. `red-green-slice` retrieves `SKILL.md#循环规则` rules for red-before-green
   and one slice at a time, then yields exactly
   `write-failing-test`, no implementation, and one slice.
2. `mock-only-system-boundary` retrieves `mocking.md#When to Mock` rules for
   system boundaries and internal collaborators, then yields exactly
   `use-real-collaborator` with `mock: false`.

`TddParityTests` verifies each retrieved local constraint appears in its cited
document and that exactly one rule yields each expected outcome.

## Task 11 review remediation

The fidelity ledger classifies only the five changed Chinese `SKILL.md` body
mappings as `translated`. The two `mocking.md` sections, two `tests.md`
sections, and the two unchanged `agents/openai.yaml#interface` fields remain
complete and byte-identical. The whole `agents/openai.yaml` file remains a
local adaptation solely because it adds policy metadata; that does not make
its unchanged interface fields translated.

`TddParityTests` now resolves every fixture constraint and every scenario
retrieval from its declared `document#heading`. It bounds the lookup at the
next heading of the same or higher level, then asserts the constraint text
inside that section. This verifies `SKILL.md#循环规则` and
`mocking.md#When to Mock` as real local headings instead of accepting text
found elsewhere in their files.
