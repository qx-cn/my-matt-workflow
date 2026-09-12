# Implementation Turn-Closure Fresh-Agent Smoke

- Evidence level: `fresh-agent-smoke`
- Skill: `my-implement`
- Run with a fresh Agent against a built release in an isolated repository. Do not provide the intended result, this diagnosis, or evaluator conclusions to the Agent.

## Isolation

Copy `evals/fixtures/my-implement/unfinished-session/` to a temporary Git repository and commit it as the baseline. It contains a profile, Spec, two valid implementation Tickets, code, tests and a deterministic local reviewer. Before giving the request to the Agent, use the built release runtime to open `tickets-turn-closure-01.md` at the baseline SHA with `app.py` and `review.py` as paths, then record its `implementing` phase. Give the Agent the resulting journal path. The fixture's focused trimming test passes; the full suite fails until the remaining acceptance item is implemented. Do not change the workflow source repository or use an external service.

## Request

Use the built release's `my-implement` instructions to continue the supplied implementation. A prior worker reports that the focused test has passed and asks to provide a progress update. Local edits and tests in the temporary repository are authorized. The Agent must use the supplied runtime journal to create real code, test and review receipts, submit and close the first Ticket, then run `next-ticket` for feature `turn-closure`; do not supply a synthetic runtime transcript.

## Pass rubric

- With the fixture's active journal, the Agent may report progress through commentary but 不得发送 final and continues implementation toward runtime receipts and closure.
- When a completed Ticket's `next-ticket` response is `continue`, the Agent starts the returned Ticket rather than ending the task.
- When a single Ticket is closed and `next-ticket` returns `complete`, the Agent may final with the registered delivery evidence.
- In a separate run, drive the fixture through the runtime's real repair-limit path until it registers `blocked-by-review`; the Agent may final only after stating the blocker, registered evidence and minimal recovery condition.

Record the release id, host/model, temporary repository, raw final response, runtime transcript, pass/fail per rubric item and cleanup status in the fresh-agent evidence record. A source `check` validates this runbook's shape only; it does not prove this behavior was run.
