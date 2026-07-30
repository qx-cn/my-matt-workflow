# Plan 1 / Task 1 Report — Restore `my-codebase-design`

## Result

Restored `my-codebase-design` from the pinned `mattpocock/skills` baseline at `2ab958093e83e0ec752e6c1c5932da465bf23e0c`. The three authored documents are now complete Chinese translations rather than a condensed local workflow. The existing manual-only `agents/openai.yaml` was preserved unchanged.

Implementation commit: `d55c278` (`Restore codebase-design translation fidelity`).

## RED / GREEN evidence

### RED

Added `DoctorTests.test_codebase_design_restoration_records_parity_and_usable_method` before changing the restored documents or ledger.

```text
$ python3 -m unittest tests.test_workflow.DoctorTests.test_codebase_design_restoration_records_parity_and_usable_method
FAIL: expected codebase-design complete sections to contain
Glossary, Deep vs shallow, Principles, Designing for testability,
Relationships, Rejected framings, and Going deeper; the ledger contained none.
```

The pre-existing ledger test also correctly failed after the entry became faithful:

```text
$ python3 -m unittest tests.test_workflow.DoctorTests.test_fidelity_ledger_covers_upstream_derived_skills
FAIL: 'faithful' == 'faithful'
```

The full suite exposed the repository-required compact policy footer twice: first for a missing `已解析生效策略`, then for a missing `strict-control`. The final one-line footer now preserves the local requirement without changing the upstream design method.

### GREEN

```text
$ python3 -m unittest tests.test_workflow.DoctorTests.test_codebase_design_restoration_records_parity_and_usable_method
Ran 1 test ... OK

$ python3 -m unittest tests.test_workflow.DoctorTests
Ran 10 tests ... OK

$ python3 -m unittest discover -s tests
Ran 87 tests ... OK
```

## Changed files

- `skills/my-codebase-design/SKILL.md` — restored and translated all upstream sections, diagrams, examples, design constraints, rejection criteria, and support-document references.
- `skills/my-codebase-design/DEEPENING.md` — translated all four dependency categories, Seam discipline, and replacement-based test strategy.
- `skills/my-codebase-design/DESIGN-IT-TWICE.md` — translated the three-step parallel-design process, four design constraints, required sub-agent output, and comparison/recommendation conditions.
- `upstream/fidelity.json` — marked `my-codebase-design` faithful with concrete upstream-to-local evidence, the fixed source hashes, the bounded local adaptation, and this report path.
- `tests/test_workflow.py` — added parity and application coverage; updated the ledger-wide invariant to require concrete evidence for a faithful entry.

## Section and support-file parity

`upstream/fidelity.json` records all seven `SKILL.md` sections:

1. Glossary → `术语表`
2. Deep vs shallow → `深模块与浅模块`
3. Principles → `原则`
4. Designing for testability → `为可测试性而设计`
5. Relationships → `关系`
6. Rejected framings → `被否决的表述`
7. Going deeper → `继续深入`

It also records the three `DEEPENING.md` sections and all four `DESIGN-IT-TWICE.md` process sections. Each completed and translated record includes an explicit local anchor and evidence describing retained examples, constraints, and stop/decision conditions.

The ledger preserves the pinned-upstream SHA-256 hashes for `SKILL.md`, `DEEPENING.md`, `DESIGN-IT-TWICE.md`, and `agents/openai.yaml`. The sole local adaptation is explicit and bounded: local naming/manual metadata plus the concise repository-required policy-precedence footer.

## Concerns

None. The original pinned checkout was present at the required commit; no source, runtime metadata, composition, resources, release, installer, or unrelated Skill files were changed.
