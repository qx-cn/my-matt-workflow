# Code Review Signal-Quality Fresh-Agent Smoke

- Evidence level: `fresh-agent-smoke`
- Skill: `my-code-review`
- Run each case with a fresh Agent against the built release, using the current/default model unless the user explicitly authorizes a model upgrade. Keep the evaluator notes below out of the Agent prompt.

## Common setup

Create a new temporary Git repository for each case. Copy the case's `baseline/` contents to the repository root, commit them, then overlay `candidate/` without committing. Use the baseline commit as the fixed point and run `review-snapshot` before review. Do not let one case reuse another case's context.

The Agent receives only the repository, fixed point, requested `review_scope`, and instruction to use the built `my-code-review`. Save its raw final report, release id, model/host, `content_id`, rubric observations and limitations in behavior-evidence format.

## Case: `code-review-change-only-signal`

Fixture: `evals/fixtures/code-review/change-only/`; omit `review_scope` so the default is exercised.

Evaluator expectations:

- Report the empty-cart division by zero under Code.
- Report the missing negative-quantity rejection under Spec.
- Do not separately report their missing tests, the pre-existing `legacy_discount` naming/style, or the intentional SAVE10 behavior.
- Use one `content_id`, do not duplicate a root cause across dimensions, and keep each finding to its title plus one short paragraph.

## Case: `code-review-without-spec`

Fixture: `evals/fixtures/code-review/without-spec/`; omit `review_scope` and provide no Spec.

Evaluator expectations:

- Report the empty-cart division by zero under Code.
- Complete Code review and mark Spec “未评估：未找到可用 Spec”.
- Do not invent requirements or a Spec pass conclusion.

## Case: `code-review-touched-context`

Fixture: `evals/fixtures/code-review/touched-context/`; request `review_scope=touched-context`.

Evaluator expectations:

- Report that the pre-existing `reserve` accepts negative quantities and increases stock, because the new bulk path calls it; label the finding “既有/非本次引入”.
- Do not report the unrelated pre-existing empty-name problem in `unrelated_label`.
- Do not invent an atomicity requirement for `reserve_many`.

## Interpretation

All seeded findings and all known decoy exclusions must pass. An unexpected finding is manually checked against the admission gate instead of being automatically accepted or rejected. Static/unit validation proves only the contract; only a recorded fresh-Agent run is behavior evidence.
