# Main Workflow Fresh-Agent Smoke

- Evidence level: `fresh-agent-smoke`
- Scope: `my-to-spec → my-to-tickets → my-implement → my-test-report`
- Exclusion: interactive `my-grill-with-docs` is represented by an already-confirmed requirements handoff; this case does not claim to test interview quality.

## Isolation

Create a new temporary directory, copy `evals/fixtures/main-workflow/` into it, initialize a Git repository, and commit the fixture as the baseline. All generated Spec, Ticket, code, reports, commits and configuration must stay in that temporary repository. Do not access an external Tracker or edit the workflow source repository.

## Request

Treat `requirements.md` as the complete, user-confirmed result of requirements elicitation. Use the built release's `my-to-spec`, `my-to-tickets`, `my-implement` and `my-test-report` instructions to complete the change. A single vertical implementation Ticket is pre-approved. Local document writes, a temporary branch and commits inside the isolated repository are authorized. Run the actual tests and preserve their exit result. Do not ask the evaluator to repeat decisions already present in `requirements.md`.

## Pass rubric

- A versioned Spec is created with `spec_id`, `revision` and `supersedes`.
- The Ticket records `spec_id`, `spec_revision` and `spec_ref`, and passes the runtime `validate-ticket` gate.
- The implementation satisfies all requirements and tests pass.
- Review evidence identifies the complete working-tree change rather than relying only on committed `HEAD`.
- The test report distinguishes requirements, executed evidence, untested items and conclusion without inventing results.
- The final response identifies generated artifact paths and any evidence limitation.

Record the release id, host/model, temporary repository, raw final response, pass/fail per rubric item and cleanup status in `.agent/work/workflow-optimization/fresh-agent-smoke.md`.
