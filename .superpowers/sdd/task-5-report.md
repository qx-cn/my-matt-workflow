# Task 5 Report — Restore my-improve-codebase-architecture

## Status

DONE

## Scope and source

- Target: `skills/my-improve-codebase-architecture`
- Verified pinned checkout: `.superpowers/sdd/mattpocock-skills-pinned`
- Pinned commit: `2ab958093e83e0ec752e6c1c5932da465bf23e0c`
- Exact source path: `skills/engineering/improve-codebase-architecture`
- Source files inspected through that checkout: `SKILL.md`, `HTML-REPORT.md`, and `agents/openai.yaml`

## TDD evidence

| Phase | Command and result |
| --- | --- |
| RED | Added `ImproveCodebaseArchitectureParityTests`, then ran `python3 -m unittest tests.test_workflow.ImproveCodebaseArchitectureParityTests -v` → failed as expected: the ledger path lacked the required `skills/` prefix and `architecture_application.json` was absent. |
| GREEN | Restored both Chinese documents, fidelity mappings, and the structured fixture; the same focused command → `Ran 2 tests ... OK`. |
| Regression | The first full suite exposed three obsolete local-adapter assertions requiring a policy footer and `.agent/work/...` report path that conflict with the pinned upstream method. They now explicitly classify this restored skill alongside the other source-faithful restorations. Final `python3 -m unittest discover -s tests -p 'test_*.py' -v` → `Ran 96 tests ... OK` (1.805s). |

## Parity evidence

- `SKILL.md` completely translates exploration: scope-before-scan YAGNI, explicit direction versus commit-history hot spots, `CONTEXT.md`/ADR reading, organic friction exploration, and the deletion-test decision signal.
- The report workflow retains OS-temp output, opening and reporting the absolute path, candidate-card fields, recommendation strengths, before/after visuals, ADR conflict threshold, top recommendation, and the stop condition that asks the user to choose before proposing interfaces.
- The grilling loop retains selection-gated grilling, inline domain-model updates, lazy `CONTEXT.md` creation, immediate term refinement, load-bearing rejection ADR offer, and alternative-interface design-twice flow.
- `HTML-REPORT.md` fully translates the scaffold, header, candidate card, diagram patterns, style guidance, recommendation, and controlled architectural vocabulary.
- `upstream/fidelity.json` records all 18 `SKILL.md`/`HTML-REPORT.md` source-to-local mappings in both `complete` and `translated`, no missing or locally added sections, all three pinned source hashes, the preserved local metadata hash `c8cb20f68ebf0edb4e497bc11ae5fcaa196004e661cd189015b04f4109ced7f1`, this evidence path, and a `faithful` conclusion.

## Offline HTML adaptation

The single bounded adaptation is explicit in the fidelity ledger: upstream Tailwind and Mermaid CDN dependencies are replaced with inline CSS/SVG and static local diagrams. This preserves the report’s single-file, visual, candidate-card, before/after, and vocabulary semantics while satisfying the local offline-report requirement; no remote scripts or CDN URLs remain.

## Retrieval/application fixture

`tests/fixtures/architecture_application.json` contains four structured scenarios. The focused test verifies that every cited Chinese constraint is retrievable from its declared restored document, belongs to a source section, and produces exactly one expected outcome when its input facts match:

- `exploration-before-recommendation` → widens a scattered scan only after the glossary/ADRs and friction exploration are complete.
- `yagni-rejection` → rejects a candidate when deletion does not concentrate complexity.
- `report-recommendation` → writes a fresh temp report with a before/after visual, asks the user to choose, and does not propose interfaces.
- `grilling-domain-modeling-loop` → starts grilling, updates `CONTEXT.md`, offers an ADR for a load-bearing rejection, and runs design-twice for alternative interfaces.

## Changed files

- `skills/my-improve-codebase-architecture/SKILL.md`
- `skills/my-improve-codebase-architecture/HTML-REPORT.md`
- `upstream/fidelity.json`
- `tests/test_workflow.py`
- `tests/fixtures/architecture_application.json`
- `.superpowers/sdd/task-5-report.md`

## Concerns

None blocking. No policy override, release, publish, push, unrelated Skill, or workflow implementation change was made.
