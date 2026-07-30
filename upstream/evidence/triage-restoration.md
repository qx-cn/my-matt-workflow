# Triage restoration evidence

## Source and restored files

- Pinned commit: `2ab958093e83e0ec752e6c1c5932da465bf23e0c`
- Source path: `skills/engineering/triage`
- Restored source SHA-256: `SKILL.md` `d45827c299c021f77b0f146fefa3ee679b13f99e9a2ffdf48e8de2347adeefe1`; `AGENT-BRIEF.md` `5b78d347cc53f6bcf7b875106005ccf5315055fa4cf75eb28d41e96ee426d27b`; `OUT-OF-SCOPE.md` `2526f998fd7ca5e956d3f6f234bcc2431a5971ee769f1148ddc60b92f04d5914`; `agents/openai.yaml` `2e683717720cf456d165d0bb1a68bb600d0b6a8ccb61841c172e50d26f95351c`.

## Parity and bounded adaptations

- `skills/my-triage/` restores the triage state machine, invocation and resumption flow, agent-brief guidance, and out-of-scope knowledge-base process. The ledger records all source mappings as complete and translated, with no missing source sections.
- Plan 4 adds one bounded local Ticket guard: structured implementation Tickets are already triaged, Wayfinder decisions are never implementation candidates, and locally stored ready-for-agent tickets use the executable ticket model.
- The upstream triage state machine remains unchanged; composition, write controls and ticket eligibility are referenced rather than duplicated.

## Verification and restoration source

- The restoration's focused parity and scenario tests cover retrieved triage constraints; the full workflow suite was run during the original restoration.
- Source restoration evidence: the original review record, `.superpowers/sdd/task-3-report.md`, whose committed replacement is this document; detailed mappings and hashes remain in `upstream/fidelity.json`.
