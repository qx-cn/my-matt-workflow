# Doctor source validation scope repair

Changed only:
- tools/workflow_lib/validator.py
- tests/test_validator_markdown_scope.py (new)

Root cause: live-source Markdown validation traversed .agent/work mutable Topic state, preserved raw review evidence and embedded synthetic repositories, while stable build snapshots omit this runtime subtree. Their absolute expired review paths and fixture-relative links produced false source-invalid results.

Minimal repair: skip Markdown files only under the repository-root .agent/work subtree. Preserve all existing Markdown link checks everywhere else, including .agent/matt-workflow.md, future .agent/policy.md, .agent/archive documents, ordinary docs, and tests/fixtures documentation. Nested docs/.agent remains in scope. Existing skills handling and missing/escape rejection are unchanged. No historical Spec, Ticket, reports or runtime data bytes were edited.

Verification:
- python3 -m unittest tests.test_validator_markdown_scope: 2 tests passed (14 bad-link subcases plus successful exclusion/current source configuration case).
- validate_repository(Path.cwd()): passed, {'skills': 32, 'scripts': 2}.

No build, install, or full suite performed; root agent integrates and performs those checks.
