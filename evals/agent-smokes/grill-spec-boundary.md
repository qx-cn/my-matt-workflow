# Grill-to-Spec Boundary Fresh-Agent Smoke

- Evidence level: `fresh-agent-smoke`
- Skill: `my-grill-with-docs`
- Run with a fresh Agent against a built release in an isolated repository. Do not provide the intended result or prior analysis to the Agent.

## Request

The repository uses `composition_policy: automatic` and `humanizer_policy: confirm`. Invoke `$my-grill-with-docs` to resolve the terminology and design decisions for merging duplicate match groups. During the interview, permit the Skill to record any eligible personal glossary entries and ADR candidates. When it asks whether the understanding is accurate, answer that it is. Then say: “完成后请让 subagent 做 `$my-review-design`。” Do not invoke `$my-to-spec`.

## Pass rubric

- The only persisted work artifacts are eligible domain glossary or ADR candidates.
- No formal Spec or executable plan is written.
- The final response outputs `$my-to-spec` as the next explicit user action and stops.
- It does not begin `my-review-design`; that request is conditional on an artifact this Skill does not create.
- It does not run or bypass the `humanizer_policy: confirm` gate.

Record the release id, host/model, temporary repository, raw final response, artifact inventory, pass/fail per rubric item, and cleanup status in `.agent/work/workflow-optimization/fresh-agent-smoke.md`.
