# Task 2 Report — Restore my-writing-great-skills

## Status

DONE

## Scope and source

- Target: `skills/my-writing-great-skills`
- Pinned semantic baseline: `2ab958093e83e0ec752e6c1c5932da465bf23e0c`
- Exact repository-relative source path: `skills/productivity/writing-great-skills`
- Source files inspected before edits: `SKILL.md`, `GLOSSARY.md`, `agents/openai.yaml`
- Corresponding local files inspected before edits: `SKILL.md`, `GLOSSARY.md`, `agents/openai.yaml`

## Restored material and parity

- `SKILL.md` is now a complete Chinese translation of all seven upstream sections: Invocation, Writing the description, Information hierarchy, When to split, Pruning, Leading words, and Failure modes. It retains the `tight` and `red` examples, hierarchy ladder, completion-condition constraints, branch/sequence split conditions, and negation hard-guardrail exception.
- `GLOSSARY.md` is now a complete Chinese translation of all 31 glossary headings, including every invocation, information-hierarchy, steering, and pruning term plus its failure modes and avoid lists.
- `upstream/fidelity.json` records all 38 source-to-local section mappings in both `complete` and `translated`, has no missing sections, uses the exact source path, links this report as evidence, records every upstream support-file hash, and has a `faithful` conclusion.
- Manual-only metadata was preserved unchanged. The local `agents/openai.yaml` hash is `b3c555d2654ec61aed78f8435f583c6a0cd6bf980d71317724682ad20075c33d`; it matches the pinned support-file hash.
- The sole bounded local adaptation is explicit: local name/manual-call metadata; no upstream method was changed.

## TDD evidence

| Phase | Command and result |
| --- | --- |
| RED | Added `WritingGreatSkillsParityTests.test_restoration_records_full_parity_and_applies_guidance`, then ran `python3 -m unittest tests.test_workflow.WritingGreatSkillsParityTests` → failed as expected: ledger path was `productivity/writing-great-skills`, not required `skills/productivity/writing-great-skills`. |
| GREEN | Restored the translation, ledger, and fixture; ran the same command → `Ran 1 test ... OK`. |
| Regression | `python3 -m unittest discover -s tests` → `Ran 88 tests ... OK` (1.771s). The sandboxed attempt could not create temporary Git repositories; rerunning the identical suite with filesystem permission passed. |

## Wording retrieval/application fixture

`tests/fixtures/writing_great_skills_wording.json` supplies 15 structured micro-tests (five per group). Every case links retrieved local guidance to an observable decision; the focused test verifies each cited wording exists in its declared local document.

| Group | Case outcomes |
| --- | --- |
| baseline | `description-one-trigger-per-branch` → rewrite; `step-needs-checkable-bound` → rewrite; `disclose-branch-specific-reference` → rewrite; `one-authoritative-rule` → rewrite; `pretrained-leading-word` → rewrite. |
| fixed | `manual-skill-remains-user-invoked` → accept; `pointer-wording-controls-retrieval` → rewrite; `sharpen-before-splitting` → rewrite; `delete-noop-prose` → reject; `positive-steering` → rewrite. |
| stress | `synonym-stuffed-description` → rewrite; `split-only-when-earned` → reject; `sprawl-needs-hierarchy` → rewrite; `hard-guardrail-keeps-positive-pair` → rewrite; `thin-legwork-is-not-premature-completion` → rewrite. |

## Changed files

- `skills/my-writing-great-skills/SKILL.md`
- `skills/my-writing-great-skills/GLOSSARY.md`
- `upstream/fidelity.json`
- `tests/test_workflow.py`
- `tests/fixtures/writing_great_skills_wording.json`
- `.superpowers/sdd/task-2-report.md`

## Commit

- `cb8677b` — Restore writing-skill guidance from the pinned baseline.
- This report is committed separately because the implementation SHA is required as its evidence.

## Concerns

None blocking. No release was built or published, and no unrelated Skill or foundational composition/resource/release/installer/.agent infrastructure was modified.

## Follow-up repair evidence

- RED: `python3 -m unittest tests.test_workflow.WritingGreatSkillsParityTests` → failed as expected because `my-writing-great-skills/SKILL.md` still contained the `项目策略优先` policy footer and the fidelity adaptation still recorded it.
- GREEN: removed only that Skill's footer and updated its fidelity adaptation; the same focused command → `Ran 2 tests ... OK`.
- RED: the upgraded fixture assertion then failed as expected because each case had a prose `input` rather than a structured mapping.
- GREEN: each of the 15 cases now supplies structured input facts plus a task-local `constraint_mapping`; the focused test retrieves every cited source phrase and applies matching facts to exactly one documented `accept`/`reject`/`rewrite` decision.
- Regression: `python3 -m unittest discover -s tests` → `Ran 89 tests ... OK` (1.997s).
- Commit: `5b9d4b0` — Restore writing guidance without policy overrides.
