# Plan 1B / Task 12 audit report

## Scope and source

- Pinned commit: `2ab958093e83e0ec752e6c1c5932da465bf23e0c`
- Audited in required dependency order; no Skill source document was restored or refactored.
- Initial population test: failed as expected for all 11 unreviewed entries.

## Conclusions

### code-review
- Canonical source: `skills/engineering/code-review`
- Conclusion: **adapter-rework-required**.
- Evidence: `upstream/evidence/code-review-audit.md`.
- Scenario: `code-review-application` resolves `SKILL.md#1. 固定基线` and derives `validate-fixed-point`.
- Follow-up: Plan 2 — `my-code-review` adapter rework.
- Concern: The local fallback to an implementation-start record and policy-controlled parallelism can bypass the upstream requirement to ask for an omitted fixed point and to run both independent review axes.

### ask-matt
- Canonical source: `skills/engineering/ask-matt`
- Conclusion: **adapter-rework-required**.
- Evidence: `upstream/evidence/ask-matt-audit.md`.
- Scenario: `ask-matt-application` resolves `SKILL.md#上下文卫生` and derives `handoff-before-degradation`.
- Follow-up: Plan 2 — `my-ask-matt` adapter rework.
- Concern: The local router adds workflow-specific entrances and composition policy dispatch; its policy footer can weaken the upstream uninterrupted-context and explicit-stop guidance.

### diagnosing-bugs
- Canonical source: `skills/engineering/diagnosing-bugs`
- Conclusion: **adapter-rework-required**.
- Evidence: `upstream/evidence/diagnosing-bugs-audit.md`.
- Scenario: `diagnosing-bugs-application` resolves `SKILL.md#确实无法建立循环时` and derives `stop-before-hypothesis`.
- Follow-up: Plan 2 — `my-diagnosing-bugs` adapter rework.
- Concern: The local autonomous limited-evidence mode permits work after the upstream hard no-loop stop condition, so the adapter must be bounded.

### handoff
- Canonical source: `skills/productivity/handoff`
- Conclusion: **adapter-rework-required**.
- Evidence: `upstream/evidence/handoff-audit.md`.
- Scenario: `handoff-application` resolves `SKILL.md#My Handoff` and derives `reference-existing-artifacts`.
- Follow-up: Plan 2 — `my-handoff` adapter rework.
- Concern: The local project-directory ownership and filename convention replace the upstream OS-temporary-directory destination and add policy-controlled behavior.

### edit-article
- Canonical source: `skills/personal/edit-article`
- Conclusion: **adapter-rework-required**.
- Evidence: `upstream/evidence/edit-article-audit.md`.
- Scenario: `edit-article-application` resolves `SKILL.md#编辑文章` and derives `rewrite-with-paragraph-limit`.
- Follow-up: Plan 2 — `my-edit-article` adapter rework.
- Concern: The local default-new-draft and approval flow extend the upstream article-editing process; the unbounded policy footer can weaken its section-confirmation gate.

### resolving-merge-conflicts
- Canonical source: `skills/engineering/resolving-merge-conflicts`
- Conclusion: **adapter-rework-required**.
- Evidence: `upstream/evidence/resolving-merge-conflicts-audit.md`.
- Scenario: `resolving-merge-conflicts-application` resolves `SKILL.md#安全解决冲突` and derives `wait-for-approval`.
- Follow-up: Plan 2 — `my-resolving-merge-conflicts` adapter rework.
- Concern: The local approval-first and destructive-command safeguards intentionally change the upstream always-resolve/finish-merge behavior and require an explicit adapter boundary.

### to-tickets
- Canonical source: `skills/engineering/to-tickets`
- Conclusion: **adapter-rework-required**.
- Evidence: `upstream/evidence/to-tickets-audit.md`.
- Scenario: `to-tickets-application` resolves `SKILL.md#3. 起草纵向切片` and derives `draft-vertical-slices`.
- Follow-up: Plan 2 — `my-to-tickets` adapter rework.
- Concern: The local backend-specific paths, confirmation gates, and humanizer step replace the upstream tracker contract and must preserve the vertical-slice and blocking-edge method.

### to-spec
- Canonical source: `skills/engineering/to-spec`
- Conclusion: **adapter-rework-required**.
- Evidence: `upstream/evidence/to-spec-audit.md`.
- Scenario: `to-spec-application` resolves `SKILL.md#document-body` and derives `synthesize-without-interview`.
- Follow-up: Plan 2 — `my-to-spec` adapter rework.
- Concern: The local backend and external-write policy add routing behavior; its policy footer can change the upstream seam-confirmation and publication sequence.

### research
- Canonical source: `skills/engineering/research`
- Conclusion: **adapter-rework-required**.
- Evidence: `upstream/evidence/research-audit.md`.
- Scenario: `research-application` resolves `SKILL.md#My Research` and derives `use-primary-sources`.
- Follow-up: Plan 2 — `my-research` adapter rework.
- Concern: The local workflow omits the upstream mandatory background-agent delegation and adds data-handling and writeback constraints.

### prototype
- Canonical source: `skills/engineering/prototype`
- Conclusion: **adapter-rework-required**.
- Evidence: `upstream/evidence/prototype-audit.md`.
- Scenario: `prototype-application` resolves `SKILL.md#My Prototype` and derives `build-throwaway-answer`.
- Follow-up: Plan 2 — `my-prototype` adapter rework.
- Concern: The local storage and capture policy replace the upstream required throwaway-branch commit with policy-controlled retention and must retain the no-production/prototype boundary.

### wayfinder
- Canonical source: `skills/engineering/wayfinder`
- Conclusion: **adapter-rework-required**.
- Evidence: `upstream/evidence/wayfinder-audit.md`.
- Scenario: `wayfinder-application` resolves `SKILL.md#规划，而不是交付` and derives `plan-not-deliver`.
- Follow-up: Plan 2 — `my-wayfinder` adapter rework.
- Concern: The local local-markdown tracker fallback and policy-controlled subagent/transition behavior adapt upstream tracker operations and require bounded preservation of one-ticket and decision-only stops.

## Verification

- Initial focused population test: failed as expected with 11 unreviewed entries.
- Focused audit tests: `python3 -m unittest tests.test_workflow.Task12AuditPopulationTests` — **11 passed**.
- Final full suite (run once after all audits): `python3 -m unittest discover -s tests` — **115 passed**.
