# Task 3 Report — Restore my-triage

## Status

DONE

## Scope and source

- Target: `skills/my-triage`
- Pinned semantic baseline: `2ab958093e83e0ec752e6c1c5932da465bf23e0c`
- Exact repository-relative source path: `skills/engineering/triage`
- Source files inspected before restoration: `SKILL.md`, `AGENT-BRIEF.md`, `OUT-OF-SCOPE.md`, `agents/openai.yaml`
- Corresponding local files inspected before restoration: `SKILL.md`, `AGENT-BRIEF.md`, `OUT-OF-SCOPE.md`, `agents/openai.yaml`

## RED / GREEN

| Phase | Command and result |
| --- | --- |
| RED | Added `TriageParityTests`, then ran `python3 -m unittest tests.test_workflow.TriageParityTests` → failed as expected: the fidelity path was `engineering/triage` instead of `skills/engineering/triage`, and the structured workflow fixture was absent. |
| GREEN | Restored the three translations, fidelity evidence, and fixture; the same focused command → `Ran 2 tests ... OK`. |
| Regression | First `python3 -m unittest discover -s tests` exposed three obsolete local-adapter assumptions (policy footer and `.agent/work` artifact layout) for the restored upstream skill. The related assertions now exclude `my-triage`; the final full run → `Ran 91 tests ... OK` (2.601s). |

## Parity evidence

- `SKILL.md` fully translates the triage state machine: role uniqueness and validation, unlabeled/`needs-triage`/active-`needs-info` ordering, PR handling, redundancy and prior-rejection checks, verification, grilling, all outcomes, state override, needs-info template, and session recovery.
- `AGENT-BRIEF.md` fully translates durable behavioral briefs, acceptance criteria, scope boundaries, templates, and Bug/enhancement/PR/negative examples.
- `OUT-OF-SCOPE.md` fully translates concept-based rejected-feature records, reason quality, matching, write exclusions for already-implemented work, closure flow, and reconsideration.
- `upstream/fidelity.json` contains all 29 source-to-local mappings in `complete` and `translated`, no missing/local-added sections, all four source support hashes, the local manual-only metadata hash, bounded name/manual-metadata adaptation, this evidence path, and a `faithful` conclusion.

## Retrieval/application fixture

`tests/fixtures/triage_workflow_application.json` contains five structured scenarios. The focused test retrieves each cited Chinese constraint from the restored document and applies matching input facts to exactly one expected outcome:

- `state-transition` → a reporter reply moves `needs-info` to `needs-triage`.
- `deterministic-ordering` → unlabeled, `needs-triage`, then active `needs-info`, oldest first.
- `needs-info` → preserve established facts and ask specific, actionable questions.
- `validation-failure` → conflicting state roles stop mutation and require maintainer input.
- `recovery` → show the updated picture without re-asking resolved questions.

## Commits

- `d8a2b2c` — Restore triage guidance from the pinned baseline.
- This evidence report is committed separately.

## Concerns

None blocking. No release was built or published, and no unrelated Skills, composition/resources/release/installer code, or `.agent/` handling was changed.
