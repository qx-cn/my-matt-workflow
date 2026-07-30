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

## Review repair — upstream provenance and local metadata

### RED / GREEN evidence

#### RED

The focused regression first rejected the ledger's unresolvable source location:

```text
$ python3 -m unittest tests.test_workflow.DoctorTests.test_codebase_design_restoration_records_parity_and_usable_method
FAIL: 'skills/engineering/codebase-design' != 'engineering/codebase-design'
```

After the source location was corrected, the same focused test exposed that the ledger recorded only the pinned upstream metadata hash, not the preserved local manual-only metadata:

```text
FAIL: None != '0c24ffe790dc0aa8291bc52076db14f8a718b96cc7ab402381a26ee81ce579a9'
```

#### GREEN

```text
$ python3 -m unittest tests.test_workflow.DoctorTests.test_codebase_design_restoration_records_parity_and_usable_method
Ran 1 test ... OK

$ python3 -m unittest discover -s tests
Ran 87 tests in 14.009s ... OK
```

The ledger now records `skills/engineering/codebase-design`, which resolves from the pinned checkout root, and separately records the SHA-256 byte hash of the unchanged local `agents/openai.yaml`. The existing `support_files` entry remains the upstream snapshot hash; `local_support_files` identifies the permitted local runtime metadata.

### Retrieval / application scenario

**Given design situation.** `OrderSubmissionService` is shallow: callers invoke `validateOrder`, `calculateTax`, `chargeCard`, and `saveOrder` separately, while `chargeCard` constructs `StripeGateway` directly. Each caller recreates ordering and error-handling logic, and tests target the four pass-through methods.

**Retrieved constraints applied.** The restored method says to accept dependencies rather than create them, classifies Stripe as a genuinely external dependency, and requires a port at that seam with both production and test Adapters before treating it as a real seam. It also requires the Interface to be the test surface and directs replacement—not layering—of obsolete shallow tests.

**Resulting interface / seam recommendation.** Replace the four public methods with one deep `OrderSubmission.submit(order)` Interface. Inject a `PaymentGateway` port into the module; provide a Stripe production Adapter and an in-memory or mock test Adapter. Keep validation, tax calculation, persistence ordering, and error translation inside the module rather than exposing their intermediate operations. Test observable `submit` results through that Interface, then delete the former per-method shallow tests. This gives callers one small entry point while keeping the only external Seam at payment.

### Changed files and commit

- `tests/test_workflow.py` — adds exact upstream-path and local metadata-byte-hash assertions.
- `upstream/fidelity.json` — corrects the source path and records the preserved local metadata hash without changing other fidelity entries.

Implementation commit: `ff06b17` (`Fix codebase-design fidelity provenance`).
