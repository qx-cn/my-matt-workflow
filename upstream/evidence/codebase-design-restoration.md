# Codebase-design restoration evidence

## Source and restored files

- Pinned commit: `2ab958093e83e0ec752e6c1c5932da465bf23e0c`
- Source path: `skills/engineering/codebase-design`
- Restored source SHA-256: `SKILL.md` `a8d50abac5a4018f60e1d911d4b6f4e36454ca14d6c390c0695a578c7de65dad`; `DEEPENING.md` `125e6b77413ad2bc7cf7a772bc74336d580a50f9e797db2178ed133d62333d06`; `DESIGN-IT-TWICE.md` `21c3264953bd30ee87b181a3ccaf0e70649f461e5ffd7dc654acee4ba1788b31`; `agents/openai.yaml` `edebc9e4fcfe102114012575eaa9600b9b5fd08c311664f389c36e7bc717740f`.

## Parity and bounded adaptations

- `skills/my-codebase-design/` restores the glossary, deep-versus-shallow model, seam/testability guidance, dependency/seam/testing references, and three-step design-twice process. The ledger records all 14 mappings as complete and translated, with no missing or local-added sections.
- The only bounded adaptation retains the local name, manual invocation metadata, and the repository's short project-policy-first reminder; it does not alter the upstream method.

## Verification and restoration source

- The restoration's focused parity test verifies the recovered files and usable design method; the full workflow suite was run during the original restoration.
- Source restoration evidence: the original review record, `.superpowers/sdd/task-1-report.md`, whose committed replacement is this document; detailed mappings and hashes remain in `upstream/fidelity.json`.
