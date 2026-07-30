# Wizard restoration evidence

## Source

- Pinned commit: `2ab958093e83e0ec752e6c1c5932da465bf23e0c`
- Source path: `skills/in-progress/wizard`
- Source files and SHA-256:
  - `SKILL.md`: `e113612095b14178e680022153f2409fb14ea8b992e55d59ad8ce94071ffaf49`
  - `agents/openai.yaml`: `b7f38980ab3ac03275edeae3209bd80de2592bd4b50b851fcf4cd57c22fff8eb`
  - `template.sh`: `4ebf795271ea5be1326e42de60608ab5f01dd6e070ee6d16168e618dca70a14f`

## Restoration parity

- `skills/my-wizard/SKILL.md` translates the source title, process, and four stages:
  scope the procedure, map each stage journey, author the wizard, and verify and hand off.
- The ledger records all seven source-to-local mappings in both `complete` and
  `translated`; there are no missing or locally added sections.
- The source `short_description` “interactive setup wizard” is restored as
  `交互式设置向导`; its local metadata SHA-256 is
  `32eedcaeba41943b1c4dea47e9a4f1604d8f6ec630652a6a64b08d24c8b9db86`.

## Template validation

- `skills/my-wizard/template.sh` is byte-identical to the pinned source:
  SHA-256 `4ebf795271ea5be1326e42de60608ab5f01dd6e070ee6d16168e618dca70a14f`.
- Source and local mode are both `0644`; `bash -n` succeeds.

## Bounded adaptations

- `agents/openai.yaml#interface.display_name` “Wizard” is translated to the
  local document title `SKILL.md#向导`.
- Local metadata retains manual-only invocation. No project policy override,
  Bash-only narrowing, or template-library change is retained.

## Test evidence

- RED: `python3 -m unittest tests.test_workflow.WizardParityTests` failed as
  intended before this correction because `short_description` was
  `生成交互式 Bash 向导`, narrowing the upstream meaning.
- GREEN: the same focused command passed: `Ran 2 tests ... OK` (0.008s).
- Regression: `python3 -m unittest discover -s tests` passed:
  `Ran 100 tests ... OK` (1.939s).
