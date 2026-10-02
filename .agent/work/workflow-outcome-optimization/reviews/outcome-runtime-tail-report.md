# Runtime tail and coarse loader repair

Changed only evidence.py, batches.py, test_batches.py relative to integrated verbose fix.

- Persist full-output execution_observed, output_complete/length and narrowly proven per-loader dependency gaps in new command rows.
- Reevaluate legacy rows using complete failure identities and footer error counts. Ran 12 with 12 complete loader errors is not evidence of executed behavior even when the tail shows only four headers.
- In partial runs, matching loader module names cannot hide current actual or unknown import failures. Only a current dependency gap proven inside a complete standard unittest report can remain a matching known loader issue. Real executed test identities keep their normal known/new comparison.
- Aggregate repeated loader identities with all diagnostic blocks; any real or unknown block defeats the environment shortcut regardless of order.
- Raw legacy cached comparisons are still reevaluated at close. No success/history rewrite or migration.

Public CLI red: tail/default+verbose with legacy unavailable false/true, plus real-passing-test + missing-to-AssertionError; duplicate real+environment loader blocks also red in both modes.

Final focused green: 11 tests / 44.470s / OK / exit 0. Covers new and legacy pure startup, truncated real partial known/new differences, duplicate block aggregation, custom multistage runner failures, Go package identity and raw legacy receipt recovery. AST, git diff --check, incremental git apply --check pass. No full suite run.

Evidence: /tmp/outcome-runtime-tail-red.log, /tmp/outcome-runtime-tail-duplicate-red.log, /tmp/outcome-runtime-tail-green.log, /tmp/outcome-runtime-tail-verification.json, /tmp/outcome-runtime-tail-source-manifest.json.

Boundary: unknown/nonstandard unittest wrappers conservatively cannot use loader name equality as behavior comparison. Actual loader AssertionError is unavailable=false and blocks close. Only synthetic reviews in toy Git fixtures were used to reach product gates; they do not certify this construction. Root independent review and integrated suite remain separate.
