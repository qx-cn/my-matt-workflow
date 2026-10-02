# CI diagnosis

- Commit: `04cd3f0f617f2a2364dc05f49d6d2eb1d4137d53`
- Run: https://github.com/qx-cn/my-matt-workflow/actions/runs/37029900314
- Failed job: `check (3.10)` / Python 3.10.21, command `python3 tools/workflow.py check`, exit 1.
- Python 3.14 job was cancelled by matrix fail-fast while its check step was running; it has no passing conclusion.
- Actual log: 352 unit tests, 263.834 seconds, 15 failures. Twelve are subtests from six BatchTests loader regressions, three are FailureClassificationTests loader regressions. The embedded `test_gate.Gate.test_fails` output is a deliberate negative deploy fixture, not the final suite failure.

## Root cause and evidence

`tools/workflow_lib/evidence.py` recognizes loader identities only when they contain `unittest.loader._FailedTest.`. `tools/workflow_lib/batches.py:338` repeats this recognition for unchanged coarse identities. Python 3.10 formats TestCase as `method (module.Class)` rather than including `.method` inside parentheses: CPython v3.10.21 `Lib/unittest/case.py` defines `__str__` as `"%s (%s)" % (self._testMethodName, strclass(self.__class__))`. Hence its loader report header is `ERROR: missing (unittest.loader._FailedTest)`.

A read-only minimal synthetic report probe using existing evidence functions confirms:

- Python 3.10 header: execution_observed=True; loader_only_failure=False; dependency fingerprints={}.
- Same report with modern `missing (unittest.loader._FailedTest.missing)` header: execution_observed=False; loader_only_failure=True; fingerprint present.

This directly explains failed comparison_eligible, unavailable_loader_failures, new_failures, and unverified assertions: loader identities are mistaken for real executed test cases; stable coarse module names then incorrectly suppress changed import diagnostics.

## Minimal repair

Add a shared strict loader-identity predicate supporting both qualified forms, use it across evidence.py and batches.py instead of string checks, and add focused raw-report compatibility regressions for both forms. Preserve identity strings and dependency diagnostic hashes, and retain complete-report/duplicate-block safeguards. Keep dependency proof version 3 because the typed complete-block fingerprint mechanism is unchanged. Previously misclassified Python 3.10 v3 receipts have empty fingerprints; the corrected coarse-loader recognition now marks their unchanged identities uncertain and new, blocking reuse until retest. A regression explicitly covers those old cached facts.

Run focused classification and BatchTests cases on the available interpreter; full check once deploy finishes. Push and inspect both Python matrix jobs. No removal of Python 3.10 from CI is needed.

The archived Markdown validator issue reported locally is a separate issue; this failed CI log does not implicate Markdown validation. Preserve original historical review evidence and synthetic fixture bytes. No source files were edited and no second build/install was launched during diagnosis.

## Implemented repair and focused evidence

Changed `tools/workflow_lib/evidence.py` and `tools/workflow_lib/batches.py` to share an anchored identity predicate for both report formats. Added `tests/test_loader_report_compatibility.py`. The predicate rejects unrelated names and trailing text; no startup exemption was added.

Python 3.10 and uv are not available locally. `/usr/bin/python3` is Python 3.9.6; `/opt/homebrew/bin/python3.14` is available. Actual missing-dependency unittest subprocess reports were captured on both: 3.9 has `_FailedTest)` and 3.14 has `_FailedTest.test_missing)`, agreeing with verified upstream 3.10 class formatting.

- New raw-report compatibility suite: 3 tests PASS on Python 3.14 and Python 3.9.6.
- Existing test_failure_classification.py: 6 tests PASS on Python 3.14 (18.017s).
- Existing six BatchTests that failed CI (12 normal/verbose subtests): PASS on Python 3.14 (40.256s).
- git diff --check: PASS.

Full-suite and exact Python 3.10 Linux validation remain for main agent/CI. No builds or installs were started by this agent.
