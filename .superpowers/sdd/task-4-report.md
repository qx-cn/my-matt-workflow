# Task 4 Report — Restore my-teach

## Status

DONE

## Scope and source

- Target: `skills/my-teach`
- Pinned semantic baseline: `2ab958093e83e0ec752e6c1c5932da465bf23e0c`
- Verified local checkout: `.superpowers/sdd/mattpocock-skills-pinned` at that exact commit
- Exact repository-relative source path: `skills/productivity/teach`
- Source files inspected before restoration: `SKILL.md`, `GLOSSARY-FORMAT.md`, `LEARNING-RECORD-FORMAT.md`, `MISSION-FORMAT.md`, `RESOURCES-FORMAT.md`, and `agents/openai.yaml`

## RED / GREEN

| Phase | Command and result |
| --- | --- |
| RED | Added `TeachParityTests`, then ran `python3 -m unittest tests.test_workflow.TeachParityTests -v` → failed as expected: fidelity used `productivity/teach` instead of the exact source path, and `teach_application.json` was absent. |
| GREEN | Restored all five Chinese documents, fidelity mappings, and the structured application fixture; the same focused command → `Ran 2 tests ... OK`. |
| Regression | First `python3 -m unittest discover -s tests -p 'test_*.py' -v` exposed obsolete local-adapter expectations for the restored upstream skill's policy footer and `.agent/work` layout. The applicable assertions now treat `my-teach` as a source-faithful restored skill; the final full run → `Ran 93 tests ... OK` (1.931s). |

## Parity evidence

- `SKILL.md` fully translates the teaching workspace, knowledge/skills/wisdom philosophy, fluency versus storage strength, short HTML lessons, reusable assets, mission confirmation, ZPD selection, citations, feedback loops, community wisdom, reference documents, and teaching notes.
- `GLOSSARY-FORMAT.md`, `LEARNING-RECORD-FORMAT.md`, `MISSION-FORMAT.md`, and `RESOURCES-FORMAT.md` fully translate their templates, examples, rules, constraints, and stop conditions.
- `upstream/fidelity.json` records all 28 source-to-local heading mappings in both `complete` and `translated`, with no missing or added sections; it retains all six pinned support hashes, the local manual-only metadata hash, the bounded local name/manual-metadata adaptation, this evidence path, and a `faithful` conclusion.

## Retrieval/application fixture

`tests/fixtures/teach_application.json` contains six structured scenarios. The focused test confirms that every cited Chinese constraint is retrievable from its restored document and that matching input facts lead to exactly one outcome:

- `zpd-selection` → read learning records and teach the most relevant topic in the learner's ZPD.
- `storage-strength` → design skill practice with retrieval, spacing, and appropriate interleaving.
- `mission-revision` → ask for confirmation before changing a shifted mission.
- `learning-record` → write a record only after demonstrated non-trivial understanding.
- `glossary-promotion` → add a term only after understanding and with a tight definition.
- `resources-curation` → exclude an untrusted, unannotated resource.

## Commits

- `5b9c84e` — Restore teaching guidance from the pinned baseline.
- This evidence report is committed separately.

## Concerns

None blocking. No policy override, release, publish, push, unrelated Skill, or workflow infrastructure change was made.
