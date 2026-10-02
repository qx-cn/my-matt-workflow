# macOS migration fixture cleanup investigation

Scope: read-only source investigation; exactly five focused test executions. No production/test source edits, full suite, deploy, or install.

Evidence:
- Failing build ran 357 tests; sole error occurred in TemporaryDirectory.cleanup, not a migration assertion: os.rmdir(project/.git), Errno 66.
- Preserved failing temp directory .git contains only empty info directory and objects/info/packs (one byte newline), timestamp 2026-10-03 00:09:34. This is consistent with a late Git server-info write recreating directories during rmtree.
- Current Git: 2.54.0 (Apple Git-157).
- Exact relevant config query git config --show-origin --get-regexp '^(maintenance|gc|core.fsmonitor)' returned no matching configuration (exit 1); defaults apply.
- tests/test_migration.py setUp performs plain git clone, then user configs. No auto maintenance controls.
- Test CLI and tools/workflow_lib/topic_service.py git helper use synchronous subprocess.run/check_output. Synchronous parent completion does not wait for a detached maintenance child.
- Default runs 1, 2, 3: all pass (~2 seconds each), but all Trace2 logs record child_start git maintenance run --auto --no-quiet --detach.
- Controlled runs 4, 5: both pass (~2 seconds each), with GIT_CONFIG_COUNT environment configuring gc.auto=0 and maintenance.auto=false for every Git invocation. Trace2 contains no maintenance/gc/repack/update-server-info child_start.

Trace logs:
/tmp/outcome-migration-cleanup-trace.json
/tmp/outcome-migration-cleanup-trace-2.json through -5.json

Conclusion: detached automatic Git maintenance is confirmed in the affected fixture path and is a credible cleanup race mechanism matching residual filesystem evidence. The actual Errno66 was not reproduced in five focused runs; we cannot prove the exact historical child process from the failing run because it had no trace. All migration assertions passed in that run and the focused matrix.

Proposed minimal repair (test fixture only):
1. In MigrationTests.setUp use git -c gc.auto=0 -c maintenance.auto=false clone ... so maintenance is disabled before clone itself.
2. After clone set local gc.auto=0 and maintenance.auto=false before any remaining Git operations, including CLI subprocesses.
3. Preserve strict TemporaryDirectory cleanup; do not ignore errors or add timing sleeps.
4. Keep production Git behavior unchanged.

Awaiting parent direction before source edits. Parent integrates checks; no further repetitions needed absent new changes.

Parent approved the fixture-only repair; implemented exactly the clone flags and two repository-local config settings in tests/test_migration.py setUp. Production helpers and TemporaryDirectory.cleanup are unchanged. No additional test executions were performed because the requested maximum-five matrix was already complete.

Executed matrix command for each run:
PYTHONPATH=tests GIT_TRACE2_EVENT=<trace-log> python3 -m unittest test_migration.MigrationTests.test_commit_failure_preserves_backup_and_allows_retry
Runs 4/5 additionally supplied GIT_CONFIG_COUNT=2, GIT_CONFIG_KEY_0=gc.auto, GIT_CONFIG_VALUE_0=0, GIT_CONFIG_KEY_1=maintenance.auto, GIT_CONFIG_VALUE_1=false.
All five exit codes were 0. Controlled trace2 logs show zero maintenance/gc/repack/update-server-info child starts. This validates the same Git configuration controls used by the source repair; the exact edited setUp awaits root's unified deploy/full-suite verification.
