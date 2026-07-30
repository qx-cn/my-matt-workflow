# To-questionnaire restoration evidence

## Source and restored files

- Pinned commit: `2ab958093e83e0ec752e6c1c5932da465bf23e0c`
- Source path: `skills/in-progress/to-questionnaire`
- Restored source SHA-256: `SKILL.md` `8e7f9ed8d7b2e66babf1a54aee9b94319bf38c32619cffe78819df6518ead5fc`; `agents/openai.yaml` `9e8a06c38c8842eea8d4922cb9d1ead8e3ace647bab259b943c994a1b4742bc2`.

## Parity and bounded adaptations

- `skills/my-to-questionnaire/` restores the questionnaire workflow and document structure. The ledger records all three source mappings as complete and translated, with no missing or local-added sections.
- The display name “To Questionnaire” is translated to the local document title `生成发现问卷`; local metadata remains manual-only. No workflow method changed.

## Verification and restoration source

- The restoration's focused parity and scenario tests cover scope, ordered steps, output file, and questionnaire content constraints; the full workflow suite was run during the original restoration.
- Source restoration evidence: the original review record, `.superpowers/sdd/task-6-report.md`, whose committed replacement is this document; detailed mappings and hashes remain in `upstream/fidelity.json`.
