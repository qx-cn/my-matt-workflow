# prototype audit evidence

## Pinned source and file accounting

- Pinned commit: `2ab958093e83e0ec752e6c1c5932da465bf23e0c`
- Canonical source path: `skills/engineering/prototype`
- Local counterpart: `skills/my-prototype`

| File | Source SHA-256 | Local SHA-256 |
| --- | --- | --- |
| `LOGIC.md` | `cf372862bccd3db7f18ea57abd76d6c32e6adf65b9e7f46c73d433e107567a5c` | `7949b2624159bdc2ebb8d1e1c00de22cdd9d1ca6409b137f8dab320f77a595be` |
| `SKILL.md` | `03074862d4b6e4eaf472aa75146e1d193dd9e3bba0e4303a9b2425562d1d44cc` | `fdc4a4fc6e4bf46090b8ba3d4c3aa7a44c8562a868bf06669d315a8b83db14c9` |
| `UI.md` | `e2ca04434be54acdee2f5df582ef8038fadf582bbcc99be0d2e27737ff8ed096` | `e8869abc5a4e7a619a903ebe52c6fa9915696499e1dc659df439ea3d86c968b1` |
| `agents/openai.yaml` | `5af65e43ab41a350436697b81e27b7f848d36782043b73c322bb2c9fa9cc55dc` | `6b2d4fa3345bda08b144147a563dafeb1e42d7bd47898d1c21f1493845f22d6a` |

## Section/source-local mapping

The audited source sections and their local counterparts are:

| Pinned upstream section | Local counterpart |
| --- | --- |
| `LOGIC.md#Logic Prototype` | `LOGIC.md#逻辑原型` |
| `LOGIC.md#When this is the right shape` | `LOGIC.md#适用情形` |
| `LOGIC.md#Process` | `LOGIC.md#过程` |
| `LOGIC.md#1. State the question` | `LOGIC.md#1. 写明问题` |
| `LOGIC.md#2. Pick the language` | `LOGIC.md#2. 选择语言` |
| `LOGIC.md#3. Isolate the logic in a portable module` | `LOGIC.md#3. 将逻辑隔离为可移植模块` |
| `LOGIC.md#4. Build the smallest TUI that exposes the state` | `LOGIC.md#4. 构建展示状态的最小 TUI` |
| `LOGIC.md#5. Make it runnable in one command` | `LOGIC.md#5. 保证一条命令可运行` |
| `LOGIC.md#6. Hand it over` | `LOGIC.md#6. 交给用户` |
| `LOGIC.md#7. Capture the answer and the prototype` | `LOGIC.md#7. 捕获结论和原型` |
| `LOGIC.md#Anti-patterns` | `LOGIC.md#反模式` |
| `SKILL.md#Prototype` | `SKILL.md#My Prototype` |
| `SKILL.md#Pick a branch` | `SKILL.md#选择分支` |
| `SKILL.md#Rules that apply to both` | `SKILL.md#两个分支都适用的规则` |
| `UI.md#UI Prototype` | `UI.md#UI 原型` |
| `UI.md#When this is the right shape` | `UI.md#适用情形` |
| `UI.md#Two sub-shapes — strongly prefer sub-shape A` | `UI.md#两种子形态——强烈优先 A` |
| `UI.md#Sub-shape A — adjustment to an existing page (preferred)` | `UI.md#子形态 A——调整现有页面（首选）` |
| `UI.md#Sub-shape B — a new page (last resort)` | `UI.md#子形态 B——新页面（最后手段）` |
| `UI.md#Process` | `UI.md#过程` |
| `UI.md#1. State the question and pick N` | `UI.md#1. 写明问题并选择 N` |
| `UI.md#2. Generate radically different variants` | `UI.md#2. 生成根本不同的变体` |
| `UI.md#3. Wire them together` | `UI.md#3. 将它们接在一起` |
| `UI.md#4. Build the floating switcher` | `UI.md#4. 构建悬浮切换器` |
| `UI.md#5. Hand it over` | `UI.md#5. 交给用户` |
| `UI.md#6. Capture the answer and clean up` | `UI.md#6. 捕获答案并清理` |
| `UI.md#Anti-patterns` | `UI.md#反模式` |
| `agents/openai.yaml#interface` | `agents/openai.yaml#interface` |

The source body was compared section-by-section, including examples, ordering, constraints, stop conditions, frontmatter/runtime metadata, and all listed support files. Metadata interface fields are accounted for separately from local policy metadata.

## Delta, allowed adaptation, and conclusion

- Allowed local adaptation: a renamed manual-invocation Skill may retain repository-specific metadata only when it does not alter the upstream method.
- Material delta: The local storage and capture policy replace the upstream required throwaway-branch commit with policy-controlled retention and must retain the no-production/prototype boundary.
- Conclusion: **adapter-rework-required**.
- Exact follow-up queue: **Plan 2 — `my-prototype` adapter rework**; this audit does not restore or refactor the Skill.

## Retrieval/application scenario

`tests/fixtures/task_12_application.json` defines `prototype-application`. It retrieves `SKILL.md#My Prototype`, verifies `原型是**回答一个问题的可抛弃代码**` within that exact heading, and independently derives `build-throwaway-answer` only when the retrieved constraint is present.
