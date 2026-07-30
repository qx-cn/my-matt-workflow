# Teach restoration evidence

## Source and restored files

- Pinned commit: `2ab958093e83e0ec752e6c1c5932da465bf23e0c`
- Source path: `skills/productivity/teach`
- Restored source SHA-256: `SKILL.md` `6d2dbe5e03084cf26fef66b535127b36cd1bcbe9478e26b0626029cd51dc2259`; `GLOSSARY-FORMAT.md` `d177def491519d97873291f2e860d8f1d60ead78feecb82eee022177958069c6`; `LEARNING-RECORD-FORMAT.md` `855f81017625256584bbf62bd5edb9b0c86605c4cc1139c56acc36b802595d17`; `MISSION-FORMAT.md` `8da6d3ac84eb2eb19f17c260b6acf01c560d3ac7a4501c415eea0e985602f4d7`; `RESOURCES-FORMAT.md` `2bc634a64b0d0daa10904f9222e7aa0d361420dfacabbf092fbe3a72222edc08`; `agents/openai.yaml` `5856f3ae8aec742f1499c640aecdd5f1d6af5fa210a7c6ec794de8263a6f733f`.

## Parity and bounded adaptations

- `skills/my-teach/` restores the teaching workspace, learning philosophy, lessons/assets/mission, ZPD, knowledge and skills guidance, wisdom, references, notes, and all four format references. The ledger records all source mappings as complete and translated, with no missing or local-added sections.
- The only bounded adaptation retains the local name and manual invocation metadata; the upstream method is unchanged.

## Verification and restoration source

- The restoration's focused parity and scenario tests cover the teaching constraints; the full workflow suite was run during the original restoration.
- Source restoration evidence: the original review record, `.superpowers/sdd/task-4-report.md`, whose committed replacement is this document; detailed mappings and hashes remain in `upstream/fidelity.json`.
