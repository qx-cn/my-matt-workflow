# Strict diagnostic type and cached proof repair

Scope: evidence.py, batches.py, test_batches.py only; incremental over integrated tail fix.

- Loader proof now accepts only specific ModuleNotFoundError exception-only diagnostics or a single complete traceback ending with that class. It cannot borrow arbitrary exception labels or interpreter startup syntax.
- General execution classification rejects AssertionError, RuntimeError and other exception labels. Genuine Python -m startup requires Python argv, -m before a script operand, and the matching interpreter diagnostic; direct and nested missing modules remain disclosed environment gaps. Shell shortcuts require actual shell argv and a shell-named diagnostic.
- Current raw receipt comparison re-proves pre-fix unavailable booleans and loader-gap lists from complete retained output. Truncated old proofs cannot establish unavailable/known comparisons and require a fresh batch test. New rows retain the single dependency_proof_version=1 marker for facts produced by strict classification; no history migration or rewriting.
- Old cached comparison fields remain non-authoritative. Tests simulate both an erroneous unavailable=true and an erroneous per-loader proof list, with empty cached new/unverified and preserved actual runner output. Status requires batch test and close fails at the test gate.

Actual public CLI red: 3 tests / 15.565s / 12 failures, covering AssertionError/RuntimeError concise diagnostics in default and verbose loader wrappers, direct concise runner, plus old cached status paths. Genuine Python -m startup controls passed in red.

Final focused green: 14 tests / 62.401s / OK / exit 0. Includes typed exception-only ModuleNotFoundError controls, direct/nested Python -m and complete legacy genuine environment receipts; all prior tail, real partial, duplicate-id, known/new test, multistage runner, Go identity and raw legacy receipt regressions passed.

AST parse, git diff --check and incremental git apply --check passed. No full suite. No workflow skills, real Topic changes, host install or release work.

Evidence: /tmp/outcome-runtime-concise-red.log, /tmp/outcome-runtime-concise-green.log, /tmp/outcome-runtime-concise-verification.json, /tmp/outcome-runtime-concise-source-manifest.json.

Compatibility boundary: pre-fix truncated current environment proofs need rerun; unknown/nonstandard diagnostics cannot use a module name or arbitrary exception text as known environment evidence. Genuine typed environment diagnostics and stable real executed test failures keep their existing path. Independent review and integrated full suite are root responsibilities.
