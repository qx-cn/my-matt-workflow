# Grilling audit evidence

## Source

- Pinned commit: `2ab958093e83e0ec752e6c1c5932da465bf23e0c`
- Source path: `skills/productivity/grilling`
- Source files and SHA-256:
  - `SKILL.md`: `44331dda57f461db4fec3f2efb6ddabe7aaaa0a57ae0f88a883bc61aed8a0587`
  - `agents/openai.yaml`: `cf29b9a8dbf35a58a908a6ca4f64dcd86c2b2130291eee0a78b9f706b138825b`

## Section and support-file comparison

| Pinned upstream | Local counterpart | Audit finding |
| --- | --- | --- |
| `SKILL.md` document body | `skills/my-grilling/SKILL.md` document body | The four workflow paragraphs are translated: branch-by-branch decision interview, one question at a time with a recommendation, look up environment facts, and do not act before shared understanding. |
| `agents/openai.yaml#interface.display_name` | `skills/my-grilling/agents/openai.yaml#interface.display_name` | Both are `Grilling`. |
| `agents/openai.yaml#interface.short_description` | `skills/my-grilling/agents/openai.yaml#interface.short_description` | Upstream is “Stress-test thinking one question at a time”; local is “Run a focused design interview”, which narrows the stress-test purpose. |
| _none_ | `SKILL.md#项目策略优先` | Local-only policy block makes instructions to ask, confirm, stop, or limit later work subordinate to an effective project policy. This can override the upstream unconditional confirmation gate. |
| _none_ | `agents/openai.yaml#policy.allow_implicit_invocation` | Local-only `false` models manual-only invocation. |

The local metadata SHA-256 is `fd9b95d5468600190f9cedf23a575fc71ffa2fde03b5d55bacd2fee2b27063a6`.

## Permitted adaptation and conclusion

- Permitted local adaptation: retain manual-only invocation metadata and a project-policy safety entry point, provided it does not weaken the upstream workflow.
- Exact material requiring rework: remove or constrain the `SKILL.md#项目策略优先` override so it cannot bypass “Do not act on it until I confirm we have reached a shared understanding”; restore the metadata description’s explicit stress-test scope while retaining any required local invocation setting.
- Conclusion: **adapter-rework-required**. The translated workflow itself is present, but the policy override can change its core confirmation behavior and the metadata narrows its stated purpose.
- Destination queue: **Plan 2 — `my-grilling` adapter rework** (next task); do not restore or refactor this Skill in this audit.

## Retrieval/application evidence

`tests/fixtures/grilling_application.json` models three constraint-retrieval scenarios:

1. facts discoverable in the environment are looked up instead of asked;
2. decisions are interviewed one at a time with a recommendation; and
3. requested execution waits until shared understanding is confirmed.

`GrillingParityTests` validates that each scenario retrieves the cited local
constraint and produces exactly one expected outcome.

## Review remediation evidence

- The fidelity ledger now records `agents/openai.yaml#interface.display_name`
  and `agents/openai.yaml#interface.short_description` independently. Only the
  unchanged display name is complete/translated.
- The narrowed short description is recorded as a Plan 2 rework-required
  adaptation delta, not as a local-only addition or a complete translation.
- The population guard parses the upstream manifest and imports
  `ADAPTATION_MAP` and `UPSTREAM_PATHS` to verify the 24-entry closure and the
  `grilling` registrations directly.
