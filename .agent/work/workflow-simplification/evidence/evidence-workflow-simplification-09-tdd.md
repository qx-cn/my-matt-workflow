# Ticket09 verification evidence

## Stable seams

- Public composition loader and actual source catalog: exactly32 entries,22 approved edges,11 call targets,31 router entries; routes are not calls.
- Real stage/build and real installer in temporary directories: shared resources bundled, no composed bodies; all Codex/Cursor/Claude metadata and local links validated.
- Broken catalog, invocation metadata or Markdown target causes build rejection before immutable release creation; fixture has no evals directory.
- Four real builds with temporary install state preserve current, previous and installed release IDs.

## TDD

Initial new-catalog/graph tests fail on baseline39 and the old copied-body model; implementation produces approved32/22/11/31 and real temporary installs. Release retention initially has no agent_homes argument; public build tests pass after implementation.

Formal Code/Spec review found explicit custom deployment home was lost before pruning. The accepted repair-plan test built/installed r1 and then deployed r4 to the same temporary custom home: before repair, automatic pruning removed r1 and actual install verification failed with `release 目录无效或为 symlink`; after preserving the argument, actual build/install succeeds and r1/r3/r4 remain. Both loops use real build/install/state verification; only the outer expensive source-test gate is replaced in the focused seam.

Final focused validation: 36 tests across test_skill_packaging_v2, test_resources and test_composition pass, including six public packaging cases and the custom-home deployment regression. Full declared command runs separately through the construction runtime; only the matching final code-content receipt is eligible for completion.

## Scope and evidence limits

User-approved splitting adjustment moves build/preflight/check eval decoupling to09; Spec revision1 and construction profile remain unchanged. Ticket13 owns deleting eval directories and remaining unused modules/commands and final integration. Shared instructions are reviewed semantically; automated install tests prove packaging and permissions, not model behavioral improvement. Only temporary hosts are written; no real deployment, push or external write.
