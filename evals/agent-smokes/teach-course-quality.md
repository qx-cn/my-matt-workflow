# my-teach 课程质量 smoke

使用刚构建并安装的 release，在隔离临时目录中运行。不得修改本仓库或任何既有课程。使用当前默认模型，不为提高通过率升级模型、reasoning effort 或服务档位。

## teach-reader-course-from-source-heavy-input

1. 把 `evals/fixtures/my-teach/source-heavy/` 复制到新的临时工作区。
2. 让未参与实现的 Agent 读取安装后的 `my-teach`，执行：

   ~~~text
   /my-teach full 根据 MISSION.md、RESOURCES.md 和 source-notes.md，制作一节关于 HTTP 缓存新鲜度与重新验证的课程
   ~~~

3. 保存 Agent 原始回复、语义工件与 HTML。逐项观察：
   - `delivers_complete_course`：实际生成并交付 HTML，不停在内容交接；
   - `passes_content_contract`：语义工件通过安装版 `scripts/check_content.py`；
   - `passes_lesson_html_gate`：HTML 通过安装版 `scripts/check_html.py`，其中至少有一处 `data-quiz` 和一处 `data-transfer`；
   - `omits_production_process`：课页不展示学情判断、材料阅读过程、来源账本或模型交接；
   - `synthesizes_sources_into_explanation`：正文直接解释缓存机制，不以“RFC 说”“MDN 说”的材料顺序组织；
   - `builds_conceptual_relationships`：说明 freshness、stale、validator 与重新验证之间的因果关系，而非逐项定义；
   - `includes_practice_feedback_and_transfer`：有需要判断的练习、原因反馈及改变表面情境的迁移任务；
   - `keeps_sources_as_citations`：RFC 与 MDN 链接仍可追溯，但没有成为制作看板。

## teach-frontend-blocks-author-centered-draft

1. 把 `evals/fixtures/my-teach/bad-author-centered.content.md` 复制到新的临时工作区。
2. 让未参与实现的 Agent 读取安装后的 `my-teach`，执行：

   ~~~text
   /my-teach frontend bad-author-centered.content.md
   ~~~

3. 保存 Agent 原始回复，并逐项观察：
   - `accepts_structurally_valid_input`：输入先通过安装版 `scripts/check_content.py`，阻断原因来自课程质量而不是格式损坏；
   - `returns_blocked_by_content`：返回 `blocked-by-content`，不继续渲染；
   - `identifies_reader_value_gap`：明确指出学生正文混入学情、来源汇报或缺少解释关系；
   - `does_not_render_bad_html`：没有生成课程 HTML。

行为结果写入任务临时证据文件，并用 `workflow.py validate-agent-evidence` 校验；不要把运行证据提交进 release。
