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
| `agents/openai.yaml#interface.short_description` | `skills/my-grilling/agents/openai.yaml#interface.short_description` | Byte-identical: “Stress-test thinking one question at a time”. |
| _none_ | `agents/openai.yaml#policy.allow_implicit_invocation` | Local-only `false` models manual-only invocation. |

The local metadata SHA-256 is `7b6a632a92aa599776dfb602d8260a75f6740f73277d523b9dc92584b584a3ef`.

## Permitted adaptation and conclusion

- Permitted local adaptation: retain manual-only invocation metadata, provided it does not weaken the upstream workflow.
- Plan 2 removed the local policy override, and Plan 6 restored the metadata description’s explicit stress-test scope.
- Conclusion: **faithful**. The translated workflow, confirmation gate, and runtime interface metadata now retain the upstream method; the local manual-only setting does not change it.

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
- Plan 6 restores the byte-identical short description, so it is a complete
  runtime-interface mapping rather than an adaptation delta.
- The population guard parses the upstream manifest and imports
  `ADAPTATION_MAP` and `UPSTREAM_PATHS` to verify the 24-entry closure and the
  `grilling` registrations directly.
