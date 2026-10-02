# R2 failure classification: final root cause repair

Scope: `tools/workflow_lib/evidence.py`, `tools/workflow_lib/batches.py` compare and import only, `tests/test_batches.py`, `tests/test_failure_classification.py`. No workflow Skills, commits, installs, or complete-suite execution.

## Final behavior

- Neither arbitrary ModuleNotFoundError diagnostics nor unittest loader wrappers prove that business initialization did not execute. Unittest loader failures are no longer marked environment-only unavailable.
- Complete loader dependency diagnostic blocks are hashed per loader identity, preserving every duplicate occurrence. A current nonzero loader may remain known only when its complete block identity matches the baseline. Changed, unknown, or insufficient legacy blocks are new failures. This applies both to all-loader baseline gaps and partial runs with real executed tests.
- Pure interpreter Python `-m` startup errors and actual OS launch failures retain their disclosed unavailable handling. Identical direct unittest missing dependency remains reviewable and closeable, with known failure and unverified disclosure.
- Proof revision is 3. Revisions 1 and 2 are reconstructed from complete diagnostic facts; old truncated evidence cannot establish a loader match. Fresh executions persist full-output fingerprints even when output_tail is truncated.
- Removed the obsolete unittest startup classifier and current-loader-only proof helper rather than adding exception-pattern exemptions.

## Verification

- Original independent dynamic loader probe on current source now produces new failures and blocks review/close: `/tmp/outcome-sol-loader-repro.json`.
- New public CLI group: 6 tests, exit 0, 19.170s, `/tmp/outcome-sol-failure-focused.log`. Includes generic dynamic error; v1 accepted-review cache; actual `-m`/OS positives; dynamic unittest loader with v1/v2 cached exemptions; identical direct loader positive; partial loader dynamic failure.
- First BatchTests plus classifier run: 41 tests, exit 1, 135.023s. Failures were obsolete expectations (loader unavailable=True; truncated old loader known; changed exception-only diagnostic known). Log `/tmp/outcome-sol-failure-green.log`. Those expectations were corrected to the new evidence boundary.
- Changed concise loader test separately: 1 test, exit 0, 6.726s, `/tmp/outcome-sol-concise-green.log`.
- Second BatchTests run started after all corrections except concise expectation; final result will be appended after completion.
- Original R2 matrix probe `/tmp/outcome-sol-R2-matrix.json`: dynamic, v1 and startup green. Loader business failure is blocked; the repair fixture runs zero tests and on Python 3.14 exits 5, therefore its repair phase cannot pass. Direct loader positive closes correctly but the old probe demands unavailable=True; final semantics correctly return known+unverified. Independent reviewer should adjust these two assertions/fixtures before final matrix verdict.

No independent-review, deployment, installation, or real business production claim is made here.

Final targeted verification: second BatchTests run completed 36 tests in 134.216s. Its only 2 failed subcases were the concise test's preloaded old expectation, changed while that process was running. The other 35 BatchTests passed. The corrected concise test (both verbose/default subcases) separately passed as noted above. Together with the 6 new classifier tests, all 42 unique targeted tests have current passing evidence. `git diff --check` passed. Do not describe the second process itself as exit 0; its recorded exit is 1. No full suite run.
